# Pharos Network Bot

A comprehensive Python toolset to automate interactions with the Pharos Network testnet, supporting both transaction batching and faucet automation.

## Overview

This repository contains two main bots:

- **Transaction Bot:** Automates sending transactions, DeFi operations, and daily point check-ins.
- **Faucet Bot:** Automates claiming and forwarding testnet tokens using newly generated wallets.

---

## Features

### Transaction Bot
- Multi-wallet support (load wallets from file)
- Connects to multiple Pharos testnet RPC endpoints
- Randomizes transaction amounts and parameters
- Verifies transactions via API
- Supports DeFi operations: token swaps & liquidity provision
- Daily check-in for points
- Detailed colored logging and statistical batch reports
- Monitors transaction confirmations
- Proxy support (including advanced tunneling with `proxy+` prefix)

### Faucet Bot
- Auto-generates wallets and manages them
- Claims testnet tokens from the Pharos faucet
- Automatically forwards claimed tokens to a central wallet
- Proxy support for improved claim success
- Progress tracking and logging
- Wallets saved for reuse

---

## Requirements

- Python 3.8 or newer
- Required packages:
  - `web3` (>=6.0.0)
  - `requests` (>=2.28.0)
  - `colorama` (>=0.4.4)
  - `eth-account` (>=0.8.0)
  - `python-dotenv` (for faucet bot)

---

## Installation

1. **Clone this repository:**
    ```bash
    git clone https://github.com/zackymrf/pharos_send.git
    cd pharos_send
    ```

2. **Install dependencies:**
    ```bash
    pip3 install -r requirements.txt
    ```

---

## Setup

### Transaction Bot

Create these files in the project directory:

- `private_key.txt`: Ethereum private keys (one per line, without the '0x' prefix)
- `recipients.txt`: Ethereum addresses to receive transactions (one per line)
- `proxy.txt`: (Optional) HTTP proxies for API/web3 connections

### Faucet Bot

1. Enter the faucet directory:
   ```bash
   cd faucet
   ```
2. Copy and configure your `.env` file:
   ```bash
   cp .env.example .env
   ```
3. (Optional) Add proxies to `proxy.txt` for higher claim rates.
4. Generated wallets will be saved to `wallets.txt`.

---

## Authentication

Signature-based authentication is used—no separate token file is required.

- Private key signs a message to obtain a JWT token
- JWT token is used for all API calls
- Daily check-ins handled automatically

---

## Usage

### Transaction Bot

Run with:
```bash
python3 bot.py
```
You'll be prompted to:
- Choose a wallet (or use all)
- Configure transaction count, amounts, delays, gas settings, DeFi options, etc.

**Example:**
```
=== Transaction Configuration ===
Number of transactions: 5
Minimum PHRS per transaction [0.001]: 0.0001
Maximum PHRS per transaction [0.002]: 0.0002
Seconds between transactions [30]: 20
Gas price in gwei [1.00]: 1
Gas limit [21000]: 21000
Perform token swaps (y/n) [n]: y
Number of swaps [1]: 2
Add liquidity to pools (y/n) [n]: y
Number of LP additions [1]: 1
```

### Faucet Bot

Run with:
```bash
cd faucet
python3 faucet.py
```
You'll be prompted for:
- Recipient address (where claimed tokens are sent)
- Number of claims to perform

Process:
1. Wallets are generated and registered
2. Claims are made from the faucet
3. Tokens are forwarded to your specified address

---

## Security Notice

⚠️ **IMPORTANT** ⚠️

- **Never share your `private_key.txt` or commit it to a public repository**
- Sensitive files are included in `.gitignore` by default
- Faucet-generated wallets are stored in `wallets.txt`—keep it secure

---

## File Structure

```
.
├── bot.py                  # Main transaction bot script
├── config.py               # Contracts and ABIs config
├── requirements.txt        # Python dependencies
├── private_key.txt         # Your private keys (keep secure)
├── proxy.txt               # List of proxies (optional)
├── recipients.txt          # Recipient addresses
├── .gitignore              # Ignores sensitive files
├── readme.md               # Documentation
└── faucet/                 # Faucet bot
    ├── faucet.py           # Faucet bot script
    ├── .env                # Env config (keep secure)
    ├── .env.example        # Example env config
    ├── proxy.txt           # Faucet proxies (optional)
    └── wallets.txt         # Generated wallets (keep secure)
```

---

## Proxy Setup

Use HTTP proxies in this format:

```
http://username:password@ip:port
proxy+http://username:password@ip:port  # For tunneling proxies
```
The `proxy+` prefix enables HTTPS tunneling for advanced proxy use.

---

## Troubleshooting

### Connection Issues
- Check your internet and proxies
- Try at different times (servers may be busy)
- Avoid restrictive firewalls

### Transaction Errors
- Ensure sufficient PHRS balance
- Check gas price and private key validity
- Verify contract addresses in `config.py`

### API Authentication Failures
- Check your private key
- The bot auto-refreshes JWT tokens as needed

### DeFi Operation Failures
- Ensure enough tokens/approvals for swaps/liquidity
- Confirm contract addresses in `config.py`

### Faucet Claim Failures
- Use more proxies to avoid rate limits
- Try smaller batch sizes in `.env`
- Some IPs may be blocked or throttled

---

## License

This project is open source and free to use.