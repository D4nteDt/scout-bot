import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime

def create_price_chart(item_name: str, history: list, output_path: str = "chart.png"):
    dates = [datetime.strptime(d['date'], "%Y-%m-%d") for d in history]
    prices = [d['price'] for d in history]
    
    plt.figure(figsize=(10, 6))
    plt.plot(dates, prices, linewidth=2, color='#2ecc71')
    plt.fill_between(dates, prices, alpha=0.3, color='#2ecc71')
    
    plt.title(f'Динамика цены: {item_name}', fontsize=14, fontweight='bold')
    plt.xlabel('Дата')
    plt.ylabel('Цена ($)')
    plt.grid(True, alpha=0.3)
    
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))
    plt.gca().xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
    plt.xticks(rotation=45)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    return output_path