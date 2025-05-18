# Pharos Network Bot

A Python toolset to automate interactions with the Pharos Network testnet. This repository contains two main bots:

- **Transaction Bot**: Sends multiple transactions with randomized amounts.
- **Faucet Bot**: Claims testnet tokens automatically and forwards them to a central wallet.

---

## Features

### Transaction Bot
- Connects to multiple Pharos testnet RPC endpoints
- Sends transactions with randomized amounts
- Automatic transaction verification via API
- Detailed logging with colored output
- Monitors transaction confirmations
- Generates statistical reports for transaction batches

### Faucet Bot
- Creates multiple wallets automatically
- Claims testnet tokens from the faucet
- Forwards claimed tokens to a central wallet
- Proxy support for improved success rates
- Detailed logging and progress tracking
- Saves wallet information for future use

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

Before running the transaction bot, create the following files in the project directory:

- **private_key.txt**: Your Ethereum private key (without the '0x' prefix)
- **token.txt**: Your Pharos Network API bearer token
- **recipients.txt**: List of Ethereum addresses to receive transactions (one per line)

### Faucet Bot

To use the faucet bot:

1. Navigate to the faucet directory:  
   `cd faucet`
2. Create a `.env` file (you can copy from `.env.example`)
3. (Optional) Configure proxies in `proxy.txt` for better success rates
4. The bot will save generated wallets to `wallets.txt`

---

## How to Obtain a Pharos Network API Token

The API token is required for transaction verification:

1. Visit [Pharos Network Testnet](https://testnet.pharosnetwork.xyz/)
2. Click "Connect Wallet" (top-right corner)
3. Connect with your Ethereum wallet (MetaMask recommended)
4. Press `F12` to open browser developer tools
5. Go to the "Application" tab
6. In the left sidebar, expand "Local Storage"
7. Click the website domain (`pharosnetwork.xyz`)
8. Find an entry with "PHAROS_AUTHORIZATION_TOKEN" in the key
9. Copy the value (starts with `eyJ...`)
10. Paste it into `token.txt`

---

## Usage

### Transaction Bot

Run the transaction bot:

```bash
python3 bot.py
```

Follow the interactive prompts to configure:

- Number of cycles (transactions) to send
- Minimum and maximum transaction amounts
- Delay between transactions (seconds)
- Gas price (gwei) and gas limit

**Example configuration:**
```
=== Transaction Configuration ===
Number of cycles to run: 5
Minimum amount to send (default: 0.001): 0.0001
Maximum amount to send (default: 0.002): 0.0002
Delay between transactions in seconds (default: 30): 20
Gas price in gwei (default: 5.00): 5
Gas limit (default: 21000): 21000
```

### Faucet Bot

Run the faucet bot:

```bash
cd faucet
python3 faucet.py
```

You'll be prompted to:
- Enter the recipient address (where all claimed tokens will be sent)
- Enter the number of faucet claims to perform

The bot will:
1. Create new wallets
2. Register them with the Pharos Network
3. Claim tokens from the faucet
4. Forward the tokens to your specified address

---

## Security Notice

⚠️ **IMPORTANT** ⚠️

- **Never share your `private_key.txt` or commit it to a public repository**
- **Keep your `token.txt` confidential**
- Both files are included in `.gitignore` to prevent accidental exposure
- The faucet bot generates new wallets and saves them to `wallets.txt` – keep this file secure

---

## File Structure

```
.
├── bot.py                  # Main transaction bot script
├── requirements.txt        # Python dependencies
├── private_key.txt         # Your private key (keep secure)
├── token.txt               # API bearer token (keep secure)
├── recipients.txt          # List of recipient addresses
├── .gitignore              # Prevents sensitive files from being committed
├── readme.md               # Documentation
└── faucet/                 # Faucet bot directory
    ├── faucet.py           # Faucet bot script
    ├── .env                # Environment configuration (keep secure)
    ├── .env.example        # Example configuration template
    ├── proxy.txt           # List of proxies for faucet claims (optional)
    └── wallets.txt         # Generated wallets (keep secure)
```

---

## Troubleshooting

### Connection Issues
- Check your internet connection
- Try running the bot at a different time (servers may be busy)
- Ensure you're not behind a restrictive firewall

### Transaction Errors
- Make sure your account holds sufficient PHRS tokens
- Confirm the gas price is adequate
- Verify your private key is correct

### API Verification Failures
- Your token may have expired (tokens usually last 30 days)
- Obtain a new token (see instructions above)
- Check that the `task_id` in the code is correct

### Faucet Claim Failures
- Add more proxies to improve success rate
- Some IP addresses may be rate-limited
- Try smaller batch sizes by editing the `.env` file

---


## License

This project is open source and free to use.