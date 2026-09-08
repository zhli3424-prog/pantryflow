from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator


class IngredientCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    meal_count: int = Field(ge=1, le=99)
    expire_at: date | None = None

    @field_validator("name")
    @classmethod
    def strip_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("不能为空")
        return value


class IngredientUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    meal_count: int | None = Field(default=None, ge=1, le=99)
    expire_at: date | None = None

    @field_validator("name")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("不能为空")
        return value


class IngredientRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    meal_count: int
    created_at: datetime
    expire_at: date | None
    expiry_status: str = "normal"
