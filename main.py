import asyncio
import json
import time
import requests
from colorama import init, Fore, Style
from web3 import Web3
import aiohttp
import argparse
from utils.banner import banner

init(autoreset=True)

print(Fore.CYAN + Style.BRIGHT + banner + Style.RESET_ALL)

# Konfigurasi
RPC_URL = "https://mainnet.base.org"
CONTRACT_ADDRESS = "0xC5bf05cD32a14BFfb705Fb37a9d218895187376c"
api_url = "https://hanafuda-backend-app-520478841386.us-central1.run.app/graphql"
AMOUNT_ETH = 0.0000000001  # Jumlah ETH untuk deposit
web3 = Web3(Web3.HTTPProvider(RPC_URL))

# Konfigurasi Telegram
TELEGRAM_BOT_TOKEN = "7606503038:AAGkbnoTvtIXNKHL2IajzikXQAVezBWKaWM"
TELEGRAM_CHAT_ID = "756671280"

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        response = requests.post(url, json=payload)
        if response.status_code != 200:
            print(f"Failed to send message: {response.text}")
    except Exception as e:
        print(f"Error sending message to Telegram: {e}")

# Load private keys dan access tokens
def load_keys(filename):
    with open(filename, "r") as file:
        return [line.strip() for line in file if line.strip()]

private_keys = load_keys("pvkey.txt")
access_tokens = load_keys("token.txt")

contract_abi = '''[
    {"constant": false, "inputs": [], "name": "depositETH", "outputs": [], "stateMutability": "payable", "type": "function"}
]'''

headers = {
    'Accept': '*/*',
    'Content-Type': 'application/json',
    'User-Agent': "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X)"
}

async def colay(session, url, method, payload_data=None):
    async with session.request(method, url, headers=headers, json=payload_data) as response:
        if response.status != 200:
            raise Exception(f'HTTP error! Status: {response.status}')
        return await response.json()

async def refresh_access_token(session, refresh_token):
    api_key = "AIzaSyDipzN0VRfTPnMGhQ5PSzO27Cxm3DohJGY"
    async with session.post(
        f'https://securetoken.googleapis.com/v1/token?key={api_key}',
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data=f'grant_type=refresh_token&refresh_token={refresh_token}'
    ) as response:
        if response.status != 200:
            raise Exception("Failed to refresh access token")
        return (await response.json()).get('access_token')

async def handle_grow_and_garden(session, refresh_token, account_index):  
    new_access_token = await refresh_access_token(session, refresh_token)
    headers['authorization'] = f'Bearer {new_access_token}'
    
    info_query = {"query": "query getCurrentUser { currentUser { id totalPoint depositCount } getGardenForCurrentUser { gardenStatus { growActionCount gardenRewardActionCount } } }"}
    info = await colay(session, api_url, 'POST', info_query)
    
    balance = info['data']['currentUser']['totalPoint']
    deposit = info['data']['currentUser']['depositCount']
    grow = info['data']['getGardenForCurrentUser']['gardenStatus']['growActionCount']
    garden = info['data']['getGardenForCurrentUser']['gardenStatus']['gardenRewardActionCount']
    
    log_message = f"Akun {account_index}:\nPOINTS: {balance} | Deposit Counts: {deposit} | Grow left: {grow} | Garden left: {garden}"
    print(Fore.GREEN + log_message + Style.RESET_ALL)
    send_telegram_message(log_message)

    async def grow_action():
        grow_action_query = {"query": "mutation executeGrowAction { executeGrowAction(withAll: true) { totalValue multiplyRate } }"}
        mine = await colay(session, api_url, 'POST', grow_action_query)
        return mine['data']['executeGrowAction']['totalValue'] if mine and 'data' in mine and 'executeGrowAction' in mine['data'] else 0
    
    if grow > 0:
        reward = await grow_action()
        if reward:
            balance += reward
            grow = 0
            reward_message = f"Akun {account_index}:\nRewards: {reward} | Balance: {balance} | Grow left: {grow}"
            print(Fore.GREEN + reward_message + Style.RESET_ALL)
            send_telegram_message(reward_message)

async def main(mode, num_transactions=None):
    async with aiohttp.ClientSession() as session:
        if mode == '1':
            if num_transactions is None:
                num_transactions = int(input(Fore.YELLOW + "Enter the number of transactions: " + Style.RESET_ALL))
            await handle_eth_transactions(session, num_transactions)
        elif mode == '2':
            while True:
                for index, refresh_token in enumerate(access_tokens, start=1):
                    await handle_grow_and_garden(session, refresh_token, index)  
                print(f"{Fore.RED}All accounts processed. Cooling down for 1 Hour...{Style.RESET_ALL}")
                time.sleep(3600)
        else:
            print(Fore.RED + "Invalid option. Choose 1 or 2." + Style.RESET_ALL)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Choose the mode of operation.')
    parser.add_argument('-a', '--action', choices=['1', '2'], help='1: Execute Transactions, 2: Grow and Garden')
    parser.add_argument('-tx', '--transactions', type=int, help='Number of transactions (optional for action 1)')
    args = parser.parse_args()

    if args.action is None:
        args.action = input(Fore.YELLOW + "Choose action (1: Execute Transactions, 2: Grow and Garden): " + Style.RESET_ALL)
    
    asyncio.run(main(args.action, args.transactions))
