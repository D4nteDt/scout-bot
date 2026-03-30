import sqlite3

print("Инициализация базы данных...")

con = sqlite3.connect("bazaIvanaNesveteeva.db")
cursor = con.cursor()

print("Создание таблицы...")
cursor.execute("""
CREATE TABLE IF NOT EXISTS steam_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    price REAL,
    median_price REAL,
    volume INTEGER,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
con.commit()
print("Таблица готова")

def save_items_from_parser(items_list):
    print(f"Сохраняю {len(items_list)} предметов...")
    saved = 0
    for item in items_list:
        if item:
            cursor.execute('''
            INSERT INTO steam_items (name, price, median_price, volume)
            VALUES (?, ?, ?, ?)
            ''', (item['name'], item['price'], item['median'], item['volume']))
            saved += 1
    con.commit()
    print(f"Сохранено {saved} предметов")

def add_items(items_list):
    """Добавляет новые предметы в базу (только названия)"""
    added = 0
    for item_name in items_list:
        try:
            cursor.execute('''
            INSERT INTO steam_items (name) VALUES (?)
            ''', (item_name,))
            added += 1
        except sqlite3.IntegrityError:
            # Предмет уже существует
            pass
    con.commit()
    print(f"   Добавлено {added} новых предметов")

def save_prices(items_list):
    """Обновляет цены для существующих предметов"""
    updated = 0
    for item in items_list:
        if item:
            cursor.execute('''
            UPDATE steam_items 
            SET price = ?, median_price = ?, volume = ?, last_updated = CURRENT_TIMESTAMP
            WHERE name = ?
            ''', (item['price'], item['median'], item['volume'], item['name']))
            updated += 1
    con.commit()
    print(f"   Обновлено {updated} предметов")

print("Модуль загружен")