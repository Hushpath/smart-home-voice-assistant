from pydantic import BaseModel, Field


class CommandParseRequest(BaseModel):
    command: str = Field(default="", max_length=200)
    dialect: str | None = Field(default=None, max_length=20)


class CommandExecuteRequest(BaseModel):
    command: str = Field(default="", max_length=200)
    dialect: str | None = Field(default=None, max_length=20)
