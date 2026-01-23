from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.presentation.server.api.v1.router import api_router
from src.utils.config import CONFIG
from src.utils.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting application...")
    yield
    logger.info("Stopping application...")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Review Summarizer API",
        description="Review summarization service",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.include_router(api_router, prefix="/api/v1")

    @app.get("/health", tags=["Health"])
    async def health_check():
        return {"status": "ok"}

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.presentation.server.server:app",
        host=CONFIG.api_host,
        port=CONFIG.api_port,
        reload=True,
    )
