import hashlib
import logging
import time
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from secrets import compare_digest

from fastapi import Depends, Header, HTTPException, Request, status

from app.chat.config import settings

logger = logging.getLogger("app.chat.api.security")


class UserRole(StrEnum):
    ATHLETE = "athlete"
    TRAINER = "trainer"
    ADMIN = "admin"


@dataclass(frozen=True)
class AuthenticatedPrincipal:
    subject: str
    role: UserRole
    authenticated: bool


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._requests: dict[str, deque[float]] = defaultdict(deque)

    def reset(self) -> None:
        self._requests.clear()

    def check(self, identity: str, max_requests: int, window_seconds: int) -> bool:
        now = time.monotonic()
        requests = self._requests[identity]
        cutoff = now - window_seconds
        while requests and requests[0] <= cutoff:
            requests.popleft()

        if len(requests) >= max_requests:
            return False

        requests.append(now)
        return True


rate_limiter = InMemoryRateLimiter()


def get_authenticated_principal(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> AuthenticatedPrincipal:
    if not settings.api_auth_enabled:
        return AuthenticatedPrincipal(
            subject="local-anonymous",
            role=UserRole.ADMIN,
            authenticated=False,
        )

    if not x_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key is required")

    for configured_key, role in parse_api_key_roles(settings.api_key_roles).items():
        if compare_digest(x_api_key, configured_key):
            return AuthenticatedPrincipal(
                subject=f"key:{fingerprint_key(configured_key)}",
                role=role,
                authenticated=True,
            )

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")


def enforce_rate_limit(
    request: Request,
    principal: AuthenticatedPrincipal = Depends(get_authenticated_principal),
) -> AuthenticatedPrincipal:
    request.state.principal = principal
    if not settings.api_rate_limit_enabled:
        return principal

    if not rate_limiter.check(
        identity=principal.subject,
        max_requests=settings.api_rate_limit_requests,
        window_seconds=settings.api_rate_limit_window_seconds,
    ):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded")

    return principal


def require_roles(*allowed_roles: UserRole) -> Callable[..., AuthenticatedPrincipal]:
    def dependency(
        principal: AuthenticatedPrincipal = Depends(enforce_rate_limit),
    ) -> AuthenticatedPrincipal:
        if principal.role not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return principal

    return dependency


def parse_api_key_roles(raw_value: str) -> dict[str, UserRole]:
    parsed: dict[str, UserRole] = {}
    for item in raw_value.split(","):
        candidate = item.strip()
        if not candidate:
            continue
        try:
            api_key, raw_role = candidate.rsplit(":", maxsplit=1)
            parsed[api_key] = UserRole(raw_role.strip().lower())
        except ValueError as exc:
            raise ValueError("API_KEY_ROLES entries must use api_key:role format") from exc
    return parsed


def fingerprint_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()[:12]


def log_chat_access(
    principal: AuthenticatedPrincipal,
    endpoint: str,
    status_code: int,
) -> None:
    logger.info(
        "chat_access",
        extra={
            "actor": principal.subject,
            "role": principal.role.value,
            "authenticated": principal.authenticated,
            "path": endpoint,
            "status_code": status_code,
        },
    )
