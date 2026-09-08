from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Ingredient
from ..schemas.common import AppError, ok
from ..schemas.ingredient import IngredientCreate, IngredientRead, IngredientUpdate
from ..services.inventory_service import expiry_status
from ..services.ingredient_names import canonical_name

router = APIRouter(prefix="/ingredients", tags=["ingredients"])


def serialize(item: Ingredient) -> dict:
    data = IngredientRead.model_validate(item).model_dump(mode="json")
    data["expiry_status"] = expiry_status(item.expire_at)
    return data


@router.get("")
def list_ingredients(include_expired: bool = True, db: Session = Depends(get_db)):
    items = db.scalars(select(Ingredient)).all()
    items.sort(key=lambda item: (item.expire_at is None, item.expire_at or date.max, item.created_at))
    if not include_expired:
        items = [item for item in items if item.expire_at is None or item.expire_at >= date.today()]
    return ok([serialize(item) for item in items])


@router.post("", status_code=201)
def create_ingredient(payload: IngredientCreate, db: Session = Depends(get_db)):
    data = payload.model_dump()
    data["name"] = canonical_name(payload.name)
    meal_count = data.pop("meal_count")
    existing = db.scalar(select(Ingredient).where(
        Ingredient.name == data["name"],
        Ingredient.expire_at == payload.expire_at,
    ))
    if existing:
        existing.meal_count += meal_count
        db.commit()
        db.refresh(existing)
        return ok(serialize(existing), "相同批次食材已合并")
    item = Ingredient(**data, quantity=1, unit="餐", meal_count=meal_count)
    db.add(item)
    db.commit()
    db.refresh(item)
    return ok(serialize(item), "食材已添加")


@router.get("/{ingredient_id}")
def get_ingredient(ingredient_id: int, db: Session = Depends(get_db)):
    item = db.get(Ingredient, ingredient_id)
    if not item:
        raise AppError(404, "INGREDIENT_NOT_FOUND", "食材不存在")
    return ok(serialize(item))


@router.patch("/{ingredient_id}")
def update_ingredient(ingredient_id: int, payload: IngredientUpdate, db: Session = Depends(get_db)):
    item = db.get(Ingredient, ingredient_id)
    if not item:
        raise AppError(404, "INGREDIENT_NOT_FOUND", "食材不存在")
    data = payload.model_dump(exclude_unset=True)
    if "name" in data:
        data["name"] = canonical_name(data["name"])
    for key, value in data.items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return ok(serialize(item), "食材已更新")


@router.delete("/{ingredient_id}")
def delete_ingredient(ingredient_id: int, db: Session = Depends(get_db)):
    item = db.get(Ingredient, ingredient_id)
    if not item:
        raise AppError(404, "INGREDIENT_NOT_FOUND", "食材不存在")
    db.delete(item)
    db.commit()
    return ok(message="食材已删除")
