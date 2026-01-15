import os
import time
import random
import requests
from datetime import datetime

# GitHub Actions Secrets:
# - LINE_OA_TOKEN : LINE Channel access token (long-lived)
# - WATCHLIST     : e.g. "2330:650,2603:180,0050:160"
LINE_TOKEN = os.getenv("LINE_OA_TOKEN")
WATCHLIST = os.getenv("WATCHLIST", "")


def send_line(text: str):
    """
    Broadcast a message to all friends/followers of your LINE Official Account.
    Requires Messaging API + Channel access token.
    """
    if not LINE_TOKEN:
        raise RuntimeError("Missing LINE_OA_TOKEN (GitHub Secret)")

    headers = {
        "Authorization": f"Bearer {LINE_TOKEN}",
        "Content-Type": "application/json",
    }
    url = "https://api.line.me/v2/bot/message/broadcast"
    payload = {"messages": [{"type": "text", "text": text}]}

    r = requests.post(url, headers=headers, json=payload, timeout=30)
    print("LINE:", r.status_code, r.text)
    r.raise_for_status()


def get_price(symbol: str) -> float:
    """
    Fetch latest price from Yahoo Finance.
    Handles Yahoo 429 rate limiting via exponential backoff retry.
    """
    url = "https://query1.finance.yahoo.com/v7/finance/quote"
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    for attempt in range(5):
        r = requests.get(url, params={"symbols": symbol}, headers=headers, timeout=30)

        # Yahoo rate-limit
        if r.status_code == 429:
            wait = (2 ** attempt) + random.uniform(0, 1)
            print(f"Yahoo 429 rate limit. Retry in {wait:.1f}s (attempt {attempt+1}/5)")
            time.sleep(wait)
            continue

        r.raise_for_status()
        data = r.json()
        result = data.get("quoteResponse", {}).get("result", [])
        if not result:
            raise RuntimeError(f"No quote for {symbol}")
        price = result[0].get("regularMarketPrice")
        if price is None:
            raise RuntimeError(f"Missing price for {symbol}")
        return float(price)

    raise RuntimeError("Yahoo rate-limited (429). Please retry later.")


def parse_watchlist(watchlist: str):
    """
    WATCHLIST format:
      "2330:650,2603:180,0050:160"
    Returns list of (code, target_price_float)
    """
    items = [x.strip() for x in watchlist.split(",") if x.strip()]
    parsed = []
    for item in items:
        if ":" not in item:
            raise ValueError(f"Invalid WATCHLIST item (missing ':'): {item}")
        code, target = item.split(":", 1)
        code = code.strip()
        target = target.strip()
        if not code or not target:
            raise ValueError(f"Invalid WATCHLIST item: {item}")
        parsed.append((code, float(target)))
    return parsed


def main():
    if not LINE_TOKEN:
        raise RuntimeError("Missing LINE_OA_TOKEN (GitHub Secret)")

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if not WATCHLIST.strip():
        print("WATCHLIST is empty. Example: 2330:650,2603:180,0050:160")
        return

    watch_items = parse_watchlist(WATCHLIST)

    for code, target in watch_items:
        # Taiwan stocks: use .TW for listed, .TWO for OTC
        # Here we default to .TW
        symbol = f"{code}.TW"

        price = get_price(symbol)
        # Reduce chance of being rate-limited
        time.sleep(1)

        if price >= target:
            send_line(
                f"📈 股價到價提醒\n"
                f"{code}\n"
                f"現價：{price}\n"
                f"目標：>= {target}\n"
                f"時間：{now}"
            )
        else:
            print(f"No trigger: {code} price={price} target>={target}")


if __name__ == "__main__":
    main()
