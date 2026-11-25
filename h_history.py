from math import ceil

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from k_settings import history_pager
import formatters as f
from ui import show

router = Router()


async def render_history(target, db, settings, page: int):
    total = await db.history_count()
    size = settings.history_page_size
    pages = max(1, ceil(total / size))
    page = min(max(page, 0), pages - 1)
    if total == 0:
        text = "📜 <b>হিস্টোরি</b>\n\n📭 এখনও কোনো রিকোয়েস্ট নেই।"
    else:
        rows = await db.history(page, size)
        lines = []
        for r in rows:
            icon = "✅" if r["success"] else "❌"
            ms = f" · {f.bn(r['duration_ms'])} মি.সে." if r["duration_ms"] is not None else ""
            lines.append(
                f"{icon} <b>{f.esc(r['name'] or '—')}</b> · {f.ACTION_TEXT.get(r['action'], r['action'])}{ms}\n"
                f"    🕒 {f.fmt_dt(r['created_at'])}"
            )
        text = f"📜 <b>হিস্টোরি</b> (পৃষ্ঠা {f.bn(page + 1)}/{f.bn(pages)})\n\n" + "\n".join(lines)
    await show(target, text, history_pager(page, pages))


@router.message(Command("history"))
async def cmd_history(message: Message, state: FSMContext, db, settings):
    await state.clear()
    await render_history(message, db, settings, 0)


@router.callback_query(F.data.startswith("nav:hist:"))
async def cb_history(cb: CallbackQuery, state: FSMContext, db, settings):
    await state.clear()
    page = int(cb.data.rsplit(":", 1)[1])
    await render_history(cb, db, settings, page)
