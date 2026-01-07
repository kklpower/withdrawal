import requests
import time
from datetime import datetime
from flask import Flask
import threading

app = Flask(__name__)

# 설정값
ETHERSCAN_API_KEY = "ZXZTDNG8Z2SZ9DI8R4SF217X59IWMAIEU2"
CONTRACT_ADDRESS = "0x99CD4Ec3f88A45940936F469E4bB72A2A701EEB9"
TELEGRAM_BOT_TOKEN = "8105012106:AAEZrP1Q_xEfbCixDrm7xfITDvbsoFhxOWw"
TELEGRAM_CHAT_ID = "1074334418"
CHECK_INTERVAL = 30  # 30초마다 체크

last_block_checked = None

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Telegram error: {e}")

def check_withdrawals():
    global last_block_checked

    # Etherscan API로 internal transactions 조회
    url = f"https://api.etherscan.io/api"
    params = {
        "module": "account",
        "action": "txlistinternal",
        "address": CONTRACT_ADDRESS,
        "startblock": last_block_checked if last_block_checked else 0,
        "endblock": 99999999,
        "sort": "asc",
        "apikey": ETHERSCAN_API_KEY
    }

    try:
        response = requests.get(url, params=params)
        data = response.json()

        if data["status"] == "1" and data["result"]:
            for tx in data["result"]:
                # withdraw 관련 트랜잭션 필터링
                if tx["from"].lower() == CONTRACT_ADDRESS.lower():
                    amount_eth = int(tx["value"]) / 1e18
                    message = f"""
🔔 <b>Withdrawal Detected!</b>

💰 Amount: {amount_eth:.4f} ETH
📤 To: {tx["to"]}
🔗 TX: <a href="https://etherscan.io/tx/{tx['hash']}">{tx['hash'][:10]}...</a>
⏰ Time: {datetime.fromtimestamp(int(tx['timeStamp']))}
                    """
                    send_telegram_message(message)

            last_block_checked = int(data["result"][-1]["blockNumber"])
    except Exception as e:
        print(f"Error checking withdrawals: {e}")

def monitor_loop():
    """백그라운드에서 계속 실행되는 모니터링 루프"""
    print("🤖 Withdrawal Monitor Bot Started!")
    send_telegram_message("✅ Withdrawal monitoring bot is now active!")

    while True:
        try:
            check_withdrawals()
            time.sleep(CHECK_INTERVAL)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(60)

@app.route('/')
def home():
    """Health check 엔드포인트"""
    return "Withdrawal Monitor Bot is running! 🤖"

@app.route('/health')
def health():
    """Render의 health check용"""
    return {"status": "ok", "last_block": last_block_checked}

if __name__ == "__main__":
    # 백그라운드 스레드로 모니터링 시작
    monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
    monitor_thread.start()

    # Flask 웹 서버 시작
    import os
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
