from aiogram import Router, F, types
from bot.keyboards import main_menu, skins_list_keyboard
from processor import OracleProcessor
from database.models import Item
import select

router = Router()

@router.callback_query(F.data == "list_skins")
async def list_skins(callback: types.CallbackQuery, session_pool):
    async with session_pool() as session:
        result = await session.execute(select(Item))
        items = result.scalars().all()
        
        await callback.message.answer(
            "Выберите скин для анализа:", 
            reply_markup=skins_list_keyboard(items)
        )

@router.callback_query(F.data.startswith("view_"))
async def view_item_details(callback: types.CallbackQuery, session_pool):
    item_id = int(callback.data.split("_")[1])
    
    async with session_pool() as session:
        processor = OracleProcessor(sql_session=session)
        prediction = await processor.get_kalman_prediction(item_id)
        item = await session.get(Item, item_id)
        
        if prediction:
            price, trend = prediction
            text = (f"Анализ: {item.name}**\n\n"
                    f"Текущая цена: {item.current_price:.2f}\n"
                    f"Оракул (Калман): {item.oracle_price:.2f}\n"
                    f"Прогноз тренда: {'Вверх' if trend > 0 else 'Вниз'} ({trend:.4f})")
            
            # Сюда же в будущем прикрутим отправку графика (через pyplot)
            await callback.message.answer(text, parse_mode="Markdown")

@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: types.CallbackQuery):
    await callback.message.edit_text("Главное меню Оракула:", reply_markup=main_menu())