import sqlite3
import asyncio
from datetime import datetime

print("Инициализация базы данных...")

con = sqlite3.connect("bazaIvanaNesveteeva.db")
cursor = con.cursor()

print("Создание таблиц...")

# Таблица 1: Только ID и названия предметов
cursor.execute("""
CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# Таблица 2: Все остальные данные + внешний ключ на items
cursor.execute("""
CREATE TABLE IF NOT EXISTS item_prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER NOT NULL,
    price REAL,
    median_price REAL,
    volume INTEGER,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE
)
""")
con.commit()
print("Таблицы готова")


# ============ API для работы с базой ============

def get_or_create_item(item_name: str) -> int:
    """
    Получает ID предмета по названию. Если предмета нет - создает.
    Возвращает ID предмета.
    """
    # Проверяем, есть ли уже такой предмет
    cursor.execute("SELECT id FROM items WHERE name = ?", (item_name,))
    result = cursor.fetchone()
    
    if result:
        return result[0]
    
    # Создаем новый предмет
    cursor.execute("INSERT INTO items (name) VALUES (?)", (item_name,))
    con.commit()
    return cursor.lastrowid


def get_item_by_name(item_name: str) -> dict:
    """
    Получает полную информацию о предмете по названию.
    Если данных о цене нет - возвращает только базовую инфу.
    """
    cursor.execute("""
        SELECT i.id, i.name, i.created_at,
               p.price, p.median_price, p.volume, p.fetched_at
        FROM items i
        LEFT JOIN item_prices p ON i.id = p.item_id
        WHERE i.name = ?
        ORDER BY p.fetched_at DESC
        LIMIT 1
    """, (item_name,))
    
    row = cursor.fetchone()
    if not row:
        return None
    
    return {
        "id": row[0],
        "name": row[1],
        "created_at": row[2],
        "price": row[3],
        "median_price": row[4],
        "volume": row[5],
        "fetched_at": row[6]
    }


def save_price_data(item_id: int, price: float, median: float, volume: int):
    """Сохраняет данные о цене для предмета"""
    cursor.execute("""
        INSERT INTO item_prices (item_id, price, median_price, volume)
        VALUES (?, ?, ?, ?)
    """, (item_id, price, median, volume))
    con.commit()
    print(f"   💾 Сохранены цены для item_id={item_id}")


# ============ ГЛАВНЫЙ МЕТОД: запрос → парсер → сохранение ============

async def request_item_data(item_name: str, parser_func) -> dict:
    """
    1. Проверяет/создает предмет в базе
    2. Запрашивает данные у парсера (parser_func)
    3. Сохраняет результат
    4. Возвращает данные
    """
    print(f"\n🔍 Запрос данных для: {item_name}")
    
    # Шаг 1: Получаем или создаем предмет
    item_id = get_or_create_item(item_name)
    print(f"   📌 Item ID: {item_id}")
    
    # Шаг 2: Запрашиваем данные у парсера
    print(f"   🌐 Отправляю запрос в парсер...")
    parsed_data = await parser_func(item_name)
    
    if not parsed_data:
        print(f"   ❌ Парсер не вернул данных")
        return get_item_by_name(item_name)
    
    # Шаг 3: Сохраняем в базу
    save_price_data(
        item_id=item_id,
        price=parsed_data.get('price', 0),
        median=parsed_data.get('median', 0),
        volume=parsed_data.get('volume', 0)
    )
    
    print(f"   ✅ Данные сохранены: {parsed_data.get('price')} руб.")
    return get_item_by_name(item_name)


print("Модуль загружен")