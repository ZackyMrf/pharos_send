import random
import time
import requests
import os
import sys
from datetime import datetime
from web3 import Web3, Account
from colorama import Fore, Style, init

init()

def print_banner():
    banner = f"""
{Fore.MAGENTA}╔════════════════════════════════════════════════════════════╗
║          🚀 PHAROS NETWORK TRANSACTION BOT 🚀             ║
║                        by Mrf                            ║
╚════════════════════════════════════════════════════════════╝{Style.RESET_ALL}
"""
    print(banner)

def log_info(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"{Fore.BLUE}[{timestamp}] [INFO]{Style.RESET_ALL} {message}")

def log_success(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"{Fore.GREEN}[{timestamp}] [SUCCESS]{Style.RESET_ALL} {message}")

def log_error(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"{Fore.RED}[{timestamp}] [ERROR]{Style.RESET_ALL} {message}")

def log_transaction(tx_number, total_txs, tx_amount, recipient_addr, tx_hash):
    timestamp = datetime.now().strftime("%H:%M:%S")
    progress = f"[{tx_number}/{total_txs}]"
    print(f"{Fore.YELLOW}[{timestamp}] {progress}{Style.RESET_ALL} Sent {Fore.CYAN}{tx_amount}{Style.RESET_ALL} PHRS to {Fore.MAGENTA}{recipient_addr}{Style.RESET_ALL}")
    print(f"  TX Hash: {Fore.BLUE}{tx_hash}{Style.RESET_ALL}")

def check_file_exists(filename):
    if not os.path.exists(filename):
        log_error(f"File '{filename}' not found. Please create it.")
        return False
    return True

def get_current_gas_price(web3_instance):
    try:
        gas_price = web3_instance.eth.gas_price
        gas_price_gwei = web3_instance.from_wei(gas_price, 'gwei')
        log_info(f"Current network gas price: {gas_price_gwei:.2f} gwei")
        return gas_price
    except Exception as error:
        log_error(f"Error getting gas price: {str(error)}")
        default_gas_price = web3_instance.to_wei(5, 'gwei')
        log_info(f"Using default gas price: 5 gwei")
        return default_gas_price

def main():
    print_banner()
    required_files = ["private_key.txt", "token.txt", "recipients.txt"]
    for file_path in required_files:
        if not check_file_exists(file_path):
            sys.exit(1)

    log_info("Connecting to Pharos Testnet...")
    rpc_endpoints = [
        "https://testnet.dplabs-internal.com",
        "https://pharos-testnet.rpc.caldera.xyz/http",
        "https://pharos-testnet-rpc.stress.run",
        "https://pharos.rpc.thirdweb.com"
    ]
    web3 = None
    connected = False
    for endpoint in rpc_endpoints:
        try:
            log_info(f"Trying endpoint: {endpoint}")
            web3 = Web3(Web3.HTTPProvider(endpoint))
            if web3.is_connected():
                connected = True
                log_success(f"Connected to Pharos Testnet via {endpoint}")
                break
        except Exception as error:
            log_error(f"Connection to {endpoint} failed: {str(error)}")
    if not connected or web3 is None:
        log_error("Failed to connect to any Pharos Testnet RPC endpoints")
        sys.exit(1)

    with open("private_key.txt", "r") as key_file:
        private_key = key_file.readline().strip()
        if not private_key:
            log_error("Private key is empty. Please add it to private_key.txt")
            sys.exit(1)
    wallet = Account.from_key(private_key)
    wallet_address = wallet.address
    log_info(f"Wallet address: {Fore.GREEN}{wallet_address}{Style.RESET_ALL}")

    balance_wei = web3.eth.get_balance(wallet_address)
    balance_phrs = web3.from_wei(balance_wei, 'ether')
    log_info(f"Current balance: {Fore.GREEN}{balance_phrs:.6f}{Style.RESET_ALL} PHRS")

    try:
        with open("recipients.txt", "r") as recipients_file:
            raw_addresses = [line.strip() for line in recipients_file if line.strip()]
        valid_recipients = []
        invalid_recipients = []
        for addr in raw_addresses:
            try:
                checksum_addr = web3.to_checksum_address(addr)
                valid_recipients.append(checksum_addr)
            except ValueError:
                invalid_recipients.append(addr)
        if invalid_recipients:
            log_error(f"Found {len(invalid_recipients)} invalid addresses (skipping them)")
            for addr in invalid_recipients[:5]:
                log_error(f"Invalid address: {addr}")
            if len(invalid_recipients) > 5:
                log_error(f"... and {len(invalid_recipients) - 5} more")
        if not valid_recipients:
            log_error("No valid recipient addresses found in recipients.txt")
            sys.exit(1)
        log_info(f"Loaded {len(valid_recipients)} valid recipient addresses")
    except Exception as error:
        log_error(f"Error loading recipients: {error}")
        sys.exit(1)

    network_gas_price = get_current_gas_price(web3)
    network_gas_gwei = web3.from_wei(network_gas_price, 'gwei')

    print(f"\n{Fore.CYAN}=== Transaction Configuration ==={Style.RESET_ALL}")
    try:
        num_transactions = int(input(f"{Fore.YELLOW}Number of transactions to send:{Style.RESET_ALL} "))
        min_phrs_amount = float(input(f"{Fore.YELLOW}Minimum PHRS per transaction (default: 0.001):{Style.RESET_ALL} ") or "0.001")
        max_phrs_amount = float(input(f"{Fore.YELLOW}Maximum PHRS per transaction (default: 0.002):{Style.RESET_ALL} ") or "0.002")
        wait_time_seconds = int(input(f"{Fore.YELLOW}Seconds between transactions (default: 30):{Style.RESET_ALL} ") or "30")
        gas_input = input(f"{Fore.YELLOW}Gas price in gwei (default: {network_gas_gwei:.2f}):{Style.RESET_ALL} ")
        gas_price_wei = web3.to_wei(float(gas_input) if gas_input else network_gas_gwei, 'gwei')
        gas_limit = int(input(f"{Fore.YELLOW}Gas limit (default: 21000):{Style.RESET_ALL} ") or "21000")
    except ValueError:
        log_error("Please enter valid numbers")
        sys.exit(1)

    with open("token.txt", "r") as token_file:
        api_token = token_file.readline().strip()
        if not api_token:
            log_error("API token is empty. Please add it to token.txt")
            sys.exit(1)

    task_id = 103

    api_headers = {
        "accept": "application/json, text/plain, */*",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "en-US,en;q=0.9,id;q=0.8",
        "authorization": f"Bearer {api_token}",
        "content-length": "0",
        "origin": "https://testnet.pharosnetwork.xyz",
        "referer": "https://testnet.pharosnetwork.xyz/",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
    }

    tx_stats = {
        "successful_txs": 0,
        "failed_txs": 0,
        "total_phrs_sent": 0,
    }

    current_nonce = web3.eth.get_transaction_count(wallet_address)
    log_info(f"Starting with nonce: {current_nonce}")

    print(f"\n{Fore.CYAN}=== Starting Transactions ==={Style.RESET_ALL}")
    start_time = time.time()

    for tx_index in range(num_transactions):
        try:
            recipient_address = random.choice(valid_recipients)
            tx_amount_phrs = round(random.uniform(min_phrs_amount, max_phrs_amount), 6)
            tx_amount_wei = web3.to_wei(tx_amount_phrs, 'ether')
            log_info(f"Preparing transaction to {recipient_address} with {tx_amount_phrs} PHRS")
            transaction = {
                'to': recipient_address,
                'value': tx_amount_wei,
                'gas': gas_limit,
                'gasPrice': gas_price_wei,
                'nonce': current_nonce + tx_index,
                'chainId': 688688,
            }
            signed_transaction = web3.eth.account.sign_transaction(transaction, private_key=private_key)
            log_info("Transaction signed successfully")
            tx_hash = web3.eth.send_raw_transaction(signed_transaction.rawTransaction)
            tx_hash_hex = web3.to_hex(tx_hash)
            log_transaction(tx_index+1, num_transactions, tx_amount_phrs, recipient_address, tx_hash_hex)
            receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            log_success(f"Transaction confirmed in block {receipt.blockNumber}")
            verification_url = (
                f"https://api.pharosnetwork.xyz/task/verify?"
                f"address={wallet_address}&task_id={task_id}&tx_hash={tx_hash_hex}"
            )
            response = requests.post(verification_url, headers=api_headers)
            if response.ok:
                log_success(f"Verification successful: {response.json()}")
                tx_stats["successful_txs"] += 1
                tx_stats["total_phrs_sent"] += tx_amount_phrs
            else:
                log_error(f"Verification failed: {response.status_code} | {response.text}")
                tx_stats["failed_txs"] += 1
        except Exception as error:
            log_error(f"Transaction error: {str(error)}")
            tx_stats["failed_txs"] += 1
        if tx_index < num_transactions - 1:
            remaining = num_transactions - (tx_index + 1)
            log_info(f"Waiting {wait_time_seconds} seconds before next transaction. Remaining: {remaining}")
            time.sleep(wait_time_seconds)

    elapsed_time = time.time() - start_time
    print(f"\n{Fore.CYAN}=== Transaction Summary ==={Style.RESET_ALL}")
    log_info(f"Total transactions: {num_transactions}")
    log_success(f"Successful transactions: {tx_stats['successful_txs']}")
    log_error(f"Failed transactions: {tx_stats['failed_txs']}")
    log_info(f"Total PHRS sent: {tx_stats['total_phrs_sent']:.6f}")
    log_info(f"Total time elapsed: {elapsed_time:.2f} seconds")
    final_balance_wei = web3.eth.get_balance(wallet_address)
    final_balance_phrs = web3.from_wei(final_balance_wei, 'ether')
    log_info(f"Final balance: {Fore.GREEN}{final_balance_phrs:.6f}{Style.RESET_ALL} PHRS")

if __name__ == "__main__":
    main()