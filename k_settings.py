from aiogram.types import InlineKeyboardMarkup as M

from k_main import btn, nav_row


def settings_menu() -> M:
    return M(inline_keyboard=[
        [btn("⚙️ API সেটিংস", "nav:api"), btn("🔐 নিরাপত্তা", "nav:sec")],
        nav_row(),
    ])


def wizard_url(has_default: bool) -> M:
    rows = []
    if has_default:
        rows.append([btn("✅ বর্তমান/ডিফল্ট ব্যবহার", "w:def")])
    rows.append([btn("❌ বাতিল", "w:cancel")])
    return M(inline_keyboard=rows)


def wizard_cancel() -> M:
    return M(inline_keyboard=[[btn("❌ বাতিল", "w:cancel")]])


def wizard_confirm() -> M:
    return M(inline_keyboard=[[btn("💾 সংরক্ষণ করুন", "w:save"), btn("❌ বাতিল", "w:cancel")]])


def history_pager(page: int, pages: int) -> M:
    row = []
    if page > 0:
        row.append(btn("◀️ আগের", f"nav:hist:{page - 1}"))
    if page < pages - 1:
        row.append(btn("পরের ▶️", f"nav:hist:{page + 1}"))
    rows = [row] if row else []
    rows.append(nav_row())
    return M(inline_keyboard=rows)


def monitor_kb() -> M:
    return M(inline_keyboard=[
        [btn("🔄 সব পরীক্ষা করুন", "mon:all")],
        [btn("💚 সিস্টেমের অবস্থা", "nav:health")],
        nav_row(),
    ])


def health_kb() -> M:
    return M(inline_keyboard=[
        [btn("🔄 রিফ্রেশ", "nav:health"), btn("📊 API মনিটর", "nav:mon")],
        nav_row(),
    ])
