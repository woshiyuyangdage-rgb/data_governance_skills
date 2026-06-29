"""Evidence-based field description and table summary enrichment."""

from collections import Counter

from pydantic import BaseModel, Field

from app.core.models.semantic_enrichment_result import (
    FieldDescriptionSuggestion,
    TableSemanticSummary,
)
from app.core.models.table_meta import TableMeta
from app.core.normalize import clean_text, expand_tokens, normalize_tokens, split_tokens
from app.core.skills.base_skill import BaseSkill

PLACEHOLDER_DESCRIPTIONS = {
    "todo",
    "tbd",
    "n/a",
    "na",
    "none",
    "null",
    "-",
    "same as name",
}
TECHNICAL_DESCRIPTION_TOKENS = {
    "etl",
    "job",
    "batch",
    "tmp",
    "temp",
    "flag",
    "interface",
    "sync",
}
GENERIC_TOKENS = {
    "field",
    "column",
    "data",
    "value",
    "info",
    "information",
    "record",
}
IDENTIFIER_TOKENS = {"id", "identifier", "number", "no", "code"}
AMOUNT_TOKENS = {"amount", "amt", "balance", "money", "price", "rate"}
DATE_TOKENS = {"date", "dt", "time", "timestamp", "created", "updated"}
STATUS_TOKENS = {"status", "state", "flag", "type", "category"}
BUSINESS_OBJECT_TOKENS = {
    "account",
    "application",
    "approval",
    "audit",
    "contract",
    "customer",
    "invoice",
    "loan",
    "merchant",
    "order",
    "payment",
    "product",
    "repayment",
    "transaction",
    "user",
}
SCENARIO_BY_OBJECT = {
    "account": ["account lookup", "account reconciliation", "customer servicing"],
    "application": ["application review", "approval tracking", "risk analysis"],
    "contract": ["contract lookup", "business tracking", "risk analysis", "operating statistics"],
    "customer": ["customer profile", "customer lookup", "risk analysis", "operating statistics"],
    "invoice": ["invoice query", "reconciliation", "regulatory reporting"],
    "loan": ["loan tracking", "repayment analysis", "risk monitoring"],
    "merchant": ["merchant management", "transaction analysis", "risk monitoring"],
    "order": ["order query", "transaction analysis", "operating statistics"],
    "payment": ["payment tracking", "reconciliation", "risk monitoring"],
    "product": ["product catalog", "operating analysis", "business reporting"],
    "repayment": ["repayment tracking", "overdue analysis", "risk monitoring"],
    "transaction": ["transaction query", "reconciliation", "operating statistics"],
}
PURPOSE_BY_OBJECT = {
    "account": "record and manage account-level information",
    "application": "support application and approval process tracking",
    "contract": "record and manage contract master information",
    "customer": "record and manage customer master information",
    "invoice": "record invoice and settlement information",
    "loan": "track loan business information",
    "merchant": "record and manage merchant information",
    "order": "store order and transaction information",
    "payment": "track payment and settlement activities",
    "product": "record product catalog and product attributes",
    "repayment": "track repayment activities and repayment status",
    "transaction": "store business transaction records",
}


class MetadataSemanticEnrichmentInput(BaseModel):
    """Input for evidence-based semantic enrichment."""

    tables: list[TableMeta] = Field(default_factory=list)


class MetadataSemanticEnrichmentOutput(BaseModel):
    """Output for field descriptions and table summaries."""

    field_description_suggestions: list[FieldDescriptionSuggestion] = Field(
        default_factory=list
    )
    table_semantic_summaries: list[TableSemanticSummary] = Field(default_factory=list)
    summary: str = ""


class MetadataSemanticEnrichmentSkill(BaseSkill):
    """Generate low-hallucination descriptions and summaries from local evidence."""

    skill_name = "metadata_semantic_enrichment"
    version = "0.1.0"
    description = "Evidence-based field description and table semantic summary generation."

    @staticmethod
    def _optional_text(value: object) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        if not text or text.lower() in {"nan", "none", "null"}:
            return None
        return text

    @staticmethod
    def _tokens(*values: object) -> list[str]:
        tokens: list[str] = []
        for value in values:
            text = MetadataSemanticEnrichmentSkill._optional_text(value)
            if text:
                tokens.extend(split_tokens(text))
        return normalize_tokens(expand_tokens(tokens))

    @staticmethod
    def _display_name(name: str, name_cn: str | None = None) -> str:
        return name_cn or name.replace("_", " ")

    @staticmethod
    def _description_quality_tags(
        field_name: str,
        description: str | None,
        tokens: list[str],
    ) -> list[str]:
        tags: list[str] = []
        if not description:
            tags.append("description_missing")
        else:
            cleaned = clean_text(description)
            if len(cleaned) < 8:
                tags.append("description_too_short")
            if cleaned in PLACEHOLDER_DESCRIPTIONS:
                tags.append("description_placeholder")
            if cleaned == clean_text(field_name).replace("_", " "):
                tags.append("description_same_as_field_name")
            if set(split_tokens(description)).intersection(TECHNICAL_DESCRIPTION_TOKENS):
                tags.append("description_too_technical")
            if len(set(tokens).difference(GENERIC_TOKENS)) <= 1:
                tags.append("description_ambiguous")
        if not tags:
            tags.append("description_usable")
        return tags

    @staticmethod
    def _concept_phrase(tokens: list[str], fallback: str) -> str:
        meaningful = [
            token
            for token in tokens
            if token not in GENERIC_TOKENS and token not in {"created", "updated"}
        ]
        if not meaningful:
            return fallback.replace("_", " ")
        return " ".join(dict.fromkeys(meaningful[:4]))

    @staticmethod
    def _first_matching_business_object(tokens: list[str], fallback: str) -> str:
        for token in tokens:
            if token in BUSINESS_OBJECT_TOKENS:
                return token
        meaningful = [
            token
            for token in tokens
            if token not in GENERIC_TOKENS
            and token not in IDENTIFIER_TOKENS
            and token not in AMOUNT_TOKENS
            and token not in DATE_TOKENS
            and token not in STATUS_TOKENS
        ]
        return meaningful[0] if meaningful else fallback.replace("_", " ")

    @staticmethod
    def _field_label(field: object) -> str:
        return (
            getattr(field, "field_name_cn", None)
            or getattr(field, "standard_name", None)
            or getattr(field, "field_name", "")
        )

    @staticmethod
    def _is_core_field(field: object) -> bool:
        tokens = set(
            MetadataSemanticEnrichmentSkill._tokens(
                getattr(field, "field_name", ""),
                getattr(field, "field_name_cn", None),
                getattr(field, "standard_name", None),
            )
        )
        return bool(
            tokens.intersection(IDENTIFIER_TOKENS)
            or tokens.intersection(AMOUNT_TOKENS)
            or tokens.intersection(DATE_TOKENS)
            or tokens.intersection(STATUS_TOKENS)
            or getattr(field, "is_primary_key", None)
            or getattr(field, "is_foreign_key", None)
        )

    @staticmethod
    def _split_scenarios(text: str | None) -> list[str]:
        if not text:
            return []
        normalized = text.replace("|", ";").replace(",", ";").replace("\n", ";")
        return [item.strip() for item in normalized.split(";") if item.strip()]

    @classmethod
    def _business_purpose(cls, business_object: str, table: TableMeta) -> str:
        if table.table_description:
            return table.table_description
        purpose = PURPOSE_BY_OBJECT.get(business_object)
        if purpose:
            return purpose
        return f"describe and manage {business_object} related business information"

    @classmethod
    def _applicable_scenarios(
        cls,
        business_object: str,
        table: TableMeta,
        core_fields: list[str],
    ) -> list[str]:
        scenarios = cls._split_scenarios(table.usage_scenarios)
        scenarios.extend(SCENARIO_BY_OBJECT.get(business_object, []))
        field_text = " ".join(core_fields).lower()
        if any(token in field_text for token in ["amount", "amt", "balance"]):
            scenarios.append("operating statistics")
        if any(token in field_text for token in ["status", "state", "flag"]):
            scenarios.append("status tracking")
        if any(token in field_text for token in ["date", "time", "dt"]):
            scenarios.append("period analysis")
        if table.downstream_applications:
            scenarios.extend(
                f"{application} consumption"
                for application in table.downstream_applications
            )
        return list(dict.fromkeys(scenarios[:6]))

    @classmethod
    def _ai_usage_risks(
        cls,
        table: TableMeta,
        core_fields: list[str],
    ) -> list[str]:
        risks: list[str] = []
        table_name = clean_text(table.table_name)
        if any(token in table_name for token in ["tmp", "temp", "bak", "old", "his", "test"]):
            risks.append("technical or lifecycle table may be selected incorrectly")
        if not table.table_description:
            risks.append("table purpose is not explicitly described")
        if not table.business_domain:
            risks.append("business domain is missing")
        if any(getattr(field, "is_sensitive", None) for field in table.fields):
            risks.append("sensitive fields require access-control context")
        field_text = " ".join(core_fields).lower()
        if any(token in field_text for token in ["status", "state", "flag"]):
            risks.append("status or flag fields need enum definitions")
        if any(token in field_text for token in ["amount", "amt", "balance", "money"]):
            risks.append("amount fields need metric scope and unit confirmation")
        if not risks:
            risks.append("no obvious AI consumption risk detected")
        return risks

    @staticmethod
    def _recommended_actions(risks: list[str]) -> list[str]:
        actions: list[str] = []
        risk_text = " ".join(risks)
        if "purpose" in risk_text:
            actions.append("add a business table description")
        if "domain" in risk_text:
            actions.append("confirm the owning business domain")
        if "enum" in risk_text:
            actions.append("add status/flag enum definitions")
        if "amount" in risk_text or "unit" in risk_text:
            actions.append("document amount metric scope and unit")
        if "sensitive" in risk_text:
            actions.append("add sensitivity labels and access-control notes")
        if "lifecycle" in risk_text or "technical" in risk_text:
            actions.append("confirm lifecycle status before catalog exposure")
        if not actions:
            actions.append("keep summary available for catalog, RAG, and Text-to-SQL context")
        return list(dict.fromkeys(actions))

    @staticmethod
    def _field_kind(tokens: list[str], data_type: str | None) -> str:
        token_set = set(tokens)
        lowered_type = clean_text(data_type or "")
        if token_set.intersection(IDENTIFIER_TOKENS):
            return "identifier"
        if token_set.intersection(AMOUNT_TOKENS) or any(
            marker in lowered_type for marker in ["decimal", "numeric", "number", "float"]
        ):
            return "amount"
        if token_set.intersection(DATE_TOKENS) or any(
            marker in lowered_type for marker in ["date", "time", "timestamp"]
        ):
            return "time"
        if token_set.intersection(STATUS_TOKENS):
            return "status"
        return "business_attribute"

    @classmethod
    def _field_description(
        cls,
        table: TableMeta,
        field_name: str,
        field_name_cn: str | None,
        field_description: str | None,
        data_type: str | None,
        data_length: str | None,
        sample_values: str | None,
        business_domain: str | None,
        standard_code: str | None,
        standard_name: str | None,
    ) -> tuple[str, float, list[str], list[str], str, bool]:
        field_tokens = cls._tokens(field_name, field_name_cn, standard_name)
        quality_tags = cls._description_quality_tags(
            field_name,
            field_description,
            field_tokens,
        )
        evidence: list[str] = [f"field_name={field_name}"]
        score = 0.32

        if field_name_cn:
            evidence.append(f"field_name_cn={field_name_cn}")
            score += 0.14
        if table.table_name or table.table_name_cn:
            evidence.append(
                f"table={table.table_name_cn or table.table_name}"
            )
            score += 0.1
        if table.table_description:
            evidence.append(f"table_description={table.table_description}")
            score += 0.1
        if business_domain or table.business_domain:
            evidence.append(f"business_domain={business_domain or table.business_domain}")
            score += 0.08
        if data_type:
            evidence.append(f"data_type={data_type}")
            score += 0.05
        if data_length:
            evidence.append(f"data_length={data_length}")
            score += 0.02
        if sample_values:
            evidence.append(f"sample_values={sample_values}")
            score += 0.06
        if standard_code or standard_name:
            evidence.append(f"standard={standard_code or standard_name}")
            score += 0.12

        concept = cls._display_name(
            cls._concept_phrase(field_tokens, field_name),
            field_name_cn,
        )
        table_context = cls._display_name(table.table_name, table.table_name_cn)
        field_kind = cls._field_kind(field_tokens, data_type)
        context_phrase = (
            f" in the {business_domain or table.business_domain} domain"
            if business_domain or table.business_domain
            else ""
        )

        if field_kind == "identifier":
            generated = (
                f"Identifies the {concept} used by {table_context}{context_phrase}."
            )
        elif field_kind == "amount":
            generated = (
                f"Records the {concept} for {table_context}{context_phrase}."
            )
        elif field_kind == "time":
            generated = (
                f"Records the {concept} associated with {table_context}{context_phrase}."
            )
        elif field_kind == "status":
            generated = (
                f"Indicates the {concept} state or classification for {table_context}{context_phrase}."
            )
        else:
            generated = (
                f"Describes the {concept} attribute used by {table_context}{context_phrase}."
            )

        weak_context = not (field_name_cn or table.table_description or standard_code or standard_name)
        if weak_context:
            generated = (
                f"Likely describes the {concept} attribute for {table_context}; "
                "confirm the exact business meaning before adoption."
            )
            score = min(score, 0.55)
            quality_tags.append("description_needs_manual_confirmation")

        if "description_usable" in quality_tags and field_description:
            action = "keep_current"
        else:
            action = "auto_complete" if score >= 0.78 else "manual_review"

        requires_manual_review = score < 0.78 or weak_context or any(
            tag in quality_tags
            for tag in [
                "description_ambiguous",
                "description_placeholder",
                "description_too_technical",
            ]
        )
        if requires_manual_review and action == "auto_complete":
            action = "manual_review"
        if standard_code is None and standard_name is None:
            quality_tags.append("standard_reference_missing")

        return (
            generated,
            round(min(score, 0.95), 2),
            evidence,
            list(dict.fromkeys(quality_tags)),
            action,
            requires_manual_review,
        )

    @classmethod
    def _field_suggestion(
        cls,
        table: TableMeta,
        field: object,
    ) -> FieldDescriptionSuggestion:
        business_domain = getattr(field, "business_domain", None) or table.business_domain
        generated, confidence, evidence, quality_tags, action, manual_review = (
            cls._field_description(
                table=table,
                field_name=getattr(field, "field_name", ""),
                field_name_cn=getattr(field, "field_name_cn", None),
                field_description=getattr(field, "field_description", None),
                data_type=getattr(field, "data_type", None),
                data_length=getattr(field, "data_length", None),
                sample_values=getattr(field, "sample_values", None),
                business_domain=business_domain,
                standard_code=getattr(field, "standard_code", None),
                standard_name=getattr(field, "standard_name", None),
            )
        )
        original = cls._optional_text(getattr(field, "field_description", None))
        return FieldDescriptionSuggestion(
            table_name=table.table_name,
            field_name=getattr(field, "field_name", ""),
            field_name_cn=getattr(field, "field_name_cn", None),
            original_description=original,
            generated_description=generated,
            optimized_description=original if action == "keep_current" and original else generated,
            confidence=confidence,
            evidence=evidence,
            quality_tags=quality_tags,
            governance_action=action,
            requires_manual_review=manual_review,
            business_domain=business_domain,
            standard_code=getattr(field, "standard_code", None),
            standard_name=getattr(field, "standard_name", None),
        )

    @classmethod
    def _table_summary(cls, table: TableMeta) -> TableSemanticSummary:
        field_tokens = []
        for field in table.fields:
            field_tokens.extend(
                cls._tokens(
                    getattr(field, "field_name", ""),
                    getattr(field, "field_name_cn", None),
                    getattr(field, "field_description", None),
                    getattr(field, "standard_name", None),
                )
            )
        token_counts = Counter(
            token
            for token in field_tokens
            if token not in GENERIC_TOKENS and token not in IDENTIFIER_TOKENS
        )
        key_concepts = [token for token, _ in token_counts.most_common(5)]
        table_tokens = cls._tokens(
            table.table_name,
            table.table_name_cn,
            table.table_description,
            table.business_domain,
            table.usage_scenarios,
        )
        business_object = cls._first_matching_business_object(
            [*table_tokens, *key_concepts],
            table.table_name,
        )
        core_fields = [
            cls._field_label(field)
            for field in table.fields
            if cls._is_core_field(field)
        ]
        if not core_fields:
            core_fields = [
                cls._field_label(field)
                for field in table.fields[:5]
            ]
        core_fields = list(dict.fromkeys([field for field in core_fields if field]))[:8]
        business_purpose = cls._business_purpose(business_object, table)
        applicable_scenarios = cls._applicable_scenarios(
            business_object,
            table,
            core_fields,
        )
        ai_usage_risks = cls._ai_usage_risks(table, core_fields)
        recommended_actions = cls._recommended_actions(ai_usage_risks)
        table_label = cls._display_name(table.table_name, table.table_name_cn)
        domain_phrase = (
            f" in the {table.business_domain} domain" if table.business_domain else ""
        )
        core_field_phrase = ", ".join(core_fields[:5]) or "core fields"
        scenario_phrase = ", ".join(applicable_scenarios[:4]) or "business analysis"
        risk_phrase = "; ".join(ai_usage_risks[:3])
        generated = (
            f"Represents {table_label}{domain_phrase}. The core business object is "
            f"{business_object}. It is used to {business_purpose}. Core fields include "
            f"{core_field_phrase}. It can support {scenario_phrase}. AI use should note: "
            f"{risk_phrase}."
        )
        evidence = [f"table_name={table.table_name}", f"field_count={len(table.fields)}"]
        confidence = 0.36
        quality_tags: list[str] = []

        if table.table_name_cn:
            evidence.append(f"table_name_cn={table.table_name_cn}")
            confidence += 0.1
        if table.table_description:
            evidence.append(f"table_description={table.table_description}")
            confidence += 0.16
            quality_tags.append("table_description_usable")
        else:
            quality_tags.append("table_description_missing")
        if table.business_domain:
            evidence.append(f"business_domain={table.business_domain}")
            confidence += 0.1
        if table.system_name:
            evidence.append(f"upstream_system={table.system_name}")
            confidence += 0.03
        if table.upstream_systems:
            evidence.append(f"upstream_systems={', '.join(table.upstream_systems)}")
            confidence += 0.03
        if table.downstream_applications:
            evidence.append(
                f"downstream_applications={', '.join(table.downstream_applications)}"
            )
            confidence += 0.03
        if table.data_layer:
            evidence.append(f"data_layer={table.data_layer}")
            confidence += 0.02
        if table.primary_key_fields:
            evidence.append(f"primary_key_fields={', '.join(table.primary_key_fields)}")
            confidence += 0.03
        if table.foreign_key_fields:
            evidence.append(f"foreign_key_fields={', '.join(table.foreign_key_fields)}")
            confidence += 0.02
        if table.usage_scenarios:
            evidence.append(f"usage_scenarios={table.usage_scenarios}")
            confidence += 0.04
        if table.frequent_query_sql:
            evidence.append("frequent_query_sql=available")
            confidence += 0.03
        if key_concepts:
            evidence.append(f"key_concepts={', '.join(key_concepts)}")
            confidence += min(0.16, 0.04 * len(key_concepts))
        if core_fields:
            evidence.append(f"core_fields={', '.join(core_fields)}")
            confidence += min(0.08, 0.02 * len(core_fields))
        if len(table.fields) < 2:
            quality_tags.append("table_summary_low_field_evidence")
            confidence = min(confidence, 0.58)

        requires_manual_review = (
            confidence < 0.75
            or not table.table_description
            or any(
                risk != "no obvious AI consumption risk detected"
                for risk in ai_usage_risks
            )
        )
        action = "keep_current" if table.table_description and not requires_manual_review else "manual_review"
        optimized = generated

        return TableSemanticSummary(
            table_name=table.table_name,
            table_name_cn=table.table_name_cn,
            original_description=table.table_description,
            business_object=business_object,
            business_purpose=business_purpose,
            core_fields=core_fields,
            applicable_scenarios=applicable_scenarios,
            ai_usage_risks=ai_usage_risks,
            recommended_actions=recommended_actions,
            generated_summary=generated,
            optimized_summary=optimized,
            confidence=round(min(confidence, 0.95), 2),
            evidence=evidence,
            quality_tags=list(dict.fromkeys(quality_tags)),
            governance_action=action,
            requires_manual_review=requires_manual_review,
            business_domain=table.business_domain,
            key_concepts=key_concepts,
        )

    def run(
        self,
        payload: MetadataSemanticEnrichmentInput,
    ) -> MetadataSemanticEnrichmentOutput:
        """Generate field descriptions and table summaries from available evidence."""
        field_suggestions = [
            self._field_suggestion(table, field)
            for table in payload.tables
            for field in table.fields
        ]
        table_summaries = [self._table_summary(table) for table in payload.tables]
        manual_count = sum(
            1
            for item in [*field_suggestions, *table_summaries]
            if item.requires_manual_review
        )
        return MetadataSemanticEnrichmentOutput(
            field_description_suggestions=field_suggestions,
            table_semantic_summaries=table_summaries,
            summary=(
                f"Generated {len(field_suggestions)} field description suggestions "
                f"and {len(table_summaries)} table semantic summaries; "
                f"{manual_count} items require manual review."
            ),
        )
