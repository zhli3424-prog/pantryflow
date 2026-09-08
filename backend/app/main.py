from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import inspect, text

from . import models  # noqa: F401
from .config import settings
from .database import Base, engine
from .routers import health, history, ingredients, recommendations
from .schemas.common import AppError
from .services.demo_data import seed_demo_data


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    if "meal_count" not in {column["name"] for column in inspect(engine).get_columns("ingredients")}:
        # ponytail: one additive SQLite migration is enough for this local MVP.
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE ingredients ADD COLUMN meal_count INTEGER NOT NULL DEFAULT 1"))
    if settings.demo_seed_on_empty:
        from .database import SessionLocal

        with SessionLocal() as db:
            seed_demo_data(db)
    yield


app = FastAPI(title="AI 做饭助手 API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppError)
async def app_error_handler(_: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "data": None, "message": exc.message, "error": {"code": exc.code, "details": None}},
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError):
    details = [
        {"location": list(error["loc"]), "message": error["msg"], "type": error["type"]}
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={"success": False, "data": None, "message": "输入内容有误，请检查后重试", "error": {"code": "VALIDATION_ERROR", "details": details}},
    )


app.include_router(health.router, prefix="/api/v1")
app.include_router(ingredients.router, prefix="/api/v1")
app.include_router(recommendations.router, prefix="/api/v1")
app.include_router(history.router, prefix="/api/v1")
