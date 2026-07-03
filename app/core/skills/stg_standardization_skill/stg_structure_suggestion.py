"""Rule-based P1.5 skill for STG structure suggestions."""

from pydantic import BaseModel, Field

from app.core.knowledge.knowledge_loader import load_standard_fields
from app.core.models.issue import Issue
from app.core.models.mapping_result import MappingResult
from app.core.models.stg_field_suggestion import StgFieldSuggestion
from app.core.models.stg_review_record import StgReviewRecord
from app.core.models.stg_table_suggestion import StgTableSuggestion
from app.core.models.table_meta import TableMeta
from app.core.normalize import clean_text, split_tokens
from app.core.review.override_store import load_stg_overrides
from app.core.review.review_service import apply_stg_overrides_to_suggestions
from app.core.rules.config_loader import (
    get_field_transform_rules_config,
    get_issue_severity,
    get_stg_rules_config,
)
from app.core.skills.base_skill import BaseSkill
from app.core.skills.stg_standardization_skill.stg_learning import (
    apply_learned_stg_field,
    load_stg_field_memory,
    lookup_learned_stg_field,
)


class StgStructureSuggestionInput(BaseModel):
    """Input schema for STG structure suggestion."""

    tables: list[TableMeta] = Field(default_factory=list)
    mapping_results: list[MappingResult] = Field(default_factory=list)
    naming_field_suggestions: dict[str, str] = Field(default_factory=dict)
    keep_unmapped_fields: bool | None = None
    apply_overrides: bool = True
    override_records: list[StgReviewRecord] = Field(default_factory=list)
    domain_pack_hints: dict = Field(default_factory=dict)


class StgStructureSuggestionOutput(BaseModel):
    """Output schema for STG structure suggestion."""

    stg_table_suggestions: list[StgTableSuggestion] = Field(default_factory=list)
    field_suggestions_flat: list[StgFieldSuggestion] = Field(default_factory=list)
    confirmed_stg_suggestions: list[StgFieldSuggestion] = Field(default_factory=list)
    issues: list[Issue] = Field(default_factory=list)
    review_applied_count: int = 0
    summary: str = ""


class StgStructureSuggestionSkill(BaseSkill):
    """Generate explainable STG structure suggestions from local metadata."""

    skill_name = "stg_structure_suggestion"
    version = "0.4.0"
    description = "P1.5 rule-based STG structure suggestion using mapping results and naming enhancement."
    mapping_use_threshold = 0.6

    @staticmethod
    def _minimal_normalize_name(name: str) -> str:
        tokens = split_tokens(clean_text(name, lower=False))
        return "_".join(tokens) or clean_text(name).replace(" ", "_")

    @classmethod
    def suggest_stg_table_name(cls, source_table_name: str) -> str:
        """Build a recommended STG table name from source naming rules."""
        stg_rules = get_stg_rules_config()
        normalized = cls._minimal_normalize_name(source_table_name)
        stripped_name = normalized
        for prefix in stg_rules.get("remove_source_prefixes", []):
            if stripped_name.startswith(prefix):
                stripped_name = stripped_name[len(prefix) :]
                break

        stripped_name = stripped_name.strip("_") or normalized
        prefix = str(stg_rules.get("default_stg_name_prefix", "stg_"))
        return f"{prefix}{stripped_name}"

    @staticmethod
    def normalize_data_type(source_data_type: str | None) -> str | None:
        """Normalize source data types based on configured transform rules."""
        if source_data_type is None:
            return None

        transform_rules = get_field_transform_rules_config()
        type_normalization = transform_rules.get("type_normalization", {})
        lowered = source_data_type.strip().lower()
        base_type = lowered.split("(", 1)[0].strip()
        return type_normalization.get(base_type, base_type or None)

    @staticmethod
    def normalize_nullable(value: bool | str | int | None) -> bool | None:
        """Normalize nullable values using configured transform rules."""
        if isinstance(value, bool) or value is None:
            return value

        transform_rules = get_field_transform_rules_config()
        nullable_rules = transform_rules.get("nullable_normalization", {})
        true_values = {
            str(item).strip().lower() for item in nullable_rules.get("true_values", [])
        }
        false_values = {
            str(item).strip().lower() for item in nullable_rules.get("false_values", [])
        }

        normalized = str(value).strip().lower()
        if normalized in true_values:
            return True
        if normalized in false_values:
            return False
        return None

    @staticmethod
    def collect_mapping_lookup(
        mapping_results: list[MappingResult],
    ) -> dict[str, MappingResult]:
        """Create a lookup for mapping results by table and field."""
        return {
            f"{result.table_name}.{result.field_name}": result for result in mapping_results
        }

    @staticmethod
    def collect_standard_lookup() -> dict[str, dict[str, str | None]]:
        """Create a lookup for standard field metadata by standard code."""
        dataframe = load_standard_fields()
        lookup: dict[str, dict[str, str | None]] = {}
        for _, row in dataframe.iterrows():
            standard_code = str(row["standard_code"]).strip()
            lookup[standard_code] = {
                "standard_name": str(row["standard_name"]).strip(),
                "standard_name_cn": (
                    None
                    if str(row["standard_name_cn"]).strip().lower() == "nan"
                    else str(row["standard_name_cn"]).strip()
                ),
                "data_type": (
                    None
                    if str(row["data_type"]).strip().lower() == "nan"
                    else str(row["data_type"]).strip()
                ),
            }
        return lookup

    @staticmethod
    def is_reserved_field(
        source_field_name: str,
        normalized_field_name: str,
    ) -> tuple[bool, str | None]:
        """Detect configured technical or audit reservation fields."""
        stg_rules = get_stg_rules_config()
        technical_keywords = {
            str(item).strip().lower()
            for item in stg_rules.get("technical_field_keywords", [])
        }
        audit_keywords = {
            str(item).strip().lower()
            for item in stg_rules.get("audit_field_keywords", [])
        }
        candidates = {
            source_field_name.strip().lower(),
            normalized_field_name.strip().lower(),
            "_".join(split_tokens(source_field_name)),
        }

        if candidates.intersection(technical_keywords):
            return True, "technical"
        if candidates.intersection(audit_keywords):
            return True, "audit"
        return False, None

    @staticmethod
    def infer_field_action(
        source_field_name: str,
        source_data_type: str | None,
        recommended_field_name: str,
        recommended_data_type: str | None,
    ) -> str:
        """Infer the STG action for one field suggestion."""
        normalized_source_name = "_".join(split_tokens(source_field_name))
        normalized_source_type = StgStructureSuggestionSkill.normalize_data_type(
            source_data_type
        )

        if recommended_field_name == source_field_name and recommended_data_type == source_data_type:
            return "keep"
        if (
            recommended_field_name == normalized_source_name
            and recommended_data_type == normalized_source_type
        ):
            return "keep"
        if recommended_field_name == normalized_source_name:
            return "keep_with_normalization"
        return "rename"

    @staticmethod
    def _stg_confidence_band(confidence_score: float | None) -> str:
        if confidence_score is None:
            return "unknown"
        if confidence_score >= 0.9:
            return "high"
        if confidence_score >= 0.6:
            return "medium"
        return "low"

    @classmethod
    def build_recommendation_evidence(
        cls,
        *,
        mapping_source: str,
        action: str,
        match_score: float | None,
        source_field_name: str,
        source_data_type: str | None,
        recommended_stg_field_name: str,
        recommended_data_type: str | None,
    ) -> dict[str, object]:
        source_category = {
            "standard_mapping": "standard_mapping",
            "naming_enhancement": "naming_enhancement",
            "original_fallback": "source_metadata_fallback",
            "reserved_field": "reserved_metadata",
            "learned_stg_memory": "learned_review_memory",
        }.get(mapping_source, "source_metadata")
        confidence_score = match_score
        if confidence_score is None:
            confidence_score = 0.7 if mapping_source == "naming_enhancement" else 0.45
        review_reason_codes: list[str] = []
        if mapping_source == "original_fallback":
            review_reason_codes.append("source_metadata_fallback")
        if mapping_source == "standard_mapping" and match_score is not None and match_score < 0.9:
            review_reason_codes.append("low_mapping_confidence")
        if action == "rename":
            review_reason_codes.append("rename_required")
        if cls.normalize_data_type(source_data_type) != recommended_data_type:
            review_reason_codes.append("data_type_normalized")
        return {
            "mapping_source": mapping_source,
            "source_category": source_category,
            "confidence_score": round(float(confidence_score), 2),
            "confidence_band": cls._stg_confidence_band(float(confidence_score)),
            "review_reason_codes": list(dict.fromkeys(review_reason_codes)),
            "action": action,
            "source_field_name": source_field_name,
            "recommended_stg_field_name": recommended_stg_field_name,
            "name_changed": source_field_name != recommended_stg_field_name,
            "source_data_type": source_data_type,
            "recommended_data_type": recommended_data_type,
        }

    @staticmethod
    def build_issue(
        issue_id: str,
        object_name: str,
        issue_type: str,
        evidence: list[str],
        suggestion: str,
        confidence: float,
    ) -> Issue:
        """Build an issue object for STG review findings."""
        return Issue(
            issue_id=issue_id,
            object_type="stg",
            object_name=object_name,
            issue_type=issue_type,
            severity=get_issue_severity(issue_type),
            evidence=evidence,
            suggestion=suggestion,
            confidence=confidence,
        )

    def build_stg_field_from_mapping(
        self,
        table: TableMeta,
        field: object,
        mapping_result: MappingResult,
        standard_lookup: dict[str, dict[str, str | None]],
    ) -> StgFieldSuggestion:
        """Build a field suggestion from a standard mapping result."""
        standard_info = standard_lookup.get(
            mapping_result.recommended_standard_code or "",
            {},
        )
        recommended_name = (
            mapping_result.recommended_standard_name
            or mapping_result.recommended_standard_code
            or self._minimal_normalize_name(field.field_name)
        )
        recommended_type = self.normalize_data_type(
            standard_info.get("data_type") or field.data_type
        )
        action = self.infer_field_action(
            field.field_name,
            field.data_type,
            recommended_name,
            recommended_type,
        )
        notes = "Derived from standard mapping."
        if mapping_result.match_score < 0.9:
            notes += " Manual confirmation required because mapping confidence is limited."

        return StgFieldSuggestion(
            source_table_name=table.table_name,
            source_field_name=field.field_name,
            source_field_name_cn=field.field_name_cn,
            source_data_type=field.data_type,
            recommended_stg_field_name=recommended_name,
            recommended_stg_field_name_cn=(
                mapping_result.recommended_standard_name_cn
                or standard_info.get("standard_name_cn")
                or field.field_name_cn
            ),
            recommended_data_type=recommended_type,
            nullable=self.normalize_nullable(field.nullable),
            mapping_source="standard_mapping",
            match_score=mapping_result.match_score,
            recommendation_evidence=self.build_recommendation_evidence(
                mapping_source="standard_mapping",
                action=action,
                match_score=mapping_result.match_score,
                source_field_name=field.field_name,
                source_data_type=field.data_type,
                recommended_stg_field_name=recommended_name,
                recommended_data_type=recommended_type,
            ),
            action=action,
            notes=notes,
        )

    def build_stg_field_from_original(
        self,
        table: TableMeta,
        field: object,
        suggested_name: str | None,
        mapping_source: str,
        note_text: str,
    ) -> StgFieldSuggestion:
        """Build a field suggestion from naming enhancement or source fallback."""
        recommended_name = suggested_name or self._minimal_normalize_name(field.field_name)
        recommended_type = self.normalize_data_type(field.data_type)
        action = self.infer_field_action(
            field.field_name,
            field.data_type,
            recommended_name,
            recommended_type,
        )
        return StgFieldSuggestion(
            source_table_name=table.table_name,
            source_field_name=field.field_name,
            source_field_name_cn=field.field_name_cn,
            source_data_type=field.data_type,
            recommended_stg_field_name=recommended_name,
            recommended_stg_field_name_cn=field.field_name_cn,
            recommended_data_type=recommended_type,
            nullable=self.normalize_nullable(field.nullable),
            mapping_source=mapping_source,
            match_score=None,
            recommendation_evidence=self.build_recommendation_evidence(
                mapping_source=mapping_source,
                action=action,
                match_score=None,
                source_field_name=field.field_name,
                source_data_type=field.data_type,
                recommended_stg_field_name=recommended_name,
                recommended_data_type=recommended_type,
            ),
            action=action,
            notes=note_text,
        )

    def run(self, payload: StgStructureSuggestionInput) -> StgStructureSuggestionOutput:
        """Generate one STG table suggestion per source table."""
        if not payload.tables:
            return StgStructureSuggestionOutput(
                stg_table_suggestions=[],
                field_suggestions_flat=[],
                confirmed_stg_suggestions=[],
                issues=[],
                review_applied_count=0,
                summary="No tables were provided, so STG structure suggestion was skipped.",
            )

        stg_rules = get_stg_rules_config()
        transform_rules = get_field_transform_rules_config()
        keep_unmapped_fields = (
            payload.keep_unmapped_fields
            if payload.keep_unmapped_fields is not None
            else bool(stg_rules.get("default_keep_unmapped_fields", True))
        )
        reserved_field_actions = {
            str(key).strip().lower(): str(value).strip().lower()
            for key, value in transform_rules.get("reserved_field_actions", {}).items()
        }
        mapping_lookup = self.collect_mapping_lookup(payload.mapping_results)
        standard_lookup = self.collect_standard_lookup()
        learned_stg_memory = load_stg_field_memory()

        stg_table_suggestions: list[StgTableSuggestion] = []
        field_suggestions_flat: list[StgFieldSuggestion] = []
        issues: list[Issue] = []
        manual_review_table_count = 0

        for table in payload.tables:
            table_issue_flags: list[str] = []
            table_field_suggestions: list[StgFieldSuggestion] = []
            recommended_table_name = self.suggest_stg_table_name(table.table_name)

            for field in table.fields:
                lookup_key = f"{table.table_name}.{field.field_name}"
                mapping_result = mapping_lookup.get(lookup_key)
                naming_suggestion = payload.naming_field_suggestions.get(lookup_key)
                raw_normalized_field_name = "_".join(split_tokens(field.field_name))
                reserved, reserved_type = self.is_reserved_field(
                    field.field_name,
                    raw_normalized_field_name,
                )

                if mapping_result is not None and mapping_result.match_score >= self.mapping_use_threshold:
                    field_suggestion = self.build_stg_field_from_mapping(
                        table,
                        field,
                        mapping_result,
                        standard_lookup,
                    )
                elif reserved:
                    reserved_action = reserved_field_actions.get(
                        raw_normalized_field_name,
                        "keep",
                    )
                    reserved_name = (
                        raw_normalized_field_name
                        if reserved_action == "keep"
                        else naming_suggestion or raw_normalized_field_name
                    )
                    field_suggestion = self.build_stg_field_from_original(
                        table,
                        field,
                        reserved_name,
                        "original_fallback",
                        (
                            f"Reserved {reserved_type} field retained for STG review. "
                            "Manual confirmation recommended."
                        ),
                    )
                    field_suggestion.action = "keep"
                elif naming_suggestion:
                    field_suggestion = self.build_stg_field_from_original(
                        table,
                        field,
                        naming_suggestion,
                        "naming_enhancement",
                        (
                            "Derived from naming enhancement."
                            if mapping_result is None
                            else "Derived from naming enhancement after rejecting a low-confidence standard mapping candidate."
                        ),
                    )
                else:
                    if not keep_unmapped_fields:
                        continue
                    field_suggestion = self.build_stg_field_from_original(
                        table,
                        field,
                        raw_normalized_field_name,
                        "original_fallback",
                        (
                            "Fallback to normalized source field. Manual confirmation recommended."
                            if mapping_result is None
                            else "Fallback to normalized source field after rejecting a low-confidence standard mapping candidate."
                        ),
                    )

                learned_stg_field = lookup_learned_stg_field(
                    field.field_name,
                    learned_stg_memory,
                    source_table_name=table.table_name,
                )
                field_suggestion = apply_learned_stg_field(
                    field_suggestion,
                    learned_stg_field,
                )
                table_field_suggestions.append(field_suggestion)
                field_suggestions_flat.append(field_suggestion)

                object_name = f"{table.table_name}.{field.field_name}"
                if mapping_result is not None and mapping_result.match_score < self.mapping_use_threshold:
                    table_issue_flags.append("low_confidence_mapping_rejected")
                    issues.append(
                        self.build_issue(
                            issue_id=f"{self.skill_name}-low-confidence-{object_name}".replace(
                                " ",
                                "_",
                            ),
                            object_name=object_name,
                            issue_type="stg_field_low_confidence",
                            evidence=[
                                f"fallback_mapping_source={field_suggestion.mapping_source}",
                                f"rejected_standard_code={mapping_result.recommended_standard_code}",
                                f"match_score={mapping_result.match_score}",
                                f"match_reason={mapping_result.match_reason}",
                            ],
                            suggestion=(
                                "Review the low-confidence standard mapping candidate and confirm whether the fallback STG field name should be retained."
                            ),
                            confidence=max(0.5, min(0.8, mapping_result.match_score / 1.5)),
                        )
                    )
                elif mapping_result is not None and mapping_result.match_score < 0.9:
                    table_issue_flags.append("low_confidence_mapping")
                    issues.append(
                        self.build_issue(
                            issue_id=f"{self.skill_name}-low-confidence-{object_name}".replace(
                                " ",
                                "_",
                            ),
                            object_name=object_name,
                            issue_type="stg_field_low_confidence",
                            evidence=[
                                f"recommended_stg_field_name={field_suggestion.recommended_stg_field_name}",
                                f"mapping_source={field_suggestion.mapping_source}",
                                f"match_score={mapping_result.match_score}",
                                f"match_reason={mapping_result.match_reason}",
                            ],
                            suggestion=(
                                "Review the mapped standard field before confirming the STG field name."
                            ),
                            confidence=max(0.5, min(0.88, mapping_result.match_score / 1.5)),
                        )
                    )

                if reserved:
                    table_issue_flags.append("technical_reservation")
                    issues.append(
                        self.build_issue(
                            issue_id=f"{self.skill_name}-technical-{object_name}".replace(
                                " ",
                                "_",
                            ),
                            object_name=object_name,
                            issue_type="stg_field_technical_reservation",
                            evidence=[
                                f"source_field_name={field.field_name}",
                                f"reserved_type={reserved_type}",
                                f"recommended_stg_field_name={field_suggestion.recommended_stg_field_name}",
                            ],
                            suggestion=(
                                "Confirm whether this technical or audit field should remain in the STG structure."
                            ),
                            confidence=0.85,
                        )
                    )

                if field_suggestion.mapping_source != "standard_mapping":
                    table_issue_flags.append("fallback_field_review")

            deduped_flags = list(dict.fromkeys(table_issue_flags))
            summary = (
                f"Suggested {len(table_field_suggestions)} STG fields for source table "
                f"{table.table_name} with target table {recommended_table_name}."
            )
            stg_table_suggestion = StgTableSuggestion(
                source_table_name=table.table_name,
                recommended_stg_table_name=recommended_table_name,
                recommended_stg_table_name_cn=table.table_name_cn,
                field_suggestions=table_field_suggestions,
                summary=summary,
                issue_flags=deduped_flags,
            )
            stg_table_suggestions.append(stg_table_suggestion)

            if deduped_flags:
                manual_review_table_count += 1
                issues.append(
                    self.build_issue(
                        issue_id=f"{self.skill_name}-table-review-{table.table_name}".replace(
                            " ",
                            "_",
                        ),
                        object_name=table.table_name,
                        issue_type="stg_table_requires_manual_review",
                        evidence=[
                            f"recommended_stg_table_name={recommended_table_name}",
                            f"issue_flags={deduped_flags}",
                        ],
                        suggestion=(
                            "Review fallback fields, technical reservations, and low-confidence mappings before confirming the STG structure."
                        ),
                        confidence=0.82,
                    )
                )

        confirmed_stg_suggestions: list[StgFieldSuggestion] = []
        review_applied_count = 0
        if payload.apply_overrides:
            override_records = payload.override_records or load_stg_overrides()
            confirmed_stg_suggestions, review_applied_count, _ = (
                apply_stg_overrides_to_suggestions(field_suggestions_flat, override_records)
            )

        summary = (
            f"Generated {len(stg_table_suggestions)} STG table suggestions and "
            f"{len(field_suggestions_flat)} field suggestions. "
            f"{manual_review_table_count} tables require manual confirmation."
        )
        if payload.apply_overrides and review_applied_count:
            summary += f" Applied {review_applied_count} STG overrides."

        # TODO: extend STG structure generation with configurable split/merge rules and optional SQL skeleton generation.
        return StgStructureSuggestionOutput(
            stg_table_suggestions=stg_table_suggestions,
            field_suggestions_flat=field_suggestions_flat,
            confirmed_stg_suggestions=confirmed_stg_suggestions,
            issues=issues,
            review_applied_count=review_applied_count,
            summary=summary,
        )
