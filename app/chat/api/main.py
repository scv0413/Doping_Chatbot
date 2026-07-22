from fastapi import FastAPI

from app.chat.api.routes import router
from app.chat.config import settings


def create_app() -> FastAPI:
    app = FastAPI(
        title="Doping Chatbot API",
        version="0.1.0",
        description="REST API for the anti-doping RAG chatbot runtime.",
    )
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
