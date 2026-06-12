from typing import Any

from sqlalchemy.orm import Session

from app.models import Device, DeviceStatusHistory, Room, Scene, User


WEATHER_DATA = {
    "本地": {"weather": "多云", "temperature": 24, "humidity": 58, "advice": "适合开窗通风。"},
    "北京": {"weather": "晴", "temperature": 28, "humidity": 35, "advice": "天气较干燥，注意补水。"},
    "上海": {"weather": "小雨", "temperature": 26, "humidity": 76, "advice": "外出建议携带雨具。"},
    "广州": {"weather": "阴", "temperature": 30, "humidity": 82, "advice": "空气湿度较高，注意除湿。"},
}


class BusinessError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400, data: Any = None):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.data = data
        super().__init__(message)


def serialize_device(device: Device) -> dict[str, Any]:
    return {
        "id": device.id,
        "name": device.name,
        "device_type": device.device_type,
        "room_id": device.room_id,
        "room_name": device.room.name if device.room else None,
        "is_on": device.is_on,
        "is_online": device.is_online,
        "properties": device.properties or {},
    }


def get_device_state(device: Device) -> dict[str, Any]:
    return {
        "is_on": device.is_on,
        "is_online": device.is_online,
        "properties": dict(device.properties or {}),
    }


def get_room_by_name(db: Session, user: User, room_name: str | None) -> Room | None:
    if room_name is None:
        return None
    query = db.query(Room).filter(Room.name == room_name)
    if user.home_id is not None:
        query = query.filter(Room.home_id == user.home_id)
    room = query.first()
    if room is None:
        raise BusinessError("ROOM_NOT_FOUND", "未找到指定房间", status_code=404)
    return room


def find_device(db: Session, user: User, room_name: str | None, device_type: str | None) -> Device:
    if device_type is None:
        raise BusinessError("DEVICE_NOT_FOUND", "未找到指定设备", status_code=404)

    room = get_room_by_name(db, user, room_name)
    query = db.query(Device).join(Room).filter(Device.device_type == device_type)
    if user.home_id is not None:
        query = query.filter(Room.home_id == user.home_id)
    if room is not None:
        query = query.filter(Device.room_id == room.id)

    device = query.order_by(Device.id.asc()).first()
    if device is None:
        raise BusinessError("DEVICE_NOT_FOUND", "未找到指定设备", status_code=404)
    return device


def list_room_devices(db: Session, user: User, room_name: str | None) -> list[Device]:
    room = get_room_by_name(db, user, room_name)
    query = db.query(Device).join(Room)
    if user.home_id is not None:
        query = query.filter(Room.home_id == user.home_id)
    if room is not None:
        query = query.filter(Device.room_id == room.id)
    return query.order_by(Device.id.asc()).all()


def apply_device_state(
    db: Session,
    device: Device,
    user: User,
    state_update: dict[str, Any],
    change_source: str,
) -> dict[str, Any]:
    before_state = get_device_state(device)
    if "is_on" in state_update:
        device.is_on = state_update["is_on"]
    if "is_online" in state_update:
        device.is_online = state_update["is_online"]
    if "properties" in state_update:
        merged_properties = dict(device.properties or {})
        merged_properties.update(state_update["properties"] or {})
        device.properties = merged_properties

    after_state = get_device_state(device)
    db.add(
        DeviceStatusHistory(
            device_id=device.id,
            user_id=user.id,
            before_state=before_state,
            after_state=after_state,
            change_source=change_source,
        )
    )
    return {
        "device": serialize_device(device),
        "before_state": before_state,
        "after_state": after_state,
    }


def validate_value_range(value: int | None, minimum: int, maximum: int, label: str) -> int:
    if value is None or value < minimum or value > maximum:
        raise BusinessError("VALUE_OUT_OF_RANGE", f"{label}必须在 {minimum}-{maximum} 范围内")
    return value


def run_scene_actions(db: Session, user: User, scene: Scene, change_source: str) -> list[dict[str, Any]]:
    results = []
    for action in sorted(scene.actions, key=lambda item: item.sort_order):
        results.append(
            apply_device_state(
                db=db,
                device=action.device,
                user=user,
                state_update=action.target_state,
                change_source=change_source,
            )
        )
    return results


def get_weather(city: str | None = None) -> dict[str, Any]:
    city_name = city or "本地"
    weather = WEATHER_DATA.get(city_name, WEATHER_DATA["本地"])
    return {
        "city": city_name,
        "weather": weather["weather"],
        "temperature": weather["temperature"],
        "humidity": weather["humidity"],
        "advice": weather["advice"],
    }
