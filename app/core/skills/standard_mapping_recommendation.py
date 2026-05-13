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
from app.core.rules.config_loader import get_issue_severity
from app.core.review.override_store import load_mapping_overrides
from app.core.review.review_service import apply_mapping_overrides_to_results
from app.core.skills.base_skill import BaseSkill


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
    business_domain: str | None
    aliases: list[str]
    normalized_name: str
    normalized_tokens: list[str]
    expanded_tokens: list[str]
    alias_lookup: list[str]


class StandardMappingRecommendationSkill(BaseSkill):
    """Recommend standard fields using explainable knowledge-pack rules."""

    skill_name = "standard_mapping_recommendation"
    version = "0.3.0"
    description = "P1 rule-based standard field recommendation using local knowledge packs."

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
            for alias in aliases:
                alias_lookup.append(alias.lower())
                alias_lookup.append(cls.normalize_field_for_matching(alias)["normalized_name"])

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
                    data_type=(
                        str(row["data_type"]).strip()
                        if str(row["data_type"]).strip().lower() != "nan"
                        else None
                    ),
                    business_domain=(
                        str(row["business_domain"]).strip()
                        if str(row["business_domain"]).strip().lower() != "nan"
                        else None
                    ),
                    aliases=aliases,
                    normalized_name=normalized["normalized_name"],
                    normalized_tokens=list(normalized["normalized_tokens"]),
                    expanded_tokens=list(normalized["expanded_tokens"]),
                    alias_lookup=list(dict.fromkeys(alias_lookup)),
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

        if cleaned_cn_name and candidate.standard_name_cn:
            standard_cn = clean_text(candidate.standard_name_cn)
            if cleaned_cn_name in standard_cn or standard_cn in cleaned_cn_name:
                score += 0.5
                reasons.append("field_name_cn matched standard_name_cn by text inclusion")

        overlap = set(normalized_tokens).intersection(candidate.normalized_tokens)
        if overlap:
            score += min(0.4, 0.1 * len(overlap))
            reasons.append(f"shared normalized tokens={sorted(overlap)}")

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
    def build_mapping_issue(
        issue_id: str,
        table_name: str,
        field_name: str,
        issue_type: str,
        evidence: list[str],
        suggestion: str,
        confidence: float,
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
        mapping_results: list[MappingResult] = []
        unmapped_fields: list[UnmappedField] = []
        issues: list[Issue] = []
        mapped_count = 0

        for table in payload.tables:
            for field in table.fields:
                field_info = self.normalize_field_for_matching(
                    field.field_name,
                    field.field_name_cn,
                )
                ranked_candidates = self.rank_standard_candidates(
                    field_info,
                    standard_candidates,
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
                            evidence=[
                                f"normalized_name={field_info['normalized_name']}",
                                f"normalized_tokens={field_info['normalized_tokens']}",
                            ]
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
                                "no standard candidate produced a positive rule-based score",
                            ]
                            + list(field_info["expansion_evidence"]),
                            suggestion=(
                                "Review whether this field should map to an existing standard "
                                "field or whether the standard library needs to be extended."
                            ),
                            confidence=0.9,
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
                mapping_results.append(
                    MappingResult(
                        table_name=table.table_name,
                        field_name=field.field_name,
                        recommended_standard_code=top_candidate.standard_code,
                        recommended_standard_name=top_candidate.standard_name,
                        recommended_standard_name_cn=top_candidate.standard_name_cn,
                        match_score=top_score,
                        match_reason="; ".join(top_reasons),
                        candidate_count=len(ranked_candidates),
                        top_candidates=[
                            {
                                "standard_code": candidate.standard_code,
                                "standard_name": candidate.standard_name,
                                "match_score": score,
                                "match_reason": "; ".join(reasons),
                            }
                            for candidate, score, reasons in top_candidates
                        ],
                    )
                )

                if top_score >= 0.9:
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
                            evidence=top_reasons + list(field_info["expansion_evidence"]),
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
                            + list(field_info["expansion_evidence"]),
                            suggestion=(
                                "Review the recommended standard candidate and refine either the "
                                "field name or the knowledge packs if the mapping is important."
                            ),
                            confidence=max(0.5, min(0.88, top_score / 1.5)),
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

        # TODO: extend mapping ranking with richer domain context and semantic retrieval in a future P2 version.
        return StandardMappingOutput(
            mapping_results=mapping_results,
            confirmed_mapping_results=confirmed_mapping_results,
            unmapped_fields=unmapped_fields,
            issues=issues,
            review_applied_count=review_applied_count,
            summary=summary,
        )
