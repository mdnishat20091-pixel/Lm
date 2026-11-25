from __future__ import annotations

import logging
import time
from collections import defaultdict, deque

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message
from cryptography.fernet import Fernet, InvalidToken

log = logging.getLogger(__name__)


class Encryptor:
    def __init__(self, key: bytes):
        self._f = Fernet(key)

    def encrypt(self, value: str) -> str:
        return self._f.encrypt(value.encode()).decode()

    def decrypt(self, token: str):
        try:
            return self._f.decrypt(token.encode()).decode()
        except InvalidToken:
            return None


def key_hint(key: str) -> str:
    return key[-4:] if len(key) >= 12 else ""


def mask_key(hint: str | None) -> str:
    return "••••••••" + (hint or "")


async def _deny(event, text: str) -> None:
    if isinstance(event, CallbackQuery):
        await event.answer(text, show_alert=True)
    elif isinstance(event, Message):
        await event.answer(text)


class AuthMiddleware(BaseMiddleware):
    def __init__(self, settings, db):
        self.allowed = settings.allowed_user_ids
        self.owner = settings.owner_id
        self.db = db

    async def __call__(self, handler, event, data):
        user = data.get("event_from_user")
        if user is None or user.id not in self.allowed:
            log.warning("Unauthorized access attempt from id=%s", getattr(user, "id", None))
            await _deny(event, "🚫 এই বট ব্যবহারের অনুমতি আপনার নেই।")
            return None
        try:
            await self.db.touch_user(user.id, user.username, user.first_name, user.id == self.owner)
        except Exception:  # noqa: BLE001
            log.exception("touch_user failed")
        return await handler(event, data)


class ThrottleMiddleware(BaseMiddleware):
    def __init__(self, events: int, window: int):
        self.events, self.window = events, window
        self._hits = defaultdict(deque)

    async def __call__(self, handler, event, data):
        user = data.get("event_from_user")
        if user is not None:
            q = self._hits[user.id]
            now = time.monotonic()
            while q and now - q[0] > self.window:
                q.popleft()
            if len(q) >= self.events:
                await _deny(event, "⏳ অনুগ্রহ করে কিছুক্ষণ অপেক্ষা করুন।")
                return None
            q.append(now)
        return await handler(event, data)
