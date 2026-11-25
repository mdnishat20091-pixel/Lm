from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from k_settings import health_kb, monitor_kb
from monitoring import collect_health
import formatters as f
from ui import show

router = Router()


async def render_health(target, db):
    h = await collect_health(db)
    if h["db_ok"]:
        db_line = f"✅ সংযুক্ত ({f.bn(h['db_ms'])} মি.সে.)"
    else:
        db_line = "❌ সংযোগ নেই"
    provs = h["providers"]
    enabled = sum(1 for p in provs if p["enabled"])
    text = (
        "💚 <b>সিস্টেমের অবস্থা</b>\n\n"
        f"🗄 ডাটাবেস: {db_line}\n"
        f"⏱ চালু আছে: {f.fmt_uptime(h['uptime'])}\n"
        f"📡 সক্রিয় প্রোভাইডার: {f.bn(enabled)}/{f.bn(len(provs))}"
    )
    await show(target, text, health_kb())


async def render_monitor(target, db, prefix: str = ""):
    provs = await db.list_providers()
    stats = {r["slug"]: r for r in await db.stats_24h()}
    blocks = []
    for p in provs:
        s = stats.get(p["slug"])
        ok, bad = (s["ok"], s["bad"]) if s else (0, 0)
        blocks.append(
            f"📡 <b>{f.esc(p['name'])}</b> — {f.status_label(f.effective_status(p))}\n"
            f"    ২৪ ঘণ্টা: ✅ {f.bn(ok)} · ❌ {f.bn(bad)}\n"
            f"    🕒 সর্বশেষ সংযোগ: {f.fmt_dt(p['last_connection_at'])}"
        )
    text = (prefix + "\n\n" if prefix else "") + "📊 <b>API মনিটর</b>\n\n" + "\n\n".join(blocks)
    await show(target, text, monitor_kb())


@router.message(Command("health"))
async def cmd_health(message: Message, state: FSMContext, db):
    await state.clear()
    await render_health(message, db)


@router.callback_query(F.data == "nav:health")
async def cb_health(cb: CallbackQuery, state: FSMContext, db):
    await state.clear()
    await render_health(cb, db)


@router.callback_query(F.data == "nav:mon")
async def cb_monitor(cb: CallbackQuery, state: FSMContext, db):
    await state.clear()
    await render_monitor(cb, db)


@router.callback_query(F.data == "mon:all")
async def cb_test_all(cb: CallbackQuery, db, api):
    await cb.answer()
    await cb.message.edit_text("🔄 সংযোগ পরীক্ষা করা হচ্ছে...")
    tested = 0
    for p in await db.list_providers():
        if p["configured"] and p["is_verified"]:
            await api.test_saved(p["slug"], cb.from_user.id)
            tested += 1
    if tested:
        await db.audit(cb.from_user.id, "test_all", None)
        prefix = "✅ সব কনফিগার করা প্রোভাইডার পরীক্ষা করা হয়েছে।"
    else:
        prefix = "ℹ️ পরীক্ষা করার মতো কনফিগার করা প্রোভাইডার নেই।"
    await render_monitor(cb, db, prefix)
