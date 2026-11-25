from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from typing import Optional

import aiohttp


@dataclass
class TestResult:
    status: str  # ok | invalid_key | failed | unconfirmed | rate_limited | unverified
    http_status: Optional[int] = None
    duration_ms: Optional[int] = None
    error_code: Optional[str] = None


class RateLimiter:
    def __init__(self, per_minute: int):
        self.per_minute = per_minute
        self._hits: deque = deque()

    def try_acquire(self) -> bool:
        now = time.monotonic()
        while self._hits and now - self._hits[0] > 60:
            self._hits.popleft()
        if len(self._hits) >= self.per_minute:
            return False
        self._hits.append(now)
        return True


class BaseProvider:
    slug: str = ""
    name: str = ""
    default_base_url: Optional[str] = None
    auth_header: str = ""
    extra_headers: dict = {}
    test_method: str = "GET"
    test_path: str = ""
    verified: bool = False
    rate_limit_per_min: int = 30

    def __init__(self) -> None:
        self.limiter = RateLimiter(self.rate_limit_per_min)

    def build_url(self, base_url: str) -> str:
        return base_url.rstrip("/") + self.test_path

    def headers(self, api_key: str) -> dict:
        return {**self.extra_headers, self.auth_header: api_key}

    @staticmethod
    def classify(status: int, duration_ms: int) -> TestResult:
        if 200 <= status < 300:
            return TestResult("ok", status, duration_ms)
        if status in (401, 403):
            return TestResult("invalid_key", status, duration_ms, "bad_key")
        if status == 429:
            return TestResult("rate_limited", status, duration_ms, "rate")
        if 300 <= status < 400:
            return TestResult("failed", status, duration_ms, "redirect")
        if status >= 500:
            return TestResult("failed", status, duration_ms, "http_5xx")
        return TestResult("unconfirmed", status, duration_ms, "unconfirmed")

    async def probe(self, session: aiohttp.ClientSession, base_url: str, api_key: str) -> TestResult:
        if not self.verified:
            return TestResult("unverified", error_code="unverified")
        url = self.build_url(base_url)
        started = time.monotonic()
        async with session.request(
            self.test_method, url, headers=self.headers(api_key), allow_redirects=False
        ) as resp:
            status = resp.status
        return self.classify(status, int((time.monotonic() - started) * 1000))
