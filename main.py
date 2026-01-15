import os
import requests
from datetime import datetime

LINE_TOKEN = os.getenv("LINE_OA_TOKEN")
WATCHLIST = os.getenv("WATCHLIST", "")

def send_line(text: str):
    headers = {
        "Authorization": f"Bearer {LINE_TOKEN}",
        "Content-Type": "application/json",
    }
    url = "https://api.line.me/v2/bot/message/broadcast"
    data = {"messages": [{"type": "text", "text": text}]}
    r = requests.post(url, headers=headers, json=data, timeout=30)
    print("LINE:", r.status_code, r.text)
    r.raise_for_status()

def get_price(symbol: str) -> float:
    url = "https://query1.finance.yahoo.com/v7/finance/quote"
    r = requests.get(url, params={"symbols": symbol}, timeout=30)
    r.raise_for_status()
    data = r.json()
    result = data.get("quoteResponse", {}).get("result", [])
    if not result:
        raise RuntimeError(f"No quote for {symbol}")
    price = result[0].get("regularMarketPrice")
    if price is None:
        raise RuntimeError(f"Missing price for {symbol}")
    return float(price)

def main():
    if not LINE_TOKEN:
        raise RuntimeError("Missing LINE_OA_TOKEN (GitHub Secret)")

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # WATCHLIST 例：2330:650,2603:180,0050:160
    for item in [x.strip() for x in WATCHLIST.split(",") if x.strip()]:
        code, target = item.split(":")
        symbol = f"{code}.TW"
        price = get_price(symbol)

        if price >= float(target):
            send_line(f"📈 股價到價提醒\n{code}\n現價：{price}\n目標：>= {target}\n時間：{now}")
        else:
            print("No trigger:", code, price,
