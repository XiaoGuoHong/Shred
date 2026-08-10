from typing import Annotated

from fastapi import Depends, FastAPI
from sqlalchemy.orm import Session

from shred.core.database import get_session


def create_app() -> FastAPI:
    app = FastAPI(title="Shred", version="0.1.0")

    @app.get("/api/health")
    def health(_: Annotated[Session, Depends(get_session)]) -> dict[str, str]:
        return {"status": "ok", "version": "0.1.0"}

    return app


app = create_app()
