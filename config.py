from __future__ import annotations

import base64
import hashlib
import os
from dataclasses import dataclass

from cryptography.fernet import Fernet


class ConfigError(Exception):
    pass


def _parse_ids(raw: str, name: str) -> set[int]:
    ids: set[int] = set()
    for part in raw.replace(";", ",").split(","):
        part = part.strip()
        if not part:
            continue
        if not part.isdigit():
            raise ConfigError(f"{name} contains a non-numeric value")
        ids.add(int(part))
    return ids


@dataclass(frozen=True)
class Settings:
    bot_token: str
    owner_id: int
    allowed_user_ids: frozenset
    database_url: str
    encryption_key: bytes
    request_timeout: int = 15
    user_rate_events: int = 20
    user_rate_window: int = 10
    history_page_size: int = 6
    default_provider_rate_per_min: int = 30


def load_settings() -> Settings:
    token = os.getenv("BOT_TOKEN", "").strip()
    owner_raw = os.getenv("OWNER_ID", "").strip()
    db_url = os.getenv("DATABASE_URL", "").strip()
    missing = [n for n, v in (("BOT_TOKEN", token), ("OWNER_ID", owner_raw), ("DATABASE_URL", db_url)) if not v]
    if missing:
        raise ConfigError("Missing environment variables: " + ", ".join(missing))
    if not owner_raw.isdigit():
        raise ConfigError("OWNER_ID must be numeric")
    owner = int(owner_raw)
    allowed = _parse_ids(os.getenv("ALLOWED_USER_IDS", ""), "ALLOWED_USER_IDS")
    allowed.add(owner)
    if len(allowed) > 10:
        raise ConfigError("Too many allowed users for a private bot (max 10)")
    if db_url.startswith("postgres://"):
        db_url = "postgresql://" + db_url[len("postgres://"):]

    key_raw = os.getenv("ENCRYPTION_KEY", "").strip()
    if key_raw:
        try:
            Fernet(key_raw.encode())
        except Exception as exc:  # noqa: BLE001
            raise ConfigError("ENCRYPTION_KEY is not a valid Fernet key") from exc
        key = key_raw.encode()
    else:
        digest = hashlib.sha256(("provider-bot:" + token).encode()).digest()
        key = base64.urlsafe_b64encode(digest)

    return Settings(
        bot_token=token,
        owner_id=owner,
        allowed_user_ids=frozenset(allowed),
        database_url=db_url,
        encryption_key=key,
    )
