"""Semantic helpers for standard mapping recommendation."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np

try:
    from sentence_transformers import SentenceTransformer
except Exception:  # pragma: no cover - optional dependency fallback
    SentenceTransformer = None  # type: ignore[assignment]

from app.core.knowledge.knowledge_loader import load_standard_fields
from app.core.rules.config_loader import load_yaml_config

PROJECT_ROOT = Path(__file__).resolve().parents[4]
SEMANTIC_CONFIG_PATH = PROJECT_ROOT / "app" / "config" / "standard_mapping_semantic.yaml"
STANDARD_FIELDS_PATH = PROJECT_ROOT / "app" / "data" / "standards" / "standard_fields.csv"
SEMANTIC_CONFIG_NAME = "standard_mapping_semantic.yaml"


@dataclass(frozen=True)
class SemanticStandardCandidate:
    """Prepared semantic representation for one standard field."""

    standard_code: str
    standard_name: str
    standard_name_cn: str | None
    description: str | None
    data_type: str | None
    business_domain: str | None
    aliases: list[str]
    semantic_text: str


@dataclass(frozen=True)
class SemanticMatch:
    """One semantic nearest-neighbor result."""

    standard_code: str
    standard_name: str
    standard_name_cn: str | None
    score: float
    rank: int


@dataclass(frozen=True)
class SemanticFieldMatch:
    """One semantic recommendation for a source field."""

    field_text: str
    best_match: SemanticMatch | None
    top_matches: list[SemanticMatch]
    threshold: float
    enabled: bool


def _normalize_text(value: str | None) -> str:
    if value is None:
        return ""
    return " ".join(str(value).strip().split())


def _join_non_empty(values: list[str | None]) -> str:
    return " | ".join(
        item for item in (_normalize_text(value) for value in values) if item
    )


@lru_cache(maxsize=1)
def load_semantic_mapping_config() -> dict[str, Any]:
    """Load semantic mapping configuration."""
    try:
        config = load_yaml_config(SEMANTIC_CONFIG_NAME)
    except FileNotFoundError:
        return {
            "enabled": False,
            "model_name_or_path": "",
            "local_files_only": True,
            "threshold": 0.85,
            "candidate_limit": 3,
            "standard_text_fields": [
                "standard_name",
                "standard_name_cn",
                "description",
                "business_domain",
                "aliases",
            ],
            "source_text_fields": [
                "field_name",
                "field_name_cn",
                "field_description",
            ],
        }

    if not isinstance(config, dict):
        raise ValueError("standard_mapping_semantic.yaml must contain a mapping.")
    return config


def _is_enabled(config: dict[str, Any]) -> bool:
    return bool(config.get("enabled", False))


def _safe_int(value: object, default: int) -> int:
    try:
        return max(1, int(value))
    except Exception:
        return default


def _safe_float(value: object, default: float) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _file_signature(file_path: Path) -> str:
    try:
        stat = file_path.stat()
    except FileNotFoundError:
        return str(file_path)
    return f"{file_path.resolve()}::{stat.st_size}::{stat.st_mtime_ns}"


def _resolve_model_path(model_name_or_path: str) -> str:
    model_path = Path(model_name_or_path)
    if model_path.is_absolute():
        return str(model_path)

    project_model_path = PROJECT_ROOT / model_path
    if project_model_path.exists():
        return str(project_model_path)
    return model_name_or_path


@lru_cache(maxsize=1)
def _load_sentence_transformer(
    model_name_or_path: str,
    local_files_only: bool,
) -> SentenceTransformer | None:
    if SentenceTransformer is None:
        return None
    if not model_name_or_path:
        return None

    resolved_model_path = _resolve_model_path(model_name_or_path)

    try:
        return SentenceTransformer(
            resolved_model_path,
            local_files_only=local_files_only,
        )
    except Exception:
        return None


def _standard_text_for_row(row: Any, standard_text_fields: list[str]) -> str:
    values: list[str | None] = []
    for field_name in standard_text_fields:
        value = row.get(field_name) if hasattr(row, "get") else None
        if value is None:
            continue
        text = str(value).strip()
        if not text or text.lower() == "nan":
            continue
        values.append(text)
    return _join_non_empty(values)


def _source_text_for_field(field: Any, source_text_fields: list[str]) -> str:
    values: list[str | None] = []
    for field_name in source_text_fields:
        value = getattr(field, field_name, None)
        if value is None:
            continue
        text = str(value).strip()
        if not text or text.lower() == "nan":
            continue
        values.append(text)
    return _join_non_empty(values)


@lru_cache(maxsize=1)
def _build_semantic_index(
    cache_token: str,
) -> tuple[list[SemanticStandardCandidate], np.ndarray | None, SentenceTransformer | None]:
    config = load_semantic_mapping_config()
    if not _is_enabled(config):
        return [], None, None

    model_name_or_path = str(config.get("model_name_or_path", "")).strip()
    local_files_only = bool(config.get("local_files_only", True))
    model = _load_sentence_transformer(model_name_or_path, local_files_only)
    if model is None:
        return [], None, None

    dataframe = load_standard_fields()
    standard_text_fields = [
        str(item).strip()
        for item in config.get("standard_text_fields", [])
        if str(item).strip()
    ] or ["standard_name", "standard_name_cn", "description", "business_domain", "aliases"]

    candidates: list[SemanticStandardCandidate] = []
    texts: list[str] = []
    for _, row in dataframe.iterrows():
        candidate = SemanticStandardCandidate(
            standard_code=str(row["standard_code"]).strip(),
            standard_name=str(row["standard_name"]).strip(),
            standard_name_cn=(
                None
                if str(row["standard_name_cn"]).strip().lower() == "nan"
                else str(row["standard_name_cn"]).strip()
            ),
            description=(
                None
                if str(row["description"]).strip().lower() == "nan"
                else str(row["description"]).strip()
            ),
            data_type=(
                None
                if str(row["data_type"]).strip().lower() == "nan"
                else str(row["data_type"]).strip()
            ),
            business_domain=(
                None
                if str(row["business_domain"]).strip().lower() == "nan"
                else str(row["business_domain"]).strip()
            ),
            aliases=[
                alias.strip()
                for alias in str(row["aliases"]).split(";")
                if alias and alias.strip() and str(alias).strip().lower() != "nan"
            ],
            semantic_text=_standard_text_for_row(row, standard_text_fields),
        )
        candidates.append(candidate)
        texts.append(candidate.semantic_text or candidate.standard_name)

    if not texts:
        return candidates, None, model

    embeddings = model.encode(texts, normalize_embeddings=True)
    if hasattr(embeddings, "detach"):
        embeddings = embeddings.detach().cpu().numpy()
    elif hasattr(embeddings, "cpu"):
        embeddings = embeddings.cpu().numpy()

    return candidates, np.asarray(embeddings), model


def get_semantic_mapping_config() -> dict[str, Any]:
    """Return normalized semantic mapping configuration."""
    return load_semantic_mapping_config()


def semantic_index_enabled() -> bool:
    """Return whether semantic matching is enabled and available."""
    config = load_semantic_mapping_config()
    if not _is_enabled(config):
        return False
    model_name_or_path = str(config.get("model_name_or_path", "")).strip()
    if not model_name_or_path:
        return False
    return _load_sentence_transformer(
        model_name_or_path,
        bool(config.get("local_files_only", True)),
    ) is not None


def build_source_field_text(field: Any) -> str:
    """Build one text payload for semantic source-field comparison."""
    config = load_semantic_mapping_config()
    source_text_fields = [
        str(item).strip()
        for item in config.get("source_text_fields", [])
        if str(item).strip()
    ] or ["field_name", "field_name_cn", "field_description"]
    return _source_text_for_field(field, source_text_fields)


def _semantic_matches_from_scores(
    field_text: str,
    scores: np.ndarray,
    candidates: list[SemanticStandardCandidate],
    *,
    limit: int,
    threshold: float,
) -> SemanticFieldMatch:
    ranked_indices = np.argsort(scores)[::-1][:limit]
    top_matches: list[SemanticMatch] = []
    for rank, index in enumerate(ranked_indices, start=1):
        candidate = candidates[int(index)]
        top_matches.append(
            SemanticMatch(
                standard_code=candidate.standard_code,
                standard_name=candidate.standard_name,
                standard_name_cn=candidate.standard_name_cn,
                score=float(scores[int(index)]),
                rank=rank,
            )
        )

    best_match = top_matches[0] if top_matches and top_matches[0].score >= threshold else None
    return SemanticFieldMatch(
        field_text=field_text,
        best_match=best_match,
        top_matches=top_matches,
        threshold=threshold,
        enabled=True,
    )


def semantic_match_source_fields(
    fields: list[Any],
    *,
    candidate_limit: int | None = None,
) -> list[SemanticFieldMatch]:
    """Return semantic nearest-neighbor matches for a batch of source fields."""
    config = load_semantic_mapping_config()
    enabled = _is_enabled(config)
    threshold = _safe_float(config.get("threshold", 0.85), 0.85)
    limit = _safe_int(candidate_limit or config.get("candidate_limit", 3), 3)
    source_text_fields = [
        str(item).strip()
        for item in config.get("source_text_fields", [])
        if str(item).strip()
    ] or ["field_name", "field_name_cn", "field_description"]
    field_texts = [_source_text_for_field(field, source_text_fields) for field in fields]
    disabled_results = [
        SemanticFieldMatch(
            field_text=field_text,
            best_match=None,
            top_matches=[],
            threshold=threshold,
            enabled=False,
        )
        for field_text in field_texts
    ]

    if not enabled or not field_texts:
        return disabled_results

    model_name_or_path = str(config.get("model_name_or_path", "")).strip()
    model = _load_sentence_transformer(
        model_name_or_path,
        bool(config.get("local_files_only", True)),
    )
    if model is None:
        return disabled_results

    cache_token = "::".join(
        [
            _file_signature(SEMANTIC_CONFIG_PATH),
            _file_signature(STANDARD_FIELDS_PATH),
            model_name_or_path,
            str(threshold),
            str(limit),
        ]
    )
    candidates, embeddings, _ = _build_semantic_index(cache_token)
    if not candidates or embeddings is None or len(candidates) != len(embeddings):
        return disabled_results

    if not any(field_texts):
        return disabled_results

    source_embeddings = model.encode(field_texts, normalize_embeddings=True)
    if hasattr(source_embeddings, "detach"):
        source_embeddings = source_embeddings.detach().cpu().numpy()
    elif hasattr(source_embeddings, "cpu"):
        source_embeddings = source_embeddings.cpu().numpy()
    source_embeddings = np.asarray(source_embeddings)
    if source_embeddings.ndim == 1:
        source_embeddings = source_embeddings.reshape(1, -1)

    if embeddings.ndim == 1:
        embeddings = embeddings.reshape(1, -1)

    matches: list[SemanticFieldMatch] = []
    for index, field_text in enumerate(field_texts):
        if not field_text:
            matches.append(disabled_results[index])
            continue
        scores = source_embeddings[index] @ embeddings.T
        matches.append(
            _semantic_matches_from_scores(
                field_text,
                np.asarray(scores),
                candidates,
                limit=limit,
                threshold=threshold,
            )
        )
    return matches


def semantic_match_source_field(
    field: Any,
    *,
    candidate_limit: int | None = None,
) -> SemanticFieldMatch:
    """Return semantic nearest-neighbor matches for one source field."""
    matches = semantic_match_source_fields([field], candidate_limit=candidate_limit)
    return matches[0] if matches else SemanticFieldMatch(
        field_text=build_source_field_text(field),
        best_match=None,
        top_matches=[],
        threshold=_safe_float(
            load_semantic_mapping_config().get("threshold", 0.85),
            0.85,
        ),
        enabled=False,
    )


def warm_semantic_mapping_index() -> bool:
    """Preload the semantic model and vector index if enabled."""
    config = load_semantic_mapping_config()
    if not _is_enabled(config):
        return False

    model_name_or_path = str(config.get("model_name_or_path", "")).strip()
    if not model_name_or_path:
        return False

    model = _load_sentence_transformer(
        model_name_or_path,
        bool(config.get("local_files_only", True)),
    )
    if model is None:
        return False

    threshold = _safe_float(config.get("threshold", 0.85), 0.85)
    limit = _safe_int(config.get("candidate_limit", 3), 3)
    cache_token = "::".join(
        [
            _file_signature(SEMANTIC_CONFIG_PATH),
            _file_signature(STANDARD_FIELDS_PATH),
            model_name_or_path,
            str(threshold),
            str(limit),
        ]
    )
    candidates, embeddings, _ = _build_semantic_index(cache_token)
    return bool(candidates and embeddings is not None)


def clear_semantic_mapping_caches() -> None:
    """Clear semantic config, model, and vector index caches."""
    load_yaml_config.cache_clear()
    load_semantic_mapping_config.cache_clear()
    _load_sentence_transformer.cache_clear()
    _build_semantic_index.cache_clear()
