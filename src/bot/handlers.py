from aiogram import Router, F, types, Bot
from aiogram.filters import Command
from sqlalchemy.orm import selectinload
from sqlalchemy import select
from analytics.filters_and_predict import plot_results
from parser.fetcher import parse_steam_market_link
from database.requests import get_or_create_user, get_or_create_item
from database.models import User, Item, Watchlist
from sqlalchemy.ext.asyncio import AsyncSession
from bot.keyboards import get_my_items_keyboard, get_item_card_keyboard, get_notifications_keyboard
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

    link = message.text.replace("/add", "").strip()

    if not link:
        await message.answer(
            "Отправьте ссылку Steam Market."
        )
        return

    parsed = parse_steam_market_link(link)

    if not parsed:
        await message.answer(
            "Неверная ссылка Steam Market."
        )
        return

    appid = parsed["appid"]
    market_hash_name = parsed["market_hash_name"]

    item = await get_or_create_item(
        session,
        appid,
        market_hash_name
    )

    if not item:
        await message.answer(
            "Не удалось получить предмет."
        )
        return

    user_stmt = (
        select(User)
        .where(User.telegram_id == str(message.from_user.id))
        .options(selectinload(User.watchlist)
                 .selectinload(Watchlist.item)
                 )
    )

    result = await session.execute(user_stmt)
    user = result.scalar_one_or_none()
    already_exists = any(watch.item_id == item.id for watch in user.watchlist)
    if already_exists:
        await message.answer("Предмет уже отслеживается.")
        return

    watch = Watchlist(item=item, notification_type="none")
    user.watchlist.append(watch)
    await session.commit()

    await message.answer(
        f"Добавлен предмет:\n"
        f"{item.name}\n"
        f"Цена: {item.current_price} ₽"
    )


@router.message(Command("my_items"))
async def cmd_my_items(message: types.Message, session: AsyncSession):
    user_id_str = str(message.from_user.id)
    user_stmt = select(User).where(User.telegram_id == user_id_str).options(
        selectinload(User.watchlist)
        .selectinload(Watchlist.item)
    )
    result = await session.execute(user_stmt)
    user = result.scalar_one_or_none()

    if not user:
        await message.answer("Пожалуйста, зарегистрируйтесь через /start")
        return
    items = [watch.item for watch in user.watchlist]
    if not items:
        await message.answer("Вы пока не отслеживаете ни одного предмета. Используйте /add [Ссылка на предмет].")
        return
    reply_markup = get_my_items_keyboard(items)
    await message.answer("Список отслеживаемых предметов:", reply_markup=reply_markup)


@router.callback_query(ItemCallback.filter())
async def show_item_info(
    callback: types.CallbackQuery,
    callback_data: ItemCallback,
    session: AsyncSession,
    bot: Bot
):
    item_id = callback_data.item_id

    item_stmt = select(Item).where(
        Item.id == item_id).options(selectinload(Item.history))
    result = await session.execute(item_stmt)
    item = result.scalar_one_or_none()

    if not item:
        await callback.answer("Предмет не найден.", show_alert=True)
        return

    clean_history = [h for h in item.history if not h.is_outlier]
    history_count = len(clean_history)

    message_text = f"**Информация по предмету: {item.name}**\n"
    message_text += f"Текущая цена: {item.current_price:.2f} ₽\n" if item.current_price is not None else "Текущая цена сейчас недоступна"
    message_text += f"Сглаженная цена: {item.oracle_price:.2f} ₽\n" if item.oracle_price is not None else "Сглаженная цена сейчас недоступна"
    message_text += f"Тренд: {item.trend:.2f}\n" if item.trend is not None else "Тренд сейчас недоступен"
    message_text += f"История записей: {history_count}\n"

    if history_count < 31:
        message_text += "\n_Недостаточно данных для прогноза (требуется 31+ чистых точек)._\n"
        message_text += "Все данные парсера актуальны. Рекомендуемое количество точек: 500"
    else:
        message_text += "\n**Прогнозы:**\n"
        oracle_processor = OracleProcessor(session, bot)
        prediction_tomorrow = await oracle_processor.get_kalman_prediction(item.id, steps=5)
        if prediction_tomorrow:
            predicted_price_tomorrow, predicted_trend_tomorrow, forecast_uncertainty = prediction_tomorrow
            message_text += f"Прогноз через 20 минут: {predicted_price_tomorrow:.2f} ₽ (Тренд: {predicted_trend_tomorrow:.2f})\n Неопределенность прогноза: {forecast_uncertainty}\n"
        else:
            message_text += "Прогноз недоступен"

    await callback.message.answer(message_text, reply_markup=get_item_card_keyboard(item.id), parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "close_item_info")
async def close_item_info_handler(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.answer()


@router.callback_query(F.data.startswith("graph_"))
async def show_forecast_graph(callback: types.CallbackQuery, session: AsyncSession):
    item_id = int(callback.data.split("_")[1])
    stmt = (
        select(Item)
        .where(Item.id == item_id)
        .options(selectinload(Item.history))
    )

    result = await session.execute(stmt)
    item = result.scalar_one_or_none()
    if len(item.history) < 3:
        await callback.answer("Недостаточно данных", show_alert=True)
        return
    original_prices = [h.price for h in item.history]
    filtered_prices = [h.kalman_price for h in item.history if h.kalman_price is not None]
    graph_buffer = plot_results(original_prices, filtered_prices)
    photo = types.BufferedInputFile(
        graph_buffer.getvalue(), filename="forecast.png")
    await callback.message.answer_photo(photo=photo, caption=f"Прогноз цены: {item.name}")
    await callback.answer()


@router.callback_query(F.data.startswith("notifications_"))
async def notifications_menu(callback: types.CallbackQuery):
    item_id = int(callback.data.split("_")[1])
    await callback.message.answer("Выберите режим уведомлений:", reply_markup=get_notifications_keyboard(item_id))
    await callback.answer()


@router.callback_query(F.data.startswith("notify_type_"))
async def set_notification_type(callback: types.CallbackQuery, session: AsyncSession):
    _, _, notification_type, item_id = callback.data.split("_")
    item_id = int(item_id)
    stmt = (
        select(User)
        .where(User.telegram_id == str(callback.from_user.id))
        .options(selectinload(User.watchlist))
    )

    result = await session.execute(stmt)
    user = result.scalar_one()
    watch = next(watch for watch in user.watchlist if watch.item_id == item_id)
    watch.notification_type = notification_type
    await session.commit()
    labels = {
        "none": "Уведомления отключены",
        "up": "Уведомления о росте включены",
        "down": "Уведомления о падении включены"
    }

    await callback.answer(labels[notification_type], show_alert=True)


@router.callback_query(F.data.startswith("remove_"))
async def remove_item_from_watchlist(callback: types.CallbackQuery, session: AsyncSession):
    item_id = int(callback.data.split("_")[1])
    stmt = (
        select(Watchlist)
        .join(User)
        .where(
            User.telegram_id == str(callback.from_user.id),
            Watchlist.item_id == item_id
        )
    )
    result = await session.execute(stmt)
    watch = result.scalar_one_or_none()
    if not watch:
        await callback.answer("Предмет уже удалён.", show_alert=True)
        return

    await session.delete(watch)
    await session.commit()
    await callback.message.delete()
    await callback.answer("Предмет удалён из отслеживания.", show_alert=True)