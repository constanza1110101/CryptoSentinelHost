Here's an improved version of the crypto host script with enhanced security features and better UI:

```python
import socket
import ssl
import json
import hashlib
import os
import time
from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress
from rich.text import Text
from datetime import datetime

# Server configuration
server_ip = "192.168.1.100"  # Replace with your server's IP
server_port = 5000
AUTH_TOKEN = hashlib.sha256(os.environ.get("CRYPTO_AUTH_TOKEN", "my_secure_token").encode()).hexdigest()

console = Console()

# Enhanced Secure Context
context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
context.verify_mode = ssl.CERT_REQUIRED
context.check_hostname = True
context.load_verify_locations("server.crt")
context.minimum_version = ssl.TLSVersion.TLSv1_3

def log_activity(action, details):
    """Log all activities for security auditing"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("activity_log.json", "a") as log_file:
        log_entry = {
            "timestamp": timestamp,
            "action": action,
            "details": details
        }
        log_file.write(json.dumps(log_entry) + "\n")

def send_request(data):
    """Sends a request to the secure server with timeout and retry logic"""
    max_retries = 3
    timeout = 10
    
    for attempt in range(max_retries):
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.settimeout(timeout)
        secure_client = context.wrap_socket(client, server_hostname=server_ip)
        
        try:
            with Progress() as progress:
                task = progress.add_task("[cyan]Connecting to server...", total=100)
                secure_client.connect((server_ip, server_port))
                progress.update(task, advance=50)
                
                # Add request ID and timestamp for security
                data["request_id"] = hashlib.md5(os.urandom(32)).hexdigest()
                data["timestamp"] = int(time.time())
                
                secure_client.sendall(json.dumps(data).encode())
                progress.update(task, advance=25)
                
                response = b""
                while True:
                    chunk = secure_client.recv(4096)
                    if not chunk:
                        break
                    response += chunk
                
                progress.update(task, advance=25)
                
            parsed_response = json.loads(response.decode())
            log_activity(data["action"], {"request": data, "response": parsed_response})
            return parsed_response
            
        except (socket.timeout, ConnectionRefusedError, json.JSONDecodeError) as e:
            console.print(f"[bold red]Error on attempt {attempt+1}/{max_retries}: {str(e)}[/bold red]")
            if attempt == max_retries - 1:
                console.print("[bold red]Failed to connect to server after multiple attempts[/bold red]")
                return {"status": "error", "message": f"Connection failed: {str(e)}"}
            time.sleep(2)  # Wait before retrying
        finally:
            secure_client.close()

def validate_address(address, token_type):
    """Validate cryptocurrency address format"""
    if token_type.upper() == "ETH" and not address.startswith("0x"):
        return False
    if token_type.upper() == "BTC" and not (address.startswith("1") or address.startswith("3") or address.startswith("bc1")):
        return False
    # Add more validation as needed
    return True

def display_rates():
    """Display current exchange rates"""
    response = send_request({"auth_token": AUTH_TOKEN, "action": "get_rates"})
    
    if response.get("status") == "success":
        rates = response.get("rates", {})
        table = Table(title="Current Exchange Rates", show_header=True, header_style="bold magenta")
        table.add_column("Currency Pair", justify="center")
        table.add_column("Rate", justify="center")
        
        for pair, rate in rates.items():
            table.add_row(pair, str(rate))
        
        console.print(table)
    else:
        console.print("[bold red]Failed to fetch current rates[/bold red]")

def main_menu():
    console.print(Panel.fit(
        Text("SECURE CRYPTO TRANSACTION SYSTEM", style="bold cyan"),
        subtitle="v2.0 Enhanced Security",
        border_style="green"
    ))
    
    while True:
        console.print("[bold cyan]🔹 Choose an Option:[/bold cyan]")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Option", justify="center", style="cyan")
        table.add_column("Action", justify="left")
        table.add_column("Description", justify="left")
        
        table.add_row("1", "Receive Payment", "Generate payment address for fiat or crypto")
        table.add_row("2", "Swap Crypto", "Exchange between different cryptocurrencies")
        table.add_row("3", "Withdraw", "Send funds to external address")
        table.add_row("4", "View Rates", "Display current exchange rates")
        table.add_row("5", "Transaction History", "View recent transactions")
        table.add_row("6", "Exit", "Close the application")
        
        console.print(table)

        choice = Prompt.ask("[bold yellow]Enter your choice[/bold yellow]", choices=["1", "2", "3", "4", "5", "6"])

        if choice == "1":
            amount = Prompt.ask("[bold green]Enter amount[/bold green]")
            currency = Prompt.ask("[bold green]Enter currency[/bold green]", choices=["USD", "EUR", "ETH", "BTC", "USDT"])
            payment_method = Prompt.ask("[bold green]Payment method[/bold green]", choices=["crypto", "card", "bank"])
            
            response = send_request({
                "auth_token": AUTH_TOKEN, 
                "action": "receive_payment", 
                "amount": amount, 
                "currency": currency,
                "payment_method": payment_method
            })
            
            if response.get("status") == "success":
                console.print(Panel(
                    f"Payment Address: [bold]{response.get('address')}[/bold]\n" +
                    f"Amount: [bold]{amount} {currency}[/bold]\n" +
                    f"Reference ID: [bold]{response.get('reference_id')}[/bold]",
                    title="Payment Details",
                    border_style="green"
                ))
            else:
                console.print(f"[bold red]✘ Error: {response.get('message', 'Unknown error')}[/bold red]")

        elif choice == "2":
            from_token = Prompt.ask("[bold blue]From token[/bold blue]", choices=["USDT", "ETH", "BTC", "XMR"])
            to_token = Prompt.ask("[bold blue]To token[/bold blue]", choices=["USDT", "ETH", "BTC", "XMR"])
            amount = Prompt.ask("[bold blue]Amount to swap[/bold blue]")
            
            # Get estimated amount before confirming
            estimate = send_request({
                "auth_token": AUTH_TOKEN, 
                "action": "estimate_swap", 
                "from_token": from_token, 
                "to_token": to_token, 
                "amount": amount
            })
            
            if estimate.get("status") == "success":
                console.print(f"[bold green]Estimated receive amount: {estimate.get('estimated_amount')} {to_token}[/bold green]")
                confirm = Prompt.ask("[bold yellow]Confirm swap?[/bold yellow]", choices=["yes", "no"])
                
                if confirm.lower() == "yes":
                    response = send_request({
                        "auth_token": AUTH_TOKEN, 
                        "action": "swap", 
                        "from_token": from_token, 
                        "to_token": to_token, 
                        "amount": amount
                    })
                    
                    if response.get("status") == "success":
                        console.print(Panel(
                            f"Swapped: [bold]{amount} {from_token}[/bold]\n" +
                            f"Received: [bold]{response.get('received_amount')} {to_token}[/bold]\n" +
                            f"Transaction ID: [bold]{response.get('tx_id')}[/bold]",
                            title="Swap Completed",
                            border_style="green"
                        ))
                    else:
                        console.print(f"[bold red]✘ Swap Error: {response.get('message', 'Unknown error')}[/bold red]")
            else:
                console.print(f"[bold red]✘ Error getting estimate: {estimate.get('message', 'Unknown error')}[/bold red]")

        elif choice == "3":
            token = Prompt.ask("[bold red]Token to withdraw[/bold red]", choices=["USDT", "ETH", "BTC", "XMR"])
            to_address = Prompt.ask("[bold red]Withdrawal address[/bold red]")
            
            # Validate address format
            if not validate_address(to_address, token):
                console.print(f"[bold red]Invalid {token} address format[/bold red]")
                continue
                
            amount = Prompt.ask("[bold red]Amount to withdraw[/bold red]")
            
            # 2FA verification for withdrawals
            verification_code = Prompt.ask("[bold yellow]Enter 2FA code from authenticator app[/bold yellow]")
            
            response = send_request({
                "auth_token": AUTH_TOKEN, 
                "action": "withdraw", 
                "to_address": to_address, 
                "amount": amount, 
                "token": token, 
                "verification_code": verification_code
            })
            
            if response.get("status") == "success":
                console.print(Panel(
                    f"Amount: [bold]{amount} {token}[/bold]\n" +
                    f"Address: [bold]{to_address}[/bold]\n" +
                    f"Transaction ID: [bold]{response.get('tx_id')}[/bold]\n" +
                    f"Fee: [bold]{response.get('fee')} {token}[/bold]",
                    title="Withdrawal Initiated",
                    border_style="green"
                ))
            else:
                console.print(f"[bold red]✘ Withdrawal Error: {response.get('message', 'Unknown error')}[/bold red]")

        elif choice == "4":
            display_rates()
            
        elif choice == "5":
            limit = Prompt.ask("[bold blue]Number of transactions to show[/bold blue]", default="10")
            response = send_request({
                "auth_token": AUTH_TOKEN, 
                "action": "transaction_history", 
                "limit": limit
            })
            
            if response.get("status") == "success":
                transactions = response.get("transactions", [])
                if transactions:
                    table = Table(show_header=True, header_style="bold magenta")
                    table.add_column("Date", justify="center")
                    table.add_column("Type", justify="center")
                    table.add_column("Amount", justify="right")
                    table.add_column("Status", justify="center")
                    
                    for tx in transactions:
                        status_style = "green" if tx.get("status") == "completed" else "yellow"
                        table.add_row(
                            tx.get("date", ""),
                            tx.get("type", ""),
                            f"{tx.get('amount', '')} {tx.get('currency', '')}",
                            f"[{status_style}]{tx.get('status', '')}[/{status_style}]"
                        )
                    
                    console.print(table)
                else:
                    console.print("[yellow]No transactions found[/yellow]")
            else:
                console.print(f"[bold red]✘ Error: {response.get('message', 'Unknown error')}[/bold red]")

        elif choice == "6":
            console.print("[bold green]🔒 Session terminated securely[/bold green]")
            break
            
        console.print("\n")

if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        console.print("\n[bold red]Emergency exit triggered[/bold red]")
    except Exception as e:
        console.print(f"[bold red]Critical error: {str(e)}[/bold red]")
        log_activity("critical_error", {"error": str(e)})
```
