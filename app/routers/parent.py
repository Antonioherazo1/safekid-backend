import uuid
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models import User, Device, UserDevice, DailyUsage
from app.schemas import LinkChildRequest, ChildInfo, ChildrenListResponse, RegisterChildDeviceRequest, RegisterDeviceResponse
from app.auth import get_current_user, generate_api_key

router = APIRouter(tags=["parent"])


@router.get("/parent/code")
async def get_parent_code(user: User = Depends(get_current_user)):
    if user.role != "parent":
        raise HTTPException(status_code=403, detail="Only parents have a code")
    if not user.parent_code:
        raise HTTPException(status_code=500, detail="Parent code not generated")
    return {"parent_code": user.parent_code}


@router.get("/parent/children", response_model=ChildrenListResponse)
async def list_children(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if user.role != "parent":
        raise HTTPException(status_code=403, detail="Only parents can view children")

    result = await db.execute(
        select(User).where(
            User.parent_id == user.id,
            User.role == "child",
        )
    )
    child_users = result.scalars().all()

    children = []
    today = date.today()
    for child in child_users:
        device_result = await db.execute(
            select(UserDevice).where(UserDevice.user_id == child.id)
            .options(selectinload(UserDevice.device))
        )
        device_link = device_result.scalar_one_or_none()

        device_id = str(device_link.device_id) if device_link else ""
        name = device_link.device.name if device_link and device_link.device else child.username
        api_key = device_link.device.api_key if device_link and device_link.device else ""
        daily_limit = device_link.device.daily_limit_minutes if device_link and device_link.device else 0
        today_seconds = 0

        if device_link and device_link.device:
            usage_result = await db.execute(
                select(DailyUsage).where(
                    DailyUsage.device_id == device_link.device_id,
                    DailyUsage.date == today,
                )
            )
            today_usage = usage_result.scalar_one_or_none()
            if today_usage:
                today_seconds = today_usage.total_seconds

        s_start = device_link.device.schedule_start_min if device_link and device_link.device else -1
        s_end = device_link.device.schedule_end_min if device_link and device_link.device else -1

        children.append(ChildInfo(
            device_id=device_id,
            name=name,
            username=child.username,
            api_key=api_key,
            daily_limit_minutes=daily_limit,
            today_seconds=today_seconds,
            schedule_start_min=s_start or -1,
            schedule_end_min=s_end or -1,
        ))

    return ChildrenListResponse(children=children)


@router.post("/parent/register-child-device", response_model=RegisterDeviceResponse)
async def register_child_device(
    body: RegisterChildDeviceRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if user.role != "parent":
        raise HTTPException(status_code=403, detail="Only parents can register child devices")

    result = await db.execute(select(User).where(User.username == body.child_username))
    child_user = result.scalar_one_or_none()
    if child_user is None or child_user.role != "child":
        raise HTTPException(status_code=404, detail="Child user not found")

    device_id = uuid.uuid4()
    api_key = generate_api_key(str(device_id))

    device = Device(id=device_id, name=body.name, api_key=api_key)
    db.add(device)
    await db.flush()

    link = UserDevice(user_id=child_user.id, device_id=device.id)
    db.add(link)
    await db.commit()

    return RegisterDeviceResponse(device_id=str(device.id), api_key=api_key, name=device.name)


@router.post("/parent/set-limit")
async def set_child_limit(
    child_username: str,
    limit_minutes: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if user.role != "parent":
        raise HTTPException(status_code=403, detail="Only parents can set limits")

    result = await db.execute(select(User).where(User.username == child_username))
    child_user = result.scalar_one_or_none()
    if child_user is None or child_user.role != "child":
        raise HTTPException(status_code=404, detail="Child user not found")

    if child_user.parent_id != user.id:
        raise HTTPException(status_code=403, detail="Child not linked to your account")

    device_result = await db.execute(
        select(UserDevice).where(UserDevice.user_id == child_user.id)
        .options(selectinload(UserDevice.device))
    )
    link = device_result.scalar_one_or_none()
    if link is None or link.device is None:
        raise HTTPException(status_code=400, detail="Child has no registered device")

    link.device.daily_limit_minutes = limit_minutes
    await db.commit()

    return {"status": "ok", "daily_limit_minutes": limit_minutes}


@router.post("/parent/set-schedule")
async def set_child_schedule(
    child_username: str,
    start_min: int,
    end_min: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if user.role != "parent":
        raise HTTPException(status_code=403, detail="Only parents can set schedules")

    result = await db.execute(select(User).where(User.username == child_username))
    child_user = result.scalar_one_or_none()
    if child_user is None or child_user.role != "child":
        raise HTTPException(status_code=404, detail="Child user not found")

    if child_user.parent_id != user.id:
        raise HTTPException(status_code=403, detail="Child not linked to your account")

    device_result = await db.execute(
        select(UserDevice).where(UserDevice.user_id == child_user.id)
        .options(selectinload(UserDevice.device))
    )
    link = device_result.scalar_one_or_none()
    if link is None or link.device is None:
        raise HTTPException(status_code=400, detail="Child has no registered device")

    link.device.schedule_start_min = start_min
    link.device.schedule_end_min = end_min
    await db.commit()

    return {"status": "ok", "schedule_start_min": start_min, "schedule_end_min": end_min}


@router.post("/parent/delete-child")
async def delete_child(
    child_username: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if user.role != "parent":
        raise HTTPException(status_code=403, detail="Only parents can delete children")

    result = await db.execute(select(User).where(User.username == child_username))
    child = result.scalar_one_or_none()
    if child is None or child.role != "child":
        raise HTTPException(status_code=404, detail="Child not found")
    if child.parent_id != user.id:
        raise HTTPException(status_code=403, detail="Child not linked to your account")

    await db.delete(child)
    await db.commit()
    return {"status": "deleted"}
