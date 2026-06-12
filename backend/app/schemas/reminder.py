from datetime import datetime

from pydantic import BaseModel, Field


class ReminderCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    remind_time: datetime | None = None


class ReminderUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    remind_time: datetime | None = None
    is_done: bool | None = None
