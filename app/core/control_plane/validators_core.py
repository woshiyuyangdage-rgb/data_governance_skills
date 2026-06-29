"""Core, registry, and dictionary asset validators."""

from typing import Any

from app.core.control_plane.validators_common import _records_from_content
from app.core.models.validation_result import ValidationResult


def _validate_workflow_profiles(content: Any) -> ValidationResult:
    asset_name = "workflow_profiles"
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(content, dict):
        return ValidationResult(
            asset_name=asset_name,
            is_valid=False,
            messages=["workflow_profiles must be a mapping."],
            warnings=[],
        )

    profiles = content.get("profiles")
    if not isinstance(profiles, list):
        errors.append("workflow_profiles must contain a 'profiles' list.")
        return ValidationResult(asset_name=asset_name, is_valid=False, messages=errors)

    names: list[str] = []
    for index, profile in enumerate(profiles):
        if not isinstance(profile, dict):
            errors.append(f"profile at index {index} must be a mapping.")
            continue
        for field_name in ["name", "enabled", "stages"]:
            if field_name not in profile:
                errors.append(f"profile at index {index} is missing '{field_name}'.")
        name = str(profile.get("name", "")).strip()
        if name:
            names.append(name)
        stages = profile.get("stages", [])
        if "stages" in profile and not isinstance(stages, list):
            errors.append(f"profile '{name or index}' must contain a stages list.")
        elif isinstance(stages, list) and not stages:
            warnings.append(f"profile '{name or index}' has an empty stages list.")

    duplicate_names = sorted({name for name in names if names.count(name) > 1})
    if duplicate_names:
        errors.append(
            f"workflow profile names must be unique: {', '.join(duplicate_names)}"
        )

    return ValidationResult(
        asset_name=asset_name,
        is_valid=not errors,
        messages=errors,
        warnings=warnings,
    )

def _validate_intent_patterns(content: Any) -> ValidationResult:
    asset_name = "intent_patterns"
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(content, dict):
        return ValidationResult(
            asset_name=asset_name,
            is_valid=False,
            messages=["intent_patterns must be a mapping."],
            warnings=[],
        )

    intents = content.get("intents")
    parameters = content.get("parameters")
    if not isinstance(intents, dict):
        errors.append("intent_patterns must contain an 'intents' mapping.")
    if not isinstance(parameters, dict):
        errors.append("intent_patterns must contain a 'parameters' mapping.")

    if isinstance(intents, dict):
        for intent_name, payload in intents.items():
            if not isinstance(payload, dict):
                errors.append(f"intent '{intent_name}' must be a mapping.")
                continue
            if not str(payload.get("profile_name", "")).strip():
                errors.append(f"intent '{intent_name}' must define profile_name.")
            keywords = payload.get("keywords")
            if not isinstance(keywords, list):
                errors.append(f"intent '{intent_name}' must define a keywords list.")
            elif not keywords:
                errors.append(f"intent '{intent_name}' must contain at least one keyword.")

    if isinstance(parameters, dict):
        for parameter_name, payload in parameters.items():
            if not isinstance(payload, dict):
                errors.append(f"parameter '{parameter_name}' must be a mapping.")
                continue
            keywords = payload.get("keywords")
            if not isinstance(keywords, list):
                errors.append(
                    f"parameter '{parameter_name}' must define a keywords list."
                )
            elif not keywords:
                warnings.append(
                    f"parameter '{parameter_name}' currently has no configured keywords."
                )

    return ValidationResult(
        asset_name=asset_name,
        is_valid=not errors,
        messages=errors,
        warnings=warnings,
    )


def _validate_intent_nlp_classifier(content: Any) -> ValidationResult:
    asset_name = "intent_nlp_classifier"
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(content, dict):
        return ValidationResult(
            asset_name=asset_name,
            is_valid=False,
            messages=["intent_nlp_classifier must be a mapping."],
            warnings=[],
        )

    if not isinstance(content.get("enabled"), bool):
        errors.append("intent_nlp_classifier must define enabled as a boolean.")

    if not isinstance(content.get("use_keyword_samples"), bool):
        errors.append(
            "intent_nlp_classifier must define use_keyword_samples as a boolean."
        )

    for field_name in ["min_similarity", "min_margin"]:
        value = content.get(field_name)
        if not isinstance(value, (int, float)):
            errors.append(
                f"intent_nlp_classifier must define a numeric '{field_name}'."
            )
        elif not 0.0 <= float(value) <= 1.0:
            errors.append(
                f"intent_nlp_classifier '{field_name}' must be between 0 and 1."
            )

    for field_name in ["ngram_min", "ngram_max"]:
        value = content.get(field_name)
        if not isinstance(value, int) or value < 1:
            errors.append(
                f"intent_nlp_classifier must define '{field_name}' as a positive integer."
            )

    examples = content.get("training_examples")
    if not isinstance(examples, list) or not examples:
        errors.append(
            "intent_nlp_classifier must define a non-empty training_examples list."
        )
    else:
        for index, example in enumerate(examples):
            if not isinstance(example, dict):
                errors.append(f"training example at index {index} must be a mapping.")
                continue
            if not str(example.get("intent_name", "")).strip():
                errors.append(
                    f"training example at index {index} must define intent_name."
                )
            if not str(example.get("text", "")).strip():
                errors.append(
                    f"training example at index {index} must define text."
                )
            inferred_parameters = example.get("inferred_parameters", {})
            if inferred_parameters and not isinstance(inferred_parameters, dict):
                errors.append(
                    f"training example at index {index} has invalid inferred_parameters."
                )

    if not examples:
        warnings.append("intent_nlp_classifier has no training examples configured.")

    return ValidationResult(
        asset_name=asset_name,
        is_valid=not errors,
        messages=errors,
        warnings=warnings,
    )

def _validate_tool_registry(content: Any) -> ValidationResult:
    asset_name = "tool_registry"
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(content, dict):
        return ValidationResult(
            asset_name=asset_name,
            is_valid=False,
            messages=["tool_registry must be a mapping."],
            warnings=[],
        )

    tools = content.get("tools")
    if not isinstance(tools, list):
        errors.append("tool_registry must contain a 'tools' list.")
        return ValidationResult(asset_name=asset_name, is_valid=False, messages=errors)

    names: list[str] = []
    for index, tool in enumerate(tools):
        if not isinstance(tool, dict):
            errors.append(f"tool at index {index} must be a mapping.")
            continue
        for field_name in ["name", "handler", "enabled"]:
            if field_name not in tool:
                errors.append(f"tool at index {index} is missing '{field_name}'.")
        name = str(tool.get("name", "")).strip()
        if name:
            names.append(name)
        if not str(tool.get("handler", "")).strip():
            errors.append(f"tool '{name or index}' must define a non-empty handler.")

    duplicate_names = sorted({name for name in names if names.count(name) > 1})
    if duplicate_names:
        errors.append(f"tool names must be unique: {', '.join(duplicate_names)}")

    return ValidationResult(
        asset_name=asset_name,
        is_valid=not errors,
        messages=errors,
        warnings=warnings,
    )

def _validate_abbreviation_dict(content: Any) -> ValidationResult:
    asset_name = "abbreviation_dict"
    errors: list[str] = []
    records = _records_from_content(content)
    if not records:
        return ValidationResult(
            asset_name=asset_name,
            is_valid=False,
            messages=["abbreviation_dict cannot be empty."],
        )

    required_columns = {"abbreviation", "expanded_form"}
    available_columns = set(records[0].keys())
    missing = sorted(required_columns - available_columns)
    if missing:
        errors.append(
            f"abbreviation_dict is missing required columns: {', '.join(missing)}"
        )
    for index, record in enumerate(records):
        if not str(record.get("abbreviation", "")).strip():
            errors.append(f"row {index} has an empty abbreviation value.")

    return ValidationResult(asset_name=asset_name, is_valid=not errors, messages=errors)

def _validate_root_word_dict(content: Any) -> ValidationResult:
    asset_name = "root_word_dict"
    errors: list[str] = []
    records = _records_from_content(content)
    if not records:
        return ValidationResult(
            asset_name=asset_name,
            is_valid=False,
            messages=["root_word_dict cannot be empty."],
        )

    required_columns = {"token", "normalized_form"}
    available_columns = set(records[0].keys())
    missing = sorted(required_columns - available_columns)
    if missing:
        errors.append(
            f"root_word_dict is missing required columns: {', '.join(missing)}"
        )

    return ValidationResult(asset_name=asset_name, is_valid=not errors, messages=errors)

def _validate_standard_fields(content: Any) -> ValidationResult:
    asset_name = "standard_fields"
    errors: list[str] = []
    records = _records_from_content(content)
    if not records:
        return ValidationResult(
            asset_name=asset_name,
            is_valid=False,
            messages=["standard_fields cannot be empty."],
        )

    required_columns = {"standard_code", "standard_name", "standard_name_cn"}
    available_columns = set(records[0].keys())
    missing = sorted(required_columns - available_columns)
    if missing:
        errors.append(
            f"standard_fields is missing required columns: {', '.join(missing)}"
        )

    standard_codes: list[str] = []
    for index, record in enumerate(records):
        code = str(record.get("standard_code", "")).strip()
        if not code:
            errors.append(f"row {index} has an empty standard_code value.")
        else:
            standard_codes.append(code)

    duplicate_codes = sorted(
        {code for code in standard_codes if standard_codes.count(code) > 1}
    )
    if duplicate_codes:
        errors.append(
            f"standard_fields standard_code values must be unique: {', '.join(duplicate_codes)}"
        )

    return ValidationResult(asset_name=asset_name, is_valid=not errors, messages=errors)


def _validate_standard_mapping_semantic(content: Any) -> ValidationResult:
    asset_name = "standard_mapping_semantic"
    errors: list[str] = []

    if not isinstance(content, dict):
        return ValidationResult(
            asset_name=asset_name,
            is_valid=False,
            messages=["standard_mapping_semantic must be a mapping."],
        )

    if not isinstance(content.get("enabled"), bool):
        errors.append("standard_mapping_semantic must define enabled as a boolean.")

    model_name_or_path = str(content.get("model_name_or_path", "")).strip()
    if not model_name_or_path:
        errors.append(
            "standard_mapping_semantic must define a non-empty model_name_or_path."
        )

    if not isinstance(content.get("local_files_only"), bool):
        errors.append(
            "standard_mapping_semantic must define local_files_only as a boolean."
        )

    threshold = content.get("threshold")
    if not isinstance(threshold, (int, float)):
        errors.append("standard_mapping_semantic must define a numeric threshold.")
    elif not 0.0 <= float(threshold) <= 1.0:
        errors.append("standard_mapping_semantic threshold must be between 0 and 1.")

    candidate_limit = content.get("candidate_limit")
    if not isinstance(candidate_limit, int) or candidate_limit < 1:
        errors.append(
            "standard_mapping_semantic must define candidate_limit as a positive integer."
        )

    for field_name in ["standard_text_fields", "source_text_fields"]:
        field_values = content.get(field_name)
        if not isinstance(field_values, list) or not field_values:
            errors.append(
                f"standard_mapping_semantic must define a non-empty '{field_name}' list."
            )
            continue
        for index, value in enumerate(field_values):
            if not str(value).strip():
                errors.append(
                    f"standard_mapping_semantic '{field_name}' item at index {index} must be a non-empty string."
                )

    return ValidationResult(asset_name=asset_name, is_valid=not errors, messages=errors)

CORE_VALIDATORS = {
    "workflow_profiles": _validate_workflow_profiles,
    "intent_patterns": _validate_intent_patterns,
    "intent_nlp_classifier": _validate_intent_nlp_classifier,
    "tool_registry": _validate_tool_registry,
    "abbreviation_dict": _validate_abbreviation_dict,
    "root_word_dict": _validate_root_word_dict,
    "standard_fields": _validate_standard_fields,
    "standard_mapping_semantic": _validate_standard_mapping_semantic,
}
