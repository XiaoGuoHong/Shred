from typing import Annotated

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException

from shred.core.database import get_session
from shred.taxonomy.router import router as taxonomy_router


def create_app() -> FastAPI:
    app = FastAPI(title="Shred", version="0.1.0")

    @app.exception_handler(StarletteHTTPException)
    async def _http_error_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        if isinstance(exc.detail, dict) and "error" in exc.detail:
            return JSONResponse(status_code=exc.status_code, content=exc.detail)
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    app.include_router(taxonomy_router, prefix="/api/categories", tags=["categories"])

    @app.get("/api/health")
    def health(_: Annotated[Session, Depends(get_session)]) -> dict[str, str]:
        return {"status": "ok", "version": "0.1.0"}

    return app


app = create_app()
