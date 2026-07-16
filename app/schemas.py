from datetime import date, datetime
from pydantic import BaseModel


class RegisterRequest(BaseModel):
    username: str
    password: str
    role: str = "child"


class LoginRequest(BaseModel):
    username: str
    password: str


class AuthResponse(BaseModel):
    token: str
    user_id: str
    username: str
    role: str


class RegisterDeviceRequest(BaseModel):
    name: str
    username: str


class RegisterDeviceResponse(BaseModel):
    device_id: str
    api_key: str
    name: str


class LinkChildRequest(BaseModel):
    child_username: str


class ChildInfo(BaseModel):
    device_id: str
    name: str
    api_key: str
    daily_limit_minutes: int
    today_seconds: int = 0


class ChildrenListResponse(BaseModel):
    children: list[ChildInfo]


class SendCommandRequest(BaseModel):
    to_device_id: str
    command_type: str  # block | unblock | start_tracking | stop_tracking


class PendingCommand(BaseModel):
    id: int
    command_type: str
    payload: dict | None = None
    created_at: datetime


class PendingCommandsResponse(BaseModel):
    commands: list[PendingCommand]


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
