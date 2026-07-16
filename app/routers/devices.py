import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import Device
from app.schemas import RegisterRequest, RegisterResponse
from app.auth import generate_api_key, get_device_from_api_key

router = APIRouter(tags=["devices"])


@router.post("/device/register", response_model=RegisterResponse)
async def register_device(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    device_id = uuid.uuid4()
    api_key = generate_api_key(str(device_id))

    device = Device(
        id=device_id,
        name=body.name,
        api_key=api_key,
    )
    db.add(device)
    await db.commit()
    await db.refresh(device)

    return RegisterResponse(
        device_id=str(device.id),
        api_key=api_key,
        name=device.name,
    )


@router.get("/device/info")
async def get_device_info(device: Device = Depends(get_device_from_api_key)):
    return {
        "device_id": str(device.id),
        "name": device.name,
        "daily_limit_minutes": device.daily_limit_minutes,
        "is_active": device.is_active,
        "created_at": device.created_at.isoformat() if device.created_at else None,
    }
