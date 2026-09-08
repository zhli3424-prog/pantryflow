from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import RecipeHistory
from ..schemas.common import AppError, ok
from ..schemas.recipe import HistoryRead

router = APIRouter(prefix="/history", tags=["history"])


@router.get("")
def list_history(db: Session = Depends(get_db)):
    rows = db.scalars(select(RecipeHistory).order_by(RecipeHistory.cooked_at.desc())).all()
    return ok([HistoryRead.model_validate(row).model_dump(mode="json") for row in rows])


@router.get("/{history_id}")
def get_history(history_id: int, db: Session = Depends(get_db)):
    row = db.get(RecipeHistory, history_id)
    if not row:
        raise AppError(404, "HISTORY_NOT_FOUND", "历史记录不存在")
    return ok(HistoryRead.model_validate(row).model_dump(mode="json"))
