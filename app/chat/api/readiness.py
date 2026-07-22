from pathlib import Path

from pydantic import BaseModel, Field

from app.chat.config import settings


class ReadinessCheck(BaseModel):
    name: str
    ready: bool
    detail: str


class ReadinessResponse(BaseModel):
    status: str
    checks: list[ReadinessCheck] = Field(default_factory=list)


def build_readiness_response() -> ReadinessResponse:
    checks = [
        check_directory("processed_data_dir", settings.processed_data_dir),
        check_directory("index_dir", settings.index_dir),
    ]
    status = "ready" if all(check.ready for check in checks) else "not_ready"
    return ReadinessResponse(status=status, checks=checks)


def check_directory(name: str, path: Path) -> ReadinessCheck:
    if not path.exists():
        return ReadinessCheck(name=name, ready=False, detail=f"missing: {path}")
    if not path.is_dir():
        return ReadinessCheck(name=name, ready=False, detail=f"not a directory: {path}")
    return ReadinessCheck(name=name, ready=True, detail=str(path))
