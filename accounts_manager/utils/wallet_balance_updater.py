import asyncio
import sys

import yaml
from aiosteampy.ext.user_agents import UserAgentsService


def load_config():
    config_path = r"C:\Users\Sivasai\Documents\GitHub\CaseFarm\config.yaml"
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    return config


_config = load_config()
ROOT_DIR = _config["ROOT_DIR"]
sys.path.insert(0, ROOT_DIR)
from tqdm.asyncio import tqdm

from database import (
    get_all_steam_accounts,
    get_client,
    steam_api_call_with_retry,
    update_steam_balance,
)
from utils.logger import get_custom_logger

logger = get_custom_logger()


async def update_steam_wallet_balances(steam_username: str | None = None) -> bool:
    """Updates the Steam wallet balances for all accounts or a specific account.

    Args:
        steam_username (str | None, optional): if No username is given then all prime accounts are updated. Defaults to None.

    Returns:
        bool: Whether or not the update was successful.
    """
    if steam_username:
        matching_accounts = [steam_username]
    all_accounts = get_all_steam_accounts()
    matching_accounts = [acc for acc in all_accounts if acc["prime"]]
    user_agents = UserAgentsService()
    await user_agents.load()

    semaphore = asyncio.Semaphore(5)
    success = True
    errors = []

    async def update_account(account):
        nonlocal success
        async with semaphore:
            try:
                username = account["steam_username"]
                account_currency = account["currency"]

                client = await get_client(account)

                wallet_balance_cents_final = await steam_api_call_with_retry(
                    client.get_wallet_balance
                )
                wallet_balance_final = wallet_balance_cents_final / 100
                update_steam_balance(username, wallet_balance_final)

                if wallet_balance_final > 5 * account["pass_value"]:
                    print("\n\n\n")
                    logger.info(
                        f"Steam wallet balance for {username} is sufficient to begin farming: {wallet_balance_final} {account_currency}"
                    )
                    print("\n\n\n")
            except Exception as e:
                logger.error(
                    f"Failed to update balance for {account['steam_username']}: {e}"
                )
                success = False
                errors.append(account["steam_username"])

    await tqdm.gather(
        *(update_account(account) for account in matching_accounts),
        desc="Updating Steam Wallet Balances",
    )

    if success:
        logger.success("All Steam wallet balances updated successfully.")
        return True
    else:
        logger.error(f"Some Steam wallet balances failed to update: {errors}")
        return False


if __name__ == "__main__":
    import asyncio

    asyncio.run(update_steam_wallet_balances())
