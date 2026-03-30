import sqlite3

con = sqlite3.connect("bazaIvanaNesveteeva.db")
cursor = con.cursor()

# 1. Проверяем, есть ли таблицы
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

print("=" * 50)
print("ПРОВЕРКА БАЗЫ ДАННЫХ")
print("=" * 50)

if tables:
    print(f"\n✅ Найдены таблицы: {[t[0] for t in tables]}")
else:
    print("\n⚠️ Таблицы не найдены. База данных пустая.")
    con.close()
    exit()

# 2. Проверяем структуру таблицы steam_items
try:
    cursor.execute("PRAGMA table_info(steam_items)")
    columns = cursor.fetchall()
    print(f"\n📋 Структура таблицы steam_items:")
    for col in columns:
        print(f"   {col[1]} ({col[2]})")
except:
    print("\n❌ Таблица steam_items не существует!")
    con.close()
    exit()

# 3. Считаем количество записей
cursor.execute("SELECT COUNT(*) FROM steam_items")
count = cursor.fetchone()[0]
print(f"\n📊 Количество записей в таблице: {count}")

# 4. Показываем первые 10 записей
if count > 0:
    cursor.execute("SELECT * FROM steam_items LIMIT 10")
    rows = cursor.fetchall()
    print(f"\n📝 Первые {len(rows)} записей:")
    print("-" * 50)
    
    # Получаем названия колонок
    cursor.execute("PRAGMA table_info(steam_items)")
    col_names = [col[1] for col in cursor.fetchall()]
    
    for row in rows:
        print("\nЗапись:")
        for i, value in enumerate(row):
            if i < len(col_names):
                print(f"   {col_names[i]}: {value}")
        print("-" * 30)
else:
    print("\n⚠️ Таблица steam_items пуста. Нет данных для отображения.")

con.close()
print("\n✅ Проверка завершена")