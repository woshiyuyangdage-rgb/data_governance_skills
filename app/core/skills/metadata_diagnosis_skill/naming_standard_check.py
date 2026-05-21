"""Rule-based v1 skill for naming standard checks with knowledge-pack support."""

import re
from functools import lru_cache

from pydantic import BaseModel, Field

from app.core.knowledge.knowledge_loader import (
    load_abbreviation_dict,
    load_root_word_dict,
)
from app.core.models.issue import Issue
from app.core.models.table_meta import TableMeta
from app.core.normalize import (
    clean_text,
    expand_tokens_with_evidence,
    normalize_tokens,
    split_tokens,
)
from app.core.rules.config_loader import get_issue_severity, get_naming_rules_config
from app.core.skills.base_skill import BaseSkill

try:
    from thefuzz import fuzz, process
except Exception:  # pragma: no cover - optional dependency fallback
    fuzz = None  # type: ignore[assignment]
    process = None  # type: ignore[assignment]

SPELLING_ISSUE_TYPE = "naming_suspected_spelling_error"


@lru_cache(maxsize=1)
def _spellcheck_candidates() -> tuple[str, ...]:
    dataframe = load_root_word_dict()
    candidates: list[str] = []
    for column_name in ("token", "normalized_form"):
        if column_name not in dataframe:
            continue
        for value in dataframe[column_name]:
            candidate = str(value).strip().lower()
            if candidate and candidate != "nan":
                candidates.append(candidate)
    return tuple(dict.fromkeys(candidates))


def clear_naming_standard_check_caches() -> None:
    """Clear cached naming-analysis helpers."""
    _spellcheck_candidates.cache_clear()


def _edit_distance(left: str, right: str) -> int:
    """Return a small edit distance that also counts adjacent transpositions."""
    if left == right:
        return 0
    if not left:
        return len(right)
    if not right:
        return len(left)

    previous_previous_row: list[int] | None = None
    previous_row = list(range(len(right) + 1))
    for i, left_char in enumerate(left, start=1):
        current_row = [i] + [0] * len(right)
        for j, right_char in enumerate(right, start=1):
            deletion = previous_row[j] + 1
            insertion = current_row[j - 1] + 1
            substitution = previous_row[j - 1] + (left_char != right_char)
            current_row[j] = min(deletion, insertion, substitution)

            if (
                previous_previous_row is not None
                and i > 1
                and j > 1
                and left_char == right[j - 2]
                and left[i - 2] == right_char
            ):
                current_row[j] = min(current_row[j], previous_previous_row[j - 2] + 1)

        previous_previous_row, previous_row = previous_row, current_row

    return previous_row[-1]


class NamingStandardCheckInput(BaseModel):
    """Input schema for naming standard checks."""

    tables: list[TableMeta] = Field(default_factory=list)


class NamingStandardCheckOutput(BaseModel):
    """Output schema for naming standard checks."""

    table_name_suggestions: dict[str, str] = Field(default_factory=dict)
    field_name_suggestions: dict[str, str] = Field(default_factory=dict)
    normalized_tokens: dict[str, list[str]] = Field(default_factory=dict)
    expanded_tokens: dict[str, list[str]] = Field(default_factory=dict)
    token_evidence: dict[str, list[str]] = Field(default_factory=dict)
    issues: list[Issue] = Field(default_factory=list)
    summary: str = ""


class NamingStandardCheckSkill(BaseSkill):
    """Evaluate names against simple configurable naming rules."""

    skill_name = "naming_standard_check"
    version = "0.4.0"
    description = (
        "Rule-based v1 naming checks with token analysis, fuzzy typo detection, "
        "and knowledge-pack suggestions."
    )

    @staticmethod
    def check_snake_case(name: str) -> bool:
        """Return whether a name follows basic snake_case."""
        return bool(re.fullmatch(r"[a-z][a-z0-9_]*", name.strip()))

    @staticmethod
    def _combine_prefixes(rule_config: dict[str, object], object_type: str) -> list[str]:
        shared_prefixes = list(rule_config.get("disallowed_prefixes", []))
        specific_key = (
            "disallowed_table_prefixes" if object_type == "table" else "disallowed_field_prefixes"
        )
        specific_prefixes = list(rule_config.get(specific_key, []))
        return list(dict.fromkeys(shared_prefixes + specific_prefixes))

    @classmethod
    def detect_disallowed_prefix(
        cls, name: str, rule_config: dict[str, object], object_type: str
    ) -> str | None:
        """Return the detected disallowed prefix if present."""
        lowered_name = name.strip().lower()
        for prefix in cls._combine_prefixes(rule_config, object_type):
            if lowered_name.startswith(prefix.lower()):
                return prefix
        return None

    @classmethod
    def normalize_name(
        cls, raw_name: str, rule_config: dict[str, object], object_type: str
    ) -> str:
        """Return a normalized suggestion based on configured naming rules."""
        normalized = raw_name.strip()

        if rule_config.get("replace_spaces_with_underscore", True):
            normalized = normalized.replace(" ", "_")
        if rule_config.get("normalize_to_lowercase", True):
            normalized = normalized.lower()
        if rule_config.get("compress_repeated_underscores", True):
            normalized = re.sub(r"_+", "_", normalized)

        detected_prefix = cls.detect_disallowed_prefix(normalized, rule_config, object_type)
        if detected_prefix:
            normalized = normalized[len(detected_prefix) :]

        normalized = normalized.strip("_")
        return normalized or raw_name.strip().lower()

    @staticmethod
    def _build_issue(
        issue_id: str,
        object_type: str,
        object_name: str,
        issue_type: str,
        evidence: list[str],
        suggestion_name: str,
        confidence: float = 0.82,
    ) -> Issue:
        return Issue(
            issue_id=issue_id,
            object_type=object_type,
            object_name=object_name,
            issue_type=issue_type,
            severity=get_issue_severity(issue_type),
            evidence=evidence + [f"suggested_name={suggestion_name}"],
            suggestion=f"Consider renaming to '{suggestion_name}'.",
            confidence=confidence,
        )

    @staticmethod
    def _dictionary_token_set() -> set[str]:
        abbreviation_df = load_abbreviation_dict()
        root_word_df = load_root_word_dict()
        tokens = set(abbreviation_df["abbreviation"].str.lower())
        tokens.update(abbreviation_df["expanded_form"].str.lower())
        tokens.update(root_word_df["token"].str.lower())
        tokens.update(root_word_df["normalized_form"].str.lower())
        return tokens

    @staticmethod
    def _should_flag_unknown_token(token: str, dictionary_tokens: set[str]) -> bool:
        return token.isalpha() and len(token) >= 3 and token not in dictionary_tokens

    @classmethod
    def _detect_spelling_suspicions(
        cls,
        normalized_tokens: list[str],
        rule_config: dict[str, object],
    ) -> tuple[list[dict[str, object]], list[str], str | None]:
        if not rule_config.get("enable_spelling_detection", True):
            return [], list(normalized_tokens), None
        if process is None or fuzz is None:
            return [], list(normalized_tokens), None

        candidates = _spellcheck_candidates()
        if not candidates:
            return [], list(normalized_tokens), None

        min_length = int(rule_config.get("spelling_min_token_length", 4))
        max_distance = int(rule_config.get("spelling_max_edit_distance", 1))
        min_similarity = int(rule_config.get("spelling_min_similarity", 86))

        spell_matches: list[dict[str, object]] = []
        corrected_tokens = list(normalized_tokens)
        for index, token in enumerate(normalized_tokens):
            if len(token) < min_length or token in candidates:
                continue

            best_match = process.extractOne(token, candidates, scorer=fuzz.ratio)
            if best_match is None:
                continue

            candidate_token = str(best_match[0]).strip().lower()
            similarity = int(best_match[1])
            distance = _edit_distance(token, candidate_token)
            if distance > max_distance or similarity < min_similarity:
                continue

            spell_matches.append(
                {
                    "token": token,
                    "suggested_token": candidate_token,
                    "edit_distance": distance,
                    "similarity": similarity,
                }
            )
            corrected_tokens[index] = candidate_token

        if not spell_matches:
            return [], list(normalized_tokens), None

        return spell_matches, corrected_tokens, "_".join(corrected_tokens)

    def _analyze_name_tokens(
        self,
        raw_name: str,
        object_type: str,
        rule_config: dict[str, object],
        dictionary_tokens: set[str],
    ) -> dict[str, object]:
        base_normalized_name = self.normalize_name(raw_name, rule_config, object_type)
        cleaned_name = clean_text(base_normalized_name, lower=False)
        tokens = split_tokens(cleaned_name)
        expanded_tokens, expanded_pairs, expansion_evidence = expand_tokens_with_evidence(tokens)
        normalized_token_list = normalize_tokens(expanded_tokens)
        spelling_matches, corrected_tokens, spelling_suggestion = self._detect_spelling_suspicions(
            normalized_token_list,
            rule_config,
        )

        suggested_source_name = spelling_suggestion or "_".join(normalized_token_list)
        suggested_name = self.normalize_name(
            suggested_source_name or base_normalized_name,
            rule_config,
            object_type,
        )
        spelling_evidence = [
            (
                "possible spelling error: "
                f"'{match['token']}' -> '{match['suggested_token']}' "
                f"(edit_distance={match['edit_distance']}, similarity={match['similarity']})"
            )
            for match in spelling_matches
        ]
        token_evidence = [
            f"original_name={raw_name}",
            f"tokens={tokens}",
            f"expanded_tokens={expanded_tokens}",
            f"normalized_tokens={normalized_token_list}",
            f"suggested_name={suggested_name}",
        ] + expansion_evidence
        if spelling_evidence:
            token_evidence.extend(spelling_evidence)

        suspicious_tokens = {match["token"] for match in spelling_matches}

        unknown_tokens = [
            token
            for token in normalized_token_list
            if self._should_flag_unknown_token(token, dictionary_tokens)
            and token not in suspicious_tokens
        ]

        return {
            "base_normalized_name": base_normalized_name,
            "tokens": tokens,
            "expanded_tokens": expanded_tokens,
            "expanded_pairs": expanded_pairs,
            "normalized_tokens": normalized_token_list,
            "token_evidence": token_evidence,
            "suggested_name": suggested_name,
            "spelling_matches": spelling_matches,
            "corrected_tokens": corrected_tokens,
            "unknown_tokens": unknown_tokens,
        }

    def _check_name_rules(
        self,
        raw_name: str,
        object_type: str,
        object_key: str,
        issue_prefix: str,
        rule_config: dict[str, object],
        dictionary_tokens: set[str],
    ) -> tuple[str, list[Issue], dict[str, object]]:
        analysis = self._analyze_name_tokens(
            raw_name=raw_name,
            object_type=object_type,
            rule_config=rule_config,
            dictionary_tokens=dictionary_tokens,
        )
        suggestion_name = analysis["suggested_name"]
        token_evidence = analysis["token_evidence"]
        issues: list[Issue] = []
        invalid_patterns = [
            re.compile(pattern) for pattern in rule_config.get("invalid_patterns", [])
        ]
        max_length = int(rule_config.get("max_recommended_name_length", 30))
        disallowed_prefix = self.detect_disallowed_prefix(raw_name, rule_config, object_type)

        if " " in raw_name:
            issues.append(
                self._build_issue(
                    issue_id=f"{issue_prefix}-space",
                    object_type=object_type,
                    object_name=object_key,
                    issue_type="naming_contains_space",
                    evidence=[f"raw_name={raw_name}", "contains spaces"] + token_evidence,
                    suggestion_name=suggestion_name,
                )
            )

        if "__" in raw_name:
            issues.append(
                self._build_issue(
                    issue_id=f"{issue_prefix}-underscore",
                    object_type=object_type,
                    object_name=object_key,
                    issue_type="naming_contains_repeated_underscore",
                    evidence=[f"raw_name={raw_name}", "contains repeated underscores"] + token_evidence,
                    suggestion_name=suggestion_name,
                )
            )

        if any(character.isupper() for character in raw_name):
            issues.append(
                self._build_issue(
                    issue_id=f"{issue_prefix}-uppercase",
                    object_type=object_type,
                    object_name=object_key,
                    issue_type="naming_contains_uppercase",
                    evidence=[f"raw_name={raw_name}", "contains uppercase letters"] + token_evidence,
                    suggestion_name=suggestion_name,
                )
            )

        if disallowed_prefix:
            issues.append(
                self._build_issue(
                    issue_id=f"{issue_prefix}-prefix",
                    object_type=object_type,
                    object_name=object_key,
                    issue_type="naming_contains_disallowed_prefix",
                    evidence=[
                        f"raw_name={raw_name}",
                        f"disallowed_prefix={disallowed_prefix}",
                    ]
                    + token_evidence,
                    suggestion_name=suggestion_name,
                )
            )

        if len(raw_name.strip()) > max_length:
            issues.append(
                self._build_issue(
                    issue_id=f"{issue_prefix}-length",
                    object_type=object_type,
                    object_name=object_key,
                    issue_type="naming_too_long",
                    evidence=[
                        f"raw_name={raw_name}",
                        f"length={len(raw_name.strip())}",
                        f"max_recommended_name_length={max_length}",
                    ]
                    + token_evidence,
                    suggestion_name=suggestion_name,
                )
            )

        pattern_mismatch = any(pattern.search(raw_name) for pattern in invalid_patterns)
        if pattern_mismatch or not self.check_snake_case(analysis["base_normalized_name"]):
            issues.append(
                self._build_issue(
                    issue_id=f"{issue_prefix}-snake",
                    object_type=object_type,
                    object_name=object_key,
                    issue_type="naming_not_snake_case",
                    evidence=[
                        f"raw_name={raw_name}",
                        "name does not conform to configured snake_case style",
                    ]
                    + token_evidence,
                    suggestion_name=suggestion_name,
                )
            )

        if analysis["spelling_matches"]:
            issues.append(
                self._build_issue(
                    issue_id=f"{issue_prefix}-spelling",
                    object_type=object_type,
                    object_name=object_key,
                    issue_type=SPELLING_ISSUE_TYPE,
                    evidence=[
                        "fuzzy dictionary comparison found a likely spelling error",
                    ]
                    + [
                        (
                            f"token={match['token']} suggested_token={match['suggested_token']} "
                            f"edit_distance={match['edit_distance']} similarity={match['similarity']}"
                        )
                        for match in analysis["spelling_matches"]
                    ]
                    + token_evidence,
                    suggestion_name=suggestion_name,
                    confidence=0.74,
                )
            )

        if analysis["expanded_pairs"]:
            issues.append(
                self._build_issue(
                    issue_id=f"{issue_prefix}-abbreviation",
                    object_type=object_type,
                    object_name=object_key,
                    issue_type="naming_contains_ambiguous_abbreviation",
                    evidence=[
                        "contains known abbreviations that were expanded via knowledge packs",
                        f"expanded_pairs={analysis['expanded_pairs']}",
                    ]
                    + token_evidence,
                    suggestion_name=suggestion_name,
                    confidence=0.75,
                )
            )

        if analysis["unknown_tokens"]:
            issues.append(
                self._build_issue(
                    issue_id=f"{issue_prefix}-dictionary",
                    object_type=object_type,
                    object_name=object_key,
                    issue_type="naming_token_not_in_dictionary",
                    evidence=[
                        f"unknown_tokens={analysis['unknown_tokens']}",
                        "normalized tokens are not fully covered by current governance dictionaries",
                    ]
                    + token_evidence,
                    suggestion_name=suggestion_name,
                    confidence=0.68,
                )
            )

        return suggestion_name, issues, analysis

    def run(self, payload: NamingStandardCheckInput) -> NamingStandardCheckOutput:
        """Run rule-based v1 naming checks and generate normalization suggestions."""
        rule_config = get_naming_rules_config()
        dictionary_tokens = self._dictionary_token_set()
        table_name_suggestions: dict[str, str] = {}
        field_name_suggestions: dict[str, str] = {}
        normalized_tokens_map: dict[str, list[str]] = {}
        expanded_tokens_map: dict[str, list[str]] = {}
        token_evidence_map: dict[str, list[str]] = {}
        issues: list[Issue] = []
        abbreviation_hit_object_count = 0
        enhanced_suggestion_count = 0
        spelling_warning_object_count = 0

        for table_index, table in enumerate(payload.tables, start=1):
            raw_table_name = table.table_name or ""
            table_key = raw_table_name or f"table_{table_index}"
            table_suggestion, table_issues, table_analysis = self._check_name_rules(
                raw_name=raw_table_name,
                object_type="table",
                object_key=table_key,
                issue_prefix=f"{self.skill_name}-table-{table_index}",
                rule_config=rule_config,
                dictionary_tokens=dictionary_tokens,
            )

            normalized_tokens_map[table_key] = table_analysis["normalized_tokens"]
            expanded_tokens_map[table_key] = table_analysis["expanded_tokens"]
            token_evidence_map[table_key] = table_analysis["token_evidence"]
            if table_suggestion != raw_table_name.strip():
                table_name_suggestions[table_key] = table_suggestion
            if table_analysis["expanded_pairs"]:
                abbreviation_hit_object_count += 1
            if table_suggestion != table_analysis["base_normalized_name"]:
                enhanced_suggestion_count += 1
            if table_analysis["spelling_matches"]:
                spelling_warning_object_count += 1
            issues.extend(table_issues)

            for field_index, field in enumerate(table.fields, start=1):
                raw_field_name = field.field_name or ""
                field_key = f"{table_key}.{raw_field_name or f'field_{field_index}'}"
                field_suggestion, field_issues, field_analysis = self._check_name_rules(
                    raw_name=raw_field_name,
                    object_type="field",
                    object_key=field_key,
                    issue_prefix=f"{self.skill_name}-field-{table_index}-{field_index}",
                    rule_config=rule_config,
                    dictionary_tokens=dictionary_tokens,
                )

                normalized_tokens_map[field_key] = field_analysis["normalized_tokens"]
                expanded_tokens_map[field_key] = field_analysis["expanded_tokens"]
                token_evidence_map[field_key] = field_analysis["token_evidence"]
                if field_suggestion != raw_field_name.strip():
                    field_name_suggestions[field_key] = field_suggestion
                if field_analysis["expanded_pairs"]:
                    abbreviation_hit_object_count += 1
                if field_suggestion != field_analysis["base_normalized_name"]:
                    enhanced_suggestion_count += 1
                if field_analysis["spelling_matches"]:
                    spelling_warning_object_count += 1
                issues.extend(field_issues)

        # TODO: extend naming enhancement with domain-specific dictionaries and semantic disambiguation.
        return NamingStandardCheckOutput(
            table_name_suggestions=table_name_suggestions,
            field_name_suggestions=field_name_suggestions,
            normalized_tokens=normalized_tokens_map,
            expanded_tokens=expanded_tokens_map,
            token_evidence=token_evidence_map,
            issues=issues,
            summary=(
                f"Checked naming standards for {len(payload.tables)} tables, "
                f"hit abbreviations on {abbreviation_hit_object_count} objects, "
                f"flagged {spelling_warning_object_count} spelling-suspicion objects, "
                f"generated {enhanced_suggestion_count} enhanced token-based suggestions, "
                f"and produced {len(issues)} naming issues."
            ),
        )
