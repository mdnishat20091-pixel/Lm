from __future__ import annotations

from datetime import datetime, timedelta, timezone
from html import escape

BD = timezone(timedelta(hours=6))
_DIGITS = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")

STATUS_LABEL = {
    "ok": "🟢 সংযুক্ত",
    "invalid_key": "🔴 Key সঠিক নয়",
    "failed": "🔴 সংযোগ ব্যর্থ",
    "unconfirmed": "🟡 নিশ্চিত নয়",
    "rate_limited": "🟡 সীমা অতিক্রম",
    "unverified": "⚪ যাচাই বাকি",
    "unknown": "⚪ পরীক্ষা হয়নি",
}

ERROR_TEXT = {
    "bad_key": "API Key সঠিক নয়",
    "rate": "অনুরোধের সীমা অতিক্রম হয়েছে",
    "redirect": "সার্ভার অন্য ঠিকানায় পাঠিয়েছে",
    "http_5xx": "প্রোভাইডারের সার্ভারে সমস্যা",
    "unconfirmed": "সার্ভার সাড়া দিয়েছে, কিন্তু সফলতা নিশ্চিত হয়নি",
    "timeout": "সময়সীমা শেষ হয়েছে",
    "network": "নেটওয়ার্ক সংযোগ ব্যর্থ",
    "internal": "অভ্যন্তরীণ সমস্যা",
    "decrypt": "সংরক্ষিত Key পড়া যায়নি",
    "unverified": "ডকুমেন্টেশন যাচাই হয়নি",
}

ACTION_TEXT = {
    "test": "সংযোগ পরীক্ষা",
    "config_saved": "কনফিগারেশন সংরক্ষণ",
    "enabled": "প্রোভাইডার সক্রিয়",
    "disabled": "প্রোভাইডার নিষ্ক্রিয়",
    "key_deleted": "API Key মুছে ফেলা",
    "test_all": "সব সংযোগ পরীক্ষা",
}


def bn(value) -> str:
    return str(value).translate(_DIGITS)


def esc(value) -> str:
    return escape(str(value), quote=False)


def fmt_dt(dt) -> str:
    if not dt:
        return "—"
    return bn(dt.astimezone(BD).strftime("%d-%m-%Y %H:%M"))


def fmt_uptime(seconds: int) -> str:
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{bn(h)} ঘণ্টা {bn(m)} মিনিট"
    if m:
        return f"{bn(m)} মিনিট {bn(s)} সেকেন্ড"
    return f"{bn(s)} সেকেন্ড"


def error_text(code) -> str:
    if not code:
        return "নেই"
    return ERROR_TEXT.get(code, "অজানা ত্রুটি")


def effective_status(p) -> str:
    if not p["is_verified"]:
        return "unverified"
    return p["connection_status"]


def status_label(status: str) -> str:
    return STATUS_LABEL.get(status, STATUS_LABEL["unknown"])


def banner(result) -> str:
    return {
        "ok": "✅ API সংযোগ সফল হয়েছে।",
        "invalid_key": "⚠️ API Key সঠিক নয়।",
        "rate_limited": "⏳ অনুরোধের সীমা অতিক্রম হয়েছে, পরে চেষ্টা করুন।",
        "unconfirmed": "⚠️ সার্ভার সাড়া দিয়েছে, কিন্তু সংযোগ নিশ্চিত করা যায়নি।",
        "unverified": "ℹ️ এই প্রোভাইডারের ডকুমেন্টেশন যাচাই হয়নি, তাই পরীক্ষা করা যায়নি।",
    }.get(result.status, "❌ API সংযোগ ব্যর্থ হয়েছে।")


def provider_card(p) -> str:
    return (
        f"📡 <b>{esc(p['name'])}</b>\n"
        f"   🔌 সংযোগ: {status_label(effective_status(p))}\n"
        f"   ⚙️ কনফিগারেশন: {'✅ করা আছে' if p['configured'] else '❌ করা নেই'}\n"
        f"   🕒 সর্বশেষ সংযোগ: {fmt_dt(p['last_connection_at'])}\n"
        f"   🔛 অবস্থা: {'🟢 সক্রিয়' if p['enabled'] else '⚪ নিষ্ক্রিয়'}"
    )


def provider_page(p, mask: str) -> str:
    key_line = mask if p["configured"] else "সংরক্ষিত নেই"
    url = p["base_url"] or p["default_base_url"] or "দেওয়া হয়নি"
    header = p["auth_header"] if p["is_verified"] else "যাচাই বাকি"
    text = (
        f"📡 <b>{esc(p['name'])}</b>\n\n"
        f"🌐 Base URL: <code>{esc(url)}</code>\n"
        f"🔑 API Key: <code>{esc(key_line)}</code>\n"
        f"🏷 অথেন্টিকেশন হেডার: <code>{esc(header)}</code>\n"
        f"⚙️ কনফিগারেশন: {'✅ করা আছে' if p['configured'] else '❌ করা নেই'}\n"
        f"🔌 সংযোগ: {status_label(effective_status(p))}\n"
        f"🔛 অবস্থা: {'🟢 সক্রিয়' if p['enabled'] else '⚪ নিষ্ক্রিয়'}\n"
        f"🕒 সর্বশেষ সংযোগ: {fmt_dt(p['last_connection_at'])}\n"
        f"❗ ত্রুটি: {esc(error_text(p['last_error']))}"
    )
    if not p["is_verified"]:
        text += "\n\nℹ️ ডকুমেন্টেশন যাচাই না হওয়া পর্যন্ত এই প্রোভাইডার নিষ্ক্রিয় থাকবে।"
    return text


def dashboard(provs, last_activity, db_ok: bool) -> str:
    total = len(provs)
    enabled = sum(1 for p in provs if p["enabled"])
    connected = sum(1 for p in provs if p["configured"] and effective_status(p) == "ok")
    configured = sum(1 for p in provs if p["configured"])
    return (
        "🏠 <b>প্রোভাইডার ম্যানেজার</b>\n\n"
        f"📦 মোট প্রোভাইডার: {bn(total)}\n"
        f"🟢 সক্রিয়: {bn(enabled)}\n"
        f"⚪ নিষ্ক্রিয়: {bn(total - enabled)}\n"
        f"🔗 API সংযোগ: {bn(connected)}/{bn(configured)} সংযুক্ত\n"
        f"🕒 সর্বশেষ কার্যক্রম: {fmt_dt(last_activity)}\n"
        f"💚 সিস্টেম: {'সুস্থ' if db_ok else '⚠️ ডাটাবেসে সমস্যা'}"
    )
