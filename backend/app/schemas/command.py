from pydantic import BaseModel, Field


class CommandParseRequest(BaseModel):
    command: str = Field(default="", max_length=200)


class CommandExecuteRequest(BaseModel):
    command: str = Field(default="", max_length=200)
