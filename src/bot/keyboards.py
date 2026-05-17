from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.types import BotCommand
from database.models import Item
from typing import List
from bot.callbacks import ItemCallback

def get_my_items_keyboard(items: List["Item"]) -> InlineKeyboardMarkup:
    buttons = []
    for item in items:
        callback_data = ItemCallback(item_id=item.id).pack()
        button_text = f"{item.name} ({item.current_price:.0f} ₽)"
        buttons.append(
            InlineKeyboardButton(text=button_text, callback_data=callback_data)
        )

    keyboard_rows = []
    for i in range(0, len(buttons), 2):
        keyboard_rows.append(buttons[i:i+2])
    keyboard_rows.append([InlineKeyboardButton(text="График", callback_data=f"graph_{item.id}")])
    keyboard_rows.append([InlineKeyboardButton(text="Закрыть", callback_data="close_item_info")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard_rows)

private = [
    BotCommand(command="start", description="Запустить бота"),
    BotCommand(command="add", description="Добавить скин в список отслеживаемых"),
    BotCommand(command="my_items", description="Список отслеживаемых предметов")
]