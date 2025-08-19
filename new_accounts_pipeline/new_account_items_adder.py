"""
Items Transfer System for New Accounts

This module implements a system for transferring items to new accounts to cover the cost of Prime status and passes.

It calculates the required item value for each target account using the formula:
  (5 * pass_cost + prime_cost - steam_balance) * 1.15
- Allocates the minimum required items to each target account from a pool of donor accounts.
- Warns if the total available items are insufficient to meet the minimum requirements for an account.

Usage:
    target_usernames = ["account1", "account2", "account3"]
    await run_items_trader_new_accounts(target_usernames=target_usernames)

Configuration:
- PRIME_COSTS: A dictionary mapping currency codes to the cost of a prime subscription.
- STEAM_TAX: A 1.15 multiplier to account for the Steam market tax.
- ARMOURY_PASS_BATCH_SIZE: The number of passes to calculate for (default is 5).
"""

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
    get_client,
    get_db_price,
    get_steam_balance,
    save_cookies_and_close_session,
    steam_api_call_with_retry,
    update_prices_from_market,
)
from utils.logger import get_custom_logger
from utils.trade_acceptor import accept_trades_multiple_accounts

logger = get_custom_logger()

from tqdm.asyncio import tqdm_asyncio

# --- Caching Configuration ---


def load_config() -> dict:
    config_path = r"C:\Users\Sivasai\Documents\GitHub\CaseFarm\config.yaml"
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    return config


_config = load_config()

# Constants
MANUAL_ITEMS_SENDER_MULTIPLIER = _config.get("MANUAL_ITEMS_SENDER_MULTIPLIER", 1)
MAIN_ACCOUNT_TRADE_URL = _config.get(
    "MAIN_ACCOUNT_TRADE_URL",
    "https://steamcommunity.com/tradeoffer/new/?partner=1597113567&token=zXZIog_y",
)
ACCOUNT_INVENTORY_SEMAPHORE = _config.get(
    "ACCOUNT_INVENTORY_SEMAPHORE_MANUAL_SENDER", 5
)
STEAM_TAX = 1.15
ARMOURY_PASS_BATCH_SIZE = 5

# Prime costs configuration by currency (in local currency)
PRIME_COSTS = {
    "VND": 375000,
    "INR": 1270,
    "UAH": 600,
    "IDR": 244999,
}


async def send_trade(
    client: SteamClient,
    items: list[Any],
    total_value: Union[int, float],
    trade_url: str,
    steam_username: str,
) -> str | None:
    """Send selected items to the trade url. Value should be passed in INR."""
    try:
        all_steam = get_all_steam_accounts()
        for account in all_steam:
            if account.get("trade_url") == trade_url:
                receiver_username = account.get("steam_username")
                break

        trade_offer_id = await steam_api_call_with_retry(
            client.make_trade_offer,
            obj=trade_url,
            to_give=items,
            to_receive=[],
            message="Sending items",
            confirm=True,
        )
        logger.success(
            f"{len(items)} items sent from account {steam_username} to account {receiver_username} with value ₹{total_value:.2f}"
        )

        return trade_offer_id
    except Exception as e:
        logger.error(f"Error sending trade offer: {e}")
        return None


async def select_items_for_prime_and_passes(
    account_data_list: list[dict[str, Any]],
    target_usernames: list[str],
    autoconfirm: bool,
) -> list[dict[str, Any]] | None:
    """
    Allocate the minimum required amount for prime and passes to each target account.
    """
    target_accounts = [
        acc
        for acc in account_data_list
        if acc["account"]["steam_username"] in target_usernames
    ]

    donor_accounts = [
        acc
        for acc in account_data_list
        if acc["account"]["steam_username"] not in target_usernames
        and acc["listable_value"] > 0
    ]

    if not target_accounts:
        logger.error("No target accounts found in the provided list")
        return None

    if not donor_accounts:
        logger.error("No donor accounts with tradable items found")
        return None

    total_tradable_value = sum(
        account["listable_value"] for account in account_data_list
    )

    print("\n")
    logger.info("--- Minimum Requirements Trading Plan ---")
    logger.info(f"Target accounts: {len(target_accounts)}")
    logger.info(f"Donor accounts: {len(donor_accounts)}")
    logger.info(
        f"Total tradable value across all accounts: ₹{total_tradable_value:.2f}"
    )

    account_data_lookup = {
        acc["account"]["steam_username"]: acc for acc in account_data_list
    }

    transfer_plan = []
    target_info = {
        target_account["account"]["steam_username"]: {
            "account_data": target_account,
            "allocation": 0,
            "required": 0,
        }
        for target_account in target_accounts
    }

    print("\n")
    logger.info("--- Calculating Minimum Requirements ---")

    stage1_failed = []
    total_required = 0

    for target_account in target_accounts:
        username = target_account["account"]["steam_username"]
        currency = target_account["account"]["currency"]
        steam_balance = get_steam_balance(username)
        pass_value = target_account["account"]["pass_value"]
        prime_cost = PRIME_COSTS.get(currency, 0)

        if prime_cost == 0:
            logger.warning(
                f"Prime cost not configured for currency {currency}, using 0"
            )

        required_amount_native = (
            ARMOURY_PASS_BATCH_SIZE * pass_value + prime_cost - steam_balance
        ) * STEAM_TAX

        if required_amount_native < 0:
            required_amount_native = 0

        required_amount_inr = await convert(
            from_currency=currency, to_currency="INR", amount=required_amount_native
        )

        total_required += required_amount_inr
        target_info[username]["required"] = required_amount_inr

        logger.info(f"Target: {username} ({currency})")
        logger.info(
            f"  - Required: {required_amount_native:.2f} {currency} (₹{required_amount_inr:.2f})"
        )

    logger.info(f"Total required for all targets: ₹{total_required:.2f}")

    available_items = []
    for donor_account in donor_accounts:
        for item in donor_account["listable_items"]:
            available_items.append(
                {
                    "item": item["item"],
                    "price": item["price"],
                    "donor_username": donor_account["account"]["steam_username"],
                    "name": item["name"],
                }
            )

    available_items.sort(key=lambda x: x["price"], reverse=True)

    for target_account in target_accounts:
        target_username = target_account["account"]["steam_username"]
        required = target_info[target_username]["required"]
        allocated = 0
        items_to_remove = []

        for item in available_items:
            if allocated >= required:
                break

            allocated += item["price"]
            items_to_remove.append(item)

            transfer_entry = next(
                (
                    plan
                    for plan in transfer_plan
                    if plan["username"] == item["donor_username"]
                    and plan["receiving_username"] == target_username
                ),
                None,
            )

            if not transfer_entry:
                transfer_entry = {
                    "account_data": account_data_lookup[item["donor_username"]],
                    "username": item["donor_username"],
                    "receiving_username": target_username,
                    "items_to_transfer": [],
                    "transfer_value": 0,
                }
                transfer_plan.append(transfer_entry)

            transfer_entry["items_to_transfer"].append(item["item"])
            transfer_entry["transfer_value"] += item["price"]

        for item in items_to_remove:
            available_items.remove(item)

        target_info[target_username]["allocation"] = allocated

        if allocated < required:
            shortage = required - allocated
            stage1_failed.append(
                {
                    "username": target_username,
                    "required": required,
                    "allocated": allocated,
                    "shortage": shortage,
                }
            )
            logger.warning(
                f"SHORTAGE for {target_username}: Required ₹{required:.2f}, Allocated ₹{allocated:.2f}, Short by ₹{shortage:.2f}"
            )
        else:
            logger.success(
                f"COMPLETE for {target_username}: Allocated ₹{allocated:.2f}"
            )

    if stage1_failed:
        print("\n")
        logger.warning("--- ALLOCATION WARNINGS ---")
        for fail in stage1_failed:
            logger.warning(f"  {fail['username']}: Short by ₹{fail['shortage']:.2f}")

    print("\n")
    logger.info("--- TRANSFER SUMMARY ---")
    total_items = sum(len(plan["items_to_transfer"]) for plan in transfer_plan)
    total_value = sum(plan["transfer_value"] for plan in transfer_plan)
    logger.info(f"Total items to transfer: {total_items}")
    logger.info(f"Total transfer value: ₹{total_value:.2f}")

    print("\n")
    logger.info("Per-Donor Breakdown:")
    for plan in transfer_plan:
        logger.info(
            f"  {plan['username']} → {plan['receiving_username']}: {len(plan['items_to_transfer'])} items (₹{plan['transfer_value']:.2f})"
        )

    if not autoconfirm:
        print("\n")
        confirm = input(
            "Do you want to proceed with this trading plan? (y/n): "
        ).lower()
        if confirm != "y":
            return None

    return transfer_plan


async def execute_transfer_plan(
    transfer_plan: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Execute trades according to the transfer plan with relogin handling."""
    trade_results = []
    from collections import defaultdict

    transfers_by_donor = defaultdict(list)
    for plan in transfer_plan:
        if plan["items_to_transfer"]:
            transfers_by_donor[
                plan["account_data"]["account"]["steam_username"]
            ].append(plan)

    all_accounts = get_all_steam_accounts()

    for donor_username, donor_transfers in transfers_by_donor.items():
        logger.info(f"Processing transfers for donor: {donor_username}")
        donor_account = next(
            acc for acc in all_accounts if acc["steam_username"] == donor_username
        )
        transfers_by_recipient = defaultdict(list)
        for transfer in donor_transfers:
            transfers_by_recipient[transfer["receiving_username"]].append(transfer)

        client = None
        try:
            for recipient_idx, (
                recipient_username,
                recipient_transfers,
            ) in enumerate(transfers_by_recipient.items()):
                if recipient_idx > 0:
                    if client:
                        logger.info(
                            f"Closing session for {donor_username} to switch recipient"
                        )
                        try:
                            await save_cookies_and_close_session(client)
                        except Exception as e:
                            logger.error(f"Error during session close: {e}")
                    logger.info(
                        f"Creating fresh login for {donor_username} to send to {recipient_username}"
                    )
                    client = await get_client(donor_account)
                elif client is None:
                    if recipient_transfers[0]["account_data"].get("logged_in_client"):
                        client = recipient_transfers[0]["account_data"][
                            "logged_in_client"
                        ]
                    else:
                        client = await get_client(donor_account)

                recipient_account = next(
                    acc
                    for acc in all_accounts
                    if acc["steam_username"] == recipient_username
                )
                trade_url = recipient_account["trade_url"]

                for transfer in recipient_transfers:
                    try:
                        print("\n")
                        logger.info(
                            f"Sending {len(transfer['items_to_transfer'])} items from {donor_username} to {recipient_username} (value: ₹{transfer['transfer_value']:.2f})"
                        )
                        trade_offer_id = await send_trade(
                            client,
                            transfer["items_to_transfer"],
                            transfer["transfer_value"],
                            trade_url,
                            donor_username,
                        )
                        trade_results.append(
                            {
                                "account": donor_username,
                                "trade_id": trade_offer_id,
                                "items_count": len(transfer["items_to_transfer"]),
                                "value": transfer["transfer_value"],
                                "success": trade_offer_id is not None,
                                "recipient": recipient_username,
                            }
                        )
                    except Exception as e:
                        logger.error(
                            f"Error sending trade from {donor_username} to {recipient_username}: {e}"
                        )
                        trade_results.append(
                            {
                                "account": donor_username,
                                "trade_id": None,
                                "items_count": len(transfer["items_to_transfer"]),
                                "value": transfer["transfer_value"],
                                "success": False,
                                "error": str(e),
                                "recipient": recipient_username,
                            }
                        )
        finally:
            if client:
                try:
                    await save_cookies_and_close_session(client)
                    logger.trace(f"Closed session for {donor_username}")
                except Exception as e:
                    logger.error(
                        f"Error during final session close for {donor_username}: {e}"
                    )

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
                f"- {trade['account']} → {trade.get('recipient', 'unknown')}: {trade['items_count']} items, ₹{trade['value']:.2f}"
            )
            if "error" in trade:
                logger.error(f"  Error: {trade['error']}")

    return trade_results


async def run_items_trader_new_accounts(
    target_usernames: list[str] = None,
    autoaccept_trades: bool = False,
    autoconfirm: bool = True,
) -> bool:
    """Main function to send items to cover prime and pass costs for target accounts."""
    if not target_usernames:
        logger.error("target_usernames must be provided as a list of steam usernames")
        return False

    user_agents = UserAgentsService()
    await user_agents.load()
    all_accounts = get_all_steam_accounts()

    accounts_to_process = [
        acc
        for acc in all_accounts
        if acc.get("prime") or acc["steam_username"] in target_usernames
    ]

    all_db_usernames = {acc["steam_username"] for acc in all_accounts}
    invalid_usernames = [
        name for name in target_usernames if name not in all_db_usernames
    ]
    if invalid_usernames:
        logger.error(f"Invalid usernames provided: {invalid_usernames}")
        return False

    print("\n")
    logger.info(f"Fetching inventory data for {len(accounts_to_process)} accounts...")
    logger.info(f"Target accounts: {target_usernames}")

    async def process_accounts_inventory(selected_accounts) -> list:
        semaphore = asyncio.Semaphore(ACCOUNT_INVENTORY_SEMAPHORE)

        async def process_account(account) -> dict:
            async with semaphore:
                logger.info(f"Processing {account['steam_username']}...")
                account_data = await get_account_details(account)
                return account_data

        tasks = [process_account(account) for account in selected_accounts]
        results = []
        for future in tqdm_asyncio.as_completed(tasks):
            account_data = await future
            results.append(account_data)
        return results

    account_data_list = await process_accounts_inventory(accounts_to_process)

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

    for account_data in account_data_list:
        listable_value = 0
        listable_value_native = 0

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
            listable_value_native += to_convert

        account_data["listable_value"] = listable_value
        account_data["listable_value_native"] = listable_value_native

    total_tradable_value = sum(
        data.get("listable_value", 0) for data in account_data_list
    )

    print("\n")
    logger.info("--- Inventory Summary ---")
    logger.info(f"Total tradable inventory value: ₹{total_tradable_value:.2f}")

    if total_tradable_value == 0:
        logger.warning(
            "Total tradable value across all accounts is 0, exiting sender..."
        )
        return True

    transfer_plan = await select_items_for_prime_and_passes(
        account_data_list, target_usernames, autoconfirm
    )

    if not transfer_plan:
        logger.info("Transfer cancelled.")
        return False

    await execute_transfer_plan(transfer_plan)

    receivers = list(
        set(
            [
                plan["receiving_username"]
                for plan in transfer_plan
                if plan.get("receiving_username")
            ]
        )
    )

    if autoaccept_trades:
        logger.trace("Waiting 10 seconds before accepting trades...")
        await asyncio.sleep(10)
        await accept_trades_multiple_accounts(receivers)
    else:
        logger.info("Please go to the receiving accounts to accept the trades:")
        for receiver in set(receivers):
            logger.info(f"{receiver} received trades (not accepted)")

    return True


async def main() -> bool:
    """
    Example function showing how to use the transfer system.
    Modify the target_usernames list with the actual Steam usernames you want to transfer to.
    """
    target_usernames = [
        "sugaryrat089",
    ]

    logger.info("Starting item transfer process...")
    logger.info(f"Target accounts: {target_usernames}")
    logger.info("This will allocate the minimum items required for prime + passes.")

    success = await run_items_trader_new_accounts(
        target_usernames=target_usernames,
        autoaccept_trades=False,
        autoconfirm=False,  # both set to false to prevent misclicks
    )

    if success:
        logger.success("Item transfer completed successfully!")
    else:
        logger.error("Item transfer failed or was cancelled")

    return success


if __name__ == "__main__":
    asyncio.run(main())
