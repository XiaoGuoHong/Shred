from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException

from shred.core.config import get_env_settings
from shred.core.database import get_session
from shred.messages.router import router as messages_router
from shred.messages.service import MessageService
from shred.events.router import router as events_router
from shred.taxonomy.router import router as taxonomy_router


@asynccontextmanager
async def lifespan(_app: FastAPI):
    session = next(get_session())
    try:
        try:
            settings = get_env_settings()
            count = MessageService(session).reconcile_stale(
                now=datetime.now(UTC),
                timeout_seconds=settings.model_timeout_seconds,
            )
            if count:
                import logging
                logging.getLogger("shred").info("Reconciled %d stale messages", count)
        except OperationalError:
            pass
    finally:
        session.close()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Shred", version="0.1.0", lifespan=lifespan)

    @app.exception_handler(StarletteHTTPException)
    async def _http_error_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        if isinstance(exc.detail, dict) and "error" in exc.detail:
            return JSONResponse(status_code=exc.status_code, content=exc.detail)
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    app.include_router(taxonomy_router, prefix="/api/categories", tags=["categories"])
    app.include_router(messages_router, prefix="/api/messages", tags=["messages"])
    app.include_router(events_router, prefix="/api/events", tags=["events"])

    @app.get("/api/health")
    def health(_: Annotated[Session, Depends(get_session)]) -> dict[str, str]:
        return {"status": "ok", "version": "0.1.0"}

    return app


app = create_app()
