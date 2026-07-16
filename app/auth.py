import os
import hashlib
import secrets
from fastapi import Header, HTTPException, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import Device


def generate_api_key(device_id: str, salt: str | None = None) -> str:
    if salt is None:
        salt = os.getenv("API_KEY_SALT", "default-salt")
    raw = f"{device_id}:{salt}:{secrets.token_hex(16)}"
    return hashlib.sha256(raw.encode()).hexdigest()


async def get_device_from_api_key(
    authorization: str = Header(..., description="Bearer <api_key>"),
    db: AsyncSession = Depends(get_db),
) -> Device:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    api_key = authorization.removeprefix("Bearer ").strip()
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing API key")

    result = await db.execute(select(Device).where(Device.api_key == api_key, Device.is_active == True))
    device = result.scalar_one_or_none()
    if device is None:
        raise HTTPException(status_code=401, detail="Invalid or inactive API key")
    return device
