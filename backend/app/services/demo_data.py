from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import Ingredient, RecipeHistory, RecipeRecommendation


def seed_demo_data(db: Session) -> bool:
    """Add anonymous showcase data only when both pantry and history are empty."""
    ingredient_count = db.scalar(select(func.count(Ingredient.id))) or 0
    history_count = db.scalar(select(func.count(RecipeHistory.id))) or 0
    if ingredient_count or history_count:
        return False

    today = date.today()
    now = datetime.now(timezone.utc)
    ingredients = [
        ("西红柿", 3, 1),
        ("青椒", 2, 2),
        ("猪肉", 3, 3),
        ("鸡胸肉", 3, 4),
        ("鸡蛋", 5, 5),
        ("胡萝卜", 3, 7),
        ("土豆", 4, 8),
    ]
    db.add_all([
        Ingredient(name=name, quantity=1, unit="餐", meal_count=meals, expire_at=today + timedelta(days=days))
        for name, meals, days in ingredients
    ])

    cooked = [
        ("青椒肉丝", ["青椒", "猪肉"], 1),
        ("西红柿炒鸡蛋", ["西红柿", "鸡蛋"], 3),
        ("土豆炖肉", ["土豆", "猪肉"], 6),
    ]
    for dish_name, used, days_ago in cooked:
        cooked_at = now - timedelta(days=days_ago)
        recommendation = RecipeRecommendation(
            dish_name=dish_name,
            description="用现有食材完成的一道日常家常菜",
            used_ingredients=used,
            missing_ingredients=[],
            consumptions=[{"ingredient_name": name, "quantity": 1, "unit": "餐"} for name in used],
            cooking_time=20,
            difficulty="简单",
            steps=["准备并切好食材", "按顺序炒熟并调味"],
            reason="优先使用现有和临期食材",
            status="cooked",
            ai_provider="mock",
            created_at=cooked_at,
        )
        db.add(recommendation)
        db.flush()
        db.add(RecipeHistory(
            recommendation_id=recommendation.id,
            dish_name=dish_name,
            ingredients=recommendation.consumptions,
            cooked_at=cooked_at,
        ))

    db.commit()
    return True
