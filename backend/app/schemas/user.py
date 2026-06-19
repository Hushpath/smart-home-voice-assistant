from pydantic import BaseModel, Field, field_validator


SUPPORTED_DIALECTS = {"auto", "mandarin", "cantonese", "southwest", "northeast"}
SUPPORTED_INPUT_MODES = {"cloud_asr", "browser_speech", "text"}


class UserPreferenceUpdateRequest(BaseModel):
    preferred_dialect: str | None = None
    preferred_input_mode: str | None = None

    @field_validator("preferred_dialect")
    @classmethod
    def validate_preferred_dialect(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip().lower()
        if normalized not in SUPPORTED_DIALECTS:
            raise ValueError("preferred_dialect 只能是 auto、mandarin、cantonese、southwest、northeast")
        return normalized

    @field_validator("preferred_input_mode")
    @classmethod
    def validate_preferred_input_mode(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip().lower()
        if normalized not in SUPPORTED_INPUT_MODES:
            raise ValueError("preferred_input_mode 只能是 cloud_asr、browser_speech 或 text")
        return normalized


class DeviceAliasCreateRequest(BaseModel):
    device_id: int
    alias: str = Field(min_length=2, max_length=20)

    @field_validator("alias")
    @classmethod
    def validate_alias(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("alias 不能为空")
        if len(normalized) < 2 or len(normalized) > 20:
            raise ValueError("alias 长度应为 2-20 个字符")
        return normalized
