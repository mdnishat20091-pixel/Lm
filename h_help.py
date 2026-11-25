from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from k_main import only_nav
from ui import show

router = Router()

HELP = (
    "❓ <b>সাহায্য</b>\n\n"
    "<b>কমান্ড</b>\n"
    "/start - মূল মেনু\n"
    "/menu - প্রধান ড্যাশবোর্ড\n"
    "/providers - প্রোভাইডার\n"
    "/settings - সেটিংস\n"
    "/api - API সেটিংস\n"
    "/health - সিস্টেমের অবস্থা\n"
    "/history - হিস্টোরি\n"
    "/help - সাহায্য\n"
    "/cancel - বাতিল\n\n"
    "<b>API Key যোগ করার নিয়ম</b>\n"
    "১. ⚙️ API সেটিংস খুলুন এবং প্রোভাইডার বেছে নিন।\n"
    "২. Base URL ও API Key পাঠান।\n"
    "৩. সংযোগ পরীক্ষার ফলাফল দেখে সংরক্ষণ করুন।\n"
    "৪. প্রোভাইডার পেজ থেকে সক্রিয় করুন।\n\n"
    "🔒 API Key এনক্রিপ্ট করে রাখা হয় এবং পুরো Key আর কখনো দেখানো হয় না।"
)


@router.message(Command("help"))
async def cmd_help(message: Message, state: FSMContext):
    await state.clear()
    await show(message, HELP, only_nav())


@router.callback_query(F.data == "nav:help")
async def cb_help(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await show(cb, HELP, only_nav())
