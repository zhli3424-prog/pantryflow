from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Consumption(BaseModel):
    ingredient_name: str = Field(min_length=1, max_length=100)
    quantity: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    unit: str = Field(min_length=1, max_length=20)


class AIRecipe(BaseModel):
    dish_name: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=300)
    used_ingredients: list[str] = Field(min_length=1)
    missing_ingredients: list[str] = Field(default_factory=list, max_length=3)
    consumptions: list[Consumption] = Field(min_length=1)
    cooking_time: int = Field(ge=1, le=180)
    difficulty: Literal["简单", "中等"]
    steps: list[str] = Field(min_length=2, max_length=12)
    reason: str = Field(min_length=1, max_length=300)

    @field_validator("used_ingredients", "missing_ingredients", "steps")
    @classmethod
    def clean_lists(cls, values: list[str]) -> list[str]:
        cleaned = [item.strip() for item in values if item.strip()]
        if len(cleaned) != len(set(cleaned)):
            raise ValueError("列表中不能有重复项")
        return cleaned


class AIRecipeList(BaseModel):
    recipes: list[AIRecipe] = Field(min_length=1, max_length=5)


class RecommendationRequest(BaseModel):
    style: Literal["不限", "家常菜", "川菜", "粤菜", "汤羹", "减脂"] = "不限"
    max_time: int | None = Field(default=None, ge=5, le=180)
    spicy: Literal["不限", "不辣", "辣"] = "不限"
    equipment: Literal["不限", "炒锅", "蒸锅", "空气炸锅"] = "不限"
    pantry_items: list[str] = Field(default_factory=list, max_length=30)
    excluded_dishes: list[str] = Field(default_factory=list, max_length=50)

    @field_validator("pantry_items", "excluded_dishes")
    @classmethod
    def clean_pantry_items(cls, values: list[str]) -> list[str]:
        return list(dict.fromkeys(item.strip() for item in values if item.strip()))


class RecommendationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    dish_name: str
    description: str
    used_ingredients: list[str]
    missing_ingredients: list[str]
    consumptions: list[dict]
    cooking_time: int
    difficulty: str
    steps: list[str]
    reason: str
    status: str
    ai_provider: str
    created_at: datetime


class HistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    recommendation_id: int
    dish_name: str
    ingredients: list[dict]
    cooked_at: datetime
