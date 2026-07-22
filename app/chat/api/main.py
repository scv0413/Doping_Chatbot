from fastapi import FastAPI

from app.chat.api.errors import register_exception_handlers
from app.chat.api.logging import configure_logging, request_logging_middleware
from app.chat.api.routes import router
from app.chat.config import settings


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(
        title="Doping Chatbot API",
        version="0.1.0",
        description="REST API for the anti-doping RAG chatbot runtime.",
    )
    register_exception_handlers(app)
    app.middleware("http")(request_logging_middleware)
    app.include_router(router)

    @app.get("/", tags=["system"])
    def root() -> dict[str, str]:
        return {
            "app": settings.app_name,
            "status": "ok",
            "docs": "/docs",
        }

    return app


app = create_app()
