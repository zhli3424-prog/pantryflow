from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..schemas.common import ok

router = APIRouter(tags=["health"])


@router.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    ai_status = "mock" if settings.ai_provider == "mock" else ("ok" if settings.ai_api_key else "degraded")
    return ok({"api": "ok", "database": "ok", "ai": ai_status})
