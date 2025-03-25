import socket
import ssl
import logging
import json
import time
import requests
import sqlite3
from rich.console import Console
from rich.table import Table
from rich.progress import track
from threading import Thread
from hashlib import sha256
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization

# Setup Logging
logging.basicConfig(filename="server.log", level=logging.INFO, format="%(asctime)s - %(message)s")

# Database Setup (SQLite)
db = sqlite3.connect("transactions.db")
cursor = db.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY,
        user_id TEXT,
        action TEXT,
        amount REAL,
        token TEXT,
        status TEXT,
        timestamp TEXT
    )
""")
db.commit()

# Rich Console
console = Console()

# Authentication Token
AUTH_TOKEN = "my_secure_token"

# Rate Limiting: Track request counts per user IP
REQUEST_COUNT = {}
RATE_LIMIT = 5  # Max 5 requests per minute

# 1inch API (DEX Swaps)
ONEINCH_API_URL = "https://api.1inch.io/v5.0/1/swap"
EXCHANGE_RATE_API = "https://api.exchangerate-api.com/v4/latest/USD"

WALLET_ADDRESS = "your_wallet_address"
PRIVATE_KEY = "your_private_key"

# Two-Factor Authentication Setup (mockup for demonstration)
def generate_2fa_code(user_id):
    """ Generate a 2FA code for the user (simple for demo purposes) """
    return sha256(f"{user_id}_{time.time()}".encode()).hexdigest()[:6]

def verify_2fa(user_id, input_code):
    """ Verify the 2FA code entered by the user """
    valid_code = generate_2fa_code(user_id)
    return valid_code == input_code

# Withdrawal Function (Send funds to a specified address)
def send_withdrawal(to_address, amount, token, user_id):
    """ Process the withdrawal after validating 2FA """
    two_fa_code = input(f"Enter 2FA code for user {user_id}: ")
    if not verify_2fa(user_id, two_fa_code):
        return {"status": "failure", "error": "Invalid 2FA code"}

    # Mocking a successful withdrawal transaction
    withdrawal_success = True
    if withdrawal_success:
        cursor.execute("INSERT INTO transactions (user_id, action, amount, token, status, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                       (user_id, "withdrawal", amount, token, "success", time.strftime("%Y-%m-%d %H:%M:%S")))
        db.commit()
        logging.info(f"Withdrawal to {to_address} successful: {amount} {token}")
        return {"status": "success", "tx_hash": "0xabcdef1234567890"}  # Mock transaction hash
    else:
        return {"status": "failure", "error": "Withdrawal failed"}

# Rate Limiting Function
def check_rate_limit(ip):
    """ Check and track request counts per IP """
    current_time = time.time()
    if ip not in REQUEST_COUNT:
        REQUEST_COUNT[ip] = {"count": 1, "timestamp": current_time}
    else:
        elapsed_time = current_time - REQUEST_COUNT[ip]["timestamp"]
        if elapsed_time < 60:
            REQUEST_COUNT[ip]["count"] += 1
        else:
            REQUEST_COUNT[ip] = {"count": 1, "timestamp": current_time}
    
    if REQUEST_COUNT[ip]["count"] > RATE_LIMIT:
        return False
    return True

# Main Server Function
def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("0.0.0.0", 5000))
    server.listen(5)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile="server.crt", keyfile="server.key")

    console.print("[bold green]🚀 Secure Payment & Swap Server Running...[/bold green]")
    
    while True:
        conn, addr = server.accept()
        ip = addr[0]
        if not check_rate_limit(ip):
            logging.warning(f"Rate limit exceeded for {ip}")
            conn.close()
            continue
        
        secure_conn = context.wrap_socket(conn, server_side=True)
        data = secure_conn.recv(1024).decode()
        if not data:
            continue

        request = json.loads(data)
        token = request.get("auth_token")
        action = request.get("action")
        user_id = request.get("user_id")

        # Authentication and Action Handling
        if token != AUTH_TOKEN:
            logging.warning(f"Unauthorized attempt from {ip}")
            secure_conn.sendall(b"Unauthorized")
            continue

        if action == "receive_payment":
            amount = request.get("amount")
            currency = request.get("currency")
            # Handle Fiat or Crypto
            response = handle_receive_payment(amount, currency)
            secure_conn.sendall(json.dumps(response).encode())
        
        elif action == "swap":
            from_token = request.get("from_token")
            to_token = request.get("to_token")
            amount = request.get("amount")
            response = handle_swap(from_token, to_token, amount)
            secure_conn.sendall(json.dumps(response).encode())

        elif action == "withdraw":
            to_address = request.get("to_address")
            amount = request.get("amount")
            token = request.get("token")
            response = send_withdrawal(to_address, amount, token, user_id)
            secure_conn.sendall(json.dumps(response).encode())

        secure_conn.close()

def handle_receive_payment(amount, currency):
    """ Handle receiving payment and convert fiat to crypto """
    rate = fetch_exchange_rate(currency)
    if rate:
        crypto_amount = float(amount) / rate
        return {"converted_to_crypto": crypto_amount}
    else:
        return {"error": "Exchange rate unavailable"}

def handle_swap(from_token, to_token, amount):
    """ Executes a crypto swap via 1inch API """
    params = {"fromTokenAddress": from_token, "toTokenAddress": to_token, "amount": amount, "fromAddress": WALLET_ADDRESS, "slippage": 1}
    response = requests.get(ONEINCH_API_URL, params=params)
    return response.json() if response.status_code == 200 else {"error": "Swap failed"}

def fetch_exchange_rate(fiat_currency):
    """ Fetch exchange rate for fiat to crypto conversion """
    try:
        response = requests.get(EXCHANGE_RATE_API)
        data = response.json()
        return data["rates"].get(fiat_currency.upper(), None)
    except Exception as e:
        logging.error(f"Exchange rate error: {e}")
        return None

if __name__ == "__main__":
    start_server()
