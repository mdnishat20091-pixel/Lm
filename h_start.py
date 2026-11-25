from aiogram import F, Router
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from k_main import main_menu
from formatters import dashboard
from ui import show

router = Router()


async def render_dashboard(target, db) -> None:
    provs = await db.list_providers()
    last = await db.last_activity()
    ok = await db.ping() is not None
    await show(target, dashboard(provs, last, ok), main_menu())


@router.message(CommandStart())
@router.message(Command("menu"))
async def cmd_start(message: Message, state: FSMContext, db):
    await state.clear()
    await render_dashboard(message, db)


@router.callback_query(F.data == "nav:home")
async def cb_home(cb: CallbackQuery, state: FSMContext, db):
    await state.clear()
    await render_dashboard(cb, db)


@router.message(Command("cancel"), StateFilter("*"))
async def cmd_cancel(message: Message, state: FSMContext, db):
    had = await state.get_state()
    await state.clear()
    await message.answer(
        "❌ চলমান কাজ বাতিল করা হয়েছে।" if had else "ℹ️ বাতিল করার মতো কোনো কাজ চলছে না।"
    )
    await render_dashboard(message, db)
