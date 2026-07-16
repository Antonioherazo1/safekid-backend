from datetime import date, datetime
from pydantic import BaseModel


class RegisterRequest(BaseModel):
    name: str


class RegisterResponse(BaseModel):
    device_id: str
    api_key: str
    name: str


class SessionData(BaseModel):
    start_time: datetime
    end_time: datetime | None = None
    duration_seconds: int


class SyncRequest(BaseModel):
    date: date
    total_seconds: int
    sessions: list[SessionData] = []


class SyncResponse(BaseModel):
    status: str
    total_seconds: int


class DailyStats(BaseModel):
    date: date
    total_seconds: int
    limit_minutes: int


class HistoryEntry(BaseModel):
    date: date
    total_seconds: int
    limit_minutes: int


class StatsResponse(BaseModel):
    today: DailyStats
    history: list[HistoryEntry]


class ErrorResponse(BaseModel):
    detail: str
