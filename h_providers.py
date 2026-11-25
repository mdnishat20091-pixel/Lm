from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import k_providers as kb
from k_main import confirm_kb
from provider_registry import PROVIDERS
from security import mask_key
import formatters as f
from ui import show

router = Router()


async def render_list(target, db):
    provs = await db.list_providers()
    text = "📡 <b>প্রোভাইডার ম্যানেজমেন্ট</b>\n\n" + "\n\n".join(f.provider_card(p) for p in provs)
    await show(target, text, kb.provider_list(provs))


async def render_page(target, db, slug: str, prefix: str = ""):
    p = await db.get_provider(slug)
    text = f.provider_page(p, mask_key(p["api_key_hint"]))
    if prefix:
        text = prefix + "\n\n" + text
    await show(target, text, kb.provider_page(p))


@router.message(Command("providers"))
async def cmd_providers(message: Message, state: FSMContext, db):
    await state.clear()
    await render_list(message, db)


@router.callback_query(F.data == "nav:prov")
async def cb_list(cb: CallbackQuery, state: FSMContext, db):
    await state.clear()
    await render_list(cb, db)


def _slug(cb: CallbackQuery):
    slug = cb.data.split(":", 1)[1]
    return slug if slug in PROVIDERS else None


@router.callback_query(F.data.startswith("p:"))
async def cb_page(cb: CallbackQuery, db):
    slug = _slug(cb)
    if slug:
        await render_page(cb, db, slug)


@router.callback_query(F.data.startswith("pt:"))
async def cb_test(cb: CallbackQuery, db, api):
    slug = _slug(cb)
    if not slug:
        return
    await cb.answer()
    await cb.message.edit_text("🔄 সংযোগ পরীক্ষা করা হচ্ছে...")
    result = await api.test_saved(slug, cb.from_user.id)
    if result is None:
        await render_page(cb, db, slug, "⚠️ প্রথমে API Key ও Base URL কনফিগার করুন।")
        return
    await render_page(cb, db, slug, f.banner(result))


@router.callback_query(F.data.startswith("pe:"))
async def cb_toggle(cb: CallbackQuery, db):
    slug = _slug(cb)
    if not slug:
        return
    p = await db.get_provider(slug)
    if not (p["configured"] and p["is_verified"]):
        await cb.answer("⚠️ এই প্রোভাইডার এখন সক্রিয় করা যাবে না।", show_alert=True)
        return
    if p["enabled"]:
        await show(cb, f"⚪ <b>{f.esc(p['name'])}</b> নিষ্ক্রিয় করতে চান?", confirm_kb(f"pec:{slug}", f"p:{slug}"))
        return
    await db.set_enabled(slug, True)
    await db.audit(cb.from_user.id, "enabled", slug)
    await render_page(cb, db, slug, "💾 সেটিংস সফলভাবে সংরক্ষণ হয়েছে।")


@router.callback_query(F.data.startswith("pec:"))
async def cb_disable(cb: CallbackQuery, db):
    slug = _slug(cb)
    if not slug:
        return
    await db.set_enabled(slug, False)
    await db.audit(cb.from_user.id, "disabled", slug)
    await render_page(cb, db, slug, "💾 সেটিংস সফলভাবে সংরক্ষণ হয়েছে।")


@router.callback_query(F.data.startswith("pd:"))
async def cb_delete_ask(cb: CallbackQuery, db):
    slug = _slug(cb)
    if not slug:
        return
    p = await db.get_provider(slug)
    await show(
        cb,
        f"🗑 <b>{f.esc(p['name'])}</b> এর API Key মুছে ফেলতে চান?\nপ্রোভাইডার নিষ্ক্রিয় হয়ে যাবে।",
        confirm_kb(f"pdc:{slug}", f"p:{slug}"),
    )


@router.callback_query(F.data.startswith("pdc:"))
async def cb_delete(cb: CallbackQuery, db):
    slug = _slug(cb)
    if not slug:
        return
    await db.delete_key(slug)
    await db.audit(cb.from_user.id, "key_deleted", slug)
    await render_page(cb, db, slug, "🗑 API Key মুছে ফেলা হয়েছে।")
