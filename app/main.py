from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.db.base import Base
from app.db.session import engine

STATIC_DIR = Path(__file__).resolve().parents[1] / "static"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if settings.ENABLE_EXPERIMENT_MODE:
        from app.modules.experimental import models as experiment_models

        _ = (experiment_models.Participant, experiment_models.RoundLog)
        Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="LIOS", lifespan=lifespan)

if settings.ENABLE_EXPERIMENT_MODE:
    from app.modules.experimental.router import router as experiment_router

    app.include_router(experiment_router, prefix="/api/v1/experiment", tags=["experiment"])


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
