import sqlite3

con = sqlite3.connect("bazaIvanaNesveteeva.db")
cursor = con.cursor()

print("=" * 50)
print("ПРОВЕРКА БАЗЫ ДАННЫХ (2 таблицы)")
print("=" * 50)

# Проверяем таблицы
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print(f"\n📋 Таблицы: {[t[0] for t in tables]}")

# Структура items
print("\n--- Таблица: items ---")
cursor.execute("PRAGMA table_info(items)")
for col in cursor.fetchall():
    print(f"   {col[1]} ({col[2]})")

# Структура item_prices
print("\n--- Таблица: item_prices ---")
cursor.execute("PRAGMA table_info(item_prices)")
for col in cursor.fetchall():
    print(f"   {col[1]} ({col[2]})")

# Количество записей
cursor.execute("SELECT COUNT(*) FROM items")
items_count = cursor.fetchone()[0]
cursor.execute("SELECT COUNT(*) FROM item_prices")
prices_count = cursor.fetchone()[0]

print(f"\n📊 Статистика:")
print(f"   Предметов в items: {items_count}")
print(f"   Записей цен в item_prices: {prices_count}")

# Показываем связанные данные
if items_count > 0:
    print(f"\n📝 Примеры данных:")
    cursor.execute("""
        SELECT i.id, i.name, p.price, p.fetched_at
        FROM items i
        LEFT JOIN item_prices p ON i.id = p.item_id
        LIMIT 5
    """)
    for row in cursor.fetchall():
        price_str = f"{row[2]} руб." if row[2] else "нет цены"
        print(f"   ID:{row[0]} | {row[1][:30]:<30} | {price_str}")

con.close()
print("\n✅ Проверка завершена")