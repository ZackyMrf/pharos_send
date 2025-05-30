import random
import time
import requests
import os
import sys
import json
from datetime import datetime
from web3 import Web3, Account
from colorama import Fore, Style, init
import shutil
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
    def test_proxy(self, test_url="https://api.pharosnetwork.xyz/health"):
        """Test if a proxy is working properly"""
        proxy_url = self.get_current_proxy()
        if not proxy_url:
            return False
        
        try:
            log_info(f"Testing proxy connection: {proxy_url}")
            response = requests.get(test_url, proxies=self.format_for_requests(), timeout=10)
            if response.status_code < 400:
                log_success(f"Proxy test successful: {proxy_url}")
                return True
            else:
                log_error(f"Proxy test failed with status {response.status_code}")
                return False
        except Exception as e:
            log_error(f"Proxy test error: {str(e)}")
            return False
        
    def format_for_web3(self):
        """Format current proxy string for Web3 connection"""
        proxy_str = self.get_current_proxy()
        if not proxy_str:
            return None
            
        # Add default protocol if missing
        if not ('://' in proxy_str):
            proxy_str = f"http://{proxy_str}"
            
        # Format for web3 provider
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
║{Fore.YELLOW}  🚀 PHAROS NETWORK SWAP BOT 🚀  {Fore.MAGENTA}{' ' * (terminal_width - 38)}║
║{Fore.CYAN}     PHRS-USDC Swap Edition v1.1     {Fore.MAGENTA}{' ' * (terminal_width - 44)}║
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

def log_warning(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"{Fore.YELLOW}[{timestamp}] [WARNING]{Style.RESET_ALL} ⚠️  {message}")

def log_swap(swap_number, total_swaps, amount, token_from, token_to, tx_hash):
    timestamp = datetime.now().strftime("%H:%M:%S")
    progress = f"[{swap_number}/{total_swaps}]"
    progress_bar = create_progress_bar(swap_number, total_swaps)
    
    print(f"\n{Fore.YELLOW}[{timestamp}] {progress} {progress_bar}{Style.RESET_ALL}")
    print(f"  {Fore.CYAN}Amount:{Style.RESET_ALL} {amount} {token_from}")
    print(f"  {Fore.CYAN}To:{Style.RESET_ALL} {token_to}")
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
    """Get JWT token from API using signature with fallback to direct connection"""
    signature, address = sign_message(web3, private_key)
    log_info(f"Generated signature for {address}")
    
    url = f"https://api.pharosnetwork.xyz/user/login?address={address}&signature={signature}"
    headers = {
        "Origin": "https://testnet.pharosnetwork.xyz", 
        "Referer": "https://testnet.pharosnetwork.xyz/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36"
    }
    
    # First try with proxy if available
    if proxy_manager and proxy_manager.has_proxies():
        for attempt in range(3):  # Try up to 3 different proxies
            proxies = proxy_manager.format_for_requests()
            current_proxy = proxy_manager.get_current_proxy()
            
            # Skip testing if proxy is clearly invalid
            if current_proxy is None or current_proxy.strip() == "":
                proxy_manager.rotate_proxy(force=True)
                continue
                
            log_info(f"Attempt {attempt+1}/3: Using proxy for API login: {current_proxy}")
            
            try:
                response = requests.post(url, headers=headers, proxies=proxies, timeout=45)
                if response.ok:
                    data = response.json()
                    if data.get("code") == 0:
                        jwt_token = data.get("data", {}).get("jwt")
                        log_success(f"Login successful via proxy, received JWT token")
                        return jwt_token
                log_error(f"Login failed via proxy: {response.status_code}")
                proxy_manager.rotate_proxy(force=True)
            except Exception as e:
                log_error(f"Login error via proxy: {str(e)}")
                proxy_manager.rotate_proxy(force=True)
    
    # Fall back to direct connection if all proxies failed
    log_info("Trying direct connection without proxy...")
    try:
        response = requests.post(url, headers=headers, timeout=45)
        if response.ok:
            data = response.json()
            if data.get("code") == 0:
                jwt_token = data.get("data", {}).get("jwt")
                log_success(f"Login successful via direct connection, received JWT token")
                return jwt_token
        log_error(f"Login failed via direct connection: {response.status_code} | {response.text}")
    except Exception as e:
        log_error(f"Login error via direct connection: {str(e)}")
        
    return None

def get_token_balance(web3, token_address, wallet_address):
    """Get balance of a specific token for a wallet"""
    try:
        token_contract = web3.eth.contract(
            address=web3.to_checksum_address(token_address), 
            abi=config.ERC20_ABI
        )
        balance_wei = token_contract.functions.balanceOf(wallet_address).call()
        return balance_wei
    except Exception as e:
        log_error(f"Error getting token balance: {str(e)}")
        return 0

def format_token_balance(balance_wei, decimals):
    """Format token balance with appropriate decimals"""
    return balance_wei / (10 ** decimals)

def check_transaction_status(web3, tx_hash, max_attempts=30, delay=6):
    """Check transaction status without blocking indefinitely"""
    tx_hash_hex = web3.to_hex(tx_hash) if not isinstance(tx_hash, str) else tx_hash
    
    for attempt in range(max_attempts):
        try:
            receipt = web3.eth.get_transaction_receipt(tx_hash)
            if receipt is not None:
                if receipt.status == 1:
                    log_success(f"Transaction {tx_hash_hex} confirmed (Attempt {attempt+1}/{max_attempts})")
                    return receipt
                else:
                    log_error(f"Transaction {tx_hash_hex} failed with status {receipt.status}")
                    return receipt
        except Exception as e:
            log_info(f"Waiting for confirmation... (Attempt {attempt+1}/{max_attempts})")
        
        if attempt < max_attempts - 1:  # Don't sleep on the last attempt
            time.sleep(delay)
    
    log_warning(f"Transaction {tx_hash_hex} not confirmed within timeout, but it might still be processed")
    return None

def swap_tokens(web3, private_key, amount_phrs, swap_route):
    """Swap PHRS for token using Pharos DEX with improved error handling"""
    # Determine token addresses based on swap route
    if swap_route == "phrs_to_usdc":
        token_in = config.WPHRS_ADDRESS
        token_out = config.USDC_ADDRESS
        token_in_name = "PHRS"
        token_out_name = "USDC"
        token_in_decimals = 18
        token_out_decimals = 6
    elif swap_route == "usdc_to_phrs":
        token_in = config.USDC_ADDRESS
        token_out = config.WPHRS_ADDRESS
        token_in_name = "USDC"
        token_out_name = "PHRS"
        token_in_decimals = 6
        token_out_decimals = 18
    else:
        log_error(f"Invalid swap route: {swap_route}")
        return None
    
    # For stablecoin to PHRS swaps, check if amount is at least 20
    if token_in_name == "USDC" and amount_phrs < 20:
        log_warning(f"USDC amount {amount_phrs} is below recommended minimum of 20. This may cause issues.")
    
    log_info(f"Preparing to swap {amount_phrs} {token_in_name} to {token_out_name}...")
    
    try:
        account = web3.eth.account.from_key(private_key)
        address = account.address
        
        # Handle different decimal places for tokens
        if token_in_decimals == 18:
            amount_in_wei = web3.to_wei(amount_phrs, 'ether')
        else:
            # USDC has 6 decimals
            amount_in_wei = int(amount_phrs * (10 ** token_in_decimals))
        
        # Get contracts with checksummed addresses
        token = web3.eth.contract(
            address=web3.to_checksum_address(token_in), 
            abi=config.ERC20_ABI
        )
        router = web3.eth.contract(
            address=web3.to_checksum_address(config.SWAP_ROUTER_ADDRESS), 
            abi=config.SWAP_ROUTER_ABI
        )
        
        # Get the precise token balance with proper decimal handling
        token_balance = token.functions.balanceOf(address).call()
        
        # For PHRS, we need to get the native balance if we're swapping from PHRS
        if token_in_name == "PHRS":
            token_balance = web3.eth.get_balance(address)
        
        token_balance_formatted = token_balance / (10 ** token_in_decimals)
        
        # Double-check if balance is sufficient before proceeding
        if token_balance < amount_in_wei:
            log_error(f"Insufficient {token_in_name} balance. Required: {amount_phrs}, Available: {token_balance_formatted:.8f}")
            return None
        
        # Check for existing allowance to avoid unnecessary approvals
        current_allowance = 0
        if token_in_name != "PHRS":  # No need to approve for native PHRS
            current_allowance = token.functions.allowance(
                address, 
                web3.to_checksum_address(config.SWAP_ROUTER_ADDRESS)
            ).call()
        
        # Get fresh nonce for each transaction to prevent replay attacks
        current_nonce = web3.eth.get_transaction_count(address, 'pending')
        log_info(f"Using nonce {current_nonce} for approval transaction")
        
        # Only approve if necessary and not swapping native PHRS
        if token_in_name != "PHRS" and current_allowance < amount_in_wei:
            log_info(f"Current allowance ({current_allowance / (10 ** token_in_decimals):.8f} {token_in_name}) is insufficient. Approving...")
            
            # Approve with a much higher amount to reduce future approvals
            approve_amount = amount_in_wei * 1000  # Approve 1000x the current amount for future swaps
            
            approve_tx = token.functions.approve(
                web3.to_checksum_address(config.SWAP_ROUTER_ADDRESS), 
                approve_amount
            ).build_transaction({
                'from': address,
                'nonce': current_nonce,
                'gas': 200000,  # Increased gas for approval
                'gasPrice': web3.eth.gas_price + random.randint(100000, 2000000),
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
            tx_hash_hex = web3.to_hex(tx_hash)
            log_info(f"Approval transaction sent: {tx_hash_hex}")
            
            # Use non-blocking checker for approval confirmation
            receipt = check_transaction_status(web3, tx_hash, max_attempts=30, delay=6)
            
            # Continue even if we couldn't confirm receipt, as approval might still succeed
            if receipt is None:
                log_warning(f"Approval transaction not confirmed yet, but continuing with swap...")
                # Sleep a bit to give the transaction time to propagate
                time.sleep(15)  # Increased wait time for approval
            elif receipt.status != 1:
                log_error("Approval transaction failed")
                return None
            else:
                log_success("Token approval confirmed")
                # Short delay after confirmed approval
                time.sleep(2)
            
            # Update nonce for next transaction to prevent replay attacks
            current_nonce = web3.eth.get_transaction_count(address, 'pending')
        elif token_in_name != "PHRS":
            log_info(f"Sufficient allowance already exists ({current_allowance / (10 ** token_in_decimals):.8f} {token_in_name}), skipping approval")
        
        # Increase slippage tolerance for better transaction success
        # Setting minimum amount out to 0 for testnet to bypass slippage checks
        min_amount_out = 0
        log_info(f"Setting minimum output to 0 to bypass slippage checks on testnet")
        
        # Higher gas limit for swaps
        gas_limit = 600000  # Significantly increased gas limit
        
        # Randomize gas price
        gas_price = web3.eth.gas_price + random.randint(500000, 5000000)
        
        # Prepare swap parameters with checksummed addresses
        swap_params = {
            "tokenIn": web3.to_checksum_address(token_in),
            "tokenOut": web3.to_checksum_address(token_out),
            "fee": 500,  # 0.05%
            "recipient": address,
            "amountIn": amount_in_wei,
            "amountOutMinimum": min_amount_out,
            "sqrtPriceLimitX96": 0
        }
        
        log_info(f"Building swap transaction with nonce {current_nonce}")
        
        # Build transaction base parameters
        tx_params = {
            'from': address,
            'nonce': current_nonce,
            'gas': gas_limit,
            'gasPrice': gas_price,
            'chainId': config.CHAIN_ID
        }
        
        # For PHRS (native token), we need to include value in transaction
        if token_in_name == "PHRS":
            tx_params['value'] = amount_in_wei
        
        # Build and sign swap transaction
        swap_tx = router.functions.exactInputSingle(
            swap_params
        ).build_transaction(tx_params)
        
        signed_swap = web3.eth.account.sign_transaction(swap_tx, private_key=private_key)
        
        # Handle different web3.py versions
        if hasattr(signed_swap, 'rawTransaction'):
            raw_swap_tx = signed_swap.rawTransaction
        elif hasattr(signed_swap, 'raw_transaction'):
            raw_swap_tx = signed_swap.raw_transaction
        else:
            raise AttributeError("Could not find raw transaction data in signed transaction")
            
        swap_tx_hash = web3.eth.send_raw_transaction(raw_swap_tx)
        swap_tx_hash_hex = web3.to_hex(swap_tx_hash)
        log_info(f"Swap transaction sent: {swap_tx_hash_hex}")
        
        # Use non-blocking checker for swap transaction
        swap_receipt = check_transaction_status(web3, swap_tx_hash, max_attempts=40, delay=6)  # Increased attempts
        
        # Better error handling
        if swap_receipt is None:
            log_warning(f"Swap transaction not confirmed within timeout, but may still succeed")
            log_info(f"You can check the status manually at {config.EXPLORER}{swap_tx_hash_hex}")
            return swap_tx_hash_hex
        elif swap_receipt.status != 1:
            log_error(f"Swap transaction failed with status {swap_receipt.status}")
            log_error("Possible reasons: 1) Insufficient liquidity, 2) Price impact too high, 3) Network congestion")
            log_error(f"Try a smaller amount (< 0.001) or wait for better network conditions")
            return None
        
        log_success(f"Successfully swapped {amount_phrs} {token_in_name} for {token_out_name}!")
        return swap_tx_hash_hex
        
    except Exception as e:
        log_error(f"Error during token swap: {str(e)}")
        # More detailed error logging
        if "gas required exceeds" in str(e):
            log_error("Transaction requires more gas than provided. Try increasing gas limit further.")
        elif "insufficient funds" in str(e):
            log_error("Insufficient funds to cover gas costs.")
        elif "nonce too low" in str(e):
            log_error("Transaction nonce issue. Network may be congested or previous transaction still pending.")
        elif "always failing transaction" in str(e):
            log_error("Contract execution always fails. This typically means there's an issue with swap parameters.")
            log_error("Try reducing swap amount significantly to < 0.001")
        return None

def process_wallet_swaps(web3, private_key, swap_config, wallet_index, total_wallets, proxy_manager=None):
    """Process swaps for a single wallet"""
    wallet = Account.from_key(private_key)
    wallet_address = wallet.address
    
    # Create a section header for this wallet
    print(f"\n{Fore.CYAN}{'═' * 70}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}║ WALLET {wallet_index+1}/{total_wallets}: {wallet_address} {' ' * (70 - 22 - len(wallet_address))}{Fore.CYAN}║{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'═' * 70}{Style.RESET_ALL}")
    
    # Get PHRS balance
    balance_wei = web3.eth.get_balance(wallet_address)
    balance_phrs = web3.from_wei(balance_wei, 'ether')
    log_info(f"Current PHRS balance: {Fore.GREEN}{balance_phrs:.8f}{Style.RESET_ALL}")
    
    # Get USDC balance with proper formatting
    try:
        # USDC balance (6 decimals)
        usdc_balance_wei = get_token_balance(web3, config.USDC_ADDRESS, wallet_address)
        usdc_balance = usdc_balance_wei / (10 ** 6)  # USDC has 6 decimals
        
        log_info(f"Current USDC balance: {Fore.GREEN}{usdc_balance:.8f}{Style.RESET_ALL}")
    except Exception as e:
        log_error(f"Error getting USDC balance: {str(e)}")
        usdc_balance = 0
    
    # Get JWT token for API calls
    jwt_token = login_with_signature(web3, private_key, proxy_manager)
    if not jwt_token:
        log_error("Failed to obtain JWT token for API authentication")
        return None
    
    # Initialize stats
    stats = {
        "total_swaps": 0,
        "successful_swaps": 0,
        "failed_swaps": 0,
        "swap_routes": {
            "phrs_to_usdc": 0,
            "usdc_to_phrs": 0
        }
    }
    
    num_swaps = swap_config["num_swaps"]
    min_amount = swap_config["min_amount"]
    max_amount = swap_config["max_amount"]
    wait_time = swap_config["wait_time"]
    
    # Always use round_trip mode (alternating PHRS->USDC and USDC->PHRS)
    swap_mode = "round_trip"
    
    # Define stablecoin minimum amount (20 USDC)
    stablecoin_min_amount = 20.0
    
    # Always alternate between PHRS -> USDC and USDC -> PHRS
    swap_routes = []
    for i in range(num_swaps):
        if i % 2 == 0:
            swap_routes.append("phrs_to_usdc")
        else:
            swap_routes.append("usdc_to_phrs")
    
    start_time = time.time()
    log_info(f"Starting {num_swaps} swaps with round-trip mode (PHRS↔USDC)")
    
    # Check if minimum amount is higher than balance for PHRS
    if float(balance_phrs) < min_amount:
        log_warning(f"PHRS balance ({float(balance_phrs):.8f}) is less than minimum swap amount ({min_amount})")
        if float(balance_phrs) > 0.0001:
            log_info(f"Using actual PHRS balance for swaps instead of minimum amount")
            min_amount_phrs = float(balance_phrs) * 0.9  # Use 90% of balance
        else:
            log_error(f"PHRS balance too low for swapping")
            min_amount_phrs = min_amount
    else:
        min_amount_phrs = min_amount
    
    # Process all swaps
    for i, route in enumerate(swap_routes):
        # Select appropriate amount based on token type
        if route == "phrs_to_usdc":
            # Check if we have enough PHRS
            if float(balance_phrs) < 0.0001:  # Minimum viable amount
                log_error(f"Insufficient PHRS balance for swap {i+1}. Available: {float(balance_phrs):.8f}")
                stats["failed_swaps"] += 1
                continue
                
            # Use available balance if it's less than min_amount but still usable
            if float(balance_phrs) < min_amount_phrs:
                amount = float(balance_phrs) * 0.9  # Use 90% of available balance
                log_info(f"Using 90% of available PHRS balance: {amount:.8f}")
            else:
                # Use random amount between min and max
                amount = round(random.uniform(min_amount_phrs, min(max_amount, float(balance_phrs) * 0.9)), 8)
        elif route == "usdc_to_phrs":
            # For USDC, use at least 20 USDC as minimum
            actual_min = max(min_amount, stablecoin_min_amount)
            # Check if we have enough USDC
            if usdc_balance < actual_min:
                log_error(f"Insufficient USDC balance for swap {i+1}. Minimum required: {actual_min} USDC, Available: {usdc_balance:.8f}")
                stats["failed_swaps"] += 1
                continue
            # Use exactly 20 USDC or user config (whichever is higher)
            amount = actual_min
            log_info(f"Using stablecoin minimum of {actual_min} USDC for this swap")
        
        # Log swap details
        log_info(f"Swap {i+1}/{num_swaps}: {amount} via {route}")
        
        # Execute the swap
        tx_hash = swap_tokens(web3, private_key, amount, route)
        
        if tx_hash:
            stats["successful_swaps"] += 1
            stats["swap_routes"][route] += 1
            
            # Determine tokens for logging
            if route == "phrs_to_usdc":
                token_from, token_to = "PHRS", "USDC"
            elif route == "usdc_to_phrs":
                token_from, token_to = "USDC", "PHRS"
            
            log_swap(i+1, num_swaps, amount, token_from, token_to, tx_hash)
            
            # Update balances after successful swap
            if route == "phrs_to_usdc":
                balance_phrs = float(balance_phrs) - amount
                usdc_balance += amount * 0.95  # Approximate, not exact
            elif route == "usdc_to_phrs":
                usdc_balance -= amount
                balance_phrs = float(balance_phrs) + amount * 0.95  # Approximate, not exact
        else:
            stats["failed_swaps"] += 1
        
        # Wait between swaps unless it's the last one
        if i < num_swaps - 1:
            actual_wait = random.uniform(wait_time * 0.8, wait_time * 1.2)
            log_info(f"Waiting {actual_wait:.1f} seconds before next swap...")
            time.sleep(actual_wait)
    
    # Get final balances with proper formatting
    final_balance_wei = web3.eth.get_balance(wallet_address)
    final_balance_phrs = web3.from_wei(final_balance_wei, 'ether')
    
    final_usdc_balance_wei = get_token_balance(web3, config.USDC_ADDRESS, wallet_address)
    final_usdc_balance = final_usdc_balance_wei / (10 ** 6)
    
    # Print summary
    elapsed_time = time.time() - start_time
    
    print(f"\n{Fore.CYAN}{'═' * 70}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}║ {Fore.YELLOW}SWAP SUMMARY FOR WALLET {wallet_index+1}/{total_wallets}{' ' * (70 - 40)}{Fore.CYAN}║{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'═' * 70}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}║{Style.RESET_ALL} Total swaps:           {stats['successful_swaps'] + stats['failed_swaps']}{' ' * (70 - 30)}{Fore.CYAN}║{Style.RESET_ALL}")
    print(f"{Fore.CYAN}║{Style.RESET_ALL} Successful swaps:      {Fore.GREEN}{stats['successful_swaps']}{Style.RESET_ALL}{' ' * (70 - 30)}{Fore.CYAN}║{Style.RESET_ALL}")
    print(f"{Fore.CYAN}║{Style.RESET_ALL} Failed swaps:          {Fore.RED}{stats['failed_swaps']}{Style.RESET_ALL}{' ' * (70 - 30)}{Fore.CYAN}║{Style.RESET_ALL}")
    print(f"{Fore.CYAN}║{Style.RESET_ALL} PHRS→USDC swaps:       {stats['swap_routes']['phrs_to_usdc']}{' ' * (70 - 30)}{Fore.CYAN}║{Style.RESET_ALL}")
    print(f"{Fore.CYAN}║{Style.RESET_ALL} USDC→PHRS swaps:       {stats['swap_routes']['usdc_to_phrs']}{' ' * (70 - 30)}{Fore.CYAN}║{Style.RESET_ALL}")
    print(f"{Fore.CYAN}║{Style.RESET_ALL} Final PHRS balance:    {Fore.GREEN}{final_balance_phrs:.8f}{Style.RESET_ALL}{' ' * (70 - 38)}{Fore.CYAN}║{Style.RESET_ALL}")
    print(f"{Fore.CYAN}║{Style.RESET_ALL} Final USDC balance:    {Fore.GREEN}{final_usdc_balance:.8f}{Style.RESET_ALL}{' ' * (70 - 38)}{Fore.CYAN}║{Style.RESET_ALL}")
    print(f"{Fore.CYAN}║{Style.RESET_ALL} Time elapsed:          {elapsed_time:.2f} seconds{' ' * (70 - 40)}{Fore.CYAN}║{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'═' * 70}{Style.RESET_ALL}")
    
    return stats

def main():
    print_banner()
    required_files = ["private_key.txt"]
    for file_path in required_files:
        if not check_file_exists(file_path):
            sys.exit(1)

    # Load private keys
    private_keys = load_private_keys()
    if not private_keys:
        log_error("No valid private keys found in private_key.txt")
        sys.exit(1)
    log_success(f"Loaded {len(private_keys)} wallets from private_key.txt")
    
    # Load proxies if available
    proxies = load_proxies()
    proxy_manager = ProxyManager(proxies)

    # Connect to RPC
    log_info("Connecting to Pharos Testnet...")
    rpc_endpoints = [
        "https://testnet.dplabs-internal.com",
        "https://pharos-testnet.rpc.caldera.xyz/http",
        "https://pharos-testnet-rpc.stress.run",
        "https://pharos.rpc.thirdweb.com"
    ]
    web3 = None
    connected = False
    
    # Try different RPC endpoints
    for endpoint in rpc_endpoints:
        try:
            log_info(f"Trying endpoint: {endpoint}")
            # Add timeout to provider
            web3 = Web3(Web3.HTTPProvider(endpoint, request_kwargs={'timeout': 180}))
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
    
    # Get swap configuration
    print(f"\n{Fore.CYAN}{'═' * 70}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}║ {Fore.YELLOW}SWAP CONFIGURATION{' ' * 51}{Fore.CYAN}║{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'═' * 70}{Style.RESET_ALL}")
    
    try:
        num_swaps = int(input(f"{Fore.CYAN}Number of swaps per wallet (max 200):{Style.RESET_ALL} "))
        if num_swaps <= 0 or num_swaps > 200:
            log_error("Number of swaps must be between 1 and 200")
            sys.exit(1)
            
        min_amount = float(input(f"{Fore.CYAN}Minimum amount per swap [0.001]:{Style.RESET_ALL} ") or "0.001")
        max_amount = float(input(f"{Fore.CYAN}Maximum amount per swap [0.005]:{Style.RESET_ALL} ") or "0.005")
        wait_time = int(input(f"{Fore.CYAN}Seconds between swaps [5]:{Style.RESET_ALL} ") or "5")
        
        # Create swap configuration - always using round_trip mode
        swap_config = {
            "num_swaps": num_swaps,
            "min_amount": min_amount,
            "max_amount": max_amount,
            "wait_time": wait_time,
            "swap_mode": "round_trip"  # Always use round_trip mode
        }
        
        log_info(f"Using Round-trip swap mode (PHRS→USDC→PHRS)")
        
    except ValueError:
        log_error("Invalid input. Please enter valid numbers.")
        sys.exit(1)
    
    # Process wallets
    overall_stats = {
        "total_wallets": len(wallets_to_process),
        "processed_wallets": 0,
        "total_swaps": 0,
        "successful_swaps": 0,
        "failed_swaps": 0
    }
    
    start_time = time.time()
    
    for idx, wallet_idx in enumerate(wallets_to_process):
        private_key = private_keys[wallet_idx]
        stats = process_wallet_swaps(web3, private_key, swap_config, idx, len(wallets_to_process), proxy_manager)
        
        if stats:
            overall_stats["processed_wallets"] += 1
            overall_stats["total_swaps"] += stats["successful_swaps"] + stats["failed_swaps"]
            overall_stats["successful_swaps"] += stats["successful_swaps"]
            overall_stats["failed_swaps"] += stats["failed_swaps"]
        
        # Wait between wallets
        if idx < len(wallets_to_process) - 1:
            wait_between_wallets = 10
            log_info(f"Waiting {wait_between_wallets} seconds before processing next wallet...")
            time.sleep(wait_between_wallets)
    
    # Print overall summary if processing multiple wallets
    if len(wallets_to_process) > 1:
        total_elapsed_time = time.time() - start_time
        
        print(f"\n{Fore.CYAN}{'═' * 70}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}║ {Fore.YELLOW}OVERALL SWAP SUMMARY{' ' * 49}{Fore.CYAN}║{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'═' * 70}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}║{Style.RESET_ALL} Total wallets processed:  {overall_stats['processed_wallets']}/{overall_stats['total_wallets']}{' ' * (70 - 35)}{Fore.CYAN}║{Style.RESET_ALL}")
        print(f"{Fore.CYAN}║{Style.RESET_ALL} Total swaps executed:     {overall_stats['total_swaps']}{' ' * (70 - 35)}{Fore.CYAN}║{Style.RESET_ALL}")
        print(f"{Fore.CYAN}║{Style.RESET_ALL} Successful swaps:         {Fore.GREEN}{overall_stats['successful_swaps']}{Style.RESET_ALL}{' ' * (70 - 35)}{Fore.CYAN}║{Style.RESET_ALL}")
        print(f"{Fore.CYAN}║{Style.RESET_ALL} Failed swaps:             {Fore.RED}{overall_stats['failed_swaps']}{Style.RESET_ALL}{' ' * (70 - 35)}{Fore.CYAN}║{Style.RESET_ALL}")
        
        # Handle division by zero
        success_rate = 0
        if overall_stats['total_swaps'] > 0:
            success_rate = overall_stats['successful_swaps']/overall_stats['total_swaps']*100
        
        print(f"{Fore.CYAN}║{Style.RESET_ALL} Success rate:             {Fore.GREEN}{success_rate:.1f}%{Style.RESET_ALL}{' ' * (70 - 35)}{Fore.CYAN}║{Style.RESET_ALL}")
        print(f"{Fore.CYAN}║{Style.RESET_ALL} Total time elapsed:       {total_elapsed_time:.2f} seconds{' ' * (70 - 45)}{Fore.CYAN}║{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'═' * 70}{Style.RESET_ALL}")
    
    log_success("Swap operations completed!")

if __name__ == "__main__":
    main()