from aiogram.types import InlineKeyboardButton as B
from aiogram.types import InlineKeyboardMarkup as M


def btn(text: str, data: str) -> B:
    return B(text=text, callback_data=data)


def nav_row(back: str | None = None) -> list:
    row = []
    if back:
        row.append(btn("🔙 পিছনে", back))
    row.append(btn("🏠 হোম", "nav:home"))
    return row


def main_menu() -> M:
    return M(inline_keyboard=[
        [btn("📡 প্রোভাইডার", "nav:prov"), btn("⚙️ API সেটিংস", "nav:api")],
        [btn("📊 API মনিটর", "nav:mon"), btn("📜 হিস্টোরি", "nav:hist:0")],
        [btn("🔐 নিরাপত্তা", "nav:sec"), btn("❓ সাহায্য", "nav:help")],
    ])


def only_nav(back: str | None = None) -> M:
    return M(inline_keyboard=[nav_row(back)])


def confirm_kb(yes: str, no: str) -> M:
    return M(inline_keyboard=[[btn("✅ হ্যাঁ", yes), btn("❌ না", no)]])
