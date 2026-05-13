"""Custom exceptions for governance knowledge pack loading."""


class KnowledgePackError(Exception):
    """Base exception for knowledge pack loading errors."""


class KnowledgePackFileNotFoundError(KnowledgePackError):
    """Raised when a required knowledge pack file does not exist."""


class KnowledgePackColumnError(KnowledgePackError):
    """Raised when a knowledge pack file is missing required columns."""

    def __init__(
        self,
        file_path: str,
        missing_columns: list[str],
        available_columns: list[str] | None = None,
    ) -> None:
        self.file_path = file_path
        self.missing_columns = sorted(dict.fromkeys(missing_columns))
        self.available_columns = available_columns or []
        message = (
            f"Knowledge pack '{file_path}' is missing required columns: "
            f"{', '.join(self.missing_columns)}."
        )
        if self.available_columns:
            message += f" Available columns: {', '.join(self.available_columns)}."
        super().__init__(message)
