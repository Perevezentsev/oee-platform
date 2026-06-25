from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # При старте: можно добавить прогрев кэша, проверку соединений
    yield
    # При остановке: очистка


app = FastAPI(
    title="OEE Platform API",
    version="0.1.0",
    docs_url="/docs" if settings.debug else None,  # Swagger только в dev
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok", "env": settings.app_env}


# Роутеры подключаем по мере готовности:
# from app.api import shifts, equipment, auth
# app.include_router(auth.router,      prefix="/api/v1/auth",      tags=["auth"])
# app.include_router(equipment.router, prefix="/api/v1/equipment", tags=["equipment"])
# app.include_router(shifts.router,    prefix="/api/v1/shifts",    tags=["shifts"])
