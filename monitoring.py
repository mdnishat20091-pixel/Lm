from __future__ import annotations

import time

START_TIME = time.monotonic()


def uptime_seconds() -> int:
    return int(time.monotonic() - START_TIME)


async def collect_health(db) -> dict:
    latency = await db.ping()
    try:
        provs = await db.list_providers() if latency is not None else []
    except Exception:  # noqa: BLE001
        provs = []
    return {
        "db_ok": latency is not None,
        "db_ms": None if latency is None else int(latency),
        "uptime": uptime_seconds(),
        "providers": provs,
    }
