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

    return InlineKeyboardMarkup(inline_keyboard=keyboard_rows)

def get_item_card_keyboard(item_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                    text="График",
                    callback_data=f"graph_{item_id}")],
            [InlineKeyboardButton(
                    text="Уведомления",
                    callback_data=f"notifications_{item_id}")],
            [InlineKeyboardButton(
                    text="Закрыть",
                    callback_data="close_item_info")]
        ]
    )

def get_notifications_keyboard(item_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                    text="Без уведомлений",
                    callback_data=f"notify_type_none_{item_id}")],
            [InlineKeyboardButton(
                    text="Рост цены",
                    callback_data=f"notify_type_up_{item_id}")],
            [InlineKeyboardButton(
                    text="Падение цены",
                    callback_data=f"notify_type_down_{item_id}")],
            [InlineKeyboardButton(
                    text="Закрыть",
                    callback_data="close_item_info")]
        ]
    )

private = [
    BotCommand(command="start", description="Запустить бота"),
    BotCommand(command="add", description="Добавить скин в список отслеживаемых"),
    BotCommand(command="my_items", description="Список отслеживаемых предметов")
]