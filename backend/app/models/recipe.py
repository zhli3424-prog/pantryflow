from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class RecipeRecommendation(Base):
    __tablename__ = "recipe_recommendations"

    id: Mapped[int] = mapped_column(primary_key=True)
    dish_name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(String(300))
    used_ingredients: Mapped[list[str]] = mapped_column(JSON)
    missing_ingredients: Mapped[list[str]] = mapped_column(JSON)
    consumptions: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    cooking_time: Mapped[int] = mapped_column(Integer)
    difficulty: Mapped[str] = mapped_column(String(20))
    steps: Mapped[list[str]] = mapped_column(JSON)
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="recommended")
    ai_provider: Mapped[str] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class RecipeHistory(Base):
    __tablename__ = "recipe_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    recommendation_id: Mapped[int] = mapped_column(
        ForeignKey("recipe_recommendations.id"), unique=True, index=True
    )
    dish_name: Mapped[str] = mapped_column(String(100))
    ingredients: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    cooked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class RecommendationBatch(Base):
    __tablename__ = "recommendation_batches"

    id: Mapped[int] = mapped_column(primary_key=True)
    recipe_ids: Mapped[list[int]] = mapped_column(JSON)
    inventory_signature: Mapped[str] = mapped_column(String(64), index=True)
    inventory_snapshot: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    preferences: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
