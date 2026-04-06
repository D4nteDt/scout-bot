from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text

DATABASE_URL = "postgresql+asyncpg://postgres:G@7BdXZdKqis*+N@db.alqjqidtvrgvxpvaojir.supabase.co:5432/postgres?ssl=require"

engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

async def test():
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        print(f"✅ Подключение успешно! Результат: {result.scalar()}")

import asyncio
asyncio.run(test())