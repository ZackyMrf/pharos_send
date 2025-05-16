# Pharos Network Transaction Bot

A Python bot for automating transactions on the Pharos Network testnet. This tool allows users to send multiple transactions with randomized amounts to different recipient addresses.

---

## Features

- Connects to multiple Pharos testnet RPC endpoints
- Sends transactions with randomized amounts
- Automatic transaction verification via API
- Detailed logging with colored output
- Monitors transaction confirmations
- Generates statistical reports for transaction batches

---

## Requirements

- Python 3.8 or newer
- Required packages:
  - `web3` (>=6.0.0)
  - `requests` (>=2.28.0)
  - `colorama` (>=0.4.4)

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

Before running the bot, prepare the following files in the project directory:

- **private_key.txt**: Your Ethereum private key (without '0x' prefix)
- **token.txt**: Your Pharos Network API bearer token
- **recipients.txt**: List of Ethereum addresses to receive transactions (one per line)

### How to Obtain a Pharos Network API Token

The bot requires an API token for transaction verification. To get it:

1. Visit [Pharos Network Testnet](https://testnet.pharosnetwork.xyz/)
2. Click "Connect Wallet" (top-right corner)
3. Connect with your Ethereum wallet (MetaMask recommended)
4. Press `F12` to open browser developer tools
5. Go to the "Application" tab
6. In the left sidebar, expand "Local Storage"
7. Click the website domain (pharosnetwork.xyz)
8. Find an entry with "PHAROS_AUTHORIZATION_TOKEN" in the key name
9. Copy the value (starts with `eyJ...`)
10. Paste it into `token.txt`

---

## Usage

Run the bot with:

```bash
python bot.py
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

---

## Security Notice

⚠️ **IMPORTANT** ⚠️

- Never share your `private_key.txt` or commit it to a public repository.
- Keep your `token.txt` confidential.
- Both files are included in `.gitignore` to prevent accidental exposure.

---

## File Structure

- `bot.py` : Main script for the transaction bot
- `requirements.txt` : Python dependencies
- `private_key.txt` : Your private key (**keep secure**)
- `token.txt` : Your API bearer token (**keep secure**)
- `recipients.txt` : List of recipient addresses
- `.gitignore` : Prevents sensitive files from being committed
- `readme.md` : This documentation

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

---

## License

This project is open source and free to use.