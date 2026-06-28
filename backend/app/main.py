from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api import shifts, dashboard, auth


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="Monitix API",
    version="0.1.0",
    docs_url="/docs" if settings.debug else None,
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


app.include_router(auth.router,      prefix="/api/v1/auth",      tags=["auth"])
app.include_router(shifts.router,    prefix="/api/v1/shifts",    tags=["shifts"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["dashboard"])