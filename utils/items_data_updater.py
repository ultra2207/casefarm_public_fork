import asyncio
import sys

import yaml
from aiosteampy.ext.user_agents import UserAgentsService
from aiosteampy.models import EconItem
from tqdm.asyncio import tqdm_asyncio


def load_config():
    config_path = r"C:\Users\Sivasai\Documents\GitHub\CaseFarm\config.yaml"
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    return config


_config = load_config()
ROOT_DIR = _config["ROOT_DIR"]
sys.path.insert(0, ROOT_DIR)
from database import (
    get_all_steam_accounts,
    get_client,
    get_full_inventory,
    refresh_items_database,
)
from utils.logger import get_custom_logger

logger = get_custom_logger()

from datetime import datetime, timedelta, timezone


def load_config() -> dict:
    config_path = r"C:\Users\Sivasai\Documents\GitHub\CaseFarm\config.yaml"
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    return config


_config = load_config()
# Load configuration
ACCOUNT_PROCESSING_SEMAPHORE = _config.get("ITEMS_DATA_UPDATER_ACCOUNTS_SEMAPHORE")

# IST timezone offset
IST_OFFSET = timedelta(hours=5, minutes=30)

# Format for parsing tradable after date strings
TRADABLE_AFTER_DATE_FORMAT = "Tradable/Marketable After %b %d, %Y (%H:%M:%S) GMT"


def process_inventory(inv: list[list[EconItem]], steam_username: str) -> bool:
    """
    Process items in inventory and refresh database with extracted information.
    Returns True if successful, False if errors occurred.
    """
    try:
        logger.trace(f"Starting inventory processing for {len(inv[0])} items")

        # List to collect all items for batch database update
        items_list = []

        # Get current timestamp for last_updated fields
        current_utc_dt = datetime.now(timezone.utc)
        current_ist_dt = current_utc_dt + IST_OFFSET
        last_updated_unix = int(current_utc_dt.timestamp())
        last_updated_ist = current_ist_dt.strftime("%d-%m-%Y %I:%M %p")

        for item in inv[0]:
            try:
                logger.trace(f"Processing item with asset_id: {item.asset_id}")

                # Extract market_hash_name
                market_hash_name = item.description.market_hash_name

                # Extract asset_id
                asset_id = item.asset_id

                # Get tradable and marketable status
                tradable = item.description.tradable
                marketable = item.description.marketable

                # Validate tradable and marketable have matching values
                if tradable != marketable:
                    logger.error(
                        f"Item {asset_id} has mismatched tradable ({tradable}) and marketable ({marketable}) values"
                    )

                # Get tradable_after datetime
                tradable_after_dt = None
                if item.tradable_after:
                    tradable_after_dt = item.tradable_after
                else:
                    sep = "Tradable/Marketable After "
                    t_a_descr = next(
                        (
                            d
                            for d in item.description.owner_descriptions
                            if d.value and sep in d.value
                        ),
                        None,
                    )
                    if t_a_descr:
                        tradable_after_str = t_a_descr.value
                        tradable_after_dt = datetime.strptime(
                            tradable_after_str, TRADABLE_AFTER_DATE_FORMAT
                        )

                # If tradable_after is None, both tradable and marketable should be True
                if not tradable_after_dt and (not tradable or not marketable):
                    logger.error(
                        f"Item {asset_id} has no trade restriction but tradable={tradable}, marketable={marketable}"
                    )

                # Convert to required format
                if tradable_after_dt:
                    # Convert GMT datetime to IST
                    tradable_after_ist_dt = tradable_after_dt + IST_OFFSET
                    # Format to 'DD-MM-YYYY hh:mm AM/PM' with capital AM/PM and no seconds
                    tradable_after_ist = tradable_after_ist_dt.strftime(
                        "%d-%m-%Y %I:%M %p"
                    )
                    # Convert to Unix timestamp
                    tradable_after_unix = int(
                        tradable_after_dt.replace(tzinfo=timezone.utc).timestamp()
                    )
                else:
                    tradable_after_ist = ""
                    tradable_after_unix = 0

                # Add item to batch update list with the tradable and marketable values
                items_list.append(
                    {
                        "market_hash_name": market_hash_name,
                        "tradable_after_ist": tradable_after_ist,
                        "asset_id": asset_id,
                        "tradable_after_unix": tradable_after_unix,
                        "tradable": 1
                        if tradable
                        else 0,  # Convert boolean to SQLite integer
                        "marketable": 1
                        if marketable
                        else 0,  # Convert boolean to SQLite integer
                        "last_updated_unix": last_updated_unix,
                        "last_updated_ist": last_updated_ist,
                    }
                )

                logger.trace(f"Successfully processed item with asset_id: {asset_id}")

            except Exception as item_error:
                logger.error(
                    f"Error processing item with asset_id {item.asset_id}: {item_error}"
                )
                # Continue processing other items despite this error

        success = refresh_items_database(items_list, steam_username)
        logger.trace(f"Updated database with {len(items_list)} items")
        return success

    except Exception as e:
        logger.error(f"Fatal error in inventory processing: {e}")
        return False


async def process_account(account) -> tuple[str, bool]:
    """Get the inventory for a single account."""

    username = account["steam_username"]
    client = await get_client(account)
    try:
        inv = await get_full_inventory(client)

    except Exception as e:
        logger.error(f"Failed to get inventory for {username}: {e}")

        return username, False

    success = process_inventory(inv, username)
    return username, success


async def update_items(
    steam_usernames=None, account_processing_concurrency=ACCOUNT_PROCESSING_SEMAPHORE
) -> bool:
    """
    Main function to select and list items on farming accounts.

    Args:
        steam_usernames (list, optional): List of Steam usernames to process.
                                         Defaults to None, which processes all prime accounts.
                                         If specific usernames are provided, only those prime accounts will be processed.
        account_processing_concurrency (int, optional): Number of accounts to process concurrently.
                                                        Defaults to ACCOUNT_PROCESSING_SEMAPHORE.
    """
    user_agents = UserAgentsService()
    await user_agents.load()
    all_accounts = get_all_steam_accounts()

    # Filter accounts based on steam_usernames or get all prime accounts
    if steam_usernames:
        selected_accounts = [
            acc
            for acc in all_accounts
            if acc["steam_username"] in steam_usernames and acc["prime"]
        ]
        print("\n")
        logger.info(
            f"Fetching inventory data for {len(selected_accounts)} specified prime accounts..."
        )
    else:
        selected_accounts = [acc for acc in all_accounts if acc["prime"]]
        print("\n")
        logger.info(f"Processing all {len(selected_accounts)} prime accounts...")

    # Create semaphore to limit concurrent processing
    semaphore = asyncio.Semaphore(account_processing_concurrency)

    async def process_account_with_semaphore(account) -> tuple[str, bool]:
        async with semaphore:
            logger.info(f"Processing {account['steam_username']}...")
            return await process_account(account)

    # Create tasks for all accounts
    tasks = [process_account_with_semaphore(account) for account in selected_accounts]

    # Process tasks with progress bar
    results = []
    failed_accounts = []
    for future in tqdm_asyncio.as_completed(tasks, total=len(tasks)):
        username, success = await future
        results.append(success)
        if not success:
            failed_accounts.append(username)

    # Log success or error based on results
    if all(results):
        logger.success("All accounts processed successfully.")
    else:
        failed_count = len(failed_accounts)
        logger.error(f"{failed_count} account(s) failed to process.")
        for username in failed_accounts:
            logger.warning(f"Failed account: {username}")

    return all(results)


if __name__ == "__main__":
    asyncio.run(update_items())
