from __future__ import annotations

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery


async def show(target, text: str, kb=None, alert: str | None = None) -> None:
    """Edit the message for callbacks, send a new one for commands."""
    if isinstance(target, CallbackQuery):
        try:
            await target.message.edit_text(text, reply_markup=kb)
        except TelegramBadRequest as exc:
            if "message is not modified" not in str(exc):
                await target.message.answer(text, reply_markup=kb)
        try:
            await target.answer(alert)
        except TelegramBadRequest:
            pass  # ইতিমধ্যে উত্তর দেওয়া হয়েছে
    else:
        await target.answer(text, reply_markup=kb)
