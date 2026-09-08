import hashlib
import json
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import Ingredient, RecommendationBatch, RecipeRecommendation
from ..schemas.common import AppError
from ..schemas.recipe import RecommendationRequest
from .ai_service import generate_recipes


def _inventory_payload(items: list[Ingredient]) -> list[dict]:
    return [
        {
            "id": item.id,
            "name": item.name,
            "quantity": item.meal_count,
            "unit": "餐",
            "expire_at": item.expire_at,
            "days_to_expire": (item.expire_at - date.today()).days if item.expire_at else None,
        }
        for item in items
    ]


def inventory_snapshot(items: list[Ingredient]) -> list[dict]:
    payload = _inventory_payload(sorted(items, key=lambda item: item.id))
    return json.loads(json.dumps(payload, ensure_ascii=False, default=str))


def inventory_signature(items: list[Ingredient]) -> str:
    encoded = json.dumps(inventory_snapshot(items), ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _usable_inventory(db: Session) -> tuple[list[Ingredient], list[Ingredient]]:
    items = db.scalars(select(Ingredient).where(Ingredient.meal_count > 0)).all()
    usable = [item for item in items if item.expire_at is None or item.expire_at >= date.today()]
    if not usable:
        raise AppError(400, "NO_USABLE_INVENTORY", "没有可用食材，请先添加或处理过期食材")
    usable.sort(key=lambda item: (item.expire_at is None, item.expire_at or date.max, item.created_at))
    return items, usable


def _validate_and_rank(result, usable: list[Ingredient]):
    stock: dict[str, Decimal] = {}
    nearest: dict[str, int] = {}
    for item in usable:
        stock[item.name] = stock.get(item.name, Decimal("0")) + Decimal(item.meal_count)
        if item.expire_at:
            nearest[item.name] = min(nearest.get(item.name, 9999), (item.expire_at - date.today()).days)

    validated = []
    for recipe in result.recipes:
        for use in recipe.consumptions:
            if use.ingredient_name not in stock or use.quantity > stock[use.ingredient_name]:
                raise AppError(502, "AI_INVENTORY_MISMATCH", "AI 推荐与当前库存不匹配，请重新生成")
        score = sum(max(0, 6 - nearest.get(name, 6)) for name in recipe.used_ingredients)
        score += len(recipe.used_ingredients) * 2 - len(recipe.missing_ingredients) * 2
        validated.append((score, recipe))
    return [recipe for _, recipe in sorted(validated, key=lambda pair: pair[0], reverse=True)]


def generate_and_save(
    db: Session, preferences: RecommendationRequest
) -> list[RecipeRecommendation]:
    items, usable = _usable_inventory(db)

    recent_dishes = db.scalars(
        select(RecipeRecommendation.dish_name)
        .order_by(RecipeRecommendation.created_at.desc(), RecipeRecommendation.id.desc())
        .limit(4)
    ).all()
    recommendation_count = db.scalar(select(func.count(RecipeRecommendation.id))) or 0
    result, provider = generate_recipes(
        _inventory_payload(usable),
        list(recent_dishes),
        rotation_seed=recommendation_count // 4,
        preferences=preferences,
    )
    saved = []
    for recipe in _validate_and_rank(result, usable):
        row = RecipeRecommendation(
            **recipe.model_dump(mode="json"),
            ai_provider=provider,
        )
        db.add(row)
        saved.append(row)
    db.flush()
    db.add(RecommendationBatch(
        recipe_ids=[row.id for row in saved],
        inventory_signature=inventory_signature(items),
        inventory_snapshot=inventory_snapshot(items),
        preferences=preferences.model_dump(mode="json"),
    ))
    db.flush()
    return saved


def replace_in_latest_batch(
    db: Session,
    recommendation_id: int,
    preferences_override: RecommendationRequest | None = None,
) -> RecipeRecommendation:
    current = db.get(RecipeRecommendation, recommendation_id)
    if not current:
        raise AppError(404, "RECIPE_NOT_FOUND", "菜谱不存在")
    if current.status == "cooked":
        raise AppError(409, "RECIPE_ALREADY_COOKED", "已经做过的菜不能替换")

    batches = db.scalars(select(RecommendationBatch).order_by(RecommendationBatch.id.desc())).all()
    batch = next((item for item in batches if recommendation_id in item.recipe_ids), None)
    if not batch:
        raise AppError(404, "RECOMMENDATION_BATCH_NOT_FOUND", "这份菜单太旧，请先生成一批新菜单")

    items, usable = _usable_inventory(db)
    current_rows = db.scalars(
        select(RecipeRecommendation).where(RecipeRecommendation.id.in_(batch.recipe_ids))
    ).all()
    current_names = {row.dish_name for row in current_rows}
    preferences = preferences_override or RecommendationRequest.model_validate(batch.preferences)
    base_seed = db.scalar(select(func.count(RecipeRecommendation.id))) or 0
    replacement = None
    provider = "mock"
    for offset in range(1, 7):
        result, provider = generate_recipes(
            _inventory_payload(usable),
            list(current_names),
            rotation_seed=base_seed + offset,
            preferences=preferences,
        )
        replacement = next(
            (recipe for recipe in _validate_and_rank(result, usable) if recipe.dish_name not in current_names),
            None,
        )
        if replacement:
            break
    if not replacement:
        raise AppError(409, "NO_ALTERNATIVE_RECIPE", "当前条件下没有其他合适菜品，可以调整筛选后再试")

    row = RecipeRecommendation(**replacement.model_dump(mode="json"), ai_provider=provider)
    db.add(row)
    db.flush()
    recipe_ids = list(batch.recipe_ids)
    recipe_ids[recipe_ids.index(recommendation_id)] = row.id
    batch.recipe_ids = recipe_ids
    batch.inventory_signature = inventory_signature(items)
    batch.inventory_snapshot = inventory_snapshot(items)
    batch.preferences = preferences.model_dump(mode="json")
    batch.created_at = datetime.now(timezone.utc)
    db.flush()
    return row
