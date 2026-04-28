from aiogram.types import (
    KeyboardButton, 
    ReplyKeyboardMarkup, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup
)

def get_main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Рынок CS2")],
            [KeyboardButton(text="Мои отслеживания"), KeyboardButton(text="Уведомления")],
            [KeyboardButton(text="Профиль"), KeyboardButton(text="Помощь")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )

def get_market_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Поиск по названию", callback_data="search_item")],
        [InlineKeyboardButton(text="Популярные предметы", callback_data="popular_items")],
        [InlineKeyboardButton(text="Тренды дня", callback_data="daily_trends")],
        [InlineKeyboardButton(text="Назад", callback_data="back_to_main")]
    ])

def get_item_actions(item_name: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="График цены", callback_data=f"chart:{item_name}")],
        [InlineKeyboardButton(text="В избранное", callback_data=f"favorite:{item_name}")],
        [InlineKeyboardButton(text="Уведомление о цене", callback_data=f"alert:{item_name}")],
        [InlineKeyboardButton(text="К рынку", callback_data="back_to_market")]
    ])

def get_favorites_list(favorites: list):
    keyboard = []
    for item in favorites:
        keyboard.append([
            InlineKeyboardButton(text=item[:30], callback_data=f"view:{item}"),
            InlineKeyboardButton(text="X", callback_data=f"remove:{item}")
        ])
    keyboard.append([InlineKeyboardButton(text="Назад", callback_data="back_to_main")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_back_button():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Назад", callback_data="back_to_main")]
    ])