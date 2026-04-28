import asyncio
import logging
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from keyboards import (
    get_main_menu, 
    get_market_menu, 
    get_back_button,
    get_item_actions,
    get_favorites_list
)
from market_api import get_item_price, search_items, get_price_history
from charts import create_price_chart

logging.basicConfig(level=logging.INFO)

user_favorites = {}
price_alerts = {}

class SearchStates(StatesGroup):
    waiting_for_name = State()

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        f"Привет, {message.from_user.first_name}!\n\n"
        f"Я Scout-bot для CS2. Помогу мониторить цены на скины "
        f"и находить выгодные предложения.",
        reply_markup=get_main_menu()
    )

@dp.message(Command("help"))
async def cmd_help(message: Message):
    help_text = (
        "Доступные команды:\n\n"
        "Рынок CS2 — поиск предметов и цены\n"
        "Мои отслеживания — список избранного\n"
        "Уведомления — настройка алертов\n"
        "Профиль — ваша статистика\n\n"
        "Или используйте: /search [название]"
    )
    await message.answer(help_text)

@dp.message(F.text.in_(["Рынок CS2", "Рынок CS2"]))
async def market_menu(message: Message):
    await message.answer(
        "Рынок CS2\n\nВыберите действие:",
        reply_markup=get_market_menu()
    )

@dp.message(F.text == "Профиль")
async def show_profile(message: Message):
    user_id = message.from_user.id
    favorites_count = len(user_favorites.get(user_id, []))
    alerts_count = len(price_alerts.get(user_id, {}))
    
    await message.answer(
        f"Ваш профиль\n\n"
        f"Избранных предметов: {favorites_count}\n"
        f"Активных уведомлений: {alerts_count}\n\n"
        f"ID: {user_id}"
    )

@dp.message(F.text == "Помощь")
async def show_help_button(message: Message):
    await cmd_help(message)

@dp.callback_query(F.data == "search_item")
async def start_search(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "Введите название предмета для поиска:\n\n"
        "Например: AK-47 | Redline или Butterfly Knife"
    )
    await state.set_state(SearchStates.waiting_for_name)
    await callback.answer()

@dp.message(SearchStates.waiting_for_name)
async def process_search(message: Message, state: FSMContext):
    await state.clear()
    query = message.text.strip()
    
    await message.answer(f"Ищу: {query}...")
    
    items = search_items(query)
    
    if not items:
        await message.answer(
            "Предметы не найдены. Попробуйте другое название.",
            reply_markup=get_back_button()
        )
        return
    
    item = items[0]
    price_data = get_item_price(item['name'])
    
    text = (
        f"{item['name']}\n\n"
        f"Текущая цена: {price_data['price']} $\n"
        f"Изменение 24ч: {price_data['change']}\n"
        f"Объём торгов: {price_data['volume']}\n\n"
        f"Выберите действие:"
    )
    
    await message.answer(
        text,
        reply_markup=get_item_actions(item['name'])
    )

@dp.callback_query(F.data.startswith("chart:"))
async def show_chart(callback: CallbackQuery):
    item_name = callback.data.split(":", 1)[1]
    
    await callback.message.answer("Строю график...")
    
    history = get_price_history(item_name)
    chart_path = create_price_chart(item_name, history)
    
    photo = FSInputFile(chart_path)
    await callback.message.answer_photo(
        photo,
        caption=f"Динамика цены: {item_name}\n(последние 30 дней)",
        reply_markup=get_back_button()
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("favorite:"))
async def add_to_favorites(callback: CallbackQuery):
    user_id = callback.from_user.id
    item_name = callback.data.split(":", 1)[1]
    
    if user_id not in user_favorites:
        user_favorites[user_id] = []
    
    if item_name in user_favorites[user_id]:
        await callback.answer("Уже в избранном!", show_alert=True)
        return
    
    user_favorites[user_id].append(item_name)
    await callback.answer(f"{item_name} добавлен в избранное!", show_alert=True)

@dp.message(F.text == "Мои отслеживания")
async def show_favorites(message: Message):
    user_id = message.from_user.id
    favorites = user_favorites.get(user_id, [])
    
    if not favorites:
        await message.answer(
            "Избранное пусто\n\n"
            "Добавляйте предметы через поиск!",
            reply_markup=get_back_button()
        )
        return
    
    await message.answer(
        f"Ваши отслеживания ({len(favorites)}):",
        reply_markup=get_favorites_list(favorites)
    )

@dp.callback_query(F.data.startswith("view:"))
async def view_favorite_item(callback: CallbackQuery):
    item_name = callback.data.split(":", 1)[1]
    price_data = get_item_price(item_name)
    
    text = (
        f"{item_name}\n\n"
        f"Текущая цена: {price_data['price']} $\n"
        f"Изменение: {price_data['change']}\n\n"
        f"Последнее обновление: {datetime.now().strftime('%H:%M')}"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_item_actions(item_name)
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("remove:"))
async def remove_from_favorites(callback: CallbackQuery):
    user_id = callback.from_user.id
    item_name = callback.data.split(":", 1)[1]
    
    if user_id in user_favorites and item_name in user_favorites[user_id]:
        user_favorites[user_id].remove(item_name)
        await callback.answer("Удалено из избранного", show_alert=True)
        await show_favorites(callback.message)
    else:
        await callback.answer("Предмет не найден", show_alert=True)

@dp.callback_query(F.data.startswith("alert:"))
async def set_price_alert(callback: CallbackQuery, state: FSMContext):
    item_name = callback.data.split(":", 1)[1]
    
    await state.update_data(item_name=item_name)
    await callback.message.edit_text(
        f"Уведомление о цене\n\n"
        f"Предмет: {item_name}\n\n"
        f"Введите целевую цену в $ (например: 150.50):"
    )
    await state.set_state("waiting_for_alert_price")
    await callback.answer()

@dp.message(F.text.regexp(r"^\d+(\.\d{1,2})?$"))
async def process_alert_price(message: Message, state: FSMContext):
    data = await state.get_data()
    item_name = data.get('item_name')
    target_price = float(message.text)
    user_id = message.from_user.id
    
    if user_id not in price_alerts:
        price_alerts[user_id] = {}
    
    price_alerts[user_id][item_name] = target_price
    
    await message.answer(
        f"Уведомление установлено!\n\n"
        f"Предмет: {item_name}\n"
        f"Целевая цена: ${target_price}\n\n"
        f"Я сообщу, когда цена достигнет этого значения.",
        reply_markup=get_back_button()
    )
    await state.clear()

@dp.message(F.text == "Уведомления")
async def show_alerts(message: Message):
    user_id = message.from_user.id
    alerts = price_alerts.get(user_id, {})
    
    if not alerts:
        await message.answer(
            "Нет активных уведомлений\n\n"
            "Установите их через карточку предмета!",
            reply_markup=get_back_button()
        )
        return
    
    text = "Ваши уведомления:\n\n"
    for item, price in alerts.items():
        current = get_item_price(item)['price']
        status = "+" if current <= price else "-"
        text += f"{status} {item}: ${price} (сейчас: ${current})\n"
    
    await message.answer(text, reply_markup=get_back_button())

@dp.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery):
    await callback.message.edit_text(
        "Главное меню",
        reply_markup=get_main_menu()
    )
    await callback.answer()

@dp.callback_query(F.data == "back_to_market")
async def back_to_market(callback: CallbackQuery):
    await callback.message.edit_text(
        "Рынок CS2",
        reply_markup=get_market_menu()
    )
    await callback.answer()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())