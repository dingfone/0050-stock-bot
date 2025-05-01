from flask import Flask, redirect, url_for, Response
import os
import requests
from datetime import datetime

app = Flask(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

def fetch_yahoo_price(symbol):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=2d"
    resp = requests.get(url, headers=HEADERS)
    data = resp.json()

    result = data["chart"]["result"][0]
    meta = result["meta"]
    quote = result["indicators"]["quote"][0]

    current_price = meta["regularMarketPrice"]
    close_prices = quote["close"]

    if len(close_prices) >= 2:
        prev_close = close_prices[-2]
    else:
        prev_close = meta.get("chartPreviousClose", current_price)

    change_pct = ((current_price - prev_close) / prev_close) * 100
    timestamp = datetime.fromtimestamp(meta["regularMarketTime"]).strftime("%Y-%m-%d %H:%M:%S")

    return current_price, prev_close, change_pct, timestamp

def get_0050_price_and_change():
    return fetch_yahoo_price("0050.TW")

def get_vix_if_high():
    try:
        current, prev, chg, _ = fetch_yahoo_price("^VIX")
        if current > 32:
            return current
    except:
        return None
    return None

def get_treasury_yield_30y_if_high():
    try:
        current, prev, chg, _ = fetch_yahoo_price("^TYX")
        if current > 4.9:
            return current
    except:
        return None
    return None

def send_bark_notification(title, body):
    bark_token = os.getenv("bark-key")
    if not bark_token:
        return "❌ 未設定 BARK_TOKEN"
    bark_url = f"https://api.day.app/{bark_token}/{title}/{body}?group=stock&sound=alarm"
    requests.get(bark_url)

@app.route("/")
def index():
    return redirect(url_for("stock_report"))

@app.route("/health")
def health():
    return "OK", 200

@app.route("/report")
def stock_report():
    messages = []

    # 0050 判斷與通知
    try:
        current_price, prev_close, drop_percent, timestamp = get_0050_price_and_change()
        if drop_percent <= -1.5:
            body = f"{timestamp}\n漲跌幅：{drop_percent:.2f}%\n現價：{current_price:.2f}\n昨日收：{prev_close:.2f}"
            send_bark_notification("📉 0050 跌幅警告", body)
            messages.append("✅ 傳送 0050 通知")
    except Exception as e:
        messages.append(f"0050 錯誤: {e}")

    # VIX 判斷與通知
    vix_value = get_vix_if_high()
    if vix_value:
        body = f"VIX 指數過高：{vix_value:.2f}"
        send_bark_notification("⚠️ VIX 警告", body)
        messages.append("✅ 傳送 VIX 通知")

    # 美債殖利率 判斷與通知
    tyx_value = get_treasury_yield_30y_if_high()
    if tyx_value:
        body = f"30Y 美債殖利率過高：{tyx_value:.2f}%"
        send_bark_notification("⚠️ 美債殖利率警告", body)
        messages.append("✅ 傳送美債通知")

    return Response("\n".join(messages) if messages else "✅ 無需通知", mimetype="text/plain")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
