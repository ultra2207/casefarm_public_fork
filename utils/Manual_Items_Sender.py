import asyncio
import logging
from typing import Any, Union

from aiosteampy import SteamClient
from aiosteampy.ext.user_agents import UserAgentsService

logging.getLogger("asyncio").setLevel(logging.CRITICAL)
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
from database import (
    convert,
    get_account_details,
    get_all_steam_accounts,
    get_db_price,
    save_cookies_and_close_session,
    steam_api_call_with_retry,
    update_prices_from_market,
)
from utils.logger import get_custom_logger
from utils.trade_acceptor import accept_trades_account

logger = get_custom_logger()

from tqdm.asyncio import tqdm_asyncio


def load_config() -> dict:
    config_path = r"C:\Users\Sivasai\Documents\GitHub\CaseFarm\config.yaml"
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    return config


_config = load_config()

# Constants
CS2_APP_ID = "730"
MANUAL_ITEMS_SENDER_MULTIPLIER = _config.get("MANUAL_ITEMS_SENDER_MULTIPLIER", 1)
MAIN_ACCOUNT_TRADE_URL = _config.get(
    "MAIN_ACCOUNT_TRADE_URL",
    "https://steamcommunity.com/tradeoffer/new/?partner=1597113567&token=zXZIog_y",
)
ACCOUNT_INVENTORY_SEMAPHORE = _config.get(
    "ACCOUNT_INVENTORY_SEMAPHORE_MANUAL_SENDER", 5
)


async def send_to_main_account(
    client: SteamClient, items: list[Any], total_value: Union[int, float]
) -> str | None:
    """Send selected items to the main account."""
    try:
        trade_offer_id = await steam_api_call_with_retry(
            client.make_trade_offer,
            obj=MAIN_ACCOUNT_TRADE_URL,
            to_give=items,
            to_receive=[],
            message="Sending item to main account",
            confirm=True,
        )
        logger.success(
            f"{len(items)} items sent to main account with trade offer id: {trade_offer_id} and value {total_value}"
        )
        return trade_offer_id
    except Exception as e:
        logger.error(f"Error sending trade offer: {e}")
        return None


async def select_items_for_balanced_transfer(
    account_data_list: list[dict[str, Any]], target_transfer_amount: int | float
) -> list[dict[str, Any]] | None:
    """
    Select items from accounts to transfer the target amount while respecting
    armoury pass grouping rules and using a round-robin selection approach.
    """

    # Calculate current total value and tradable value across all accounts
    total_current_value = sum(account["total_value"] for account in account_data_list)
    total_tradable_value = sum(
        account["listable_value"] for account in account_data_list
    )
    print("\n")
    logger.info("--- Value Balancing Plan ---")
    logger.info(
        f"Total inventory value across all accounts: ₹{total_current_value:.2f}"
    )
    logger.info(
        f"Total tradable value across all accounts: ₹{total_tradable_value:.2f}"
    )
    logger.info(f"Target transfer to main account: ₹{target_transfer_amount:.2f}")

    # Store the items to transfer from each account
    transfer_plan = []

    # Calculate each account's minimum safe threshold based on armoury passes
    for account_data in account_data_list:
        account_username = account_data["account"]["steam_username"]
        current_value = account_data["total_value"]
        tradable_value = account_data["listable_value"]
        wallet_balance = account_data["account"]["steam_balance"]
        armoury_bool = account_data["account"]["is_armoury"]
        num_active_passes = account_data["active_armoury_passes"]
        pass_value = account_data["pass_value"] * 1.15
        # Calculate armoury value based on the grouping rules
        armoury_value = 5 * pass_value if armoury_bool else 0

        # Create a transfer plan entry
        transfer_plan.append(
            {
                "account_data": account_data,
                "username": account_username,
                "current_value": current_value,
                "tradable_value": tradable_value,
                "wallet_balance": wallet_balance,
                "armoury_value": armoury_value,
                "num_active_passes": num_active_passes,
                "items_to_transfer": [],
                "transfer_value": 0,
                "currency": account_data["currency"],
            }
        )

    # Calculate total achievable transfer amount
    total_achievable = sum(
        max(
            0,
            min(
                (
                    plan["tradable_value"] / 1.15
                    + plan["wallet_balance"]
                    - plan["armoury_value"]
                ),
                plan["tradable_value"],
            ),
        )
        for plan in transfer_plan
    )

    if total_achievable < target_transfer_amount:
        print("\n")
        logger.warning(
            f"⚠️ WARNING: Cannot safely transfer ₹{target_transfer_amount:.2f}."
        )
        logger.warning(f"Maximum safe transfer amount: ₹{total_achievable:.2f}")
        print("\n")
        confirm = input(
            "Do you want to proceed with this selling plan? (y/n): "
        ).lower()
        if confirm != "y":
            return None

        target_transfer_amount = total_achievable

    # Round-robin item selection
    remaining_target = target_transfer_amount
    accounts_exhausted = False

    # Pre-sort all tradable items by value (descending)
    for plan in transfer_plan:
        plan["remaining_items"] = sorted(
            plan["account_data"]["listable_items"],
            key=lambda x: x["price"],
            reverse=True,
        )
        plan["current_item_index"] = 0

    # Continue until we've reached the target or can't add more items
    while remaining_target > 0 and not accounts_exhausted:
        accounts_exhausted = True

        # Try to take one item from each account in turn
        for plan in transfer_plan:
            # Skip if we've reached our target
            if remaining_target <= 0:
                break

            tradable_value = plan["tradable_value"] - plan["transfer_value"]
            armoury_value = plan["armoury_value"]

            # Find the next item we can safely take
            item_found = False
            while plan["current_item_index"] < len(plan["remaining_items"]):
                item = plan["remaining_items"][plan["current_item_index"]]
                plan["current_item_index"] += 1

                # Check if removing this item would drop below minimum safe value
                if (
                    (tradable_value - item["price"]) / 1.15 + plan["wallet_balance"]
                ) >= armoury_value:
                    # Add this item to the transfer
                    plan["items_to_transfer"].append(item["item"])
                    plan["transfer_value"] += item["price"]
                    remaining_target -= item["price"]
                    accounts_exhausted = False
                    item_found = True
                    break

            if item_found:
                # We found an item to transfer from this account
                accounts_exhausted = False

    # Calculate actual total transfer
    total_transfer = sum(plan["transfer_value"] for plan in transfer_plan)

    # Print the plan
    print("\n")
    logger.info("--- Transfer Plan ---")
    logger.info(
        f"Total items to transfer: {sum(len(plan['items_to_transfer']) for plan in transfer_plan)}"
    )
    logger.info(
        f"Total transfer value: ₹{total_transfer:.2f} (Target: ₹{target_transfer_amount:.2f})"
    )
    print("\n")
    logger.info("Per-Account Breakdown:")
    for plan in transfer_plan:
        remaining_safe_margin = (
            plan["tradable_value"] - plan["transfer_value"]
        ) / 1.15 + plan["wallet_balance"]
        print("\n")
        logger.info(f"{plan['username']}:")
        logger.info(f"  Tradable value: ₹{plan['tradable_value']:.2f}")
        logger.info(f"  Armoury value threshold: ₹{plan['armoury_value']:.2f}")
        logger.info(
            f"  Items to transfer: {len(plan['items_to_transfer'])} (₹{plan['transfer_value']:.2f})"
        )
        logger.info(
            f"Remaining safe margin after transfer: ₹{remaining_safe_margin:.2f}"
        )

    # Check if transfer would drop inventory value below armory pass threshold for any account
    warning_accounts = []
    for plan in transfer_plan:
        post_transfer_value = (
            plan["tradable_value"] - plan["transfer_value"]
        ) / 1.15 + plan["wallet_balance"]
        if post_transfer_value < plan["armoury_value"]:
            warning_accounts.append(
                {
                    "username": plan["username"],
                    "post_value": post_transfer_value,
                    "armoury_value": plan["armoury_value"],
                    "deficit": plan["armoury_value"] - post_transfer_value,
                }
            )

    if warning_accounts:
        print("\n")
        logger.warning(
            "⚠️ WARNING: Trading these items will drop inventory value below armory pass threshold for these accounts:"
        )
        for acc in warning_accounts:
            logger.warning(
                f"• {acc['username']}: Post-transfer value (₹{acc['post_value']:.2f}) will be ₹{acc['deficit']:.2f} below armory passes value (₹{acc['armoury_value']:.2f})"
            )

    # Ask for confirmation
    print("\n")
    confirm = input("Do you want to proceed with this selling plan? (y/n): ").lower()
    if confirm != "y":
        return None

    return transfer_plan


async def execute_transfer_plan(
    transfer_plan: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Execute trades according to the transfer plan."""
    trade_results = []

    for plan in transfer_plan:
        if not plan["items_to_transfer"]:
            continue

        account = plan["account_data"]["account"]
        username = account["steam_username"]

        client = plan["account_data"]["logged_in_client"]
        try:
            print("\n")
            logger.info(
                f"Sending {len(plan['items_to_transfer'])} items from {username} (value: ₹{plan['transfer_value']:.2f})"
            )
            try:
                trade_offer_id = await send_to_main_account(
                    client, plan["items_to_transfer"], plan["transfer_value"]
                )
                trade_results.append(
                    {
                        "account": username,
                        "trade_id": trade_offer_id,
                        "items_count": len(plan["items_to_transfer"]),
                        "value": plan["transfer_value"],
                        "success": trade_offer_id is not None,
                    }
                )
            except Exception as e:
                logger.error(f"Error sending trade from {username}: {e}")
                trade_results.append(
                    {
                        "account": username,
                        "trade_id": None,
                        "items_count": len(plan["items_to_transfer"]),
                        "value": plan["transfer_value"],
                        "success": False,
                        "error": str(e),
                    }
                )
        finally:
            try:
                if client:
                    await save_cookies_and_close_session(client)
            except Exception as e:
                logger.error(f"Error during logout: {e}")

    # Print summary
    print("\n")
    logger.info("--- Trade Summary ---")
    successful_trades = [t for t in trade_results if t["success"]]
    failed_trades = [t for t in trade_results if not t["success"]]

    total_items = sum(t["items_count"] for t in successful_trades)
    total_value = sum(t["value"] for t in successful_trades)

    logger.info(f"Total items traded: {total_items}")
    logger.info(f"Total value traded: ₹{total_value:.2f}")
    logger.info(f"Successful trades: {len(successful_trades)}")
    logger.info(f"Failed trades: {len(failed_trades)}")

    if failed_trades:
        print("\n")
        logger.warning("Failed trades:")
        for trade in failed_trades:
            logger.warning(
                f"- {trade['account']}: {trade['items_count']} items, ₹{trade['value']:.2f}"
            )
            if "error" in trade:
                logger.error(f"  Error: {trade['error']}")

    return trade_results


async def items_sender(autoaccept_trades: bool = False) -> bool:
    """Main function to select and send items from farming accounts to main account."""
    user_agents = UserAgentsService()
    await user_agents.load()
    all_accounts = get_all_steam_accounts()

    # Get inventory for all prime accounts
    account_data_list = []
    prime_accounts = [acc for acc in all_accounts if acc["prime"]]

    print("\n")
    logger.info(f"Fetching inventory data for {len(prime_accounts)} prime accounts...")

    async def process_accounts_inventory(selected_accounts) -> list:
        semaphore = asyncio.Semaphore(ACCOUNT_INVENTORY_SEMAPHORE)
        account_data_list = []

        async def process_account(account) -> dict:
            async with semaphore:
                logger.info(f"Processing {account['steam_username']}...")
                account_data = await get_account_details(account)
                return account_data

        tasks = [process_account(account) for account in selected_accounts]
        for future in tqdm_asyncio.as_completed(tasks):
            account_data = await future
            account_data_list.append(account_data)

        return account_data_list

    account_data_list = await process_accounts_inventory(prime_accounts)

    # Initialize dictionary to hold sets of items for each currency
    items_by_currency = {}

    for account_data in account_data_list:
        currency = account_data["currency"]

        # If this currency doesn't exist in dict, add it with empty set
        if currency not in items_by_currency:
            items_by_currency[currency] = set()

        # Add all listable items from this account to the currency's set
        for item in account_data["listable_items"]:
            items_by_currency[currency].add(item["name"])

    # Convert all sets to lists for compatibility
    items_by_currency = {
        currency: list(items) for currency, items in items_by_currency.items()
    }

    clients = [
        account_data["logged_in_client"]
        for account_data in account_data_list
        if account_data.get("logged_in_client")
    ]

    await update_prices_from_market(
        items_by_currency=items_by_currency,
        override_armoury_only=True,
        multiple_clients=clients,
    )

    # Update prices and calculate values for all accounts
    for account_data in account_data_list:
        listable_value = 0
        non_listable_value = 0

        for item in account_data["listable_items"]:
            to_convert = await get_db_price(
                item["name"],
                client=account_data["logged_in_client"],
                currency=account_data["currency"],
            )

            if to_convert is None:
                to_convert = 0

            price = await convert(
                from_currency=account_data["currency"],
                to_currency="INR",
                amount=to_convert,
            )
            price *= MANUAL_ITEMS_SENDER_MULTIPLIER
            item["price"] = price
            listable_value += price

        for item in account_data["non_listable_items"]:
            to_convert = await get_db_price(
                item["name"],
                client=account_data["logged_in_client"],
                currency=account_data["currency"],
            )

            if to_convert is None:
                to_convert = 0

            price = await convert(
                from_currency=account_data["currency"],
                to_currency="INR",
                amount=to_convert,
            )

            price *= MANUAL_ITEMS_SENDER_MULTIPLIER
            item["price"] = price
            non_listable_value += price

        account_data["listable_value"] = listable_value
        account_data["non_listable_value"] = non_listable_value
        account_data["total_value"] = listable_value + non_listable_value

    # Calculate totals
    total_listable_value = sum(data["listable_value"] for data in account_data_list)
    total_inventory_value = sum(data["total_value"] for data in account_data_list)
    total_active_armoury_passes = sum(
        data["active_armoury_passes"] for data in account_data_list
    )
    total_tradable_value = total_listable_value

    for data in account_data_list:
        if data["pass_value"] is None:
            data["pass_value"] = 0

    total_active_armoury_passes_value = sum(
        (data["active_armoury_passes"] * data["pass_value"])
        for data in account_data_list
    )
    print("\n")
    logger.info("--- Inventory Summary ---")
    logger.info(f"Total tradable inventory value: ₹{total_tradable_value:.2f}")
    logger.info(f"Total inventory value: ₹{total_inventory_value:.2f}")
    logger.info(
        f"Total armory passes: {total_active_armoury_passes} (value: ₹{total_active_armoury_passes_value:.2f})"
    )

    if total_tradable_value == 0:
        logger.warning(
            "Total tradable value across all accounts is 0, exiting sender..."
        )
        return False

    try:
        while True:
            try:
                print("\n")
                user_input = input(
                    "How much value do you want to transfer to your main account (in rupees)? "
                    "(Press Ctrl+C to cancel): "
                ).strip()

                target_transfer = float(user_input)
                if target_transfer <= 0:
                    logger.warning("Please enter a positive value.")
                    continue
                if target_transfer > total_tradable_value:
                    logger.warning(
                        f"Cannot transfer more than available tradable value (₹{total_tradable_value:.2f})."
                    )
                    continue
                break
            except ValueError:
                logger.error("Please enter a valid number.")
    except KeyboardInterrupt:
        print("\nOperation cancelled by user (Ctrl+C detected). Exiting gracefully.")
        sys.exit(0)

    # Create a balanced transfer plan
    transfer_plan = await select_items_for_balanced_transfer(
        account_data_list, target_transfer
    )

    if not transfer_plan:
        logger.info("Transfer cancelled.")
        return False

    # Execute the transfer plan
    await execute_transfer_plan(transfer_plan)

    # If autoaccept trades is on then automatically accept the trades after they're sent
    if autoaccept_trades:
        logger.trace("Waiting 10 seconds before accepting trades...")
        await asyncio.sleep(10)  # Wait for all trades to be sent

        await accept_trades_account(username="sivasai2208")

    return True


if __name__ == "__main__":
    asyncio.run(
        items_sender()
    )  # Util is only used for sending to main account, hence no option to change username
