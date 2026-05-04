from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import types

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
    builder.row(types.InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main"))
    return builder.as_markup()