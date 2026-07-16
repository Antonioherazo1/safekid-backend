from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models import User, Device, UserDevice, DailyUsage
from app.schemas import LinkChildRequest, ChildInfo, ChildrenListResponse
from app.auth import get_current_user

router = APIRouter(tags=["parent"])


@router.post("/parent/link-child", response_model=ChildInfo)
async def link_child(
    body: LinkChildRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if user.role != "parent":
        raise HTTPException(status_code=403, detail="Only parents can link children")

    result = await db.execute(select(User).where(User.username == body.child_username))
    child_user = result.scalar_one_or_none()
    if child_user is None or child_user.role != "child":
        raise HTTPException(status_code=404, detail="Child user not found")

    result = await db.execute(
        select(UserDevice).where(
            UserDevice.user_id == child_user.id,
        ).options(selectinload(UserDevice.device))
    )
    child_device_link = result.scalar_one_or_none()
    if child_device_link is None:
        raise HTTPException(status_code=400, detail="Child has no registered device")

    existing = await db.execute(
        select(UserDevice).where(
            UserDevice.user_id == user.id,
            UserDevice.device_id == child_device_link.device_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Child already linked")

    link = UserDevice(user_id=user.id, device_id=child_device_link.device_id)
    db.add(link)
    await db.commit()

    device = child_device_link.device
    return ChildInfo(
        device_id=str(device.id),
        name=device.name,
        api_key=device.api_key,
        daily_limit_minutes=device.daily_limit_minutes,
        today_seconds=0,
    )


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

    result = await db.execute(
        select(UserDevice).where(UserDevice.user_id == child_user.id)
        .options(selectinload(UserDevice.device))
    )
    link = result.scalar_one_or_none()
    if link is None:
        raise HTTPException(status_code=400, detail="Child has no registered device")

    parent_link = await db.execute(
        select(UserDevice).where(
            UserDevice.user_id == user.id,
            UserDevice.device_id == link.device_id,
        )
    )
    if not parent_link.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Child not linked to your account")

    device = link.device
    device.daily_limit_minutes = limit_minutes
    await db.commit()

    return {"status": "ok", "daily_limit_minutes": limit_minutes}

@router.get("/parent/children", response_model=ChildrenListResponse)
async def list_children(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if user.role != "parent":
        raise HTTPException(status_code=403, detail="Only parents can view children")

    result = await db.execute(
        select(UserDevice)
        .where(UserDevice.user_id == user.id)
        .options(selectinload(UserDevice.device))
    )
    links = result.scalars().all()

    children = []
    today = date.today()
    for link in links:
        device = link.device
        usage_result = await db.execute(
            select(DailyUsage).where(
                DailyUsage.device_id == device.id,
                DailyUsage.date == today,
            )
        )
        today_usage = usage_result.scalar_one_or_none()

        children.append(ChildInfo(
            device_id=str(device.id),
            name=device.name,
            api_key=device.api_key,
            daily_limit_minutes=device.daily_limit_minutes,
            today_seconds=today_usage.total_seconds if today_usage else 0,
        ))

    return ChildrenListResponse(children=children)
