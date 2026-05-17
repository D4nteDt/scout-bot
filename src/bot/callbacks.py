from aiogram.filters.callback_data import CallbackData
class ItemCallback(CallbackData, prefix="item"):
    item_id: int