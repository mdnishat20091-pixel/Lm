from aiogram.types import InlineKeyboardMarkup as M

from k_main import btn, nav_row


def _grid(provs, prefix: str) -> list:
    rows, row = [], []
    for p in provs:
        row.append(btn(f"📡 {p['name']}", f"{prefix}:{p['slug']}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return rows


def provider_list(provs) -> M:
    return M(inline_keyboard=_grid(provs, "p") + [nav_row()])


def api_provider_list(provs) -> M:
    return M(inline_keyboard=_grid(provs, "api") + [nav_row()])


def provider_page(p) -> M:
    rows = []
    slug = p["slug"]
    if p["configured"] and p["is_verified"]:
        rows.append([btn("🔌 সংযোগ পরীক্ষা", f"pt:{slug}")])
    rows.append([btn("⚙️ কনফিগার", f"api:{slug}")])
    if p["configured"] and p["is_verified"]:
        rows.append([btn("⚪ নিষ্ক্রিয় করুন" if p["enabled"] else "🟢 সক্রিয় করুন", f"pe:{slug}")])
    if p["configured"]:
        rows.append([btn("🗑 Key মুছুন", f"pd:{slug}")])
    rows.append(nav_row("nav:prov"))
    return M(inline_keyboard=rows)
