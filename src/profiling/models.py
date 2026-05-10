from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    INFO = "INFO"


class ProfilingFinding(BaseModel):
    dataset: str
    file_name: str
    severity: Severity
    rule: str
    message: str
    affected_rows: int
    sample_rows: list[dict]
    timestamp: str | None
