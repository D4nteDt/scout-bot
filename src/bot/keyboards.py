from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup

main_menu_keyboard = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="💰 Рынок CS2")],
    [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="Помощь")]
], resize_keyboard=True, one_time_keyboard=False)

inline = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Поиск по названию", url= "")],
    [InlineKeyboardButton(text="Мои отслеживания", url= "")],
    [InlineKeyboardButton(text="Уведомления о ценах", url= "")],
    [InlineKeyboardButton(text="Назад", url="")]
])