from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Ingredient, RecommendationBatch, RecipeHistory, RecipeRecommendation
from ..schemas.common import AppError, ok
from ..schemas.recipe import HistoryRead, RecommendationRead, RecommendationRequest
from ..services.inventory_service import complete_recipe
from ..services.recommendation_service import generate_and_save, inventory_signature, replace_in_latest_batch

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.post("", status_code=201)
def create_recommendations(
    payload: RecommendationRequest | None = None,
    db: Session = Depends(get_db),
):
    rows = generate_and_save(db, payload or RecommendationRequest())
    db.commit()
    return ok([RecommendationRead.model_validate(row).model_dump(mode="json") for row in rows], "推荐已生成")


@router.get("/latest")
def get_latest_recommendations(db: Session = Depends(get_db)):
    batch = db.scalar(select(RecommendationBatch).order_by(RecommendationBatch.id.desc()))
    if not batch:
        return ok(None)
    rows = db.scalars(
        select(RecipeRecommendation).where(RecipeRecommendation.id.in_(batch.recipe_ids))
    ).all()
    by_id = {row.id: row for row in rows}
    recipes = [
        RecommendationRead.model_validate(by_id[recipe_id]).model_dump(mode="json")
        for recipe_id in batch.recipe_ids
        if recipe_id in by_id
    ]
    ingredients = db.scalars(select(Ingredient).where(Ingredient.meal_count > 0)).all()
    return ok({
        "recipes": recipes,
        "inventory_changed": batch.inventory_signature != inventory_signature(ingredients),
        "preferences": RecommendationRequest.model_validate(batch.preferences).model_dump(mode="json"),
        "created_at": batch.created_at.isoformat(),
    })


@router.get("/{recommendation_id}")
def get_recommendation(recommendation_id: int, db: Session = Depends(get_db)):
    row = db.get(RecipeRecommendation, recommendation_id)
    if not row:
        raise AppError(404, "RECIPE_NOT_FOUND", "菜谱不存在")
    return ok(RecommendationRead.model_validate(row).model_dump(mode="json"))


@router.post("/{recommendation_id}/replace")
def replace_recommendation(
    recommendation_id: int,
    payload: RecommendationRequest | None = None,
    db: Session = Depends(get_db),
):
    row = replace_in_latest_batch(db, recommendation_id, payload)
    db.commit()
    db.refresh(row)
    return ok(RecommendationRead.model_validate(row).model_dump(mode="json"), "已换成另一道菜")


@router.post("/{recommendation_id}/cook")
def cook_recommendation(
    recommendation_id: int,
    db: Session = Depends(get_db),
):
    row = db.get(RecipeRecommendation, recommendation_id)
    if not row:
        raise AppError(404, "RECIPE_NOT_FOUND", "菜谱不存在")
    try:
        history = complete_recipe(db, row)
        db.commit()
        db.refresh(history)
    except Exception:
        db.rollback()
        raise
    return ok(HistoryRead.model_validate(history).model_dump(mode="json"), "已完成，库存已更新")
