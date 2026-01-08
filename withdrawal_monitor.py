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
CHECK_INTERVAL = 600  # 30초마다 체크

last_block_checked = None
processed_tx_hashes = set()  # 중복 알림 방지

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, json=payload)
        print(f"Telegram message sent: {response.status_code}")
    except Exception as e:
        print(f"Telegram error: {e}")

def check_token_transfers():
    """ERC-20 토큰 출금 체크"""
    global last_block_checked

    url = f"https://api.etherscan.io/api"
    params = {
        "module": "account",
        "action": "tokentx",  # 토큰 전송 조회
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
            new_withdrawals = []

            for tx in data["result"]:
                # 컨트랙트에서 나가는 토큰 전송 (출금)
                if tx["from"].lower() == CONTRACT_ADDRESS.lower():
                    tx_hash = tx["hash"]

                    # 이미 처리한 트랜잭션은 스킵
                    if tx_hash in processed_tx_hashes:
                        continue

                    processed_tx_hashes.add(tx_hash)

                    # 토큰 금액 계산 (decimals 고려)
                    decimals = int(tx["tokenDecimal"])
                    amount = int(tx["value"]) / (10 ** decimals)
                    token_symbol = tx["tokenSymbol"]
                    token_name = tx["tokenName"]

                    message = f"""
🔔 <b>Token Withdrawal Detected!</b>

💰 Amount: {amount:,.4f} {token_symbol}
🪙 Token: {token_name}
📤 To: {tx["to"]}
🔗 TX: <a href="https://etherscan.io/tx/{tx_hash}">{tx_hash[:10]}...</a>
⏰ Time: {datetime.fromtimestamp(int(tx["timeStamp"]))}
🏦 Block: {tx["blockNumber"]}
                    """
                    send_telegram_message(message)
                    new_withdrawals.append(tx)
                    print(f"✅ Withdrawal detected: {amount} {token_symbol}")

            # 마지막 블록 번호 업데이트
            if data["result"]:
                last_block_checked = int(data["result"][-1]["blockNumber"])

    except Exception as e:
        print(f"Error checking token transfers: {e}")

def check_eth_withdrawals():
    """ETH 출금 체크 (Internal Transactions)"""
    global last_block_checked

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
                if tx["from"].lower() == CONTRACT_ADDRESS.lower():
                    tx_hash = tx["hash"]

                    if tx_hash in processed_tx_hashes:
                        continue

                    processed_tx_hashes.add(tx_hash)

                    amount_eth = int(tx["value"]) / 1e18

                    message = f"""
🔔 <b>ETH Withdrawal Detected!</b>

💰 Amount: {amount_eth:.4f} ETH
📤 To: {tx["to"]}
🔗 TX: <a href="https://etherscan.io/tx/{tx_hash}">{tx_hash[:10]}...</a>
⏰ Time: {datetime.fromtimestamp(int(tx["timeStamp"]))}
🏦 Block: {tx["blockNumber"]}
                    """
                    send_telegram_message(message)
                    print(f"✅ ETH Withdrawal detected: {amount_eth} ETH")

            if data["result"]:
                last_block_checked = int(data["result"][-1]["blockNumber"])

    except Exception as e:
        print(f"Error checking ETH withdrawals: {e}")

def monitor_loop():
    """백그라운드에서 계속 실행되는 모니터링 루프"""
    print("🤖 Withdrawal Monitor Bot Started!")
    print(f"📍 Monitoring contract: {CONTRACT_ADDRESS}")
    send_telegram_message("✅ Withdrawal monitoring bot is now active!")

    while True:
        try:
            print(f"🔍 Checking withdrawals... (Block: {last_block_checked})")

            # 토큰 출금 체크
            check_token_transfers()

            # ETH 출금 체크
            check_eth_withdrawals()

            time.sleep(CHECK_INTERVAL)
        except Exception as e:
            print(f"Error in monitor loop: {e}")
            time.sleep(60)

@app.route('/')
def home():
    """Health check 엔드포인트"""
    status = f"Withdrawal Monitor Bot is running! 🤖<br>"
    status += f"Last block checked: {last_block_checked}<br>"
    status += f"Transactions processed: {len(processed_tx_hashes)}"
    return status

@app.route('/health')
def health():
    """Render의 health check용"""
    return {
        "status": "ok", 
        "last_block": last_block_checked,
        "processed_count": len(processed_tx_hashes)
    }

if __name__ == "__main__":
    # 백그라운드 스레드로 모니터링 시작
    monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
    monitor_thread.start()

    # Flask 웹 서버 시작
    import os
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
