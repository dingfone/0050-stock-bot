from flask import Flask, redirect, url_for, Response
import os
import requests
import datetime

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
        prev_close = meta["chartPreviousClose"]

    change_pct = ((current_price - prev_close) / prev_close) * 100
    return current_price, prev_close, change_pct

def send_bark_notification(title, body):
    bark_token = os.getenv("bark-key")
    if not bark_token:
        return "❌ 未設定 BARK_TOKEN"
    bark_url = f"https://api.day.app/{bark_token}/{title}/{body}?group=stock&sound=bell"
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

    try:
        p0050, prev0050, ch0050 = fetch_yahoo_price("0050.TW")
        if ch0050 <= -1.5:
            body = f"0050 跌幅：{ch0050:.2f}%\n現價：{p0050:.2f}，昨收：{prev0050:.2f}"
            send_bark_notification("📉 0050 跌幅警告", body)
            messages.append("✅ 傳送 0050 通知")
    except Exception as e:
        messages.append(f"❌ 0050 錯誤：{e}")

    try:
        pvix, prevvix, chvix = fetch_yahoo_price("^VIX")
        if pvix > 32:
            body = f"VIX：{pvix:.2f}（+{chvix:.2f}%）"
            send_bark_notification("⚠️ VIX 指數警告", body)
            messages.append("✅ 傳送 VIX 通知")
    except Exception as e:
        messages.append(f"❌ VIX 錯誤：{e}")

    try:
        ptyx, prevtyx, chtyx = fetch_yahoo_price("^TYX")
        if ptyx > 4.9:
            body = f"30Y 殖利率：{ptyx:.2f}%（+{chtyx:.2f}%）"
            send_bark_notification("⚠️ 美債殖利率警告", body)
            messages.append("✅ 傳送 TYX 通知")
    except Exception as e:
        messages.append(f"❌ TYX 錯誤：{e}")

    return Response("\n".join(messages) if messages else "✅ 無需通知", mimetype="text/plain")

@app.route("/test")
def test_notify():
    try:
        p0050, prev0050, ch0050 = fetch_yahoo_price("0050.TW")
        pvix, prevvix, chvix = fetch_yahoo_price("^VIX")
        ptyx, prevtyx, chtyx = fetch_yahoo_price("^TYX")

        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

        body = f"""⏰ {now}
0050：{p0050:.2f}（{ch0050:.2f}%）
VIX：{pvix:.2f}（{chvix:.2f}%）
30Y 美債：{ptyx:.2f}%（{chtyx:.2f}%）"""

        send_bark_notification("📊 股票測試通知", body)
        return "✅ 測試通知已送出", 200
    except Exception as e:
        return f"❌ 測試錯誤：{e}", 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
