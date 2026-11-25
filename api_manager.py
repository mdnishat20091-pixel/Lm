from __future__ import annotations

import asyncio
import logging
from typing import Optional

import aiohttp

from provider_registry import PROVIDERS, TestResult

log = logging.getLogger(__name__)


class ApiManager:
    def __init__(self, db, enc, settings):
        self.db, self.enc, self.settings = db, enc, settings
        self.session: Optional[aiohttp.ClientSession] = None

    async def start(self) -> None:
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.settings.request_timeout),
            connector=aiohttp.TCPConnector(ssl=True),
        )

    async def close(self) -> None:
        if self.session:
            await self.session.close()

    async def test(self, slug: str, base_url: str, api_key: str, user_id: Optional[int] = None) -> TestResult:
        provider = PROVIDERS[slug]
        if not provider.verified:
            return TestResult("unverified", error_code="unverified")
        if not provider.limiter.try_acquire():
            result = TestResult("rate_limited", error_code="rate")
        else:
            try:
                result = await provider.probe(self.session, base_url, api_key)
            except asyncio.TimeoutError:
                result = TestResult("failed", error_code="timeout")
            except aiohttp.ClientError:
                result = TestResult("failed", error_code="network")
            except Exception:  # noqa: BLE001
                log.exception("Unexpected probe error for %s", slug)
                result = TestResult("failed", error_code="internal")
        try:
            await self.db.log_request(
                user_id, slug, "test", result.status == "ok", result.http_status,
                result.duration_ms, result.error_code,
            )
        except Exception:  # noqa: BLE001
            log.exception("log_request failed")
        return result

    async def test_saved(self, slug: str, user_id: Optional[int]) -> Optional[TestResult]:
        secret = await self.db.get_secret(slug)
        if not secret or not secret["api_key_enc"] or not secret["base_url"]:
            return None
        key = self.enc.decrypt(secret["api_key_enc"])
        if key is None:
            await self.db.update_status(slug, "failed", "decrypt")
            return TestResult("failed", error_code="decrypt")
        result = await self.test(slug, secret["base_url"], key, user_id)
        await self.db.update_status(slug, result.status, result.error_code)
        return result
