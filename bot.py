from __future__ import annotations

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, ErrorEvent

from config import ConfigError, load_settings
from database import Database
import h_health as health
import h_help as help_h
import h_history as history
import h_providers as prov_h
import h_settings as settings_h
import h_start as start
from provider_registry import PROVIDERS
from api_manager import ApiManager
from logger import setup_logging
from security import AuthMiddleware, Encryptor, ThrottleMiddleware

log = logging.getLogger("bot")

COMMANDS = [
    ("start", "মূল মেনু"),
    ("menu", "প্রধান ড্যাশবোর্ড"),
    ("providers", "প্রোভাইডার"),
    ("settings", "সেটিংস"),
    ("api", "API সেটিংস"),
    ("health", "সিস্টেমের অবস্থা"),
    ("history", "হিস্টোরি"),
    ("help", "সাহায্য"),
    ("cancel", "বাতিল"),
]


async def on_error(event: ErrorEvent) -> bool:
    log.error("Handler error: %s", type(event.exception).__name__, exc_info=event.exception)
    text = "⚠️ একটি সমস্যা হয়েছে। অনুগ্রহ করে আবার চেষ্টা করুন।"
    update = event.update
    try:
        if update.callback_query:
            await update.callback_query.answer(text, show_alert=True)
        elif update.message:
            await update.message.answer(text)
    except Exception:  # noqa: BLE001
        pass
    return True


async def main() -> None:
    setup_logging()
    try:
        settings = load_settings()
    except ConfigError as exc:
        log.critical("Configuration error: %s", exc)
        sys.exit(1)

    db = Database(settings.database_url)
    try:
        await db.connect()
    except RuntimeError as exc:
        log.critical("%s", exc)
        sys.exit(1)
    await db.sync_providers(PROVIDERS.values())
    await db.set_setting("last_start", "ok")

    api = ApiManager(db, Encryptor(settings.encryption_key), settings)
    await api.start()

    bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    try:
        me = await bot.get_me()
        log.info("Bot started as @%s (allowed users: %d)", me.username, len(settings.allowed_user_ids))

        dp = Dispatcher(storage=MemoryStorage(), db=db, api=api, settings=settings)
        for observer in (dp.message, dp.callback_query):
            observer.outer_middleware(AuthMiddleware(settings, db))
            observer.outer_middleware(ThrottleMiddleware(settings.user_rate_events, settings.user_rate_window))
        dp.errors.register(on_error)
        dp.include_routers(start.router, prov_h.router, history.router, health.router, help_h.router, settings_h.router)

        await bot.set_my_commands([BotCommand(command=c, description=d) for c, d in COMMANDS])
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        log.info("Shutting down")
        await api.close()
        await db.close()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
