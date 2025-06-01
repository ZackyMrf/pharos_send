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
    log_info(f"Preparing to add liquidity with {amount_usdc} USDC using {tick_range_type} range...")
    
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