"""Rule-based domain governance pack matcher."""

from app.core.domain.domain_pack_loader import (
    get_domain_pack,
    list_enabled_domain_packs,
)
from app.core.models.domain_governance_pack import DomainGovernancePack
from app.core.models.domain_pack_match_result import DomainPackMatchResult
from app.core.models.table_meta import TableMeta
from app.core.normalize import clean_text


class DomainPackMatcher:
    """Match domain packs using explicit tokens from metadata text."""

    @staticmethod
    def _tables_to_text(tables: list[TableMeta]) -> str:
        parts: list[str] = []
        for table in tables:
            parts.extend(
                [
                    table.table_name,
                    table.table_name_cn or "",
                    table.table_description or "",
                    table.schema_name or "",
                    table.system_name or "",
                ]
            )
            for field in table.fields:
                parts.extend(
                    [
                        field.field_name,
                        field.field_name_cn or "",
                        field.field_description or "",
                    ]
                )
        return " ".join(parts)

    def match_domain_pack_from_text(self, text: str) -> DomainPackMatchResult:
        """Match a domain pack from free text."""
        cleaned = clean_text(text or "")
        best_pack: DomainGovernancePack | None = None
        best_tokens: list[str] = []
        for pack in list_enabled_domain_packs():
            matched = [
                token
                for token in pack.trigger_tokens
                if clean_text(token) and clean_text(token) in cleaned
            ]
            if len(matched) > len(best_tokens):
                best_pack = pack
                best_tokens = matched
        if best_pack is None:
            return DomainPackMatchResult(
                fallback_used=True,
                confidence=0.0,
                message="No domain governance pack matched the provided text.",
            )
        confidence = min(1.0, max(0.3, len(best_tokens) / max(1, len(best_pack.trigger_tokens))))
        return DomainPackMatchResult(
            matched_pack_name=best_pack.pack_name,
            confidence=round(confidence, 2),
            matched_tokens=best_tokens,
            fallback_used=False,
            message=f"Matched domain pack '{best_pack.pack_name}'.",
        )

    def match_domain_pack_from_tables(
        self,
        tables: list[TableMeta],
    ) -> DomainPackMatchResult:
        """Match a domain pack from parsed table metadata."""
        return self.match_domain_pack_from_text(self._tables_to_text(tables))

    @staticmethod
    def apply_domain_pack_hints(
        payload: dict[str, object],
        domain_pack_name: str | None = None,
    ) -> dict[str, object]:
        """Attach domain pack hints to a payload without changing core logic."""
        if not domain_pack_name:
            return dict(payload)
        pack = get_domain_pack(domain_pack_name)
        enriched = dict(payload)
        enriched["domain_pack_name"] = pack.pack_name
        enriched["domain_pack_hints"] = {
            "preferred_group_by": pack.preferred_group_by,
            "default_owner_roles": pack.default_owner_roles,
            "mapping_hints": pack.mapping_hints,
            "quality_rule_hints": pack.quality_rule_hints,
            "cross_field_hints": pack.cross_field_hints,
            "remediation_hints": pack.remediation_hints,
        }
        return enriched

