"""Object fingerprint model for incremental rerun comparison."""

from pydantic import BaseModel


class ObjectFingerprint(BaseModel):
    """Stable fingerprint for one governance metadata object."""

    object_type: str
    object_name: str
    group_name: str | None = None
    fingerprint: str
    source_file: str | None = None

