from aiogram import Router, F, types
from aiogram.filters import Command
from sqlalchemy.orm import selectinload
from sqlalchemy import select
from database.requests import get_or_create_user, get_or_create_item
from database.models import User, Item, ItemHistory
from sqlalchemy.ext.asyncio import AsyncSession
from bot.keyboards import get_my_items_keyboard
from processor import OracleProcessor
from bot.callbacks import ItemCallback
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
    user_id_str = str(message.from_user.id)
    user_stmt = select(User).where(User.telegram_id == user_id_str).options(
        selectinload(User.watchlist)
    )
    result = await session.execute(user_stmt)
    user = result.scalar_one_or_none()

    if not user:
        await message.answer("Пожалуйста, зарегистрируйтесь через /start")
        return
    items = user.watchlist 
    if not items:
        await message.answer("Вы пока не отслеживаете ни одного предмета. Используйте /add 'NameItem'.")
        return
    reply_markup = get_my_items_keyboard(items)
    await message.answer("Список отслеживаемых предметов:", reply_markup=reply_markup)

@router.callback_query(ItemCallback.filter())
async def show_item_info(
    callback: types.CallbackQuery,
    callback_data: ItemCallback,
    session: AsyncSession
):
    item_id = callback_data.item_id

    item_stmt = select(Item).where(Item.id == item_id).options(
        selectinload(Item.history.and_(ItemHistory.is_outlier == False))
    )
    result = await session.execute(item_stmt)
    item = result.scalar_one_or_none()

    if not item:
        await callback.answer("Предмет не найден.", show_alert=True)
        return

    clean_history = [h for h in item.history if not h.is_outlier]
    history_count = len(clean_history)

    message_text = f"**Информация по предмету: {item.name}**\n"
    message_text += f"Текущая цена: {item.current_price:.2f} ₽\n" if item.current_price is not None else "Текущая цена сейчас недоступна"
    message_text += f"Oracle цена: {item.oracle_price:.2f} ₽\n" if item.oracle_price is not None else "Oracle цена сейчас недоступна"
    message_text += f"Тренд: {item.trend:.2f}\n" if item.trend is not None else "Trend сейчас недоступен"
    message_text += f"История записей (чистых): {history_count}\n"

    if history_count < 101:
        message_text += "\n_Недостаточно данных для прогноза (требуется 101+ чистых точек)._\n"
        message_text += "Все данные парсера актуальны."
    else:
        message_text += "\n**Прогнозы:**\n"
        oracle_processor = OracleProcessor(session)
        prediction_tomorrow = await oracle_processor.get_kalman_prediction(item.id, steps=5)
        if prediction_tomorrow:
            predicted_price_tomorrow, predicted_trend_tomorrow = prediction_tomorrow
            message_text += f"Прогноз на завтра: {predicted_price_tomorrow:.2f} ₽ (Тренд: {predicted_trend_tomorrow:.2f})\n"
        else:
            message_text += "Прогноз на завтра: _Недоступен_\n"
        

    await callback.message.edit_text(message_text, reply_markup=callback.message.reply_markup, parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == "close_item_info")
async def close_item_info_handler(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.answer()