from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

def main_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="Добавить скин", callback_data="add_skin")
    builder.button(text="Список всех скинов", callback_data="list_skins")
    builder.adjust(1)
    return builder.as_markup()

def skins_list_keyboard(items):
    builder = InlineKeyboardBuilder()
    for item in items:
        builder.button(text=f"📊 {item.name}", callback_data=f"view_{item.id}")
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main"))
    return builder.as_markup()

def get_my_items_keyboard(watchlist: list[str]) -> InlineKeyboardMarkup:
    keyboard_buttons = []
    if watchlist:
        for item in watchlist:
            keyboard_buttons.append([InlineKeyboardButton(text=item, callback_data=f"item_info:{item}")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)