from aiogram import F, Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from src.bot.keyboards import main_menu_keyboard, inline

router = Router()
@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(f"Привет, {message.from_user.first_name}! Я твой личный Scout-bot для CS2. Помогу тебе мониториь рынок скинов, анализировать цены и находить наиболее выгодные предложения. Что тебя интересует?", reply_markup=main_menu_keyboard)

@router.message(Command('help'))
async def get_help(message: Message):
    await message.answer("Это команда /help")

@router.message(F.text == "Рынок CS2")
async def how_are_you(message: Message):
    await message.answer("Отлично! Введите название интересующего вас предмета:", reply_markup=inline)