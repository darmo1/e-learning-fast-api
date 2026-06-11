import os
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status


def is_dev() -> bool:
    return os.getenv("ENVIRONMENT", "development").lower() == "development"


class InMemoryRateLimiter:
    """Rate limiter simple por IP, en memoria.

    Suficiente para un MVP con un solo proceso uvicorn; si se escala a varios
    workers/instancias hay que migrar a Redis o similar.
    """

    def __init__(self, max_attempts: int, window_seconds: int):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._attempts: dict[str, deque] = defaultdict(deque)

    def check(self, request: Request):
        ip = request.client.host if request.client else "unknown"
        now = time.monotonic()
        attempts = self._attempts[ip]

        while attempts and now - attempts[0] > self.window_seconds:
            attempts.popleft()

        if len(attempts) >= self.max_attempts:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Demasiados intentos, intenta de nuevo más tarde",
            )
        attempts.append(now)


login_rate_limiter = InMemoryRateLimiter(max_attempts=10, window_seconds=300)
register_rate_limiter = InMemoryRateLimiter(max_attempts=5, window_seconds=3600)
