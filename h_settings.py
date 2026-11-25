from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from h_providers import render_page
import k_providers as pkb
import k_settings as skb
from k_main import only_nav
from provider_registry import PROVIDERS
from security import key_hint, mask_key
import formatters as f
from ui import show
from validators import validate_api_key, validate_base_url

log = logging.getLogger(__name__)
router = Router()


class Wizard(StatesGroup):
    url = State()
    key = State()
    confirm = State()


# ---------- সেটিংস ----------
@router.message(Command("settings"))
async def cmd_settings(message: Message, state: FSMContext, settings):
    await state.clear()
    await show(message, _settings_text(settings), skb.settings_menu())


@router.callback_query(F.data == "nav:set")
async def cb_settings(cb: CallbackQuery, state: FSMContext, settings):
    await state.clear()
    await show(cb, _settings_text(settings), skb.settings_menu())


def _settings_text(s) -> str:
    return (
        "⚙️ <b>সেটিংস</b>\n\n"
        f"⏱ রিকোয়েস্ট সময়সীমা: {f.bn(s.request_timeout)} সেকেন্ড\n"
        f"🚦 ব্যবহারকারী সীমা: {f.bn(s.user_rate_window)} সেকেন্ডে {f.bn(s.user_rate_events)}টি অনুরোধ\n"
        f"👥 অনুমোদিত ব্যবহারকারী: {f.bn(len(s.allowed_user_ids))} জন\n"
        "🔒 API Key এনক্রিপশন: সক্রিয়"
    )


# ---------- নিরাপত্তা ----------
@router.callback_query(F.data == "nav:sec")
async def cb_security(cb: CallbackQuery, state: FSMContext, db, settings):
    await state.clear()
    rows = await db.audit_recent(5)
    lines = []
    for r in rows:
        name = PROVIDERS[r["detail"]].name if r["detail"] in PROVIDERS else ""
        lines.append(f"• {f.ACTION_TEXT.get(r['action'], r['action'])} {f.esc(name)} — {f.fmt_dt(r['created_at'])}")
    audit = "\n".join(lines) or "এখনও কোনো রেকর্ড নেই।"
    text = (
        "🔐 <b>নিরাপত্তা</b>\n\n"
        f"👥 অনুমোদিত ব্যবহারকারী: {f.bn(len(settings.allowed_user_ids))} জন\n"
        f"🆔 আপনার আইডি: <code>{cb.from_user.id}</code>\n"
        "🔒 API Key এনক্রিপশন: সক্রিয়\n"
        "🌐 সংযোগ: শুধু HTTPS, রিডাইরেক্ট বন্ধ\n"
        f"⏱ রিকোয়েস্ট সময়সীমা: {f.bn(settings.request_timeout)} সেকেন্ড\n\n"
        "🔒 আপনার API Key নিরাপদে সংরক্ষিত আছে।\n\n"
        f"📋 <b>সাম্প্রতিক কার্যক্রম</b>\n{audit}"
    )
    await show(cb, text, only_nav())


# ---------- API কনফিগারেশন উইজার্ড ----------
async def render_api_list(target, db, prefix: str = ""):
    provs = await db.list_providers()
    text = (prefix + "\n\n" if prefix else "") + "⚙️ <b>API সেটিংস</b>\n\nধাপ ১/৫: প্রোভাইডার নির্বাচন করুন।"
    await show(target, text, pkb.api_provider_list(provs))


@router.message(Command("api"))
async def cmd_api(message: Message, state: FSMContext, db):
    await state.clear()
    await render_api_list(message, db)


@router.callback_query(F.data == "nav:api")
async def cb_api(cb: CallbackQuery, state: FSMContext, db):
    await state.clear()
    await render_api_list(cb, db)


@router.callback_query(F.data.startswith("api:"))
async def wiz_start(cb: CallbackQuery, state: FSMContext, db):
    slug = cb.data.split(":", 1)[1]
    if slug not in PROVIDERS:
        return
    p = await db.get_provider(slug)
    suggested = p["base_url"] or p["default_base_url"]
    await state.clear()
    await state.set_state(Wizard.url)
    await state.update_data(slug=slug, suggested=suggested)
    text = f"⚙️ <b>{f.esc(p['name'])}</b> কনফিগারেশন\n\nধাপ ২/৫: Base URL পাঠান (https সহ)।"
    if suggested:
        text += f"\n\n🌐 বর্তমান/ডিফল্ট:\n<code>{f.esc(suggested)}</code>"
    if not p["is_verified"]:
        text += "\n\nℹ️ এই প্রোভাইডারের ডকুমেন্টেশন যাচাই হয়নি, তাই সংযোগ পরীক্ষা হবে না।"
    await show(cb, text, skb.wizard_url(bool(suggested)))


async def _ask_key(target, state: FSMContext, url: str):
    await state.update_data(url=url)
    await state.set_state(Wizard.key)
    text = (
        "ধাপ ৩/৫: API Key পাঠান।\n\n"
        "🔒 বার্তাটি পাঠানোর পরই চ্যাট থেকে মুছে ফেলা হবে।"
    )
    await show(target, text, skb.wizard_cancel())


@router.callback_query(F.data == "w:def", Wizard.url)
async def wiz_default_url(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    url, err = validate_base_url(data.get("suggested") or "")
    if err:
        await cb.answer(err, show_alert=True)
        return
    await _ask_key(cb, state, url)


@router.message(Wizard.url, F.text, ~F.text.startswith("/"))
async def wiz_url(message: Message, state: FSMContext):
    url, err = validate_base_url(message.text)
    if err:
        await message.answer(err + "\nআবার পাঠান।", reply_markup=skb.wizard_cancel())
        return
    await _ask_key(message, state, url)


@router.message(Wizard.key, F.text, ~F.text.startswith("/"))
async def wiz_key(message: Message, state: FSMContext, api):
    key, err = validate_api_key(message.text)
    try:
        await message.delete()
    except Exception:  # noqa: BLE001
        pass
    if err:
        await message.answer(err + "\nআবার পাঠান।", reply_markup=skb.wizard_cancel())
        return
    data = await state.get_data()
    slug, url = data["slug"], data["url"]
    provider = PROVIDERS[slug]
    status_msg = await message.answer(
        "🔄 সংযোগ পরীক্ষা করা হচ্ছে..." if provider.verified else "⏳ প্রস্তুত করা হচ্ছে..."
    )
    result = await api.test(slug, url, key, message.from_user.id)
    await state.update_data(key=key, status=result.status, error=result.error_code)
    await state.set_state(Wizard.confirm)
    text = (
        f"ধাপ ৫/৫: যাচাই সম্পন্ন\n\n"
        f"📡 {f.esc(provider.name)}\n"
        f"🌐 <code>{f.esc(url)}</code>\n"
        f"🔑 <code>{f.esc(mask_key(key_hint(key)))}</code>\n\n"
        f"{f.banner(result)}\n\nকনফিগারেশন সংরক্ষণ করবেন?"
    )
    await status_msg.edit_text(text, reply_markup=skb.wizard_confirm())


@router.message(Wizard.url)
@router.message(Wizard.key)
async def wiz_bad_input(message: Message):
    if message.text and message.text.startswith("/"):
        return
    await message.answer("⚠️ শুধু টেক্সট পাঠান।", reply_markup=skb.wizard_cancel())


@router.callback_query(F.data == "w:save", Wizard.confirm)
async def wiz_save(cb: CallbackQuery, state: FSMContext, db, api):
    data = await state.get_data()
    slug, key = data["slug"], data["key"]
    await db.save_config(
        slug, data["url"], api.enc.encrypt(key), key_hint(key),
        data["status"], data.get("error"), cb.from_user.id,
    )
    await db.audit(cb.from_user.id, "config_saved", slug)
    await state.clear()
    await render_page(cb, db, slug, "💾 সেটিংস সফলভাবে সংরক্ষণ হয়েছে।\n🔒 আপনার API Key নিরাপদে সংরক্ষিত আছে।")


@router.callback_query(F.data == "w:cancel")
async def wiz_cancel(cb: CallbackQuery, state: FSMContext, db):
    await state.clear()
    await render_api_list(cb, db, "❌ কাজ বাতিল করা হয়েছে।")


@router.callback_query(F.data.startswith("w:"))
async def wiz_stale(cb: CallbackQuery):
    await cb.answer("⚠️ এই কাজের সময় শেষ। আবার শুরু করুন।", show_alert=True)
