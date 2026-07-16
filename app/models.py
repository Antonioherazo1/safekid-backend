import uuid
from datetime import date, datetime, timezone
from sqlalchemy import Column, String, Integer, BigInteger, Boolean, Date, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class Device(Base):
    __tablename__ = "safekid_devices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    api_key = Column(String(64), unique=True, nullable=False, index=True)
    daily_limit_minutes = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    daily_usage = relationship("DailyUsage", back_populates="device", cascade="all, delete-orphan")
    sessions = relationship("UsageSession", back_populates="device", cascade="all, delete-orphan")


class DailyUsage(Base):
    __tablename__ = "safekid_daily_usage"
    __table_args__ = (
        UniqueConstraint("device_id", "date", name="uq_device_date"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(UUID(as_uuid=True), ForeignKey("safekid_devices.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    total_seconds = Column(BigInteger, default=0)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    device = relationship("Device", back_populates="daily_usage")


class UsageSession(Base):
    __tablename__ = "safekid_usage_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(UUID(as_uuid=True), ForeignKey("safekid_devices.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(BigInteger, default=0)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    device = relationship("Device", back_populates="sessions")
