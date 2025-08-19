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

from aiosteampy.ext.user_agents import UserAgentsService
from tqdm import tqdm

from database import (
    get_all_steam_accounts,
    get_client,
    save_cookies_and_close_session,
    steam_api_call_with_retry,
    update_trade_token,
    update_trade_url,
)


async def update_trade_tokens_db() -> None:
    """Populates the missing trade tokens in the db."""
    all_accounts: list[dict] = get_all_steam_accounts()
    logger.info(f"Retrieved {len(all_accounts)} accounts from database")

    # if trade_token is null then update that account with its trade token
    user_agents = UserAgentsService()
    await user_agents.load()
    logger.debug("User agents service loaded")

    # Using tqdm to wrap the iteration
    for account in tqdm(all_accounts, desc="Processing accounts"):
        if account["trade_token"] is None:
            username: str = account["steam_username"]
            logger.debug(f"Processing account: {username} to update trade token")

            client = await get_client(account)
            logger.debug(f"Successfully logged in: {username}")

            token: str | None = await steam_api_call_with_retry(client.get_trade_token)
            logger.info(f"Retrieved trade token for {username}")

            # update it in the db
            update_trade_token(account["steam_username"], token)
            logger.info(f"Updated trade token in database for {username}")

            try:
                await save_cookies_and_close_session(client)
            except Exception as e:
                logger.error(f"Error closing session for {username}: {e}")

        if account["trade_url"] is None:
            DIFFERENCE_VALUE: int = 76561197960265728
            token: str | None = account["trade_token"]
            steam_partner_id: int = int(account["steam_id"]) - DIFFERENCE_VALUE
            account_trade_url: str = f"https://steamcommunity.com/tradeoffer/new/?partner={steam_partner_id}&token={token}"
            # update it in the db
            update_trade_url(account["steam_username"], account_trade_url)
            logger.info(
                f"Updated trade URL in database for {account['steam_username']}"
            )


async def main() -> None:
    """Main entry point for the script."""
    logger.info("Starting trade tokens update process")
    await update_trade_tokens_db()
    logger.success("Trade tokens update completed successfully")


if __name__ == "__main__":
    asyncio.run(main())
