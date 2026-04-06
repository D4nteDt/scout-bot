import asyncio
from aiogram import Bot, Dispatcher
from src.bot.handlers import router
from src.config.settings import BOT_TOKEN
bot = Bot(BOT_TOKEN)
dp = Dispatcher()

async def main():
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Exit")