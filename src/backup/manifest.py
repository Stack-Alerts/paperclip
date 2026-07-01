"""Backup manifest — rich metadata record for a completed backup."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

CURRENT_SCHEMA_VERSION = 1
CURRENT_MANIFEST_VERSION = 1


class ManifestEntry(BaseModel):
    """Describes one file stored inside a backup archive."""

    path: str
    size_bytes: int
    sha256: str


class BackupManifest(BaseModel):
    """Full metadata record for a completed backup.

    Serialise with ``manifest.model_dump_json()``; deserialise with
    ``BackupManifest.model_validate_json(raw)`` or
    ``BackupManifest.model_validate(dict_)``.
    """

    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    provider: str
    kind: Literal["db", "system"]
    path: str
    size_bytes: int
    sha256: str
    duration_seconds: int
    postgres_version: str = "18.1"
    host_fingerprint: str
    schema_version: int = CURRENT_SCHEMA_VERSION
    manifest_version: int = CURRENT_MANIFEST_VERSION
    contents: list[ManifestEntry] = Field(default_factory=list)

    model_config = {"json_encoders": {datetime: lambda dt: dt.isoformat()}}

    # ------------------------------------------------------------------ I/O

    def to_json(self, indent: int | None = 2) -> str:
        """Serialise to a JSON string (ISO-8601 timestamps, UUID as string)."""
        return self.model_dump_json(indent=indent)

    @classmethod
    def from_json(cls, raw: str | bytes) -> "BackupManifest":
        """Deserialise from a JSON string or bytes."""
        return cls.model_validate_json(raw)

    @classmethod
    def from_dict(cls, data: dict) -> "BackupManifest":
        return cls.model_validate(data)

    def to_dict(self) -> dict:
        return json.loads(self.to_json())
