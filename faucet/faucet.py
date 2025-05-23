import requests
import json
import time
import random
from eth_account import Account
from eth_account.messages import encode_defunct
from web3 import Web3
import os
import sys
from datetime import datetime
from colorama import Fore, Style, init
from dotenv import load_dotenv

load_dotenv()
init()

def print_banner():
    banner = f"""
{Fore.MAGENTA}╔════════════════════════════════════════════════════════════╗
║          🚀 PHAROS NETWORK FAUCET BOT 🚀                ║
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

def log_wallet(wallet_number, total_wallets, address):
    timestamp = datetime.now().strftime("%H:%M:%S")
    progress = f"[{wallet_number}/{total_wallets}]"
    print(f"{Fore.YELLOW}[{timestamp}] {progress}{Style.RESET_ALL} Created wallet: {Fore.MAGENTA}{address}{Style.RESET_ALL}")

def log_transfer(wallet_number, total_wallets, amount, from_addr, to_addr, tx_hash):
    timestamp = datetime.now().strftime("%H:%M:%S")
    progress = f"[{wallet_number}/{total_wallets}]"
    print(f"{Fore.YELLOW}[{timestamp}] {progress}{Style.RESET_ALL} Sent {Fore.CYAN}{amount}{Style.RESET_ALL} PHRS from {Fore.MAGENTA}{from_addr[:8]}...{Style.RESET_ALL} to {Fore.MAGENTA}{to_addr[:8]}...{Style.RESET_ALL}")
    print(f"  TX Hash: {Fore.BLUE}{tx_hash}{Style.RESET_ALL}")

# Network configuration from .env or fallback to defaults
RPC_ENDPOINT = os.getenv("RPC_ENDPOINT", "https://testnet.dplabs-internal.com")
FAUCET_API = os.getenv("FAUCET_API", "https://api.pharosnetwork.xyz/faucet/daily")
AUTH_API = os.getenv("AUTH_API", "https://api.pharosnetwork.xyz/user/login")
REFERRAL_CODE = os.getenv("REFERRAL_CODE", "7fD7mFucakbRirlH")
CHAIN_ID = int(os.getenv("CHAIN_ID", "688688"))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "10"))
DEFAULT_WAIT_TIME = float(os.getenv("DEFAULT_WAIT_TIME", "3"))
CLAIM_RETRIES = int(os.getenv("CLAIM_RETRIES", "3"))
MAX_GAS_LIMIT = int(os.getenv("MAX_GAS_LIMIT", "21000"))
WALLET_FILE = os.getenv("WALLET_FILE", "wallets.txt")

# HTTP request headers
REQUEST_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": "https://testnet.pharosnetwork.xyz",
    "Referer": "https://testnet.pharosnetwork.xyz/",
    "Sec-Ch-Ua": '"Chromium";v="137", "Not/A)Brand";v="24"',
    "Sec-Ch-Ua-Mobile": "?1",
    "Sec-Ch-Ua-Platform": '"Android"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36"
}

# Initialize web3 connection
web3 = Web3(Web3.HTTPProvider(RPC_ENDPOINT))

def load_proxies():
    """Load proxies from proxy.txt file"""
    try:
        if not os.path.exists("proxy.txt"):
            log_error("proxy.txt file not found, running without proxies")
            return []
        with open("proxy.txt", "r") as f:
            proxies = [line.strip() for line in f if line.strip()]
        if not proxies:
            log_error("proxy.txt file is empty, running without proxies")
        return proxies
    except Exception as e:
        log_error(f"Failed to read proxy.txt: {str(e)}")
        return []

class ProxyManager:
    """Manages proxy rotation"""
    def __init__(self):
        self.proxies = load_proxies()
        self.current_index = 0
    
    def get_next_proxy(self):
        """Get next proxy in rotation"""
        if not self.proxies:
            return None
        
        proxy = self.proxies[self.current_index]
        
        # Extract hostname for logging (avoid showing credentials)
        hostname = proxy.split('@')[-1] if '@' in proxy else proxy
        hostname = hostname.replace("proxy+", "") if hostname.startswith("proxy+") else hostname
        log_info(f"Using proxy: {hostname}")
        
        # Handle tunneling proxy format with proxy+ prefix
        if proxy.startswith("proxy+"):
            proxy_url = proxy.replace("proxy+", "")
            proxy_dict = {
                "http": proxy_url,
                "https": proxy_url  # Same URL for HTTPS tunneling
            }
        else:
            # Standard proxy format
            if not ('://' in proxy):
                proxy = f"http://{proxy}"
            proxy_dict = {
                "http": proxy,
                "https": proxy
            }
        
        self.current_index = (self.current_index + 1) % len(self.proxies)
        return proxy_dict

def save_wallets_to_file(wallets, filename=WALLET_FILE):
    """Save wallet addresses and private keys to a file"""
    try:
        with open(filename, "a") as f:
            for address, private_key in wallets:
                f.write(f"{address}:{private_key}\n")
        log_success(f"Saved {len(wallets)} wallets to {filename}")
        return True
    except Exception as e:
        log_error(f"Failed to save wallets to file: {str(e)}")
        return False

proxy_manager = ProxyManager()

def check_rpc_connection():
    """Verify connection to RPC endpoint"""
    try:
        if web3.is_connected():
            log_success(f"Connected to RPC: {RPC_ENDPOINT}")
            return True
        else:
            log_error(f"Failed to connect to RPC: {RPC_ENDPOINT}")
            return False
    except Exception as e:
        log_error(f"Error checking RPC connection: {str(e)}")
        return False

def generate_wallet():
    """Create a new Ethereum wallet"""
    account = Account.create()
    address = account.address
    private_key = account._private_key.hex()
    return address, private_key

def create_signature(private_key, message="pharos"):
    """Create a signature for authentication"""
    try:
        account = web3.eth.account.from_key(private_key)
        message_hash = encode_defunct(text=message)
        signed_message = web3.eth.account.sign_message(message_hash, private_key=private_key)
        return signed_message.signature.hex(), account.address
    except Exception as e:
        log_error(f"Failed to create signature: {str(e)}")
        return None, None

def login(address, signature, proxy=None, retries=3):
    """Login to get JWT token"""
    login_params = {
        "address": address,
        "signature": signature,
        "invite_code": REFERRAL_CODE
    }
    
    for attempt in range(retries):
        try:
            response = requests.post(
                AUTH_API, 
                headers=REQUEST_HEADERS, 
                params=login_params, 
                proxies=proxy,
                timeout=15
            )
            
            if response.status_code == 200 and response.json().get("code") == 0:
                log_success(f"Login successful for {address}")
                return response.json().get("data").get("jwt")
            
            error_msg = response.json() if response.status_code == 200 else f"HTTP {response.status_code}"
            log_error(f"Login failed (Attempt {attempt+1}/{retries}): {error_msg}")
        
        except Exception as e:
            log_error(f"Login error (Attempt {attempt+1}/{retries}): {str(e)}")
        
        if attempt < retries - 1:
            delay = random.uniform(2, 4)
            log_info(f"Waiting {delay:.1f} seconds before retry...")
            time.sleep(delay)
    
    log_error(f"Login failed after {retries} attempts")
    return None

def claim_faucet(address, token, proxy=None):
    """Claim tokens from faucet"""
    headers = REQUEST_HEADERS.copy()
    headers["Authorization"] = f"Bearer {token}"
    
    for attempt in range(CLAIM_RETRIES):
        try:
            response = requests.post(
                f"{FAUCET_API}?address={address}", 
                headers=headers, 
                proxies=proxy,
                timeout=15
            )
            
            if response.status_code == 200 and response.json().get("code") == 0:
                log_success(f"Successfully claimed faucet for {address}")
                return True
            
            error_msg = response.json() if response.status_code == 200 else f"HTTP {response.status_code}"
            log_error(f"Faucet claim failed (Attempt {attempt+1}/{CLAIM_RETRIES}): {error_msg}")
        
        except Exception as e:
            log_error(f"Faucet claim error (Attempt {attempt+1}/{CLAIM_RETRIES}): {str(e)}")
        
        if attempt < CLAIM_RETRIES - 1:
            delay = random.uniform(2, 4)
            log_info(f"Waiting {delay:.1f} seconds before retry...")
            time.sleep(delay)
    
    log_error(f"Faucet claim failed after {CLAIM_RETRIES} attempts")
    return False

def get_balance(address):
    """Get wallet balance"""
    try:
        balance_wei = web3.eth.get_balance(address)
        balance_phrs = web3.from_wei(balance_wei, "ether")
        return balance_wei, balance_phrs
    except Exception as e:
        log_error(f"Failed to get balance for {address}: {str(e)}")
        return 0, 0

def transfer_tokens(private_key, to_address, amount_wei):
    """Transfer tokens to destination address"""
    try:
        account = web3.eth.account.from_key(private_key)
        from_address = account.address
        
        nonce = web3.eth.get_transaction_count(from_address, "pending")
        gas_price = web3.eth.gas_price
        gas_limit = MAX_GAS_LIMIT
        
        tx = {
            "from": from_address,
            "to": to_address,
            "value": amount_wei,
            "gas": gas_limit,
            "gasPrice": gas_price,
            "nonce": nonce,
            "chainId": CHAIN_ID
        }
        
        signed_tx = web3.eth.account.sign_transaction(tx, private_key)
        
        # Handle different attribute names based on web3.py version
        if hasattr(signed_tx, 'rawTransaction'):
            raw_tx = signed_tx.rawTransaction
        elif hasattr(signed_tx, 'raw_transaction'):
            raw_tx = signed_tx.raw_transaction
        else:
            raise AttributeError("Could not find raw transaction data in signed transaction")
        
        tx_hash = web3.eth.send_raw_transaction(raw_tx)
        
        log_info("Waiting for transaction confirmation...")
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
        
        if receipt.status == 1:
            log_success(f"Transfer success! Tx Hash: {web3.to_hex(tx_hash)}")
            return web3.to_hex(tx_hash)
        else:
            log_error(f"Transfer failed for {from_address}")
            return None
    except Exception as e:
        log_error(f"Transfer error from {from_address}: {str(e)}")
        return None

def is_valid_address(address):
    """Validate Ethereum address format"""
    return web3.is_address(address)

def get_recipient_address():
    """Get recipient address from user input"""
    while True:
        address = input(f"{Fore.YELLOW}Enter recipient address (Ethereum format): {Style.RESET_ALL}").strip()
        if is_valid_address(address):
            return web3.to_checksum_address(address)
        log_error("Invalid address, please enter a valid Ethereum address")

def get_claim_count():
    """Get number of claims from user input"""
    while True:
        try:
            count = int(input(f"{Fore.YELLOW}Enter number of faucet claims to perform: {Style.RESET_ALL}"))
            if count <= 0:
                log_error("Claim count must be greater than 0")
                continue
            log_info(f"Will perform {count} faucet claims")
            return count
        except ValueError:
            log_error("Please enter a valid number")

def process_batch(recipient, batch_size=10, total_processed=0, total_claims=0):
    """Process a batch of wallets claiming and transferring tokens"""
    successful_claims = 0
    successful_transfers = 0
    wallets = []
    
    # Generate wallets
    log_info(f"Creating {batch_size} new wallets...")
    for i in range(batch_size):
        address, private_key = generate_wallet()
        wallets.append((address, private_key))
        log_wallet(i+1+total_processed, total_claims, address)
        time.sleep(0.1)  # Small delay between wallet creations
    
    # Save wallets to file
    save_wallets_to_file(wallets)
    
    # Handle each wallet
    for i, (address, private_key) in enumerate(wallets):
        wallet_idx = i+1+total_processed
        log_info(f"Processing wallet {wallet_idx}/{total_claims}: {address}")
        
        # Create signature
        signature, recovered_address = create_signature(private_key)
        if not signature or recovered_address.lower() != address.lower():
            log_error(f"Signature creation failed for {address}, skipping")
            continue
            
        # Get proxy and authenticate
        proxy = proxy_manager.get_next_proxy()
        jwt_token = login(address, signature, proxy)
        if not jwt_token:
            log_error(f"Authentication failed for {address}, skipping")
            continue
            
        # Claim from faucet
        if claim_faucet(address, jwt_token, proxy):
            successful_claims += 1
            # Wait for transaction to be mined
            wait_time = random.uniform(10, 15)
            log_info(f"Waiting {wait_time:.1f} seconds for faucet transaction to be processed...")
            time.sleep(wait_time)
            
            # Check balance and transfer
            balance_wei, balance_phrs = get_balance(address)
            log_info(f"Balance for {address}: {balance_phrs:.4f} PHRS")
            
            if balance_wei == 0:
                log_error(f"Zero balance for {address}, skipping transfer")
                continue
                
            # Calculate amount to transfer (total - gas fee)
            gas_limit = MAX_GAS_LIMIT
            gas_price = web3.eth.gas_price
            gas_fee = gas_limit * gas_price
            
            if balance_wei <= gas_fee:
                log_error(f"Insufficient balance for gas in {address}, skipping transfer")
                continue
                
            transfer_amount = balance_wei - gas_fee
            transfer_amount_phrs = web3.from_wei(transfer_amount, "ether")
            
            tx_hash = transfer_tokens(private_key, recipient, transfer_amount)
            if tx_hash:
                successful_transfers += 1
                log_transfer(wallet_idx, total_claims, transfer_amount_phrs, address, recipient, tx_hash)
        
        # Add delay between operations
        if i < batch_size - 1:
            delay = random.uniform(2, 5)
            log_info(f"Waiting {delay:.1f} seconds before next wallet...")
            time.sleep(delay)
    
    return successful_claims, successful_transfers

def main():
    """Main function to run the bot"""
    print_banner()
    
    if not check_rpc_connection():
        log_error("Cannot continue due to RPC connection issues")
        return
    
    recipient = get_recipient_address()
    total_claims = get_claim_count()
    
    log_info(f"Starting process for {total_claims} claims and transfers to {recipient}")
    
    total_successful_claims = 0
    total_successful_transfers = 0
    processed = 0
    
    print(f"\n{Fore.CYAN}=== Starting Faucet Claims ==={Style.RESET_ALL}")
    start_time = time.time()
    
    while processed < total_claims:
        batch_size = min(BATCH_SIZE, total_claims - processed)
        log_info(f"Processing batch {processed//BATCH_SIZE + 1} ({batch_size} wallets)...")
        claims, transfers = process_batch(recipient, batch_size, processed, total_claims)
        
        total_successful_claims += claims
        total_successful_transfers += transfers
        processed += batch_size
        
        if processed < total_claims:
            delay = random.uniform(5, 8)
            log_info(f"Waiting {delay:.1f} seconds before next batch. Remaining: {total_claims - processed}")
            time.sleep(delay)
    
    # Summary
    elapsed_time = time.time() - start_time
    print(f"\n{Fore.CYAN}=== Faucet Summary ==={Style.RESET_ALL}")
    log_info(f"Total wallets created: {total_claims}")
    log_success(f"Successful claims: {total_successful_claims}/{total_claims}")
    log_success(f"Successful transfers: {total_successful_transfers}/{total_claims}")
    log_info(f"Total time elapsed: {elapsed_time:.2f} seconds")
    log_success(f"Process completed! All wallets saved to {WALLET_FILE}")

if __name__ == "__main__":
    main()