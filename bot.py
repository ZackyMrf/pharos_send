import random
import time
import requests
import os
import sys
import json
import datetime
from datetime import datetime
from web3 import Web3, Account
from colorama import Fore, Style, init
import shutil  # For terminal width detection
from eth_account.messages import encode_defunct
import config  # Import configuration

init()

class ProxyManager:
    """Manager for proxy rotation and formatting"""
    def __init__(self, proxy_list=None):
        self.proxies = proxy_list or []
        self.current_index = 0
        self.last_rotation = time.time()
        self.rotation_interval = 60  # seconds between proxy rotations
    
    def has_proxies(self):
        return len(self.proxies) > 0
    
    def get_current_proxy(self):
        if not self.has_proxies():
            return None
        
        return self.proxies[self.current_index]
    
    def rotate_proxy(self, force=False):
        if not self.has_proxies():
            return None
            
        current_time = time.time()
        if force or (current_time - self.last_rotation) > self.rotation_interval:
            self.current_index = (self.current_index + 1) % len(self.proxies)
            self.last_rotation = current_time
            log_info(f"Rotated to proxy #{self.current_index + 1}: {self.proxies[self.current_index]}")
        
        return self.get_current_proxy()
    
    def format_for_requests(self):
        """Format current proxy string for requests library"""
        proxy_str = self.get_current_proxy()
        if not proxy_str:
            return None
        
        # Handle tunneling proxy format with proxy+ prefix
        if proxy_str.startswith("proxy+"):
            proxy_url = proxy_str.replace("proxy+", "")
            return {
                'http': proxy_url,
                'https': proxy_url  # Same URL for HTTPS tunneling
            }
            
        # Add default protocol if missing
        if not ('://' in proxy_str):
            proxy_str = f"http://{proxy_str}"
            
        return {
            'http': proxy_str,
            'https': proxy_str
        }
        
    def format_for_web3(self):
        """Format current proxy string for Web3 connection"""
        proxy_str = self.get_current_proxy()
        if not proxy_str:
            return None
            
        # Add default protocol if missing
        if not ('://' in proxy_str):
            proxy_str = f"http://{proxy_str}"
            
        # Extract components
        if '@' in proxy_str:
            # proxy has authentication
            auth_part, server_part = proxy_str.split('@', 1)
            protocol = auth_part.split('://', 1)[0] if '://' in auth_part else 'http'
            
            # Format for web3 provider
            return {
                'http': proxy_str,
                'https': proxy_str.replace('http://', 'https://') if proxy_str.startswith('http://') else proxy_str
            }
        else:
            # proxy without authentication
            return {
                'http': proxy_str,
                'https': proxy_str.replace('http://', 'https://') if proxy_str.startswith('http://') else proxy_str
            }

def print_banner():
    # Get terminal width
    terminal_width = shutil.get_terminal_size().columns
    
    banner = f"""
{Fore.MAGENTA}{'═' * (terminal_width - 2)}
║{' ' * (terminal_width - 4)}║
║{Fore.YELLOW}  🚀 PHAROS NETWORK TRANSACTION BOT 🚀  {Fore.MAGENTA}{' ' * (terminal_width - 44)}║
║{Fore.CYAN}             Version 2.3 by Mrf           {Fore.MAGENTA}{' ' * (terminal_width - 44)}║
║{' ' * (terminal_width - 4)}║
{'═' * (terminal_width - 2)}{Style.RESET_ALL}
"""
    print(banner)

def log_info(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"{Fore.BLUE}[{timestamp}] [INFO]{Style.RESET_ALL} ℹ️  {message}")

def log_success(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"{Fore.GREEN}[{timestamp}] [SUCCESS]{Style.RESET_ALL} ✅ {message}")

def log_error(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"{Fore.RED}[{timestamp}] [ERROR]{Style.RESET_ALL} ❌ {message}")

def log_transaction(tx_number, total_txs, tx_amount, recipient_addr, tx_hash):
    timestamp = datetime.now().strftime("%H:%M:%S")
    progress = f"[{tx_number}/{total_txs}]"
    progress_bar = create_progress_bar(tx_number, total_txs)
    
    print(f"\n{Fore.YELLOW}[{timestamp}] {progress} {progress_bar}{Style.RESET_ALL}")
    print(f"  {Fore.CYAN}Amount:{Style.RESET_ALL} {tx_amount} PHRS")
    print(f"  {Fore.CYAN}To:{Style.RESET_ALL} {Fore.MAGENTA}{recipient_addr}{Style.RESET_ALL}")
    print(f"  {Fore.CYAN}Hash:{Style.RESET_ALL} {Fore.BLUE}{tx_hash}{Style.RESET_ALL}")
    print(f"  {Fore.CYAN}Explorer:{Style.RESET_ALL} {config.EXPLORER}{tx_hash}")

def create_progress_bar(current, total, bar_length=20):
    progress = min(1.0, current / total)
    arrow = '█' * int(round(progress * bar_length))
    spaces = ' ' * (bar_length - len(arrow))
    
    # Color the progress bar based on completion percentage
    if progress < 0.3:
        color = Fore.RED
    elif progress < 0.7:
        color = Fore.YELLOW
    else:
        color = Fore.GREEN
        
    return f"{color}[{arrow}{spaces}] {int(progress * 100)}%{Style.RESET_ALL}"

def check_file_exists(filename):
    if not os.path.exists(filename):
        log_error(f"File '{filename}' not found. Please create it.")
        return False
    return True

def load_proxies(filename="proxy.txt"):
    """Load proxies from file"""
    if not os.path.exists(filename):
        log_info(f"Proxy file {filename} not found, continuing without proxies")
        return []
    
    with open(filename, "r") as file:
        proxies = [line.strip() for line in file if line.strip()]
    
    if proxies:
        log_success(f"Loaded {len(proxies)} proxies from {filename}")
    else:
        log_info(f"No proxies found in {filename}, continuing without proxies")
    
    return proxies

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

def print_section_header(title):
    terminal_width = shutil.get_terminal_size().columns
    padding = max(0, (terminal_width - len(title) - 4) // 2)
    print(f"\n{Fore.CYAN}{'═' * padding} {title} {'═' * padding}{Style.RESET_ALL}\n")

def print_summary_box(stats, elapsed_time, final_balance):
    terminal_width = shutil.get_terminal_size().columns
    box_width = min(60, terminal_width - 4)
    
    print(f"\n{Fore.CYAN}{'═' * box_width}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}║{Fore.YELLOW} TRANSACTION SUMMARY {' ' * (box_width - 21)}{Fore.CYAN}║{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'═' * box_width}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}║{Style.RESET_ALL} Total transactions:     {Fore.WHITE}{stats['successful_txs'] + stats['failed_txs']}{' ' * (box_width - 29)}{Fore.CYAN}║{Style.RESET_ALL}")
    print(f"{Fore.CYAN}║{Style.RESET_ALL} Successful transactions: {Fore.GREEN}{stats['successful_txs']}{' ' * (box_width - 29)}{Fore.CYAN}║{Style.RESET_ALL}")
    print(f"{Fore.CYAN}║{Style.RESET_ALL} Failed transactions:     {Fore.RED}{stats['failed_txs']}{' ' * (box_width - 29)}{Fore.CYAN}║{Style.RESET_ALL}")
    print(f"{Fore.CYAN}║{Style.RESET_ALL} Total PHRS sent:         {Fore.YELLOW}{stats['total_phrs_sent']:.6f}{' ' * (box_width - 36)}{Fore.CYAN}║{Style.RESET_ALL}")
    print(f"{Fore.CYAN}║{Style.RESET_ALL} Time elapsed:            {elapsed_time:.2f} seconds{' ' * (box_width - 33)}{Fore.CYAN}║{Style.RESET_ALL}")
    print(f"{Fore.CYAN}║{Style.RESET_ALL} Final balance:           {Fore.GREEN}{final_balance:.6f}{Style.RESET_ALL} PHRS{' ' * (box_width - 37)}{Fore.CYAN}║{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'═' * box_width}{Style.RESET_ALL}")

def load_private_keys(filename="private_key.txt"):
    """Load all private keys from file"""
    if not os.path.exists(filename):
        log_error(f"File {filename} not found")
        return []
    
    with open(filename, "r") as file:
        keys = [line.strip() for line in file if line.strip()]
    
    if not keys:
        log_error(f"No private keys found in {filename}")
        return []
    
    return keys

def display_wallets(web3, private_keys):
    """Display all available wallets with addresses and balances"""
    print(f"\n{Fore.CYAN}{'═' * 70}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}║ {'#':^4} │ {'Wallet Address':^42} │ {'Balance':^15} ║{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'═' * 70}{Style.RESET_ALL}")
    
    for idx, key in enumerate(private_keys):
        try:
            account = Account.from_key(key)
            address = account.address
            balance_wei = web3.eth.get_balance(address)
            balance = web3.from_wei(balance_wei, 'ether')
            print(f"{Fore.CYAN}║ {idx+1:^4} │ {Fore.YELLOW}{address}{Fore.CYAN} │ {Fore.GREEN}{balance:.6f} PHRS{Fore.CYAN} ║{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.CYAN}║ {idx+1:^4} │ {Fore.RED}Invalid private key{Fore.CYAN} │ {Fore.RED}Error{Fore.CYAN}        ║{Style.RESET_ALL}")
    
    print(f"{Fore.CYAN}{'═' * 70}{Style.RESET_ALL}")

def sign_message(web3, private_key, message="pharos"):
    """Create signature for authentication"""
    account = web3.eth.account.from_key(private_key)
    address = account.address
    message_hash = encode_defunct(text=message)
    signed_message = web3.eth.account.sign_message(message_hash, private_key=private_key)
    return signed_message.signature.hex(), address

def login_with_signature(web3, private_key, proxy_manager=None):
    """Get JWT token from API using signature"""
    signature, address = sign_message(web3, private_key)
    log_info(f"Generated signature for {address}")
    
    url = f"https://api.pharosnetwork.xyz/user/login?address={address}&signature={signature}"
    headers = {
        "Origin": "https://testnet.pharosnetwork.xyz", 
        "Referer": "https://testnet.pharosnetwork.xyz/"
    }
    
    # Prepare proxy if available
    proxies = None
    if proxy_manager and proxy_manager.has_proxies():
        proxies = proxy_manager.format_for_requests()
        log_info(f"Using proxy for API login: {proxy_manager.get_current_proxy()}")
    
    try:
        response = requests.post(url, headers=headers, proxies=proxies, timeout=30)
        if response.ok:
            data = response.json()
            if data.get("code") == 0:
                jwt_token = data.get("data", {}).get("jwt")
                log_success(f"Login successful, received JWT token")
                return jwt_token
        log_error(f"Login failed: {response.status_code} | {response.text}")
        
        # Rotate proxy on failure if we're using proxies
        if proxy_manager and proxy_manager.has_proxies():
            proxy_manager.rotate_proxy(force=True)
            
        return None
    except Exception as e:
        log_error(f"Login error: {str(e)}")
        
        # Rotate proxy on failure if we're using proxies
        if proxy_manager and proxy_manager.has_proxies():
            proxy_manager.rotate_proxy(force=True)
            
        return None

def get_profile_info(address, jwt_token, proxy_manager=None):
    """Get user profile information from Pharos API"""
    url = f"https://api.pharosnetwork.xyz/user/profile?address={address}"
    
    headers = {
        'Authorization': f'Bearer {jwt_token}',
        'wallet-address': address,
        'Origin': 'https://testnet.pharosnetwork.xyz',
        'Referer': 'https://testnet.pharosnetwork.xyz/'
    }
    
    # Prepare proxy if available
    proxies = None
    if proxy_manager and proxy_manager.has_proxies():
        proxies = proxy_manager.format_for_requests()
    
    try:
        response = requests.get(url, headers=headers, proxies=proxies, timeout=30)
        if response.ok:
            data = response.json()
            points = data.get("data", {}).get("user_info", {}).get("TotalPoints", 0)
            log_info(f"Current points: {Fore.GREEN}{points}{Style.RESET_ALL}")
            return data
        else:
            log_error(f"Failed to get profile: {response.status_code} | {response.text}")
            
            # Rotate proxy on failure
            if proxy_manager and proxy_manager.has_proxies():
                proxy_manager.rotate_proxy(force=True)
                
            return None
    except Exception as e:
        log_error(f"Error getting profile: {str(e)}")
        
        # Rotate proxy on failure
        if proxy_manager and proxy_manager.has_proxies():
            proxy_manager.rotate_proxy(force=True)
            
        return None

def daily_check_in(address, jwt_token, proxy_manager=None):
    """Perform daily check-in to get additional points"""
    log_info("Attempting daily check-in...")
    
    # Get current check-in status
    status_url = f"https://api.pharosnetwork.xyz/sign/status?address={address}"
    headers = {
        'Authorization': f'Bearer {jwt_token}',
        'wallet-address': address,
        'Origin': 'https://testnet.pharosnetwork.xyz',
        'Referer': 'https://testnet.pharosnetwork.xyz/'
    }
    
    # Prepare proxy if available
    proxies = None
    if proxy_manager and proxy_manager.has_proxies():
        proxies = proxy_manager.format_for_requests()
    
    try:
        response = requests.get(status_url, headers=headers, proxies=proxies, timeout=30)
        if not response.ok:
            log_error(f"Failed to get check-in status: {response.status_code} | {response.text}")
            
            # Rotate proxy on failure
            if proxy_manager and proxy_manager.has_proxies():
                proxy_manager.rotate_proxy(force=True)
                
            return False
            
        status_str = response.json().get("data", {}).get("status", "")
        day_of_week = datetime.now().weekday()
        
        if len(status_str) != 7:
            log_error("Invalid status format received")
            return False
            
        if status_str[day_of_week] == "2":  # Can check-in
            check_in_url = f"https://api.pharosnetwork.xyz/sign/in?address={address}"
            checkin_response = requests.post(check_in_url, headers=headers, proxies=proxies, timeout=30)
            
            if checkin_response.ok:
                log_success("Daily check-in successful!")
                return True
            else:
                log_error(f"Check-in failed: {checkin_response.status_code} | {checkin_response.text}")
                
                # Rotate proxy on failure
                if proxy_manager and proxy_manager.has_proxies():
                    proxy_manager.rotate_proxy(force=True)
                    
                return False
        elif status_str[day_of_week] == "0":
            log_info("Already checked in today")
            return True
        else:
            log_info("Check-in not available today")
            return False
            
    except Exception as e:
        log_error(f"Error during check-in: {str(e)}")
        
        # Rotate proxy on failure
        if proxy_manager and proxy_manager.has_proxies():
            proxy_manager.rotate_proxy(force=True)
            
        return False

def swap_tokens(web3, private_key, amount_phrs):
    """Swap PHRS for USDC using Pharos DEX"""
    log_info(f"Preparing to swap {amount_phrs} PHRS for USDC...")
    
    try:
        account = web3.eth.account.from_key(private_key)
        address = account.address
        amount_in_wei = web3.to_wei(amount_phrs, 'ether')
        
        # Get contracts with checksummed addresses
        token = web3.eth.contract(
            address=web3.to_checksum_address(config.WPHRS_ADDRESS), 
            abi=config.ERC20_ABI
        )
        router = web3.eth.contract(
            address=web3.to_checksum_address(config.SWAP_ROUTER_ADDRESS), 
            abi=config.SWAP_ROUTER_ABI
        )
        
        # Get current nonce
        nonce = web3.eth.get_transaction_count(address)
        
        # First approve tokens to router with checksummed address
        approve_tx = token.functions.approve(
            web3.to_checksum_address(config.SWAP_ROUTER_ADDRESS), 
            amount_in_wei
        ).build_transaction({
            'from': address,
            'nonce': nonce,
            'gas': 100000,
            'gasPrice': web3.eth.gas_price,
            'chainId': config.CHAIN_ID
        })
        
        signed_approve = web3.eth.account.sign_transaction(approve_tx, private_key=private_key)
        
        # Handle different web3.py versions
        if hasattr(signed_approve, 'rawTransaction'):
            raw_tx = signed_approve.rawTransaction
        elif hasattr(signed_approve, 'raw_transaction'):
            raw_tx = signed_approve.raw_transaction
        else:
            raise AttributeError("Could not find raw transaction data in signed transaction")
            
        tx_hash = web3.eth.send_raw_transaction(raw_tx)
        log_info(f"Approval transaction sent: {web3.to_hex(tx_hash)}")
        
        # Wait for approval to be mined
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
        if receipt.status != 1:
            log_error("Approval transaction failed")
            return None
            
        log_success("Token approval confirmed")
        
        # Prepare swap parameters with checksummed addresses
        swap_params = {
            "tokenIn": web3.to_checksum_address(config.WPHRS_ADDRESS),
            "tokenOut": web3.to_checksum_address(config.USDC_ADDRESS),
            "fee": 500,  # 0.05%
            "recipient": address,
            "amountIn": amount_in_wei,
            "amountOutMinimum": 0,
            "sqrtPriceLimitX96": 0
        }
        
        # Build and sign swap transaction
        swap_tx = router.functions.exactInputSingle(
            swap_params
        ).build_transaction({
            'from': address,
            'nonce': nonce + 1,
            'gas': 300000,
            'gasPrice': web3.eth.gas_price,
            'chainId': config.CHAIN_ID
        })
        
        signed_swap = web3.eth.account.sign_transaction(swap_tx, private_key=private_key)
        
        # Handle different web3.py versions
        if hasattr(signed_swap, 'rawTransaction'):
            raw_swap_tx = signed_swap.rawTransaction
        elif hasattr(signed_swap, 'raw_transaction'):
            raw_swap_tx = signed_swap.raw_transaction
        else:
            raise AttributeError("Could not find raw transaction data in signed transaction")
            
        swap_tx_hash = web3.eth.send_raw_transaction(raw_swap_tx)
        log_info(f"Swap transaction sent: {web3.to_hex(swap_tx_hash)}")
        
        # Wait for swap to be mined
        swap_receipt = web3.eth.wait_for_transaction_receipt(swap_tx_hash)
        if swap_receipt.status != 1:
            log_error("Swap transaction failed")
            return None
            
        log_success(f"Successfully swapped {amount_phrs} PHRS for USDC!")
        return web3.to_hex(swap_tx_hash)
        
    except Exception as e:
        log_error(f"Error during token swap: {str(e)}")
        return None

def add_liquidity(web3, private_key, amount_phrs):
    """Add liquidity to the PHRS-USDC pool"""
    log_info(f"Preparing to add liquidity with {amount_phrs} PHRS...")
    
    try:
        account = web3.eth.account.from_key(private_key)
        address = account.address
        amount_in_wei = web3.to_wei(amount_phrs, 'ether')
        
        # Get contracts with checksummed addresses
        token0 = web3.eth.contract(
            address=web3.to_checksum_address(config.WPHRS_ADDRESS), 
            abi=config.ERC20_ABI
        )
        token1 = web3.eth.contract(
            address=web3.to_checksum_address(config.USDC_ADDRESS), 
            abi=config.ERC20_ABI
        )
        position_manager = web3.eth.contract(
            address=web3.to_checksum_address(config.POSITION_MANAGER_ADDRESS), 
            abi=config.POSITION_MANAGER_ABI
        )
        
        # Get current nonce
        nonce = web3.eth.get_transaction_count(address)
        
        # First approve tokens to position manager with checksummed address
        approve_tx0 = token0.functions.approve(
            web3.to_checksum_address(config.POSITION_MANAGER_ADDRESS), 
            amount_in_wei
        ).build_transaction({
            'from': address,
            'nonce': nonce,
            'gas': 100000,
            'gasPrice': web3.eth.gas_price,
            'chainId': config.CHAIN_ID
        })
        
        signed_approve0 = web3.eth.account.sign_transaction(approve_tx0, private_key=private_key)
        
        # Handle different web3.py versions
        if hasattr(signed_approve0, 'rawTransaction'):
            raw_tx0 = signed_approve0.rawTransaction
        elif hasattr(signed_approve0, 'raw_transaction'):
            raw_tx0 = signed_approve0.raw_transaction
        else:
            raise AttributeError("Could not find raw transaction data in signed transaction")
            
        tx_hash0 = web3.eth.send_raw_transaction(raw_tx0)
        log_info(f"Token0 approval transaction sent: {web3.to_hex(tx_hash0)}")
        
        # Wait for approval to be mined
        receipt0 = web3.eth.wait_for_transaction_receipt(tx_hash0)
        if receipt0.status != 1:
            log_error("Token0 approval transaction failed")
            return None
            
        log_success("Token0 approval confirmed")
        
        # Approve token1 with checksummed address
        approve_tx1 = token1.functions.approve(
            web3.to_checksum_address(config.POSITION_MANAGER_ADDRESS), 
            amount_in_wei  # Use same amount for simplicity
        ).build_transaction({
            'from': address,
            'nonce': nonce + 1,
            'gas': 100000,
            'gasPrice': web3.eth.gas_price,
            'chainId': config.CHAIN_ID
        })
        
        signed_approve1 = web3.eth.account.sign_transaction(approve_tx1, private_key=private_key)
        
        # Handle different web3.py versions
        if hasattr(signed_approve1, 'rawTransaction'):
            raw_tx1 = signed_approve1.rawTransaction
        elif hasattr(signed_approve1, 'raw_transaction'):
            raw_tx1 = signed_approve1.raw_transaction
        else:
            raise AttributeError("Could not find raw transaction data in signed transaction")
            
        tx_hash1 = web3.eth.send_raw_transaction(raw_tx1)
        log_info(f"Token1 approval transaction sent: {web3.to_hex(tx_hash1)}")
        
        # Wait for approval to be mined
        receipt1 = web3.eth.wait_for_transaction_receipt(tx_hash1)
        if receipt1.status != 1:
            log_error("Token1 approval transaction failed")
            return None
            
        log_success("Token1 approval confirmed")
        
        # Prepare liquidity parameters with checksummed addresses
        current_timestamp = int(time.time())
        deadline = current_timestamp + 600  # 10 minutes from now
        
        mint_params = {
            "token0": web3.to_checksum_address(config.WPHRS_ADDRESS),
            "token1": web3.to_checksum_address(config.USDC_ADDRESS),
            "fee": 3000,  # 0.3% fee tier
            "tickLower": -60000,  # Wide range
            "tickUpper": 60000,   # Wide range
            "amount0Desired": amount_in_wei,
            "amount1Desired": amount_in_wei,  # Using same amount for both tokens
            "amount0Min": 0,
            "amount1Min": 0,
            "recipient": address,
            "deadline": deadline
        }
        
        # Build and sign mint transaction
        mint_tx = position_manager.functions.mint(
            mint_params
        ).build_transaction({
            'from': address,
            'nonce': nonce + 2,
            'gas': 500000,
            'gasPrice': web3.eth.gas_price,
            'chainId': config.CHAIN_ID
        })
        
        signed_mint = web3.eth.account.sign_transaction(mint_tx, private_key=private_key)
        
        # Handle different web3.py versions
        if hasattr(signed_mint, 'rawTransaction'):
            raw_mint_tx = signed_mint.rawTransaction
        elif hasattr(signed_mint, 'raw_transaction'):
            raw_mint_tx = signed_mint.raw_transaction
        else:
            raise AttributeError("Could not find raw transaction data in signed transaction")
            
        mint_tx_hash = web3.eth.send_raw_transaction(raw_mint_tx)
        log_info(f"Liquidity addition transaction sent: {web3.to_hex(mint_tx_hash)}")
        
        # Wait for transaction to be mined
        mint_receipt = web3.eth.wait_for_transaction_receipt(mint_tx_hash)
        if mint_receipt.status != 1:
            log_error("Liquidity addition transaction failed")
            return None
            
        log_success(f"Successfully added liquidity with {amount_phrs} PHRS!")
        return web3.to_hex(mint_tx_hash)
        
    except Exception as e:
        log_error(f"Error during liquidity addition: {str(e)}")
        return None

def process_wallet(web3, private_key, valid_recipients, tx_config, wallet_index, total_wallets, proxy_manager=None):
    """Process a single wallet with the given configuration"""
    wallet = Account.from_key(private_key)
    wallet_address = wallet.address
    
    print_section_header(f"PROCESSING WALLET {wallet_index+1}/{total_wallets}: {wallet_address}")
    log_info(f"Wallet address: {Fore.GREEN}{wallet_address}{Style.RESET_ALL}")
    
    balance_wei = web3.eth.get_balance(wallet_address)
    balance_phrs = web3.from_wei(balance_wei, 'ether')
    log_info(f"Current balance: {Fore.GREEN}{balance_phrs:.6f}{Style.RESET_ALL} PHRS")
    
    # Get JWT token from API using signature auth
    jwt_token = login_with_signature(web3, private_key, proxy_manager)
    if not jwt_token:
        log_error("Failed to obtain JWT token for API authentication")
        return None
        
    # Get user profile and check-in daily
    profile = get_profile_info(wallet_address, jwt_token, proxy_manager)
    daily_check_in(wallet_address, jwt_token, proxy_manager)
    
    # Use JWT token for authentication
    api_headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "en-US,en;q=0.9,id;q=0.8",
        "Authorization": f"Bearer {jwt_token}",
        "wallet-address": wallet_address,
        "origin": "https://testnet.pharosnetwork.xyz",
        "referer": "https://testnet.pharosnetwork.xyz/",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    tx_stats = {
        "successful_txs": 0,
        "failed_txs": 0,
        "total_phrs_sent": 0,
    }

    current_nonce = web3.eth.get_transaction_count(wallet_address)
    log_info(f"Starting with nonce: {current_nonce}")

    print_section_header("STARTING TRANSACTIONS")
    start_time = time.time()
    
    # Regular transactions
    num_transactions = tx_config["num_transactions"]
    min_phrs_amount = tx_config["min_phrs_amount"]
    max_phrs_amount = tx_config["max_phrs_amount"]
    wait_time_seconds = tx_config["wait_time_seconds"]
    gas_price_wei = tx_config["gas_price_wei"]
    gas_limit = tx_config["gas_limit"]
    task_id = tx_config["task_id"]

    # Process transactions with retry mechanism
    for tx_index in range(num_transactions):
        # Add retry mechanism
        max_retries = 3  # Maximum number of retry attempts
        retry_count = 0
        success = False
        
        while not success and retry_count < max_retries:
            try:
                if retry_count > 0:
                    log_info(f"Retrying transaction {tx_index+1}/{num_transactions} (Attempt {retry_count+1}/{max_retries})")
                    # Add exponential backoff for retries
                    backoff_time = retry_count * 5
                    log_info(f"Waiting {backoff_time} seconds before retry...")
                    time.sleep(backoff_time)
                
                recipient_address = random.choice(valid_recipients)
                tx_amount_phrs = round(random.uniform(min_phrs_amount, max_phrs_amount), 6)
                tx_amount_wei = web3.to_wei(tx_amount_phrs, 'ether')
                log_info(f"Preparing transaction to {recipient_address} with {tx_amount_phrs} PHRS")
                
                # Get fresh nonce for retry attempts
                if retry_count > 0:
                    current_nonce = web3.eth.get_transaction_count(wallet_address)
                    log_info(f"Updated nonce to: {current_nonce + tx_index}")
                
                transaction = {
                    'to': recipient_address,
                    'value': tx_amount_wei,
                    'gas': gas_limit,
                    'gasPrice': gas_price_wei,
                    'nonce': current_nonce + tx_index,
                    'chainId': config.CHAIN_ID,
                }
                signed_transaction = web3.eth.account.sign_transaction(transaction, private_key=private_key)
                log_info("Transaction signed successfully")
                
                # Fix for different web3.py versions (handle both attribute names)
                raw_tx = None
                if hasattr(signed_transaction, 'rawTransaction'):
                    raw_tx = signed_transaction.rawTransaction
                elif hasattr(signed_transaction, 'raw_transaction'):
                    raw_tx = signed_transaction.raw_transaction
                else:
                    raise AttributeError("Could not find raw transaction data in signed transaction object")
                    
                tx_hash = web3.eth.send_raw_transaction(raw_tx)
                tx_hash_hex = web3.to_hex(tx_hash)
                log_transaction(tx_index+1, num_transactions, tx_amount_phrs, recipient_address, tx_hash_hex)
                
                # Wait for transaction confirmation with timeout and retry
                receipt = None
                receipt_retries = 2
                for receipt_attempt in range(receipt_retries):
                    try:
                        receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
                        break
                    except Exception as receipt_error:
                        if receipt_attempt < receipt_retries - 1:
                            log_error(f"Error waiting for receipt: {str(receipt_error)}. Retrying...")
                            time.sleep(10)
                        else:
                            raise
                
                if receipt.status != 1:
                    raise Exception(f"Transaction failed with status {receipt.status}")
                    
                log_success(f"Transaction confirmed in block {receipt.blockNumber}")
                
                # Use proxy for verification if available
                proxies = None
                if proxy_manager and proxy_manager.has_proxies():
                    proxies = proxy_manager.format_for_requests()
                    
                verification_url = (
                    f"https://api.pharosnetwork.xyz/task/verify?"
                    f"address={wallet_address}&task_id={task_id}&tx_hash={tx_hash_hex}"
                )
                verify_retries = 2
                for verify_attempt in range(verify_retries):
                    try:
                        response = requests.post(verification_url, headers=api_headers, proxies=proxies, timeout=30)
                        if response.ok:
                            response_json = response.json()
                            log_success(f"Verification successful: {response_json}")
                            tx_stats["successful_txs"] += 1
                            tx_stats["total_phrs_sent"] += tx_amount_phrs
                            success = True
                            break
                        else:
                            log_error(f"Verification failed: {response.status_code} | {response.text}")
                            if verify_attempt < verify_retries - 1:
                                log_info(f"Retrying verification...")
                                time.sleep(5)
                            else:
                                tx_stats["failed_txs"] += 1
                                
                        # Rotate proxy on verification failure
                        if proxy_manager and proxy_manager.has_proxies():
                            proxy_manager.rotate_proxy(force=True)
                    except Exception as verify_error:
                        log_error(f"Verification error: {str(verify_error)}")
                        if verify_attempt < verify_retries - 1:
                            log_info(f"Retrying verification...")
                            time.sleep(5)
                        else:
                            tx_stats["failed_txs"] += 1
                
                # Mark as success if we got this far
                if not success:
                    success = True
                    
            except Exception as error:
                log_error(f"Transaction error: {str(error)}")
                retry_count += 1
                if retry_count >= max_retries:
                    log_error(f"Failed to complete transaction after {max_retries} attempts")
                    tx_stats["failed_txs"] += 1
                # Rotate proxy on error if available
                if proxy_manager and proxy_manager.has_proxies():
                    proxy_manager.rotate_proxy(force=True)
            
            if success:
                break
        
        if tx_index < num_transactions - 1:
            remaining = num_transactions - (tx_index + 1)
            log_info(f"Waiting {wait_time_seconds} seconds before next transaction. Remaining: {remaining}")
            time.sleep(wait_time_seconds)

    # Perform token swaps if enabled
    perform_swaps = tx_config["perform_swaps"]
    num_swaps = tx_config["num_swaps"]
    
    if perform_swaps and num_swaps > 0:
        print_section_header("TOKEN SWAPS")
        for swap_index in range(num_swaps):
            swap_amount = round(random.uniform(min_phrs_amount, max_phrs_amount), 6)
            log_info(f"Swap #{swap_index + 1}/{num_swaps}: {swap_amount} PHRS to USDC")
            swap_tx_hash = swap_tokens(web3, private_key, swap_amount)
            if swap_tx_hash:
                log_success(f"Swap transaction completed: {swap_tx_hash}")
            if swap_index < num_swaps - 1:
                wait_time = wait_time_seconds // 2
                log_info(f"Waiting {wait_time} seconds before next swap...")
                time.sleep(wait_time)
                
    # Add liquidity if enabled
    add_liquidity_pools = tx_config["add_liquidity_pools"]
    num_lp_adds = tx_config["num_lp_adds"]
    
    if add_liquidity_pools and num_lp_adds > 0:
        print_section_header("LIQUIDITY PROVISION")
        for lp_index in range(num_lp_adds):
            lp_amount = round(random.uniform(min_phrs_amount * 5, max_phrs_amount * 5), 6)  # Use larger amount for LPs
            log_info(f"LP Addition #{lp_index + 1}/{num_lp_adds}: {lp_amount} PHRS")
            lp_tx_hash = add_liquidity(web3, private_key, lp_amount)
            if lp_tx_hash:
                log_success(f"Liquidity addition completed: {lp_tx_hash}")
            if lp_index < num_lp_adds - 1:
                wait_time = wait_time_seconds // 2
                log_info(f"Waiting {wait_time} seconds before next LP addition...")
                time.sleep(wait_time)

    elapsed_time = time.time() - start_time
    final_balance_wei = web3.eth.get_balance(wallet_address)
    final_balance_phrs = web3.from_wei(final_balance_wei, 'ether')
    
    print_summary_box(tx_stats, elapsed_time, final_balance_phrs)
    return tx_stats

def main():
    print_banner()
    required_files = ["private_key.txt", "recipients.txt"]
    for file_path in required_files:
        if not check_file_exists(file_path):
            sys.exit(1)

    # Load all private keys
    private_keys = load_private_keys()
    if not private_keys:
        log_error("No valid private keys found in private_key.txt")
        sys.exit(1)
    log_success(f"Loaded {len(private_keys)} wallets from private_key.txt")
    
    # Load proxies if available
    proxies = load_proxies()
    proxy_manager = ProxyManager(proxies)

    log_info("Connecting to Pharos Testnet...")
    rpc_endpoints = [
        "https://testnet.dplabs-internal.com",
        "https://pharos-testnet.rpc.caldera.xyz/http",
        "https://pharos-testnet-rpc.stress.run",
        "https://pharos.rpc.thirdweb.com"
    ]
    web3 = None
    connected = False
    
    # Try connections with proxies first if available
    if proxy_manager.has_proxies():
        for endpoint in rpc_endpoints:
            try:
                proxy_settings = proxy_manager.format_for_web3()
                log_info(f"Trying endpoint {endpoint} with proxy {proxy_manager.get_current_proxy()}")
                
                # Create HTTP provider with proxy settings
                provider = Web3.HTTPProvider(
                    endpoint,
                    request_kwargs={'proxies': proxy_settings}
                )
                web3 = Web3(provider)
                
                if web3.is_connected():
                    connected = True
                    log_success(f"Connected to Pharos Testnet via {endpoint} using proxy")
                    break
                    
                # Try next proxy if available
                proxy_manager.rotate_proxy(force=True)
                
            except Exception as error:
                log_error(f"Connection to {endpoint} with proxy failed: {str(error)}")
                proxy_manager.rotate_proxy(force=True)
    
    # Fall back to direct connection if proxy connection failed
    if not connected:
        for endpoint in rpc_endpoints:
            try:
                log_info(f"Trying direct connection to endpoint: {endpoint}")
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
    
    # Display available wallets
    display_wallets(web3, private_keys)
    
    # Wallet selection
    print(f"\n{Fore.YELLOW}Select wallet to use:{Style.RESET_ALL}")
    print(f"  {Fore.CYAN}[1-{len(private_keys)}] Specific wallet{Style.RESET_ALL}")
    print(f"  {Fore.CYAN}[0] All wallets (run sequentially){Style.RESET_ALL}")
    
    wallet_choice = -1
    while wallet_choice < 0 or wallet_choice > len(private_keys):
        try:
            wallet_choice = int(input(f"{Fore.GREEN}Enter choice: {Style.RESET_ALL}"))
        except ValueError:
            log_error("Please enter a valid number")
    
    # Process single wallet or all wallets
    wallets_to_process = []
    if wallet_choice == 0:
        log_info("Running with all wallets sequentially")
        wallets_to_process = list(range(len(private_keys)))
    else:
        log_info(f"Running with wallet #{wallet_choice}")
        wallets_to_process = [wallet_choice - 1]

    # Load recipients
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

    # Get transaction configuration for all wallets
    print_section_header("TRANSACTION CONFIGURATION")
    try:
        print(f"{Fore.YELLOW}Please enter transaction details (applied to all selected wallets):{Style.RESET_ALL}")
        num_transactions = int(input(f"  {Fore.CYAN}Number of transactions:{Style.RESET_ALL} "))
        min_phrs_amount = float(input(f"  {Fore.CYAN}Minimum PHRS per transaction [0.001]:{Style.RESET_ALL} ") or "0.001")
        max_phrs_amount = float(input(f"  {Fore.CYAN}Maximum PHRS per transaction [0.002]:{Style.RESET_ALL} ") or "0.002")
        wait_time_seconds = int(input(f"  {Fore.CYAN}Seconds between transactions [30]:{Style.RESET_ALL} ") or "30")
        gas_input = input(f"  {Fore.CYAN}Gas price in gwei [{network_gas_gwei:.2f}]:{Style.RESET_ALL} ")
        gas_price_wei = web3.to_wei(float(gas_input) if gas_input else network_gas_gwei, 'gwei')
        gas_limit = int(input(f"  {Fore.CYAN}Gas limit [21000]:{Style.RESET_ALL} ") or "21000")
        
        # DeFi features
        perform_swaps = input(f"  {Fore.CYAN}Perform token swaps (y/n) [n]:{Style.RESET_ALL} ").lower() == 'y'
        num_swaps = int(input(f"  {Fore.CYAN}Number of swaps [1]:{Style.RESET_ALL} ") or "1") if perform_swaps else 0
        
        add_liquidity_pools = input(f"  {Fore.CYAN}Add liquidity to pools (y/n) [n]:{Style.RESET_ALL} ").lower() == 'y'
        num_lp_adds = int(input(f"  {Fore.CYAN}Number of LP additions [1]:{Style.RESET_ALL} ") or "1") if add_liquidity_pools else 0
        
        task_id = 103  # Default task ID for verification
        
        tx_config = {
            "num_transactions": num_transactions,
            "min_phrs_amount": min_phrs_amount,
            "max_phrs_amount": max_phrs_amount,
            "wait_time_seconds": wait_time_seconds,
            "gas_price_wei": gas_price_wei,
            "gas_limit": gas_limit,
            "perform_swaps": perform_swaps,
            "num_swaps": num_swaps,
            "add_liquidity_pools": add_liquidity_pools,
            "num_lp_adds": num_lp_adds,
            "task_id": task_id
        }
    except ValueError:
        log_error("Please enter valid numbers")
        sys.exit(1)
    
    # Process wallets
    overall_stats = {
        "total_wallets": len(wallets_to_process),
        "successful_wallets": 0,
        "successful_txs": 0,
        "failed_txs": 0,
        "total_phrs_sent": 0
    }
    
    start_time = time.time()
    
    for idx, wallet_idx in enumerate(wallets_to_process):
        private_key = private_keys[wallet_idx]
        stats = process_wallet(web3, private_key, valid_recipients, tx_config, idx, len(wallets_to_process), proxy_manager)
        
        if stats:
            overall_stats["successful_wallets"] += 1
            overall_stats["successful_txs"] += stats["successful_txs"]
            overall_stats["failed_txs"] += stats["failed_txs"]
            overall_stats["total_phrs_sent"] += stats["total_phrs_sent"]
        
        # Wait between wallets - FIXED: time.time(10) to time.sleep(10) 
        if idx < len(wallets_to_process) - 1:
            log_info(f"Waiting 10 seconds before processing next wallet...")
            time.sleep(10)  # Fixed from time.time(10)
    
    total_elapsed_time = time.time() - start_time
    
    # Final overall summary for multi-wallet processing
    if len(wallets_to_process) > 1:
        print_section_header("OVERALL SUMMARY")
        print(f"{Fore.YELLOW}Total wallets processed: {Fore.GREEN}{overall_stats['successful_wallets']}{Fore.YELLOW}/{overall_stats['total_wallets']}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Total successful transactions: {Fore.GREEN}{overall_stats['successful_txs']}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Total failed transactions: {Fore.RED}{overall_stats['failed_txs']}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Total PHRS sent: {Fore.GREEN}{overall_stats['total_phrs_sent']:.6f}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Total elapsed time: {Fore.CYAN}{total_elapsed_time:.2f} seconds{Style.RESET_ALL}")
    
    log_success("Script execution completed!")

if __name__ == "__main__":
    main()