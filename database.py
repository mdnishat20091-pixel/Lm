from __future__ import annotations

import asyncio
import functools
import logging
from pathlib import Path
from typing import Optional

import asyncpg

log = logging.getLogger(__name__)
MIGRATIONS_DIR = Path(__file__).parent

LIST_SQL = """
SELECT p.slug, p.name, p.default_base_url, p.auth_header, p.is_verified, p.position,
       c.base_url, c.api_key_hint, (c.api_key_enc IS NOT NULL) AS configured,
       c.enabled, c.connection_status, c.last_connection_at, c.last_error
FROM providers p JOIN provider_configs c ON c.provider_id = p.id
"""


RETRYABLE = (asyncpg.PostgresConnectionError, asyncpg.InterfaceError, ConnectionError, OSError)


def _retry(fn):
    """সংযোগ-সংক্রান্ত সাময়িক ত্রুটিতে সর্বোচ্চ ৩ বার চেষ্টা করে।"""

    @functools.wraps(fn)
    async def wrapper(self, *args, **kwargs):
        for attempt in (1, 2, 3):
            try:
                return await fn(self, *args, **kwargs)
            except RETRYABLE as exc:
                if attempt == 3:
                    raise
                log.warning("DB connection error (%s), retry %s", type(exc).__name__, attempt)
                await asyncio.sleep(0.4 * attempt)

    return wrapper


class Database:
    def __init__(self, dsn: str):
        self.dsn = dsn
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self) -> None:
        last: Optional[Exception] = None
        for attempt in range(1, 6):
            try:
                self.pool = await asyncpg.create_pool(
                    self.dsn, min_size=1, max_size=5, command_timeout=15,
                    max_inactive_connection_lifetime=20,
                )
                break
            except (OSError, asyncpg.PostgresError) as exc:
                last = exc
                log.warning("Database connection attempt %s failed: %s", attempt, type(exc).__name__)
                await asyncio.sleep(min(2 * attempt, 10))
        else:
            raise RuntimeError("Database connection failed") from last
        await self._migrate()

    async def close(self) -> None:
        if self.pool:
            await self.pool.close()

    async def _migrate(self) -> None:
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("SELECT pg_advisory_xact_lock(727001)")
                await conn.execute(
                    "CREATE TABLE IF NOT EXISTS schema_migrations "
                    "(name TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())"
                )
                done = {r["name"] for r in await conn.fetch("SELECT name FROM schema_migrations")}
                for path in sorted(MIGRATIONS_DIR.glob("[0-9]*.sql")):
                    if path.name in done:
                        continue
                    await conn.execute(path.read_text(encoding="utf-8"))
                    await conn.execute("INSERT INTO schema_migrations (name) VALUES ($1)", path.name)
                    log.info("Applied migration %s", path.name)

    async def ping(self) -> Optional[float]:
        import time
        started = time.monotonic()
        try:
            async with self.pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
        except Exception:  # noqa: BLE001
            return None
        return (time.monotonic() - started) * 1000

    # ---- users / settings / audit ----
    @_retry
    async def touch_user(self, tg_id: int, username, first_name, is_owner: bool) -> None:
        await self.pool.execute(
            """INSERT INTO users (telegram_id, username, first_name, is_owner)
               VALUES ($1,$2,$3,$4)
               ON CONFLICT (telegram_id) DO UPDATE
               SET username=EXCLUDED.username, first_name=EXCLUDED.first_name, last_seen=now()""",
            tg_id, username, first_name, is_owner,
        )

    @_retry
    async def set_setting(self, key: str, value: str) -> None:
        await self.pool.execute(
            """INSERT INTO settings (key, value) VALUES ($1,$2)
               ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value, updated_at=now()""",
            key, value,
        )

    @_retry
    async def audit(self, user_id: Optional[int], action: str, detail: Optional[str] = None) -> None:
        await self.pool.execute(
            "INSERT INTO audit_logs (user_id, action, detail) VALUES ($1,$2,$3)", user_id, action, detail
        )

    @_retry
    async def audit_recent(self, limit: int = 5):
        return await self.pool.fetch(
            "SELECT user_id, action, detail, created_at FROM audit_logs ORDER BY id DESC LIMIT $1", limit
        )

    # ---- providers ----
    @_retry
    async def sync_providers(self, providers) -> None:
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                for pos, p in enumerate(providers):
                    pid = await conn.fetchval(
                        """INSERT INTO providers (slug,name,default_base_url,auth_header,is_verified,position)
                           VALUES ($1,$2,$3,$4,$5,$6)
                           ON CONFLICT (slug) DO UPDATE SET name=EXCLUDED.name,
                             default_base_url=EXCLUDED.default_base_url, auth_header=EXCLUDED.auth_header,
                             is_verified=EXCLUDED.is_verified, position=EXCLUDED.position
                           RETURNING id""",
                        p.slug, p.name, p.default_base_url, p.auth_header, p.verified, pos,
                    )
                    await conn.execute(
                        "INSERT INTO provider_configs (provider_id) VALUES ($1) ON CONFLICT DO NOTHING", pid
                    )
                    if not p.verified:  # যাচাই না হওয়া প্রোভাইডার সবসময় নিষ্ক্রিয়
                        await conn.execute(
                            "UPDATE provider_configs SET enabled=FALSE WHERE provider_id=$1", pid
                        )

    @_retry
    async def list_providers(self):
        return await self.pool.fetch(LIST_SQL + " ORDER BY p.position")

    @_retry
    async def get_provider(self, slug: str):
        return await self.pool.fetchrow(LIST_SQL + " WHERE p.slug=$1", slug)

    @_retry
    async def get_secret(self, slug: str):
        return await self.pool.fetchrow(
            """SELECT c.base_url, c.api_key_enc FROM provider_configs c
               JOIN providers p ON p.id=c.provider_id WHERE p.slug=$1""", slug,
        )

    @_retry
    async def save_config(self, slug, base_url, key_enc, key_hint, status, error, user_id) -> None:
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    """UPDATE provider_configs c SET base_url=$2, api_key_enc=$3, api_key_hint=$4,
                         connection_status=$5, last_error=$6, updated_at=now(), updated_by=$7,
                         last_connection_at = CASE WHEN $5='ok' THEN now() ELSE last_connection_at END
                       FROM providers p WHERE p.id=c.provider_id AND p.slug=$1""",
                    slug, base_url, key_enc, key_hint, status, error, user_id,
                )

    @_retry
    async def set_enabled(self, slug: str, enabled: bool) -> None:
        await self.pool.execute(
            """UPDATE provider_configs c SET enabled=$2, updated_at=now()
               FROM providers p WHERE p.id=c.provider_id AND p.slug=$1""", slug, enabled,
        )

    @_retry
    async def delete_key(self, slug: str) -> None:
        await self.pool.execute(
            """UPDATE provider_configs c SET api_key_enc=NULL, api_key_hint=NULL, enabled=FALSE,
                 connection_status='unknown', last_error=NULL, updated_at=now()
               FROM providers p WHERE p.id=c.provider_id AND p.slug=$1""", slug,
        )

    @_retry
    async def update_status(self, slug: str, status: str, error: Optional[str]) -> None:
        await self.pool.execute(
            """UPDATE provider_configs c SET connection_status=$2, last_error=$3,
                 last_connection_at = CASE WHEN $2='ok' THEN now() ELSE last_connection_at END
               FROM providers p WHERE p.id=c.provider_id AND p.slug=$1""", slug, status, error,
        )

    # ---- request logs ----
    @_retry
    async def log_request(self, user_id, slug, action, success, http_status, duration_ms, error_code) -> None:
        await self.pool.execute(
            """INSERT INTO request_logs (user_id, provider_id, action, success, http_status, duration_ms, error_code)
               VALUES ($1,(SELECT id FROM providers WHERE slug=$2),$3,$4,$5,$6,$7)""",
            user_id, slug, action, success, http_status, duration_ms, error_code,
        )

    @_retry
    async def history_count(self) -> int:
        return await self.pool.fetchval("SELECT count(*) FROM request_logs")

    @_retry
    async def history(self, page: int, size: int):
        return await self.pool.fetch(
            """SELECT p.name, r.action, r.success, r.http_status, r.duration_ms, r.created_at
               FROM request_logs r LEFT JOIN providers p ON p.id=r.provider_id
               ORDER BY r.id DESC LIMIT $1 OFFSET $2""", size, page * size,
        )

    @_retry
    async def last_activity(self):
        return await self.pool.fetchval("SELECT max(created_at) FROM request_logs")

    @_retry
    async def stats_24h(self):
        return await self.pool.fetch(
            """SELECT p.slug, count(*) FILTER (WHERE r.success) AS ok,
                      count(*) FILTER (WHERE NOT r.success) AS bad
               FROM request_logs r JOIN providers p ON p.id=r.provider_id
               WHERE r.created_at > now() - interval '24 hours' GROUP BY p.slug"""
        )
