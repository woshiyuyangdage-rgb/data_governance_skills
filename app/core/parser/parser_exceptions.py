"""Custom exceptions for metadata file parsing."""


class ParserError(Exception):
    """Base exception for supported parser errors."""


class EmptyInputFileError(ParserError):
    """Raised when an input file contains no usable rows."""


class MissingRequiredColumnsError(ParserError):
    """Raised when a file is missing one or more required columns."""

    def __init__(
        self,
        missing_columns: list[str],
        available_columns: list[str] | None = None,
    ) -> None:
        self.missing_columns = sorted(dict.fromkeys(missing_columns))
        self.available_columns = available_columns or []
        message = (
            "Missing required columns: "
            f"{', '.join(self.missing_columns)}."
        )
        if self.available_columns:
            message += f" Available columns: {', '.join(self.available_columns)}."
        super().__init__(message)


class UnsupportedFileFormatError(ParserError):
    """Raised when the file extension is not supported by the loader."""

