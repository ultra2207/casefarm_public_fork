import sys

import yaml


def load_config():
    config_path = r"C:\Users\Sivasai\Documents\GitHub\CaseFarm\config.yaml"
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    return config


_config = load_config()
ROOT_DIR = _config["ROOT_DIR"]
sys.path.insert(0, ROOT_DIR)
from utils.logger import get_custom_logger

logger = get_custom_logger()


import asyncio
import json

from aiosteampy import SteamClient
from aiosteampy.ext import user_agents
from tqdm import tqdm

from database import get_client, get_steam_credentials, steam_api_call_with_retry


# Function to get trade offers
async def get_trades(client: SteamClient) -> list:
    try:
        trade_offers = await steam_api_call_with_retry(
            client.get_trade_offers, sent=False
        )
    except Exception as e:
        logger.error(f"Caught Exception: {e}")
    return trade_offers


# Function to process a single account
async def accept_trades_account(username: str) -> None:
    # Special case for sivasai2208 - use .maFile
    if username == "sivasai2208":
        mafile_path = r"C:\Users\Sivasai\Documents\GitHub\CaseFarm\utils\cache\miscellaneous\sivasai2208.maFile"

        with open(mafile_path, "r", encoding="utf-8") as f:
            mafile_data = json.load(f)

        password: str = mafile_data["steam_password"]  # Now reading from .maFile

        logger.info(f"Using .maFile for special account {username}")
    else:
        # Use existing logic for all other usernames
        credentials = get_steam_credentials(username)
        password: str = credentials["steam_password"]
    logger.info(
        f"Logging into account with username {username} and password {password} to accept trades..."
    )

    u_a = user_agents.UserAgentsService()
    await u_a.load()

    try:
        client = await get_client(credentials)

        trade_offers: list = []

        trade_offers = await get_trades(client=client)
        if trade_offers[1]:
            trade_offer_items = trade_offers[1]

            # Wrap the trade_offer_items in tqdm to show progress
            for trade_offer in tqdm(
                trade_offer_items, desc="Processing Trade Offers", unit="offer"
            ):
                if trade_offer.is_active:
                    await steam_api_call_with_retry(
                        client.accept_trade_offer, obj=trade_offer, confirm=True
                    )

    except Exception as e:
        logger.error(e)


# Function to process multiple accounts with semaphore
async def accept_trades_multiple_accounts(
    usernames: list[str], max_concurrent: int = 5
) -> None:
    """
    Accept trades for multiple accounts concurrently with a semaphore to limit concurrent operations.

    Args:
        usernames: List of usernames to process
        max_concurrent: Maximum number of accounts to process simultaneously (default: 5)
    """
    semaphore = asyncio.Semaphore(max_concurrent)

    async def process_with_semaphore(username: str) -> None:
        async with semaphore:
            try:
                await accept_trades_account(username)
                logger.info(f"Completed trade acceptance for {username}")
            except Exception as e:
                logger.error(f"Failed to process trades for {username}: {e}")

    # Create tasks for all accounts
    tasks = [process_with_semaphore(username) for username in usernames]

    # Wait for all tasks to complete
    await asyncio.gather(*tasks, return_exceptions=True)

    logger.info(f"Completed trade acceptance for all {len(usernames)} accounts")


# Main function to process the account based on the provided index and sleep time
async def main() -> None:
    await accept_trades_multiple_accounts(usernames=["brainyCod11974"])


# Entry point
if __name__ == "__main__":
    asyncio.run(main())
