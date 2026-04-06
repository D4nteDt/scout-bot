import asyncio
from database import engine
from models import Base

async def init_db():
    print("Starting DB initialization...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database is ready!")

if __name__ == "__main__":
    try:
        asyncio.run(init_db())
    except Exception as e:
        print(f"Error during initialization: {e}")
