from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models import Device, DeviceStatusHistory, Room, User
from app.schemas.device import DeviceStateUpdateRequest
from app.utils.response import error_response, success_response


router = APIRouter(tags=["房间与设备"])


def serialize_room(room: Room) -> dict[str, Any]:
    return {
        "id": room.id,
        "name": room.name,
        "home_id": room.home_id,
        "device_count": len(room.devices),
        "created_at": room.created_at.isoformat() if room.created_at else None,
    }


def serialize_device(device: Device) -> dict[str, Any]:
    return {
        "id": device.id,
        "name": device.name,
        "device_type": device.device_type,
        "room_id": device.room_id,
        "room_name": device.room.name if device.room else None,
        "is_on": device.is_on,
        "is_online": device.is_online,
        "properties": device.properties,
        "created_at": device.created_at.isoformat() if device.created_at else None,
        "updated_at": device.updated_at.isoformat() if device.updated_at else None,
    }


def serialize_history(history: DeviceStatusHistory) -> dict[str, Any]:
    return {
        "id": history.id,
        "device_id": history.device_id,
        "user_id": history.user_id,
        "before_state": history.before_state,
        "after_state": history.after_state,
        "change_source": history.change_source,
        "created_at": history.created_at.isoformat() if history.created_at else None,
    }


def get_device_state(device: Device) -> dict[str, Any]:
    return {
        "is_on": device.is_on,
        "is_online": device.is_online,
        "properties": device.properties or {},
    }


def get_device_for_user(db: Session, device_id: int, user: User) -> Device:
    device = db.query(Device).join(Room).filter(Device.id == device_id).first()
    if device is None or (user.home_id is not None and device.room.home_id != user.home_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_response("DEVICE_NOT_FOUND", "未找到指定设备"),
        )
    return device


@router.get("/rooms", summary="查询房间列表")
def list_rooms(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Room).order_by(Room.id.asc())
    if current_user.home_id is not None:
        query = query.filter(Room.home_id == current_user.home_id)
    rooms = query.all()
    return success_response(data=[serialize_room(room) for room in rooms])


@router.get("/devices", summary="查询设备列表")
def list_devices(
    room_id: int | None = Query(default=None, description="按房间 ID 筛选"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Device).join(Room).order_by(Device.id.asc())
    if current_user.home_id is not None:
        query = query.filter(Room.home_id == current_user.home_id)
    if room_id is not None:
        query = query.filter(Device.room_id == room_id)
    devices = query.all()
    return success_response(data=[serialize_device(device) for device in devices])


@router.get("/devices/{device_id}", summary="查询设备详情")
def get_device(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    device = get_device_for_user(db, device_id, current_user)
    return success_response(data=serialize_device(device))


@router.patch("/devices/{device_id}/state", summary="修改设备状态")
def update_device_state(
    device_id: int,
    payload: DeviceStateUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    device = get_device_for_user(db, device_id, current_user)
    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_response("INVALID_REQUEST", "至少需要提供一个要修改的状态字段"),
        )

    before_state = get_device_state(device)
    if "is_on" in update_data:
        device.is_on = update_data["is_on"]
    if "is_online" in update_data:
        device.is_online = update_data["is_online"]
    if "properties" in update_data:
        merged_properties = dict(device.properties or {})
        merged_properties.update(update_data["properties"] or {})
        device.properties = merged_properties

    after_state = get_device_state(device)
    db.add(
        DeviceStatusHistory(
            device_id=device.id,
            user_id=current_user.id,
            before_state=before_state,
            after_state=after_state,
            change_source="manual",
        )
    )
    db.commit()
    db.refresh(device)
    return success_response(data=serialize_device(device), message="设备状态修改成功")


@router.get("/devices/{device_id}/history", summary="查询设备状态历史")
def get_device_history(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_device_for_user(db, device_id, current_user)
    history_items = (
        db.query(DeviceStatusHistory)
        .filter(DeviceStatusHistory.device_id == device_id)
        .order_by(DeviceStatusHistory.id.desc())
        .all()
    )
    return success_response(data=[serialize_history(item) for item in history_items])


@router.get("/dashboard", summary="查询仪表盘统计")
def dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    room_query = db.query(Room)
    device_query = db.query(Device).join(Room)
    if current_user.home_id is not None:
        room_query = room_query.filter(Room.home_id == current_user.home_id)
        device_query = device_query.filter(Room.home_id == current_user.home_id)

    total_devices = device_query.count()
    online_devices = device_query.filter(Device.is_online.is_(True)).count()
    on_devices = device_query.filter(Device.is_on.is_(True)).count()
    total_rooms = room_query.count()
    return success_response(
        data={
            "room_count": total_rooms,
            "device_count": total_devices,
            "online_device_count": online_devices,
            "on_device_count": on_devices,
            "offline_device_count": total_devices - online_devices,
        }
    )
