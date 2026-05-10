from __future__ import annotations

from pydantic import BaseModel


class TimeRangeQuery(BaseModel):
    start_timestamp: str
    end_timestamp: str


class SpotQuery(BaseModel):
    timestamp: str


class OptionsSnapshotQuery(BaseModel):
    timestamp: str
    strike: int | None = None
    side: str | None = None


class FuturesQuery(BaseModel):
    timestamp: str
