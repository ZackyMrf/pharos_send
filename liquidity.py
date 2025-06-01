import time
import random
from web3 import Web3
from web3.exceptions import ContractLogicError
import config
from datetime import datetime

def log_info(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] [INFO] ℹ️  {message}")

def log_success(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] [SUCCESS] ✅ {message}")

def log_error(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] [ERROR] ❌ {message}")

def add_liquidity(web3, private_key, amount_usdc, tick_range_type="full", amount1=None):
    """
    Add liquidity to the USDC-PHRS pool
    
    Parameters:
    - web3: Web3 instance
    - private_key: Wallet private key
    - amount_usdc: Amount of USDC to add
    - tick_range_type: Type of tick range ("full", "narrow", "custom")
    - amount1: Optional amount of USDC to add (if None, uses same value as PHRS)
    
    Returns:
    - Transaction hash if successful, None otherwise
    """
    log_info(f"Preparing to add liquidity with {amount_usdc} PHRS using {tick_range_type} range...")
    
    try:
        account = web3.eth.account.from_key(private_key)
        address = account.address
        amount0_in_wei = web3.to_wei(amount_usdc, 'ether')
        
        # If amount1 not specified, use same amount as PHRS
        amount1_in_wei = amount0_in_wei if amount1 is None else web3.to_wei(amount1, 'ether')
        
        # Get contracts with checksummed addresses
        token0 = web3.eth.contract(
            address=web3.to_checksum_address(config.WPHRS_ADDRESS), 
            abi=config.ERC20_ABI
        )
        token1 = web3.eth.contract(
            address=web3.to_checksum_address(config.USDC_ADDRESS), 
            abi=config.USDC_ABI
        )
        position_manager = web3.eth.contract(
            address=web3.to_checksum_address(config.POSITION_MANAGER_ADDRESS), 
            abi=config.POSITION_MANAGER_ABI
        )
        
        # Get current nonce
        nonce = web3.eth.get_transaction_count(address)
        
        # Approve with larger amounts for future operations
        approve_amount = amount0_in_wei * 10  # 10x for future approvals
        
        # Check current allowance for token0
        allowance0 = token0.functions.allowance(
            address, 
            web3.to_checksum_address(config.POSITION_MANAGER_ADDRESS)
        ).call()
        
        # Only approve if needed
        if allowance0 < amount0_in_wei:
            # First approve tokens to position manager
            approve_tx0 = token0.functions.approve(
                web3.to_checksum_address(config.POSITION_MANAGER_ADDRESS), 
                approve_amount
            ).build_transaction({
                'from': address,
                'nonce': nonce,
                'gas': 200000,
                'gasPrice': web3.eth.gas_price + random.randint(100000, 2000000),
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
            receipt0 = web3.eth.wait_for_transaction_receipt(tx_hash0, timeout=120)
            if receipt0.status != 1:
                log_error("Token0 approval transaction failed")
                return None
                
            log_success("Token0 approval confirmed")
            nonce += 1
        else:
            log_info("Token0 already has sufficient allowance")
        
        # Check current allowance for token1
        allowance1 = token1.functions.allowance(
            address, 
            web3.to_checksum_address(config.POSITION_MANAGER_ADDRESS)
        ).call()
        
        # Only approve if needed
        if allowance1 < amount1_in_wei:
            # Approve token1
            approve_tx1 = token1.functions.approve(
                web3.to_checksum_address(config.POSITION_MANAGER_ADDRESS), 
                approve_amount
            ).build_transaction({
                'from': address,
                'nonce': nonce,
                'gas': 200000,
                'gasPrice': web3.eth.gas_price + random.randint(100000, 2000000),
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
            receipt1 = web3.eth.wait_for_transaction_receipt(tx_hash1, timeout=120)
            if receipt1.status != 1:
                log_error("Token1 approval transaction failed")
                return None
                
            log_success("Token1 approval confirmed")
            nonce += 1
        else:
            log_info("Token1 already has sufficient allowance")
        
        # Prepare liquidity parameters
        current_timestamp = int(time.time())
        deadline = current_timestamp + 600  # 10 minutes from now
        
        # Set tick range based on the specified type
        if tick_range_type == "full":
            # Maximum possible range for full range position
            tick_lower = -887220
            tick_upper = 887220
        elif tick_range_type == "narrow":
            # More narrow range around current price
            # This should be around 20% price movement in either direction
            tick_lower = -4000
            tick_upper = 4000
        elif tick_range_type == "custom":
            # Custom range for current price of ~4156 USDC per PHRS
            # This covers price range from ~1000 USDC to ~10000 USDC per PHRS
            tick_lower = -10000
            tick_upper = 10000
        else:
            # Default to full range
            tick_lower = -887220
            tick_upper = 887220
        
        mint_params = {
            "token0": web3.to_checksum_address(config.WPHRS_ADDRESS),
            "token1": web3.to_checksum_address(config.USDC_ADDRESS),
            "fee": 3000,  # 0.3% fee tier
            "tickLower": tick_lower,
            "tickUpper": tick_upper,
            "amount0Desired": amount0_in_wei,
            "amount1Desired": amount1_in_wei,
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
            'nonce': nonce,
            'gas': 1000000,  # Increased gas limit for complex operation
            'gasPrice': web3.eth.gas_price + random.randint(100000, 2000000),
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
        try:
            mint_receipt = web3.eth.wait_for_transaction_receipt(mint_tx_hash, timeout=180)
            if mint_receipt.status != 1:
                log_error(f"Liquidity addition transaction failed with status {mint_receipt.status}")
                return None
                
            log_success(f"Successfully added liquidity with {amount_usdc} USDC!")
            
            # Parse events to get token ID
            position_id = None
            for log in mint_receipt.logs:
                if log.get('address') == config.POSITION_MANAGER_ADDRESS.lower():
                    # Try to find IncreaseLiquidity event
                    try:
                        event = position_manager.events.IncreaseLiquidity().process_log(log)
                        position_id = event.args.tokenId
                        log_success(f"Created position ID: {position_id}")
                        break
                    except:
                        pass
            
            return {
                'tx_hash': web3.to_hex(mint_tx_hash),
                'position_id': position_id
            }
        except Exception as receipt_error:
            log_error(f"Error waiting for receipt: {str(receipt_error)}")
            log_info(f"Transaction may still be pending. Check explorer: {config.EXPLORER}{web3.to_hex(mint_tx_hash)}")
            return {'tx_hash': web3.to_hex(mint_tx_hash)}
        
    except ContractLogicError as cle:
        log_error(f"Contract logic error: {str(cle)}")
        if "tick" in str(cle).lower():
            log_error("This could be due to tick range issues. Try different tick ranges.")
        return None
    except Exception as e:
        log_error(f"Error during liquidity addition: {str(e)}")
        if "execution reverted" in str(e):
            log_error("Contract execution reverted. Common causes:")
            log_error("1. Position out of range")
            log_error("2. Insufficient token balance")
            log_error("3. Incorrect tick spacing")
        elif "gas required exceeds" in str(e):
            log_error("Transaction requires more gas. Try increasing the gas limit.")
        return None

def remove_liquidity(web3, private_key, token_id, liquidity_percentage=100):
    """
    Remove liquidity from a position
    
    Parameters:
    - web3: Web3 instance
    - private_key: Wallet private key
    - token_id: NFT token ID representing the position
    - liquidity_percentage: Percentage of liquidity to remove (1-100)
    
    Returns:
    - Transaction hash if successful, None otherwise
    """
    log_info(f"Preparing to remove {liquidity_percentage}% liquidity from position #{token_id}...")
    
    try:
        account = web3.eth.account.from_key(private_key)
        address = account.address
        
        # Get position manager contract
        position_manager = web3.eth.contract(
            address=web3.to_checksum_address(config.POSITION_MANAGER_ADDRESS), 
            abi=config.POSITION_MANAGER_ABI
        )
        
        # Get current nonce
        nonce = web3.eth.get_transaction_count(address)
        
        # First get position information
        try:
            position = position_manager.functions.positions(token_id).call()
            liquidity = position[7]  # Liquidity is at index 7
            
            # Calculate liquidity to remove based on percentage
            liquidity_to_remove = int(liquidity * liquidity_percentage / 100)
            
            if liquidity_to_remove <= 0:
                log_error(f"No liquidity to remove from position #{token_id}")
                return None
                
            log_info(f"Position has {liquidity} liquidity, removing {liquidity_to_remove}")
        except Exception as e:
            log_error(f"Failed to get position info: {str(e)}")
            return None
        
        # Prepare decrease liquidity parameters
        current_timestamp = int(time.time())
        deadline = current_timestamp + 600  # 10 minutes from now
        
        decrease_params = {
            "tokenId": token_id,
            "liquidity": liquidity_to_remove,
            "amount0Min": 0,
            "amount1Min": 0,
            "deadline": deadline
        }
        
        # Build and sign decreaseLiquidity transaction
        decrease_tx = position_manager.functions.decreaseLiquidity(
            decrease_params
        ).build_transaction({
            'from': address,
            'nonce': nonce,
            'gas': 500000,
            'gasPrice': web3.eth.gas_price + random.randint(100000, 2000000),
            'chainId': config.CHAIN_ID
        })
        
        signed_decrease = web3.eth.account.sign_transaction(decrease_tx, private_key=private_key)
        
        # Handle different web3.py versions
        if hasattr(signed_decrease, 'rawTransaction'):
            raw_tx = signed_decrease.rawTransaction
        elif hasattr(signed_decrease, 'raw_transaction'):
            raw_tx = signed_decrease.raw_transaction
        else:
            raise AttributeError("Could not find raw transaction data in signed transaction")
            
        tx_hash = web3.eth.send_raw_transaction(raw_tx)
        log_info(f"Decrease liquidity transaction sent: {web3.to_hex(tx_hash)}")
        
        # Wait for transaction to be mined
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
        if receipt.status != 1:
            log_error("Decrease liquidity transaction failed")
            return None
            
        log_success(f"Successfully decreased liquidity for position #{token_id}")
        
        # If we're removing 100% liquidity, collect all fees and tokens
        if liquidity_percentage == 100:
            nonce += 1
            
            # Collect all tokens
            collect_params = {
                "tokenId": token_id,
                "recipient": address,
                "amount0Max": 2**128 - 1,  # Max uint128
                "amount1Max": 2**128 - 1   # Max uint128
            }
            
            collect_tx = position_manager.functions.collect(
                collect_params
            ).build_transaction({
                'from': address,
                'nonce': nonce,
                'gas': 300000,
                'gasPrice': web3.eth.gas_price + random.randint(100000, 2000000),
                'chainId': config.CHAIN_ID
            })
            
            signed_collect = web3.eth.account.sign_transaction(collect_tx, private_key=private_key)
            
            # Handle different web3.py versions
            if hasattr(signed_collect, 'rawTransaction'):
                raw_collect_tx = signed_collect.rawTransaction
            elif hasattr(signed_collect, 'raw_transaction'):
                raw_collect_tx = signed_collect.raw_transaction
            else:
                raise AttributeError("Could not find raw transaction data in signed transaction")
                
            collect_tx_hash = web3.eth.send_raw_transaction(raw_collect_tx)
            log_info(f"Collect tokens transaction sent: {web3.to_hex(collect_tx_hash)}")
            
            # Wait for transaction to be mined
            collect_receipt = web3.eth.wait_for_transaction_receipt(collect_tx_hash, timeout=180)
            if collect_receipt.status != 1:
                log_error("Collect tokens transaction failed")
            else:
                log_success(f"Successfully collected tokens from position #{token_id}")
        
        return web3.to_hex(tx_hash)
        
    except Exception as e:
        log_error(f"Error during liquidity removal: {str(e)}")
        return None

def get_liquidity_positions(web3, address):
    """
    Get all liquidity positions for a wallet
    
    Parameters:
    - web3: Web3 instance
    - address: Wallet address
    
    Returns:
    - List of position details
    """
    log_info(f"Fetching liquidity positions for {address}...")
    
    try:
        # Get position manager contract
        position_manager = web3.eth.contract(
            address=web3.to_checksum_address(config.POSITION_MANAGER_ADDRESS), 
            abi=config.POSITION_MANAGER_ABI
        )
        
        # Get balance of position NFTs
        balance = position_manager.functions.balanceOf(address).call()
        log_info(f"Found {balance} liquidity positions")
        
        positions = []
        
        # Iterate through each position
        for i in range(balance):
            try:
                token_id = position_manager.functions.tokenOfOwnerByIndex(address, i).call()
                position_data = position_manager.functions.positions(token_id).call()
                
                # Format position data
                position = {
                    'token_id': token_id,
                    'token0': position_data[2],
                    'token1': position_data[3],
                    'fee': position_data[4],
                    'tick_lower': position_data[5],
                    'tick_upper': position_data[6],
                    'liquidity': position_data[7],
                    'fee_growth_inside0_last_X128': position_data[8],
                    'fee_growth_inside1_last_X128': position_data[9],
                    'tokens_owed0': position_data[10],
                    'tokens_owed1': position_data[11]
                }
                
                positions.append(position)
                log_info(f"Position #{token_id}: Liquidity={position['liquidity']}")
            except Exception as e:
                log_error(f"Error fetching position {i}: {str(e)}")
        
        return positions
        
    except Exception as e:
        log_error(f"Error getting liquidity positions: {str(e)}")
        return []

def main():
    """
    Main function to demonstrate usage
    """
    import sys
    import os
    from web3 import Web3
    
    # Connect to network
    rpc_endpoint = "https://testnet.dplabs-internal.com"
    web3 = Web3(Web3.HTTPProvider(rpc_endpoint))
    
    # Check connection
    if not web3.is_connected():
        log_error("Failed to connect to RPC endpoint")
        sys.exit(1)
    
    log_success("Connected to Pharos Network")
    
    # Load private key
    if not os.path.exists("private_key.txt"):
        log_error("private_key.txt file not found")
        sys.exit(1)
        
    with open("private_key.txt", "r") as f:
        private_keys = [line.strip() for line in f if line.strip()]
        
    if not private_keys:
        log_error("No private keys found in private_key.txt")
        sys.exit(1)
        
    private_key = private_keys[0]
    account = web3.eth.account.from_key(private_key)
    address = account.address
    
    log_info(f"Using wallet: {address}")
    
    # Show command menu
    print("\nLiquidity Management Options:")
    print("1. View Liquidity Positions")
    print("2. Add Liquidity")
    print("3. Remove Liquidity")
    print("4. Exit")
    
    choice = input("\nEnter your choice (1-4): ")
    
    if choice == "1":
        positions = get_liquidity_positions(web3, address)
        if positions:
            print("\nLiquidity Positions:")
            for pos in positions:
                print(f"Position #{pos['token_id']}: {pos['liquidity']} liquidity units")
    
    elif choice == "2":
        amount = float(input("Enter USDC amount to add: "))
        range_type = input("Select range type (full/narrow/custom) [full]: ") or "full"
        result = add_liquidity(web3, private_key, amount, range_type)
        if result:
            log_success(f"Liquidity added successfully: {result}")
    
    elif choice == "3":
        token_id = int(input("Enter position token ID to remove: "))
        percentage = int(input("Enter percentage to remove (1-100) [100]: ") or "100")
        result = remove_liquidity(web3, private_key, token_id, percentage)
        if result:
            log_success(f"Liquidity removed successfully: {result}")
    
    elif choice == "4":
        sys.exit(0)
    
    else:
        log_error("Invalid choice")

if __name__ == "__main__":
    main()