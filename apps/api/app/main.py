from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.db.init_db import init_db
from app.routes import router


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


settings = get_settings()

app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix=settings.api_prefix)

settings.storage_dir.mkdir(parents=True, exist_ok=True)
app.mount("/storage", StaticFiles(directory=settings.storage_dir), name="storage")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
