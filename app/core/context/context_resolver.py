"""Rule-based context resolver for session-aware parameter autofill."""

from pathlib import Path

from app.core.agent.session_store import get_session
from app.core.context.context_loader import load_context_resolution_config
from app.core.models.governance_task_request import GovernanceTaskRequest
from app.core.models.parameter_resolution_result import ParameterResolutionResult
from app.core.models.resolved_context import ResolvedContext
from app.core.normalize import clean_text

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SAMPLE_METADATA_PATH = PROJECT_ROOT / "app" / "data" / "samples" / "sample_metadata.csv"

CURRENT_FILE_MARKERS = [
    "this file",
    "current file",
    "uploaded file",
    "this metadata file",
    "\u8fd9\u4e2a\u6587\u4ef6",
    "\u5f53\u524d\u6587\u4ef6",
    "\u521a\u4e0a\u4f20\u7684\u6587\u4ef6",
]
PREVIOUS_FILE_MARKERS = [
    "last file",
    "previous file",
    "\u4e0a\u4e00\u4e2a\u6587\u4ef6",
    "\u4e0a\u6b21\u6587\u4ef6",
]


class ContextResolver:
    """Resolve safe execution parameters from local session context."""

    @staticmethod
    def clean_intent_text(text: str) -> str:
        """Normalize task text before context phrase matching."""
        return clean_text(text or "")

    @staticmethod
    def _match_references(cleaned_text: str, candidates: list[object]) -> list[str]:
        matches: list[str] = []
        for candidate in candidates:
            phrase = clean_text(str(candidate or ""))
            if phrase and phrase in cleaned_text:
                matches.append(str(candidate))
        return matches

    def detect_file_reference_phrases(self, raw_text: str) -> list[str]:
        """Return configured file-reference phrases matched in task text."""
        config = load_context_resolution_config()
        return self._match_references(
            self.clean_intent_text(raw_text),
            list(config.get("supported_file_references", [])),
        )

    def detect_result_reference_phrases(self, raw_text: str) -> list[str]:
        """Return configured result-reference phrases matched in task text."""
        config = load_context_resolution_config()
        return self._match_references(
            self.clean_intent_text(raw_text),
            list(config.get("supported_result_references", [])),
        )

    @staticmethod
    def _infer_file_reference_mode(reference_matches: list[str]) -> str | None:
        """Classify a matched file reference as current-like or previous-like."""
        if not reference_matches:
            return None

        normalized = " ".join(clean_text(item) for item in reference_matches)
        if any(marker in normalized for marker in CURRENT_FILE_MARKERS):
            return "current"
        if any(marker in normalized for marker in PREVIOUS_FILE_MARKERS):
            return "previous"
        return None

    def resolve_file_path_from_session(
        self,
        session_id: str | None,
        file_reference_matches: list[str],
    ) -> tuple[str | None, str | None, bool, list[str]]:
        """Resolve a missing file_path from local session context."""
        config = load_context_resolution_config()
        autofill_policy = config.get("autofill_policy", {})
        ambiguity_policy = config.get("ambiguity_policy", {})
        if not bool(autofill_policy.get("enable_file_path_autofill", True)):
            return None, None, False, []

        session = get_session(session_id or "") if session_id else None
        source_lookup: dict[str, str] = {}
        if session and session.last_uploaded_file_path:
            source_lookup["session_last_uploaded_file"] = session.last_uploaded_file_path
        if (
            session
            and session.last_task_request is not None
            and session.last_task_request.file_path
        ):
            source_lookup["session_last_task_file"] = session.last_task_request.file_path
        if bool(autofill_policy.get("fallback_to_sample_file", False)) and SAMPLE_METADATA_PATH.exists():
            source_lookup["session_last_sample_file"] = str(SAMPLE_METADATA_PATH)

        if not source_lookup:
            return None, None, False, ["No session-based file candidate was available."]

        reference_mode = self._infer_file_reference_mode(file_reference_matches)
        priority = [str(item) for item in config.get("file_resolution_priority", [])]
        if reference_mode == "current":
            priority = [
                "session_last_uploaded_file",
                "session_last_task_file",
                "session_last_sample_file",
            ]
        elif reference_mode == "previous":
            priority = [
                "session_last_task_file",
                "session_last_uploaded_file",
                "session_last_sample_file",
            ]

        if reference_mode is None:
            distinct_candidates = {
                str(path).strip()
                for path in source_lookup.values()
                if str(path).strip()
            }
            if len(distinct_candidates) > 1 and bool(
                ambiguity_policy.get("require_confirmation_if_multiple_candidates", True)
            ):
                messages = [
                    "Multiple candidate files were found in the current session, so file_path was not autofilled."
                ]
                messages.append(
                    "Candidates: " + ", ".join(sorted(distinct_candidates))
                )
                return None, None, True, messages

        chosen_source: str | None = None
        chosen_path: str | None = None
        for source_name in priority:
            if source_name == "explicit_file_path":
                continue
            candidate = source_lookup.get(source_name)
            if candidate:
                chosen_source = source_name
                chosen_path = candidate
                break

        if not chosen_source or not chosen_path:
            return None, None, False, ["No eligible file candidate survived resolution."]

        if reference_mode == "current":
            messages = [
                "file_path was autofilled from the current session file reference."
            ]
        elif reference_mode == "previous":
            messages = [
                "file_path was autofilled from the previous session file reference."
            ]
        else:
            messages = [f"file_path was autofilled from {chosen_source}."]

        return chosen_path, chosen_source, False, messages

    @staticmethod
    def _extract_unique_parent_dir(exported_files: dict[str, str]) -> str | None:
        parents = {
            str(Path(path).resolve().parent)
            for path in exported_files.values()
            if str(path).strip()
        }
        if len(parents) == 1:
            return next(iter(parents))
        return None

    def resolve_output_dir_from_session(
        self,
        task_request: GovernanceTaskRequest,
        session_id: str | None,
        result_reference_matches: list[str],
    ) -> tuple[str | None, str | None, bool, list[str]]:
        """Resolve an output_dir from local session export history when useful."""
        config = load_context_resolution_config()
        autofill_policy = config.get("autofill_policy", {})
        if not bool(autofill_policy.get("enable_output_dir_autofill", True)):
            return None, None, False, []

        session = get_session(session_id or "") if session_id else None
        if session is None or not session.last_exported_files:
            return None, None, False, []

        should_try = bool(task_request.export_reports or result_reference_matches)
        if not should_try:
            return None, None, False, []

        resolved_output_dir = self._extract_unique_parent_dir(session.last_exported_files)
        if not resolved_output_dir:
            return None, None, True, [
                "Multiple exported output directories were found, so output_dir was not autofilled."
            ]

        return (
            resolved_output_dir,
            "session_last_exported_files",
            False,
            ["output_dir was autofilled from the last exported files in this session."],
        )

    @staticmethod
    def apply_resolution_to_request(
        task_request: GovernanceTaskRequest,
        resolved_file_path: str | None = None,
        resolved_output_dir: str | None = None,
    ) -> GovernanceTaskRequest:
        """Return a copy of the task request with resolved parameters applied."""
        return task_request.model_copy(
            update={
                "file_path": resolved_file_path or task_request.file_path,
                "output_dir": resolved_output_dir or task_request.output_dir,
            }
        )

    def resolve(
        self,
        raw_text: str,
        task_request: GovernanceTaskRequest,
        session_id: str | None = None,
    ) -> ParameterResolutionResult:
        """Resolve missing task parameters from session-scoped local context."""
        original_task_request = task_request.model_copy(deep=True)
        resolved_context = ResolvedContext(session_id=session_id)

        file_reference_matches = self.detect_file_reference_phrases(raw_text)
        result_reference_matches = self.detect_result_reference_phrases(raw_text)
        resolved_context.reference_matches = (
            file_reference_matches + result_reference_matches
        )

        if task_request.file_path:
            resolved_context.resolved_file_path = task_request.file_path
            resolved_context.resolved_from.append("explicit_file_path")
            resolved_context.messages.append("file_path was provided explicitly.")
        else:
            (
                resolved_file_path,
                file_source,
                file_ambiguous,
                file_messages,
            ) = self.resolve_file_path_from_session(
                session_id=session_id,
                file_reference_matches=file_reference_matches,
            )
            resolved_context.ambiguity_detected = file_ambiguous
            resolved_context.messages.extend(file_messages)
            if resolved_file_path and file_source:
                resolved_context.resolved_file_path = resolved_file_path
                resolved_context.resolved_from.append(file_source)
                resolved_context.autofilled_parameters["file_path"] = resolved_file_path

        if task_request.output_dir:
            resolved_context.resolved_output_dir = task_request.output_dir
            resolved_context.resolved_from.append("explicit_output_dir")
        else:
            (
                resolved_output_dir,
                output_source,
                output_ambiguous,
                output_messages,
            ) = self.resolve_output_dir_from_session(
                task_request=task_request,
                session_id=session_id,
                result_reference_matches=result_reference_matches,
            )
            resolved_context.ambiguity_detected = (
                resolved_context.ambiguity_detected or output_ambiguous
            )
            resolved_context.messages.extend(output_messages)
            if resolved_output_dir and output_source:
                resolved_context.resolved_output_dir = resolved_output_dir
                resolved_context.resolved_from.append(output_source)
                resolved_context.autofilled_parameters["output_dir"] = resolved_output_dir

        resolved_task_request = self.apply_resolution_to_request(
            task_request=task_request,
            resolved_file_path=resolved_context.resolved_file_path,
            resolved_output_dir=resolved_context.resolved_output_dir,
        )

        return ParameterResolutionResult(
            original_task_request=original_task_request,
            resolved_task_request=resolved_task_request,
            resolved_context=resolved_context,
            resolution_applied=bool(resolved_context.autofilled_parameters),
        )


# TODO: extend the resolver with safer local file search and optional LLM-assisted clarification once the current session-scoped rules remain stable.
