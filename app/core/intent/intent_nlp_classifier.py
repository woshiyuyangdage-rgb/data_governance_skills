"""Local lightweight NLP intent classifier for governance requests."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
import math
from typing import Iterable

from app.core.intent.intent_loader import get_intent_definitions
from app.core.normalize import clean_text
from app.core.rules.config_loader import load_yaml_config


@dataclass(frozen=True)
class IntentNlpMatch:
    """Nearest local training signal for one natural-language request."""

    intent_name: str
    similarity: float
    margin: float
    matched_text: str
    inferred_parameters: dict[str, object]


@dataclass(frozen=True)
class _TrainingExample:
    intent_name: str
    text: str
    inferred_parameters: dict[str, object]
    vector: dict[str, float]


def _safe_int(value: object, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _safe_float(value: object, default: float) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _safe_bool(value: object, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _classifier_config() -> dict[str, object]:
    try:
        config = load_yaml_config("intent_nlp_classifier.yaml")
    except FileNotFoundError:
        return {}
    return config if isinstance(config, dict) else {}


def _ngrams(text: str, *, ngram_min: int, ngram_max: int) -> tuple[str, ...]:
    normalized = clean_text(text)
    compact = "".join(normalized.split())
    tokens: list[str] = []

    words = [word for word in normalized.split(" ") if word]
    tokens.extend(words)

    for source in [compact, *words]:
        if not source:
            continue
        if len(source) < ngram_min:
            tokens.append(source)
            continue
        upper = min(ngram_max, len(source))
        for size in range(max(1, ngram_min), upper + 1):
            tokens.extend(
                source[index : index + size]
                for index in range(0, len(source) - size + 1)
            )
    return tuple(tokens)


def _vectorize(text: str, *, ngram_min: int, ngram_max: int) -> dict[str, float]:
    counts = Counter(_ngrams(text, ngram_min=ngram_min, ngram_max=ngram_max))
    norm = math.sqrt(sum(count * count for count in counts.values()))
    if norm == 0:
        return {}
    return {token: count / norm for token, count in counts.items()}


def _cosine(left: dict[str, float], right: dict[str, float]) -> float:
    if not left or not right:
        return 0.0
    if len(left) > len(right):
        left, right = right, left
    return sum(value * right.get(token, 0.0) for token, value in left.items())


def _configured_training_examples(
    config: dict[str, object],
) -> Iterable[tuple[str, str, dict[str, object]]]:
    examples = config.get("training_examples", [])
    if not isinstance(examples, list):
        return
    for example in examples:
        if not isinstance(example, dict):
            continue
        intent_name = str(example.get("intent_name", "")).strip()
        text = str(example.get("text", "")).strip()
        if not intent_name or not text:
            continue
        inferred_parameters = example.get("inferred_parameters", {})
        yield (
            intent_name,
            text,
            dict(inferred_parameters) if isinstance(inferred_parameters, dict) else {},
        )


def _keyword_training_examples() -> Iterable[tuple[str, str, dict[str, object]]]:
    for intent_name, payload in get_intent_definitions().items():
        keywords = payload.get("keywords", [])
        if not isinstance(keywords, list):
            continue
        for keyword in keywords:
            text = str(keyword).strip()
            if text:
                yield intent_name, text, {}


@lru_cache(maxsize=1)
def _training_index() -> tuple[_TrainingExample, ...]:
    config = _classifier_config()
    if not _safe_bool(config.get("enabled"), True):
        return ()

    ngram_min = max(1, _safe_int(config.get("ngram_min"), 2))
    ngram_max = max(ngram_min, _safe_int(config.get("ngram_max"), 4))
    examples: list[_TrainingExample] = []
    seen: set[tuple[str, str]] = set()

    raw_examples = list(_configured_training_examples(config))
    if _safe_bool(config.get("use_keyword_samples"), True):
        raw_examples.extend(_keyword_training_examples())

    for intent_name, text, inferred_parameters in raw_examples:
        cleaned_text = clean_text(text)
        if not cleaned_text:
            continue
        key = (intent_name, cleaned_text)
        if key in seen:
            continue
        seen.add(key)
        vector = _vectorize(
            cleaned_text,
            ngram_min=ngram_min,
            ngram_max=ngram_max,
        )
        if not vector:
            continue
        examples.append(
            _TrainingExample(
                intent_name=intent_name,
                text=text,
                inferred_parameters=inferred_parameters,
                vector=vector,
            )
        )
    return tuple(examples)


def clear_intent_nlp_classifier_cache() -> None:
    """Clear cached local NLP classifier artifacts."""
    _training_index.cache_clear()


def classify_intent_text(text: str) -> IntentNlpMatch | None:
    """Classify text with local n-gram similarity over configured examples."""
    config = _classifier_config()
    if not _safe_bool(config.get("enabled"), True):
        return None

    ngram_min = max(1, _safe_int(config.get("ngram_min"), 2))
    ngram_max = max(ngram_min, _safe_int(config.get("ngram_max"), 4))
    min_similarity = _safe_float(config.get("min_similarity"), 0.42)
    min_margin = _safe_float(config.get("min_margin"), 0.02)

    query_vector = _vectorize(
        text,
        ngram_min=ngram_min,
        ngram_max=ngram_max,
    )
    if not query_vector:
        return None

    ranked = sorted(
        (
            (_cosine(query_vector, example.vector), example)
            for example in _training_index()
        ),
        key=lambda item: item[0],
        reverse=True,
    )
    if not ranked:
        return None

    best_similarity, best_example = ranked[0]
    second_similarity = ranked[1][0] if len(ranked) > 1 else 0.0
    margin = best_similarity - second_similarity
    if best_similarity < min_similarity or margin < min_margin:
        return None

    return IntentNlpMatch(
        intent_name=best_example.intent_name,
        similarity=round(best_similarity, 4),
        margin=round(margin, 4),
        matched_text=best_example.text,
        inferred_parameters=dict(best_example.inferred_parameters),
    )
