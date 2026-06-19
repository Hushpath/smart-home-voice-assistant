from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from sqlalchemy.orm import Session

from app.models import Device, DeviceStatusHistory, Room, Scene, User


WEATHER_DATA = {
    "本地": {"weather": "多云", "temperature": 24, "humidity": 58, "wind_speed": 6, "advice": "适合开窗通风。"},
    "北京": {"weather": "晴", "temperature": 28, "humidity": 35, "wind_speed": 8, "advice": "天气较干燥，注意补水。"},
    "上海": {"weather": "小雨", "temperature": 26, "humidity": 76, "wind_speed": 10, "advice": "外出建议携带雨具。"},
    "广州": {"weather": "阴", "temperature": 30, "humidity": 82, "wind_speed": 7, "advice": "空气湿度较高，注意除湿。"},
    "深圳": {"weather": "多云", "temperature": 29, "humidity": 78, "wind_speed": 9, "advice": "湿度偏高，建议开启除湿。"},
    "杭州": {"weather": "多云", "temperature": 27, "humidity": 70, "wind_speed": 6, "advice": "天气舒适，适合室内通风。"},
    "南京": {"weather": "晴", "temperature": 29, "humidity": 62, "wind_speed": 8, "advice": "午后偏热，注意补水。"},
    "成都": {"weather": "阴", "temperature": 25, "humidity": 74, "wind_speed": 5, "advice": "空气湿润，注意保持室内干爽。"},
    "重庆": {"weather": "多云", "temperature": 31, "humidity": 68, "wind_speed": 6, "advice": "体感偏热，建议适当降温。"},
    "西安": {"weather": "晴", "temperature": 30, "humidity": 42, "wind_speed": 9, "advice": "天气较干燥，注意补水。"},
    "武汉": {"weather": "多云", "temperature": 30, "humidity": 73, "wind_speed": 7, "advice": "湿度较高，注意室内通风。"},
}

CITY_COORDINATES = {
    "北京": (39.9042, 116.4074),
    "上海": (31.2304, 121.4737),
    "广州": (23.1291, 113.2644),
    "深圳": (22.5431, 114.0579),
    "杭州": (30.2741, 120.1551),
    "南京": (32.0603, 118.7969),
    "成都": (30.5728, 104.0668),
    "重庆": (29.5630, 106.5516),
    "西安": (34.3416, 108.9398),
    "武汉": (30.5928, 114.3055),
}

OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
WEATHER_REQUEST_TIMEOUT_SECONDS = 3.0
WEATHER_CACHE_TTL_SECONDS = 600
_WEATHER_CACHE: dict[str, tuple[datetime, dict[str, Any]]] = {}


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
    city_name = _normalize_city(city)
    if city_name in CITY_COORDINATES:
        cached = _get_cached_weather(city_name)
        if cached is not None:
            return cached

        try:
            weather = _fetch_open_meteo_weather(city_name)
            _set_cached_weather(city_name, weather)
            return weather
        except (httpx.HTTPError, ImportError, ValueError, KeyError, TypeError):
            pass

    return _mock_weather(city_name)


def clear_weather_cache() -> None:
    _WEATHER_CACHE.clear()


def _normalize_city(city: str | None) -> str:
    if city is None:
        return "本地"
    city_name = city.strip()
    return city_name or "本地"


def _get_cached_weather(city_name: str) -> dict[str, Any] | None:
    cached = _WEATHER_CACHE.get(city_name)
    if cached is None:
        return None
    expires_at, data = cached
    if expires_at <= datetime.now(timezone.utc):
        _WEATHER_CACHE.pop(city_name, None)
        return None
    return dict(data)


def _set_cached_weather(city_name: str, weather: dict[str, Any]) -> None:
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=WEATHER_CACHE_TTL_SECONDS)
    _WEATHER_CACHE[city_name] = (expires_at, dict(weather))


def _mock_weather(city_name: str) -> dict[str, Any]:
    weather = WEATHER_DATA.get(city_name, WEATHER_DATA["本地"])
    return {
        "city": city_name,
        "weather": weather["weather"],
        "temperature": weather["temperature"],
        "humidity": weather["humidity"],
        "wind_speed": weather["wind_speed"],
        "advice": weather["advice"],
        "source": "mock",
        "updated_at": _now_iso(),
    }


def _fetch_open_meteo_weather(city_name: str) -> dict[str, Any]:
    latitude, longitude = CITY_COORDINATES[city_name]
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
        "timezone": "Asia/Shanghai",
    }
    with httpx.Client(timeout=WEATHER_REQUEST_TIMEOUT_SECONDS, trust_env=False) as client:
        response = client.get(OPEN_METEO_FORECAST_URL, params=params)
        response.raise_for_status()
        payload = response.json()

    current = payload["current"]
    temperature = current["temperature_2m"]
    humidity = current["relative_humidity_2m"]
    wind_speed = current["wind_speed_10m"]
    weather_code = current["weather_code"]
    return {
        "city": city_name,
        "weather": _weather_code_to_text(weather_code),
        "temperature": round(float(temperature), 1),
        "humidity": int(humidity),
        "wind_speed": round(float(wind_speed), 1),
        "advice": _build_weather_advice(weather_code, float(temperature), int(humidity), float(wind_speed)),
        "source": "open_meteo",
        "updated_at": current.get("time") or _now_iso(),
    }


def _weather_code_to_text(code: int) -> str:
    code = int(code)
    if code == 0:
        return "晴"
    if code in {1, 2, 3}:
        return "多云"
    if code in {45, 48}:
        return "雾"
    if 51 <= code <= 67 or 80 <= code <= 82:
        return "雨"
    if 71 <= code <= 77 or 85 <= code <= 86:
        return "雪"
    if 95 <= code <= 99:
        return "雷雨"
    return "多云"


def _build_weather_advice(code: int, temperature: float, humidity: int, wind_speed: float) -> str:
    code = int(code)
    if 51 <= code <= 67 or 80 <= code <= 82:
        return "外出建议携带雨具。"
    if 71 <= code <= 77 or 85 <= code <= 86:
        return "注意保暖，外出留意道路湿滑。"
    if temperature >= 32:
        return "气温较高，建议开启空调并注意补水。"
    if humidity >= 80:
        return "空气湿度较高，建议开启除湿。"
    if wind_speed >= 12:
        return "风力较大，外出注意防风。"
    return "天气较适宜，可根据室内状态通风或调节设备。"


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")
