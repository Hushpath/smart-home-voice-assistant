from typing import Any

from pydantic import BaseModel


class DeviceStateUpdateRequest(BaseModel):
    is_on: bool | None = None
    is_online: bool | None = None
    properties: dict[str, Any] | None = None
