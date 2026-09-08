from datetime import date
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Ingredient, RecipeHistory, RecipeRecommendation
from ..schemas.common import AppError


def expiry_status(expire_at: date | None) -> str:
    if expire_at is None:
        return "unknown"
    days = (expire_at - date.today()).days
    if days < 0:
        return "expired"
    if days <= 2:
        return "urgent"
    if days <= 5:
        return "soon"
    return "normal"


def complete_recipe(
    db: Session,
    recommendation: RecipeRecommendation,
) -> RecipeHistory:
    existing = db.scalar(
        select(RecipeHistory).where(RecipeHistory.recommendation_id == recommendation.id)
    )
    if existing:
        return existing

    all_items = db.scalars(select(Ingredient)).all()
    all_items.sort(key=lambda item: (item.expire_at is None, item.expire_at or date.max, item.created_at))
    deductions: list[dict] = []
    for ingredient_name in recommendation.used_ingredients:
        matches = [
            item for item in all_items
            if item.name == ingredient_name
            and item.meal_count > 0
            and (item.expire_at is None or item.expire_at >= date.today())
        ]
        if not matches:
            raise AppError(409, "INSUFFICIENT_INVENTORY", f"{ingredient_name}已经没有可用餐数，请更新食材后重试")
        item = matches[0]
        item.meal_count -= 1
        deductions.append({"ingredient_name": item.name, "quantity": 1, "unit": "餐"})
        if item.meal_count == 0:
            db.delete(item)

    history = RecipeHistory(
        recommendation_id=recommendation.id,
        dish_name=recommendation.dish_name,
        ingredients=deductions,
    )
    recommendation.status = "cooked"
    db.add(history)
    db.flush()
    return history
