"""Rule-based P1 skill for standard field mapping recommendations."""

from dataclasses import dataclass

from pydantic import BaseModel, Field

from app.core.knowledge.knowledge_loader import load_standard_fields
from app.core.models.issue import Issue
from app.core.models.mapping_result import MappingResult, UnmappedField
from app.core.models.mapping_review_record import MappingReviewRecord
from app.core.models.table_meta import TableMeta
from app.core.normalize import (
    clean_text,
    expand_tokens_with_evidence,
    normalize_tokens,
    split_tokens,
)
from app.core.review.override_store import load_mapping_overrides
from app.core.review.review_service import apply_mapping_overrides_to_results
from app.core.rules.config_loader import get_issue_severity
from app.core.skills.base_skill import BaseSkill
from app.core.skills.data_standard_mapping_skill.mapping_learning import (
    LearnedStandardMapping,
    explain_standard_mapping_memory_lookup,
    load_standard_mapping_memory,
)
from app.core.skills.data_standard_mapping_skill.semantic_index import (
    SemanticFieldMatch,
    semantic_match_source_fields,
)

EMPTY_TEXT_VALUES = {"", "nan", "none", "null"}
SHARED_DOMAIN_VALUES = {"shared", "common", "global", "enterprise"}
IDENTIFIER_TOKENS = {"id", "identifier", "number", "no", "code"}
STRING_TYPE_TOKENS = {
    "char",
    "character",
    "clob",
    "nchar",
    "nvarchar",
    "string",
    "text",
    "varchar",
    "varchar2",
}
INTEGER_TYPE_TOKENS = {"bigint", "int", "integer", "long", "smallint", "tinyint"}
DECIMAL_TYPE_TOKENS = {
    "decimal",
    "double",
    "float",
    "money",
    "number",
    "numeric",
    "real",
}
DATE_TYPE_TOKENS = {"date"}
DATETIME_TYPE_TOKENS = {"datetime", "timestamp", "timestamptz"}
BOOLEAN_TYPE_TOKENS = {"bool", "boolean"}


class StandardMappingInput(BaseModel):
    """Input schema for standard mapping recommendations."""

    tables: list[TableMeta] = Field(default_factory=list)
    apply_overrides: bool = True
    override_records: list[MappingReviewRecord] = Field(default_factory=list)
    domain_pack_hints: dict = Field(default_factory=dict)


class StandardMappingOutput(BaseModel):
    """Output schema for standard mapping recommendations."""

    mapping_results: list[MappingResult] = Field(default_factory=list)
    confirmed_mapping_results: list[MappingResult] = Field(default_factory=list)
    unmapped_fields: list[UnmappedField] = Field(default_factory=list)
    issues: list[Issue] = Field(default_factory=list)
    review_applied_count: int = 0
    summary: str = ""


@dataclass
class StandardCandidate:
    """Lightweight prepared standard-field record."""

    standard_code: str
    standard_name: str
    standard_name_cn: str | None
    description: str | None
    data_type: str | None
    data_length: str | None
    value_domain: str | None
    business_domain: str | None
    aliases: list[str]
    normalized_name: str
    normalized_tokens: list[str]
    expanded_tokens: list[str]
    alias_lookup: list[str]
    alias_token_groups: list[list[str]]
    context_tokens: list[str]


class StandardMappingRecommendationSkill(BaseSkill):
    """Recommend standard fields using explainable knowledge-pack rules."""

    skill_name = "standard_mapping_recommendation"
    version = "0.4.0"
    description = "P1 standard field recommendation using local knowledge packs and optional semantic retrieval."

    @staticmethod
    def _optional_text(value: object) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        if not text or text.lower() in EMPTY_TEXT_VALUES:
            return None
        return text

    @staticmethod
    def _normalize_domain(value: object) -> str:
        text = StandardMappingRecommendationSkill._optional_text(value)
        return clean_text(text) if text else ""

    @staticmethod
    def _normalize_data_type(value: object) -> str:
        text = StandardMappingRecommendationSkill._optional_text(value)
        if text is None:
            return ""
        base_type = clean_text(text.split("(", 1)[0])
        if base_type in STRING_TYPE_TOKENS:
            return "string"
        if base_type in INTEGER_TYPE_TOKENS:
            return "integer"
        if base_type in DECIMAL_TYPE_TOKENS:
            return "decimal"
        if base_type in DATETIME_TYPE_TOKENS:
            return "datetime"
        if base_type in DATE_TYPE_TOKENS:
            return "date"
        if base_type in BOOLEAN_TYPE_TOKENS:
            return "boolean"
        return base_type

    @staticmethod
    def _types_compatible(field_type: str, standard_type: str) -> bool:
        if not field_type or not standard_type:
            return True
        if field_type == standard_type:
            return True
        if field_type == "datetime" and standard_type == "date":
            return True
        if field_type == "integer" and standard_type == "decimal":
            return True
        return False

    @staticmethod
    def _domains_compatible(field_domain: str, standard_domain: str) -> bool:
        if not field_domain or not standard_domain:
            return True
        if field_domain == standard_domain:
            return True
        return field_domain in SHARED_DOMAIN_VALUES or standard_domain in SHARED_DOMAIN_VALUES

    @staticmethod
    def _text_tokens(*values: object) -> list[str]:
        tokens: list[str] = []
        for value in values:
            text = StandardMappingRecommendationSkill._optional_text(value)
            if text:
                tokens.extend(split_tokens(text))
        return normalize_tokens(tokens)

    @staticmethod
    def normalize_field_for_matching(
        field_name: str,
        field_name_cn: str | None = None,
    ) -> dict[str, object]:
        """Normalize field metadata into match-friendly tokens."""
        cleaned_name = clean_text(field_name, lower=False)
        original_tokens = split_tokens(cleaned_name)
        expanded_tokens, expanded_pairs, expansion_evidence = expand_tokens_with_evidence(
            original_tokens
        )
        normalized_token_list = normalize_tokens(expanded_tokens)
        normalized_name = "_".join(normalized_token_list)
        cn_text = clean_text(field_name_cn or "")
        return {
            "normalized_name": normalized_name,
            "original_tokens": original_tokens,
            "expanded_tokens": expanded_tokens,
            "normalized_tokens": normalized_token_list,
            "expanded_pairs": expanded_pairs,
            "expansion_evidence": expansion_evidence,
            "cleaned_cn_name": cn_text,
        }

    @classmethod
    def build_field_context(cls, table: TableMeta, field: object) -> dict[str, object]:
        """Build match context from field, table, domain, type, and sample metadata."""
        field_info = cls.normalize_field_for_matching(
            getattr(field, "field_name", ""),
            getattr(field, "field_name_cn", None),
        )
        field_domain = cls._normalize_domain(
            getattr(field, "business_domain", None) or table.business_domain
        )
        table_domain = cls._normalize_domain(table.business_domain)
        data_type = cls._normalize_data_type(getattr(field, "data_type", None))
        context_tokens = cls._text_tokens(
            table.table_name,
            table.table_name_cn,
            table.table_description,
            field_domain,
            table_domain,
            getattr(field, "field_description", None),
            getattr(field, "sample_values", None),
        )
        field_info.update(
            {
                "table_name": table.table_name,
                "table_description": table.table_description,
                "table_business_domain": table_domain,
                "field_business_domain": field_domain,
                "effective_business_domain": field_domain or table_domain,
                "data_type": data_type,
                "raw_data_type": getattr(field, "data_type", None),
                "data_length": cls._optional_text(getattr(field, "data_length", None)),
                "sample_values": cls._optional_text(getattr(field, "sample_values", None)),
                "field_description": cls._optional_text(
                    getattr(field, "field_description", None)
                ),
                "context_tokens": context_tokens,
                "existing_standard_code": cls._optional_text(
                    getattr(field, "standard_code", None)
                ),
                "existing_standard_name": cls._optional_text(
                    getattr(field, "standard_name", None)
                ),
            }
        )
        return field_info

    @classmethod
    def _prepare_standard_candidates(cls) -> list[StandardCandidate]:
        dataframe = load_standard_fields()
        candidates: list[StandardCandidate] = []

        for _, row in dataframe.iterrows():
            standard_name = str(row["standard_name"]).strip()
            normalized = cls.normalize_field_for_matching(
                standard_name,
                str(row["standard_name_cn"]).strip()
                if str(row["standard_name_cn"]).strip().lower() != "nan"
                else None,
            )
            aliases = [
                alias.strip()
                for alias in str(row["aliases"]).split(";")
                if alias and alias.strip() and str(alias).strip().lower() != "nan"
            ]
            alias_lookup = []
            alias_token_groups = []
            for alias in aliases:
                normalized_alias = cls.normalize_field_for_matching(alias)
                normalized_alias_name = str(normalized_alias["normalized_name"])
                normalized_alias_tokens = list(normalized_alias["normalized_tokens"])
                alias_lookup.append(alias.lower())
                alias_lookup.append(normalized_alias_name)
                if normalized_alias_tokens:
                    alias_token_groups.append(normalized_alias_tokens)

            candidates.append(
                StandardCandidate(
                    standard_code=str(row["standard_code"]).strip(),
                    standard_name=standard_name,
                    standard_name_cn=(
                        str(row["standard_name_cn"]).strip()
                        if str(row["standard_name_cn"]).strip().lower() != "nan"
                        else None
                    ),
                    description=(
                        str(row["description"]).strip()
                        if str(row["description"]).strip().lower() != "nan"
                        else None
                    ),
                    data_type=cls._optional_text(row.get("data_type")),
                    data_length=cls._optional_text(row.get("data_length")),
                    value_domain=cls._optional_text(row.get("value_domain")),
                    business_domain=cls._optional_text(row.get("business_domain")),
                    aliases=aliases,
                    normalized_name=normalized["normalized_name"],
                    normalized_tokens=list(normalized["normalized_tokens"]),
                    expanded_tokens=list(normalized["expanded_tokens"]),
                    alias_lookup=list(dict.fromkeys(alias_lookup)),
                    alias_token_groups=[
                        list(tokens)
                        for tokens in dict.fromkeys(
                            tuple(tokens) for tokens in alias_token_groups
                        )
                    ],
                    context_tokens=cls._text_tokens(
                        standard_name,
                        row.get("standard_name_cn"),
                        row.get("description"),
                        row.get("business_domain"),
                        "; ".join(aliases),
                    ),
                )
            )

        return candidates

    @staticmethod
    def compute_match_score(
        field_info: dict[str, object],
        candidate: StandardCandidate,
    ) -> tuple[float, list[str]]:
        """Compute an explainable score between a field and one standard candidate."""
        score = 0.0
        reasons: list[str] = []
        normalized_name = str(field_info["normalized_name"])
        normalized_tokens = list(field_info["normalized_tokens"])
        expanded_tokens = list(field_info["expanded_tokens"])
        cleaned_cn_name = str(field_info["cleaned_cn_name"])
        field_type = str(field_info.get("data_type") or "")
        standard_type = StandardMappingRecommendationSkill._normalize_data_type(
            candidate.data_type
        )
        field_domain = str(field_info.get("effective_business_domain") or "")
        standard_domain = StandardMappingRecommendationSkill._normalize_domain(
            candidate.business_domain
        )
        context_tokens = list(field_info.get("context_tokens", []))
        normalized_token_set = set(normalized_tokens)
        context_token_set = set(context_tokens)

        if normalized_name and normalized_name == candidate.standard_name.lower():
            score += 1.0
            reasons.append("exact standard_name match after normalization")

        if normalized_name and normalized_name == candidate.normalized_name:
            score += 0.9
            reasons.append("exact normalized token match")

        if normalized_tokens and normalized_tokens == candidate.normalized_tokens:
            score += 0.75
            reasons.append("normalized token sequence match")

        if expanded_tokens and expanded_tokens == candidate.expanded_tokens:
            score += 0.6
            reasons.append("expanded token sequence match")

        if normalized_name and normalized_name in candidate.alias_lookup:
            score += 0.7
            reasons.append("matched standard alias after normalization")

        for alias_tokens in candidate.alias_token_groups:
            alias_token_set = set(alias_tokens)
            if (
                not alias_token_set
                or not alias_token_set.issubset(normalized_token_set)
            ):
                continue
            field_qualifiers = normalized_token_set.difference(alias_token_set)
            if not field_qualifiers:
                continue
            score += 0.35
            reasons.append(
                "standard alias tokens matched within field name "
                f"alias_tokens={sorted(alias_token_set)} "
                f"field_qualifiers={sorted(field_qualifiers)}"
            )
            context_qualifiers = field_qualifiers.intersection(context_token_set)
            if context_qualifiers:
                score += 0.15
                reasons.append(
                    "field qualifier tokens are supported by table context "
                    f"context_tokens={sorted(context_qualifiers)}"
                )
            break

        if cleaned_cn_name and candidate.standard_name_cn:
            standard_cn = clean_text(candidate.standard_name_cn)
            if cleaned_cn_name in standard_cn or standard_cn in cleaned_cn_name:
                score += 0.5
                reasons.append("field_name_cn matched standard_name_cn by text inclusion")

        overlap = set(normalized_tokens).intersection(candidate.normalized_tokens)
        if overlap:
            score += min(0.4, 0.1 * len(overlap))
            reasons.append(f"shared normalized tokens={sorted(overlap)}")

        field_identifier_tokens = set(normalized_tokens).intersection(IDENTIFIER_TOKENS)
        candidate_identifier_tokens = set(candidate.normalized_tokens).intersection(
            IDENTIFIER_TOKENS
        )
        shared_business_tokens = (
            set(normalized_tokens)
            .intersection(candidate.normalized_tokens)
            .difference(IDENTIFIER_TOKENS)
        )
        if field_identifier_tokens and candidate_identifier_tokens and shared_business_tokens:
            score += 0.45
            reasons.append(
                "identifier-style token alignment "
                f"shared_business_tokens={sorted(shared_business_tokens)}"
            )

        context_overlap = (
            set(context_tokens)
            .intersection(candidate.context_tokens)
            .difference(IDENTIFIER_TOKENS)
        )
        if context_overlap:
            score += min(0.12, 0.04 * len(context_overlap))
            reasons.append(f"table/domain context tokens={sorted(context_overlap)}")

        if field_type and standard_type:
            if StandardMappingRecommendationSkill._types_compatible(
                field_type,
                standard_type,
            ):
                score += 0.12
                reasons.append(
                    f"data type compatible field={field_type} standard={standard_type}"
                )
            else:
                score -= 0.25
                reasons.append(
                    f"data type conflict field={field_type} standard={standard_type}"
                )

        if field_domain and standard_domain:
            if StandardMappingRecommendationSkill._domains_compatible(
                field_domain,
                standard_domain,
            ):
                score += 0.1
                reasons.append(
                    f"business domain compatible field={field_domain} standard={standard_domain}"
                )
            else:
                score -= 0.15
                reasons.append(
                    f"business domain mismatch field={field_domain} standard={standard_domain}"
                )

        field_length = StandardMappingRecommendationSkill._optional_text(
            field_info.get("data_length")
        )
        standard_length = StandardMappingRecommendationSkill._optional_text(
            candidate.data_length
        )
        if field_length and standard_length:
            if field_length == standard_length:
                score += 0.04
                reasons.append(f"data length matched length={field_length}")
            else:
                score -= 0.04
                reasons.append(
                    f"data length differs field={field_length} standard={standard_length}"
                )

        return round(score, 2), reasons

    @classmethod
    def rank_standard_candidates(
        cls,
        field_info: dict[str, object],
        candidates: list[StandardCandidate],
    ) -> list[tuple[StandardCandidate, float, list[str]]]:
        """Rank standard candidates for one field."""
        scored: list[tuple[StandardCandidate, float, list[str]]] = []
        for candidate in candidates:
            score, reasons = cls.compute_match_score(field_info, candidate)
            if score > 0:
                scored.append((candidate, score, reasons))

        scored.sort(
            key=lambda item: (item[1], len(item[2]), item[0].standard_code),
            reverse=True,
        )
        return scored

    @staticmethod
    def _semantic_match_lookup(
        semantic_match: SemanticFieldMatch | None,
    ) -> dict[str, object]:
        if semantic_match is None or not semantic_match.enabled:
            return {}
        return {
            match.standard_code: match
            for match in semantic_match.top_matches
        }

    @classmethod
    def rank_standard_candidates_with_semantics(
        cls,
        field_info: dict[str, object],
        candidates: list[StandardCandidate],
        semantic_match: SemanticFieldMatch | None = None,
    ) -> list[tuple[StandardCandidate, float, list[str]]]:
        """Rank standard candidates by combining rules and optional semantic retrieval."""
        rule_ranked = cls.rank_standard_candidates(field_info, candidates)
        ranked_lookup: dict[str, tuple[StandardCandidate, float, list[str]]] = {
            candidate.standard_code: (candidate, score, list(reasons))
            for candidate, score, reasons in rule_ranked
        }
        candidate_lookup = {candidate.standard_code: candidate for candidate in candidates}
        semantic_lookup = cls._semantic_match_lookup(semantic_match)

        if semantic_match is not None and semantic_match.enabled:
            for standard_code, match in semantic_lookup.items():
                candidate = candidate_lookup.get(standard_code)
                if candidate is None:
                    continue

                semantic_score = round(float(match.score), 2)
                semantic_reason = (
                    "semantic embedding cosine similarity "
                    f"{semantic_score:.2f} >= threshold {semantic_match.threshold:.2f}"
                    if semantic_score >= semantic_match.threshold
                    else f"semantic embedding cosine similarity {semantic_score:.2f}"
                )
                existing = ranked_lookup.get(standard_code)
                if existing is None:
                    ranked_lookup[standard_code] = (
                        candidate,
                        semantic_score,
                        [semantic_reason],
                    )
                    continue

                _, rule_score, reasons = existing
                combined_score = max(rule_score, semantic_score)
                ranked_lookup[standard_code] = (
                    candidate,
                    round(combined_score, 2),
                    list(dict.fromkeys([*reasons, semantic_reason])),
                )

        ranked = list(ranked_lookup.values())
        ranked.sort(
            key=lambda item: (item[1], len(item[2]), item[0].standard_code),
            reverse=True,
        )
        if (
            semantic_match is not None
            and semantic_match.enabled
            and semantic_match.best_match is not None
            and semantic_match.best_match.score >= semantic_match.threshold
            and ranked
            and ranked[0][1] < 0.9
        ):
            accepted_code = semantic_match.best_match.standard_code
            ranked = [
                item for item in ranked if item[0].standard_code == accepted_code
            ] + [
                item for item in ranked if item[0].standard_code != accepted_code
            ]
        return ranked

    @classmethod
    def promote_learned_standard_candidate(
        cls,
        ranked_candidates: list[tuple[StandardCandidate, float, list[str]]],
        candidates: list[StandardCandidate],
        learned_mapping: LearnedStandardMapping | None,
    ) -> list[tuple[StandardCandidate, float, list[str]]]:
        """Promote a human-reviewed learned standard without auto-confirming it."""
        if learned_mapping is None:
            return ranked_candidates

        candidate_lookup = {candidate.standard_code: candidate for candidate in candidates}
        learned_candidate = candidate_lookup.get(learned_mapping.standard_code)
        if learned_candidate is None:
            return ranked_candidates

        reason = (
            "learned mapping memory matched "
            f"scope={learned_mapping.match_scope} "
            f"field_key={learned_mapping.field_key} "
            f"source={learned_mapping.source or 'review'} "
            f"action={learned_mapping.review_action or 'unknown'}"
        )
        promoted_score = 1.15
        promoted: tuple[StandardCandidate, float, list[str]] | None = None
        remaining: list[tuple[StandardCandidate, float, list[str]]] = []
        for candidate, score, reasons in ranked_candidates:
            if candidate.standard_code != learned_mapping.standard_code:
                remaining.append((candidate, score, reasons))
                continue
            promoted = (
                candidate,
                round(max(score, promoted_score), 2),
                list(dict.fromkeys([reason, *reasons])),
            )

        if promoted is None:
            promoted = (learned_candidate, promoted_score, [reason])

        return [promoted, *remaining]

    @staticmethod
    def _has_accepted_semantic_match(
        semantic_match: SemanticFieldMatch | None,
        standard_code: str,
    ) -> bool:
        if (
            semantic_match is None
            or not semantic_match.enabled
            or semantic_match.best_match is None
        ):
            return False
        return semantic_match.best_match.standard_code == standard_code

    @classmethod
    def _candidate_risk_hints(
        cls,
        field_info: dict[str, object],
        candidate: StandardCandidate,
        score: float,
    ) -> tuple[list[str], list[str], bool]:
        """Explain candidate risk, suggested action, and manual-review need."""
        risks: list[str] = []
        actions: list[str] = []
        requires_manual_review = False
        field_type = str(field_info.get("data_type") or "")
        standard_type = cls._normalize_data_type(candidate.data_type)
        field_domain = str(field_info.get("effective_business_domain") or "")
        standard_domain = cls._normalize_domain(candidate.business_domain)

        if field_type and standard_type and not cls._types_compatible(
            field_type,
            standard_type,
        ):
            risks.append(
                f"Field type {field_type} conflicts with standard type {standard_type}"
            )
            actions.append("Review the field data type against the standard definition")
            requires_manual_review = True

        if field_domain and standard_domain and not cls._domains_compatible(
            field_domain,
            standard_domain,
        ):
            risks.append(
                f"Field domain {field_domain} differs from standard domain {standard_domain}"
            )
            actions.append("Review table ownership, business domain, or cross-domain reuse")
            requires_manual_review = True

        if 0 < score < 0.9:
            risks.append("Recommendation confidence is below the auto-accept threshold")
            actions.append("Ask a data steward to review the candidate standard")
            requires_manual_review = True

        if candidate.value_domain and field_info.get("sample_values"):
            actions.append("Use sample values to validate the candidate value domain")

        if not risks:
            risks.append("No obvious type or business-domain conflict")

        if not actions:
            actions.append("Use as an auto recommendation for review or downstream rules")

        return list(dict.fromkeys(risks)), list(dict.fromkeys(actions)), requires_manual_review

    @classmethod
    def _candidate_payload(
        cls,
        field_info: dict[str, object],
        candidate: StandardCandidate,
        score: float,
        reasons: list[str],
    ) -> dict[str, object]:
        risks, actions, requires_manual_review = cls._candidate_risk_hints(
            field_info,
            candidate,
            score,
        )
        return {
            "standard_code": candidate.standard_code,
            "standard_name": candidate.standard_name,
            "standard_name_cn": candidate.standard_name_cn,
            "match_score": score,
            "match_reason": "; ".join(reasons),
            "risk_hint": "; ".join(risks),
            "action_suggestion": "; ".join(actions),
            "requires_manual_review": requires_manual_review,
            "standard_data_type": candidate.data_type,
            "standard_business_domain": candidate.business_domain,
        }

    @classmethod
    def _result_explanation(
        cls,
        field_info: dict[str, object],
        candidate: StandardCandidate,
        score: float,
        existing_standard_code: str | None = None,
    ) -> tuple[str, str, bool, str, list[str]]:
        risks, actions, requires_manual_review = cls._candidate_risk_hints(
            field_info,
            candidate,
            score,
        )
        mapping_status = "auto_recommended"
        if requires_manual_review:
            mapping_status = "manual_review"
        if score <= 0:
            mapping_status = "needs_new_standard"
        if (
            existing_standard_code
            and existing_standard_code != candidate.standard_code
            and score >= 0.75
        ):
            risks.append(
                f"Existing binding {existing_standard_code} differs from top candidate {candidate.standard_code}"
            )
            actions.append("Review whether the historical binding should be corrected")
            requires_manual_review = True
            mapping_status = "existing_mapping_suspect"

        context_evidence = [
            f"field_data_type={field_info.get('raw_data_type') or 'N/A'}",
            f"normalized_data_type={field_info.get('data_type') or 'N/A'}",
            f"field_business_domain={field_info.get('effective_business_domain') or 'N/A'}",
            f"standard_data_type={candidate.data_type or 'N/A'}",
            f"standard_business_domain={candidate.business_domain or 'N/A'}",
        ]
        if field_info.get("table_description"):
            context_evidence.append(
                f"table_description={field_info['table_description']}"
            )

        return (
            "; ".join(list(dict.fromkeys(risks))),
            "; ".join(list(dict.fromkeys(actions))),
            requires_manual_review,
            mapping_status,
            context_evidence,
        )

    @staticmethod
    def _semantic_candidate_payloads(
        semantic_match: SemanticFieldMatch | None,
    ) -> list[dict[str, object]]:
        if semantic_match is None or not semantic_match.enabled:
            return []
        return [
            {
                "standard_code": match.standard_code,
                "standard_name": match.standard_name,
                "match_score": round(match.score, 2),
                "match_reason": (
                    "semantic embedding cosine similarity "
                    f"{match.score:.2f} against source_text={semantic_match.field_text}"
                ),
                "risk_hint": "Semantic candidate should be reviewed with rules, type, and domain evidence",
                "action_suggestion": "Compare with rule candidates before confirmation",
                "requires_manual_review": match.score < semantic_match.threshold,
            }
            for match in semantic_match.top_matches
        ]

    @classmethod
    def _merge_top_candidates(
        cls,
        field_info: dict[str, object],
        top_candidates: list[tuple[StandardCandidate, float, list[str]]],
        semantic_match: SemanticFieldMatch | None,
    ) -> list[dict[str, object]]:
        payloads = [
            cls._candidate_payload(field_info, candidate, score, reasons)
            for candidate, score, reasons in top_candidates
        ]
        seen = {str(payload["standard_code"]) for payload in payloads}
        for semantic_payload in cls._semantic_candidate_payloads(
            semantic_match
        ):
            standard_code = str(semantic_payload["standard_code"])
            if standard_code in seen:
                continue
            payloads.append(semantic_payload)
            seen.add(standard_code)
        return payloads[:3]

    @staticmethod
    def build_mapping_issue(
        issue_id: str,
        table_name: str,
        field_name: str,
        issue_type: str,
        evidence: list[str],
        suggestion: str,
        confidence: float,
        system_name: str | None = None,
        business_domain: str | None = None,
        ai_risk: str | None = None,
        requires_manual_review: bool | None = None,
        evidence_details: dict[str, object] | None = None,
    ) -> Issue:
        """Create a normalized mapping issue object."""
        return Issue(
            issue_id=issue_id,
            object_type="field",
            object_name=f"{table_name}.{field_name}",
            issue_type=issue_type,
            severity=get_issue_severity(issue_type),
            evidence=evidence,
            suggestion=suggestion,
            confidence=confidence,
            system_name=system_name,
            business_domain=business_domain,
            impact_scope="standard-mapping/text-to-sql/rag",
            ai_risk=ai_risk,
            recommended_priority=(
                "priority_governance"
                if issue_type == "standard_mapping_suspected_wrong"
                else "key_tracking"
            ),
            requires_manual_review=requires_manual_review,
            evidence_details=evidence_details or {},
        )

    @classmethod
    def _build_existing_mapping_issue(
        cls,
        table: TableMeta,
        field: object,
        field_info: dict[str, object],
        top_candidate: StandardCandidate,
        top_score: float,
        top_reasons: list[str],
        current_candidate: StandardCandidate | None,
        current_score: float | None,
    ) -> Issue | None:
        existing_code = str(field_info.get("existing_standard_code") or "")
        if not existing_code or existing_code == top_candidate.standard_code:
            return None
        if top_score < 0.75:
            return None
        if current_candidate is not None and current_score is not None:
            if current_score >= top_score - 0.1:
                return None

        current_text = existing_code
        if current_candidate is not None:
            current_text = f"{current_candidate.standard_code} score={current_score}"
        return cls.build_mapping_issue(
            issue_id=(
                f"{cls.skill_name}-suspected-wrong-"
                f"{table.table_name}-{getattr(field, 'field_name', '')}"
            ).replace(" ", "_"),
            table_name=table.table_name,
            field_name=getattr(field, "field_name", ""),
            issue_type="standard_mapping_suspected_wrong",
            evidence=[
                f"existing_standard={current_text}",
                f"recommended_standard={top_candidate.standard_code}",
                f"recommended_score={top_score}",
                *top_reasons,
            ],
            suggestion=(
                "Review the existing standard binding. If the current binding came from "
                "history, compare it with the new top candidate before downstream reuse."
            ),
            confidence=max(0.7, min(0.95, top_score)),
            system_name=table.system_name,
            business_domain=str(field_info.get("effective_business_domain") or "")
            or table.business_domain,
            ai_risk=(
                "Historical standard binding may mislead Text-to-SQL, RAG field interpretation, and quality-rule recommendation."
            ),
            requires_manual_review=True,
            evidence_details={
                "existing_standard_code": existing_code,
                "recommended_standard_code": top_candidate.standard_code,
                "recommended_score": top_score,
                "current_score": current_score,
            },
        )

    def run(self, payload: StandardMappingInput) -> StandardMappingOutput:
        """Recommend standard mappings for field-level metadata."""
        if not payload.tables:
            return StandardMappingOutput(
                mapping_results=[],
                confirmed_mapping_results=[],
                unmapped_fields=[],
                issues=[],
                review_applied_count=0,
                summary="No tables were provided, so standard mapping was skipped.",
            )

        standard_candidates = self._prepare_standard_candidates()
        learned_mapping_memory = load_standard_mapping_memory()
        mapping_results: list[MappingResult] = []
        unmapped_fields: list[UnmappedField] = []
        issues: list[Issue] = []
        mapped_count = 0

        field_entries = [
            (table, field)
            for table in payload.tables
            for field in table.fields
        ]
        semantic_matches = semantic_match_source_fields(
            [field for _, field in field_entries]
        )
        semantic_match_by_key = {
            f"{table.table_name}.{field.field_name}": semantic_match
            for (table, field), semantic_match in zip(
                field_entries,
                semantic_matches,
                strict=True,
            )
        }

        for table in payload.tables:
            for field in table.fields:
                field_info = self.build_field_context(table, field)
                lookup_key = f"{table.table_name}.{field.field_name}"
                semantic_match = semantic_match_by_key.get(lookup_key)
                ranked_candidates = self.rank_standard_candidates_with_semantics(
                    field_info,
                    standard_candidates,
                    semantic_match,
                )
                learned_lookup = explain_standard_mapping_memory_lookup(
                    field.field_name,
                    learned_mapping_memory,
                    table_name=table.table_name,
                )
                learning_evidence = list(learned_lookup.evidence)
                ranked_candidates = self.promote_learned_standard_candidate(
                    ranked_candidates,
                    standard_candidates,
                    learned_lookup.learned_mapping,
                )
                top_candidates = ranked_candidates[:3]

                if not top_candidates:
                    unmapped_fields.append(
                        UnmappedField(
                            table_name=table.table_name,
                            field_name=field.field_name,
                            field_name_cn=field.field_name_cn,
                            best_candidate_code=None,
                            best_candidate_score=0.0,
                            reason="No standard candidate exceeded the minimum rule-based score.",
                            risk_hint="No explainable rule, semantic, or context candidate was found",
                            action_suggestion=(
                                "Add field Chinese name/description or assess whether a new standard is needed"
                            ),
                            requires_manual_review=True,
                            evidence=[
                                f"normalized_name={field_info['normalized_name']}",
                                f"normalized_tokens={field_info['normalized_tokens']}",
                                (
                                    f"semantic_text={semantic_match.field_text}"
                                    if semantic_match is not None
                                    else "semantic_text="
                                ),
                                (
                                    "semantic_retrieval=unavailable"
                                    if semantic_match is None or not semantic_match.enabled
                                    else "semantic_retrieval=no candidate above threshold"
                                ),
                            ]
                            + learning_evidence
                            + list(field_info["expansion_evidence"]),
                        )
                    )
                    issues.append(
                        self.build_mapping_issue(
                            issue_id=(
                                f"{self.skill_name}-missing-"
                                f"{table.table_name}-{field.field_name}"
                            ).replace(" ", "_"),
                            table_name=table.table_name,
                            field_name=field.field_name,
                            issue_type="standard_mapping_missing",
                            evidence=[
                                f"normalized_name={field_info['normalized_name']}",
                                f"normalized_tokens={field_info['normalized_tokens']}",
                                "no standard candidate produced a positive rule-based or semantic score",
                            ]
                            + learning_evidence
                            + list(field_info["expansion_evidence"]),
                            suggestion=(
                                "Review whether this field should map to an existing standard "
                                "field or whether the standard library needs to be extended."
                            ),
                            confidence=0.9,
                            system_name=table.system_name,
                            business_domain=str(
                                field_info.get("effective_business_domain") or ""
                            )
                            or table.business_domain,
                            ai_risk=(
                                "Missing standard mapping weakens semantic consistency for Text-to-SQL, RAG, and reusable quality rules."
                            ),
                            requires_manual_review=True,
                            evidence_details={
                                "normalized_name": field_info["normalized_name"],
                                "normalized_tokens": field_info["normalized_tokens"],
                                "data_type": field_info.get("data_type"),
                                "business_domain": field_info.get(
                                    "effective_business_domain"
                                ),
                            },
                        )
                    )
                    continue

                top_candidate, top_score, top_reasons = top_candidates[0]
                preferred_codes = set(
                    payload.domain_pack_hints.get("mapping_hints", {}).get(
                        "preferred_standard_codes",
                        [],
                    )
                )
                if top_candidate.standard_code in preferred_codes:
                    top_reasons = [
                        *top_reasons,
                        "domain pack preferred_standard_codes hint matched",
                    ]
                if semantic_match is not None and semantic_match.enabled:
                    top_reasons = [
                        *top_reasons,
                        f"semantic_source_text={semantic_match.field_text}",
                    ]
                current_candidate = next(
                    (
                        candidate
                        for candidate in standard_candidates
                        if candidate.standard_code
                        == str(field_info.get("existing_standard_code") or "")
                    ),
                    None,
                )
                current_score = None
                if current_candidate is not None:
                    current_score, _ = self.compute_match_score(
                        field_info,
                        current_candidate,
                    )
                existing_issue = self._build_existing_mapping_issue(
                    table,
                    field,
                    field_info,
                    top_candidate,
                    top_score,
                    top_reasons,
                    current_candidate,
                    current_score,
                )
                if existing_issue is not None:
                    issues.append(existing_issue)

                (
                    risk_hint,
                    action_suggestion,
                    requires_manual_review,
                    mapping_status,
                    context_evidence,
                ) = self._result_explanation(
                    field_info,
                    top_candidate,
                    top_score,
                    str(field_info.get("existing_standard_code") or "") or None,
                )
                mapping_results.append(
                    MappingResult(
                        table_name=table.table_name,
                        field_name=field.field_name,
                        recommended_standard_code=top_candidate.standard_code,
                        recommended_standard_name=top_candidate.standard_name,
                        recommended_standard_name_cn=top_candidate.standard_name_cn,
                        match_score=top_score,
                        match_reason="; ".join(top_reasons),
                        risk_hint=risk_hint,
                        action_suggestion=action_suggestion,
                        requires_manual_review=requires_manual_review,
                        mapping_status=mapping_status,
                        context_evidence=context_evidence,
                        candidate_count=len(ranked_candidates),
                        top_candidates=self._merge_top_candidates(
                            field_info,
                            top_candidates,
                            semantic_match,
                        ),
                    )
                )

                if top_score >= 0.9 or self._has_accepted_semantic_match(
                    semantic_match,
                    top_candidate.standard_code,
                ):
                    mapped_count += 1
                else:
                    unmapped_fields.append(
                        UnmappedField(
                            table_name=table.table_name,
                            field_name=field.field_name,
                            field_name_cn=field.field_name_cn,
                            best_candidate_code=top_candidate.standard_code,
                            best_candidate_score=top_score,
                            reason="Best candidate exists but confidence is still low.",
                            risk_hint=risk_hint,
                            action_suggestion=action_suggestion,
                            requires_manual_review=True,
                            evidence=top_reasons
                            + learning_evidence
                            + list(field_info["expansion_evidence"]),
                        )
                    )
                    issues.append(
                        self.build_mapping_issue(
                            issue_id=(
                                f"{self.skill_name}-low-confidence-"
                                f"{table.table_name}-{field.field_name}"
                            ).replace(" ", "_"),
                            table_name=table.table_name,
                            field_name=field.field_name,
                            issue_type="standard_mapping_low_confidence",
                            evidence=top_reasons
                            + [
                                f"top_candidate={top_candidate.standard_code}",
                                f"match_score={top_score}",
                            ]
                            + learning_evidence
                            + list(field_info["expansion_evidence"]),
                            suggestion=(
                                "Review the recommended standard candidate and refine either the "
                                "field name or the knowledge packs if the mapping is important."
                            ),
                            confidence=max(0.5, min(0.88, top_score / 1.5)),
                            system_name=table.system_name,
                            business_domain=str(
                                field_info.get("effective_business_domain") or ""
                            )
                            or table.business_domain,
                            ai_risk=(
                                "Low-confidence mapping can make field interpretation, rule recommendation, and semantic retrieval unstable."
                            ),
                            requires_manual_review=True,
                            evidence_details={
                                "top_candidate": top_candidate.standard_code,
                                "match_score": top_score,
                                "data_type": field_info.get("data_type"),
                                "business_domain": field_info.get(
                                    "effective_business_domain"
                                ),
                            },
                        )
                    )

        confirmed_mapping_results: list[MappingResult] = []
        review_applied_count = 0
        if payload.apply_overrides:
            override_records = payload.override_records or load_mapping_overrides()
            confirmed_mapping_results, review_applied_count, _ = (
                apply_mapping_overrides_to_results(mapping_results, override_records)
            )

        summary = (
            f"Evaluated standard mapping for {len(mapping_results)} fields, "
            f"produced {mapped_count} higher-confidence recommendations, and "
            f"flagged {len(unmapped_fields)} unmapped or low-confidence fields."
        )
        if payload.apply_overrides and review_applied_count:
            summary += f" Applied {review_applied_count} mapping overrides."

        return StandardMappingOutput(
            mapping_results=mapping_results,
            confirmed_mapping_results=confirmed_mapping_results,
            unmapped_fields=unmapped_fields,
            issues=issues,
            review_applied_count=review_applied_count,
            summary=summary,
        )
