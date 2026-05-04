from aiogram import Router, F, types
from aiogram.filters import Command
from sqlalchemy.orm import selectinload
from sqlalchemy import select
from database.requests import get_or_create_user, get_or_create_item
from database.models import Item, User
from processor import OracleProcessor
from sqlalchemy.ext.asyncio import AsyncSession
from bot.keyboards import main_menu, skins_list_keyboard, get_my_items_keyboard
import logging

router = Router()

@router.message(Command("start"))
async def cmd_start(message: types.Message, session: AsyncSession):
    is_new_user_flag, user = await get_or_create_user(session, message.from_user.id, message.from_user.username)
    try:
        if is_new_user_flag:
            session.add(user)
            await session.commit()
            await message.answer(f"Добро пожаловать в Оракул, {user.username}")
        else:
            await message.answer(f"С возвращением!")
    except Exception as e:
        await session.rollback()
        await message.answer("Произошла ошибка. Попробуйте позже.")
        logging.info(f"Ошибка при обработке /start: {e}")

@router.message(Command("add"))
async def add_skin(message: types.Message, session: AsyncSession):
    skin_name = message.text.replace("/add", "").strip()
    if not skin_name:
        await message.answer("Введите название предмета после команды.")
        return
    item, is_created = await get_or_create_item(session, skin_name)
    if not item:
        await message.answer(f"К сожалению, предмет {skin_name} не найден в Steam. Проверьте правильность написания и повторите попытку.")
        return
    user_stmt = select(User).where(User.telegram_id == str(message.from_user.id)).options(selectinload(User.watchlist))
    result = await session.execute(user_stmt)
    user = result.scalar_one_or_none()
    if item in user.watchlist:
        await message.answer("Данный предмет уже есть в вашем списке отслеживания.")
    else:
        user.watchlist.append(item)
        await session.commit()
        msg = f"Предмет добавлен." if is_created else "Предмет привязан."
        await message.answer(f"{msg} Текущая цена: {item.current_price} ₽")

@router.message(Command("my_items"))
async def cmd_my_items(message: types.Message, session: AsyncSession):
    tg_id = message.from_user.id
    user = await session.scalar(select(User).where(User.telegram_id == tg_id))
    if not user:
        await message.answer("Пройдите пожалуйста регистрацию с помощью команды /start")
        return
    if not user.watchlist:
        await message.answer("Вы пока не отслеживаете ни одного предмета. Используйте команду /add [Название скина] для добавления.")
        return
    keyboard_buttons = []
    reply_markup = get_my_items_keyboard(user.watchlist)
    await message.answer("Список отслеживаемых предметов:", reply_markup=reply_markup)
    

@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: types.CallbackQuery):
    await callback.message.edit_text("🧙‍♂️ Главное меню Оракула:", reply_markup=main_menu())

@router.callback_query(F.data == "list_skins")
async def list_skins(callback: types.CallbackQuery, session_pool):
    async with session_pool() as session:
        result = await session.execute(select(Item))
        items = result.scalars().all()
        
        if not items:
            await callback.answer("В базе пока пусто. Подожди, пока парсер соберет данные.")
            return

        await callback.message.edit_text("Выберите скин для анализа:", reply_markup=skins_list_keyboard(items))

@router.callback_query(F.data.startswith("view_"))
async def view_item_details(callback: types.CallbackQuery, session_pool):
    item_id = int(callback.data.split("_")[1])
    
    async with session_pool() as session:
        processor = OracleProcessor(sql_session=session)
        item = await session.get(Item, item_id)
        
        prediction = await processor.get_kalman_prediction(item_id, steps=5)
        
        text = (f"Аналитика: {item.name}**\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"Реальная цена: `{item.current_price:.2f}`\n"
                f"Цена Оракула: `{item.oracle_price:.2f}`\n"
                f"Тренд: `{'Вверх' if item.trend > 0 else 'Вниз'} ({item.trend:.4f})`\n")
        
        if prediction:
            p_price, p_trend = prediction
            text += f"\n🔮 **Прогноз на 5 шагов:**\nОжидаемая цена: `{p_price:.2f}`"
        
        await callback.message.answer(text, parse_mode="Markdown")
        await callback.answer()