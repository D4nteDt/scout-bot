from aiogram.utils.keyboard import InlineKeyboardBuilder

def main_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="Добавить скин", callback_data="add_skin")
    builder.button(text="Мои скины", callback_data="list_skins")
    builder.adjust(1)
    return builder.as_markup()

def skins_list_keyboard(items):
    builder = InlineKeyboardBuilder()
    for item in items:
        builder.button(text=f"{item.name}", callback_data=f"view_{item.id}")
    builder.adjust(2)
    return builder.as_markup()