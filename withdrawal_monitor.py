import requests
import time
from datetime import datetime

# 설정값
ETHERSCAN_API_KEY = "ZXZTDNG8Z2SZ9DI8R4SF217X59IWMAIEU2"
CONTRACT_ADDRESS = "0x99CD4Ec3f88A45940936F469E4bB72A2A701EEB9"
TELEGRAM_BOT_TOKEN = "8105012106:AAEZrP1Q_xEfbCixDrm7xfITDvbsoFhxOWw"
TELEGRAM_CHAT_ID = "1074334418"
CHECK_INTERVAL = 1200  # 30초마다 체크

last_block_checked = None

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    requests.post(url, json=payload)

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

def main():
    print("🤖 Withdrawal Monitor Bot Started!")
    send_telegram_message("✅ Withdrawal monitoring bot is now active!")

    while True:
        try:
            check_withdrawals()
            time.sleep(CHECK_INTERVAL)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
