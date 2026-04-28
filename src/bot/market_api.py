import random
from datetime import datetime, timedelta

def search_items(query: str):
    mock_items = [
        {"name": "AK-47 | Redline (Field-Tested)", "market_hash_name": "AK-47 | Redline (Field-Tested)"},
        {"name": "Butterfly Knife | Fade (Factory New)", "market_hash_name": "..."},
        {"name": "M4A4 | Howl (Factory New)", "market_hash_name": "..."},
    ]
    return [item for item in mock_items if query.lower() in item['name'].lower()] or mock_items[:1]

def get_item_price(item_name: str):
    base_price = random.uniform(50, 500)
    return {
        "price": round(base_price, 2),
        "change": f"+{random.uniform(1, 15):.1f}%" if random.random() > 0.5 else f"-{random.uniform(1, 10):.1f}%",
        "volume": random.randint(10, 1000),
        "currency": "$"
    }

def get_price_history(item_name: str, days: int = 30):
    history = []
    base_price = random.uniform(100, 300)
    current_date = datetime.now()
    
    for i in range(days):
        date = current_date - timedelta(days=days-i)
        change = random.uniform(-0.05, 0.05)
        base_price *= (1 + change)
        history.append({
            "date": date.strftime("%Y-%m-%d"),
            "price": round(base_price, 2)
        })
    
    return history