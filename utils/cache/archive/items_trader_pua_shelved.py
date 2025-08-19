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
    update_pua_status,
)
from utils.logger import get_custom_logger
from utils.trade_acceptor import accept_trades_multiple_accounts

logger = get_custom_logger()

from collections import Counter

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
STEAM_TAX = 1.15
ARMOURY_PASS_BATCH_SIZE = 5


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


async def select_items_for_balanced_transfer(
    account_data_list: list[dict[str, Any]], autoconfirm: bool
) -> list[dict[str, Any]] | None:
    """
    Select items from accounts to transfer to pua accounts.
    Each PUA account receives items to meet fua_threshold requirements and moves onto next pua account.
    """

    # Check exactly one account has pua=1
    pua_accounts = [acc for acc in account_data_list if acc["account"].get("pua") == 1]
    if len(pua_accounts) != 1:
        logger.critical(f"Expected exactly one PUA account, found {len(pua_accounts)}")
        raise Exception("Critical: There must be exactly one PUA account")

    # Calculate current total value and tradable value across all accounts
    total_current_value = sum(account["total_value"] for account in account_data_list)
    total_tradable_value = sum(
        account["listable_value"] for account in account_data_list
    )

    print("\n")
    logger.info("--- Trading Plan ---")
    logger.info(
        f"Total inventory value across all accounts: ₹{total_current_value:.2f}"
    )
    logger.info(
        f"Total tradable value across all accounts: ₹{total_tradable_value:.2f}"
    )

    # Store the items to transfer from each account
    transfer_plan = []
    for account_data in account_data_list:
        transfer_plan.append(
            {
                "account_data": account_data,
                "username": account_data["account"]["steam_username"],
                "current_value": account_data["total_value"],
                "current_value_native": account_data["total_value_native"],
                "tradable_value": account_data["listable_value"],
                "fua_threshold_value": account_data["account"]["fua_threshold"]
                * ARMOURY_PASS_BATCH_SIZE
                * account_data["account"]["pass_value"]
                * STEAM_TAX,
                "items_to_transfer": [],
                "transfer_value": 0,
                "currency": account_data["currency"],
                "receiving_username": None,  # Will be set when items are allocated
            }
        )

    # Start with the initial PUA account
    current_pua_account = pua_accounts[0]

    # Create a list of accounts sorted by current_value_native descending for processing order
    sorted_accounts = sorted(
        account_data_list, key=lambda x: x["total_value_native"], reverse=True
    )
    processed_accounts = []

    # Track global item availability
    all_items_exhausted = False

    while len(processed_accounts) < len(account_data_list) and not all_items_exhausted:
        # Get current PUA plan
        pua_plan = next(
            plan
            for plan in transfer_plan
            if plan["username"] == current_pua_account["account"]["steam_username"]
        )

        # Calculate required transfer amount for current PUA account
        required_transfer_amount = (
            pua_plan["fua_threshold_value"] - pua_plan["current_value_native"]
        )
        if required_transfer_amount < 0:
            required_transfer_amount = 0

        logger.info(
            f"Processing PUA account: {current_pua_account['account']['steam_username']}"
        )
        logger.info(f"Required transfer amount: ₹{required_transfer_amount:.2f}")

        # Get donor accounts (all accounts except current PUA and already processed)
        donor_accounts = [
            acc
            for acc in account_data_list
            if acc["account"]["steam_username"]
            != current_pua_account["account"]["steam_username"]
            and acc["account"]["steam_username"] not in processed_accounts
        ]

        # Check if any donor accounts have items left
        total_available_items = sum(
            len(
                [
                    item
                    for item in donor["listable_items"]
                    if item["item"]
                    not in [
                        transfer_item
                        for plan in transfer_plan
                        for transfer_item in plan["items_to_transfer"]
                    ]
                ]
            )
            for donor in donor_accounts
        )

        if total_available_items == 0:
            logger.info("No more items available for allocation")
            all_items_exhausted = True
            break

        # Simple for loop to add items until target reached or items exhausted
        remaining_target = required_transfer_amount
        items_allocated_this_round = 0

        for donor_account in donor_accounts:
            if remaining_target <= 0:
                break

            donor_plan = next(
                plan
                for plan in transfer_plan
                if plan["username"] == donor_account["account"]["steam_username"]
            )

            # Get available items (not already allocated)
            allocated_items = set(donor_plan["items_to_transfer"])
            available_items = [
                item
                for item in donor_account["listable_items"]
                if item["item"] not in allocated_items
            ]

            # Sort available items by price descending for efficient allocation
            sorted_items = sorted(
                available_items, key=lambda x: x["price"], reverse=True
            )

            for item in sorted_items:
                if remaining_target <= 0:
                    break

                # Add item to donor's transfer list
                donor_plan["items_to_transfer"].append(item["item"])
                donor_plan["transfer_value"] += item["price"]
                donor_plan["receiving_username"] = current_pua_account["account"][
                    "steam_username"
                ]
                remaining_target -= item["price"]
                items_allocated_this_round += 1

        allocated_amount = required_transfer_amount - remaining_target
        logger.info(
            f"Allocated ₹{allocated_amount:.2f} to PUA account ({items_allocated_this_round} items)"
        )

        # Check if threshold was met or if no more items are available
        threshold_met = remaining_target <= 0
        no_more_items = items_allocated_this_round == 0

        if no_more_items:
            logger.warning(
                f"No items could be allocated to PUA account {current_pua_account['account']['steam_username']}"
            )
            all_items_exhausted = True
            break
        elif not threshold_met:
            remaining_target_converted = await convert(
                from_currency=current_pua_account["account"]["currency"],
                to_currency="INR",
                amount=remaining_target,
            )

            logger.warning(
                f"Threshold not reached for PUA account {current_pua_account['account']['steam_username']} - allocated all available items but still short by {remaining_target} {current_pua_account['account']['currency']}, approximately ₹{remaining_target_converted:.2f}..."
            )
            break
        else:
            logger.success(
                f"Threshold met for PUA account {current_pua_account['account']['steam_username']}"
            )

        # Mark current PUA account as processed
        processed_accounts.append(current_pua_account["account"]["steam_username"])

        # If there are more accounts to process and items are available, select next highest value account as PUA
        remaining_accounts = [
            acc
            for acc in sorted_accounts
            if acc["account"]["steam_username"] not in processed_accounts
        ]

        if remaining_accounts and threshold_met:
            # Check if there are still items available before moving PUA
            remaining_items = sum(
                len(
                    [
                        item
                        for item in donor["listable_items"]
                        if item["item"]
                        not in [
                            transfer_item
                            for plan in transfer_plan
                            for transfer_item in plan["items_to_transfer"]
                        ]
                    ]
                )
                for donor in account_data_list
                if donor["account"]["steam_username"] not in processed_accounts
            )

            if remaining_items == 0:
                logger.info("No more items available for next PUA account")
                all_items_exhausted = True
                break

            # Update PUA status in database
            await update_pua_status(current_pua_account["account"]["steam_username"], 0)

            # Select next account with highest current value
            next_pua_account = remaining_accounts[0]
            await update_pua_status(next_pua_account["account"]["steam_username"], 1)

            current_pua_account = next_pua_account
            logger.info(
                f"Next PUA account: {current_pua_account['account']['steam_username']}"
            )
        else:
            break

    # Filter transfer_plan to only include accounts with items to transfer
    filtered_transfer_plan = [
        plan for plan in transfer_plan if plan["items_to_transfer"]
    ]

    # Calculate actual total transfer
    total_transfer = sum(plan["transfer_value"] for plan in filtered_transfer_plan)

    # Print the plan
    print("\n")
    logger.info("--- Transfer Plan ---")
    logger.info(
        f"Total items to transfer: {sum(len(plan['items_to_transfer']) for plan in filtered_transfer_plan)}"
    )
    logger.info(f"Total transfer value: ₹{total_transfer:.2f}")

    if all_items_exhausted:
        logger.info("All items have been allocated.")

    print("\n")
    logger.info("Per-Account Breakdown:")
    for plan in filtered_transfer_plan:
        print("\n")
        logger.info(f"{plan['username']} → {plan['receiving_username']}:")
        logger.info(
            f"  Items to transfer: {len(plan['items_to_transfer'])} (₹{plan['transfer_value']:.2f})"
        )

    # Ask for confirmation
    if not autoconfirm:
        print("\n")
        confirm = input(
            "Do you want to proceed with this trading plan? (y/n): "
        ).lower()  # Will be commented out in production
        if confirm != "y":
            return None

    return filtered_transfer_plan


async def create_fresh_client(account: dict[str, Any]) -> SteamClient:
    """Create a fresh Steam client and login for an account."""
    username = account["steam_username"]

    client = await get_client(account)

    logger.trace(f"Successfully logged into account: {username}")

    return client


async def execute_transfer_plan(
    transfer_plan: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Execute trades according to the transfer plan with relogin handling."""
    trade_results = []

    # Group transfers by donor account
    from collections import defaultdict

    transfers_by_donor = defaultdict(list)

    for plan in transfer_plan:
        if plan["items_to_transfer"]:
            transfers_by_donor[plan["username"]].append(plan)

    all_accounts = get_all_steam_accounts()

    # Process each donor account
    for donor_username, donor_transfers in transfers_by_donor.items():
        logger.info(f"Processing transfers for donor: {donor_username}")

        # Get account info
        donor_account = next(
            acc for acc in all_accounts if acc["steam_username"] == donor_username
        )

        # Group transfers by recipient to handle multiple recipients
        transfers_by_recipient = defaultdict(list)
        for transfer in donor_transfers:
            transfers_by_recipient[transfer["receiving_username"]].append(transfer)

        client = None

        try:
            # Process each recipient for this donor
            for recipient_idx, (recipient_username, recipient_transfers) in enumerate(
                transfers_by_recipient.items()
            ):
                # If this is not the first recipient, we need to logout and relogin
                if recipient_idx > 0:
                    if client:
                        logger.info(
                            f"Logging out from {donor_username} to switch recipient"
                        )
                        try:
                            await save_cookies_and_close_session(client)
                        except Exception as e:
                            logger.error(f"Error during logout: {e}")

                    # Create fresh client for new recipient
                    logger.info(
                        f"Creating fresh login for {donor_username} to send to {recipient_username}"
                    )
                    client = await create_fresh_client(donor_account)

                elif client is None:
                    # First recipient, use existing client or create new one
                    if recipient_transfers[0]["account_data"].get("logged_in_client"):
                        client = recipient_transfers[0]["account_data"][
                            "logged_in_client"
                        ]
                    else:
                        client = await create_fresh_client(donor_account)

                # Get recipient's trade URL
                recipient_account = next(
                    acc
                    for acc in all_accounts
                    if acc["steam_username"] == recipient_username
                )
                trade_url = recipient_account["trade_url"]

                # Combine all items for this recipient
                all_items = []
                total_value = 0

                for transfer in recipient_transfers:
                    all_items.extend(transfer["items_to_transfer"])
                    total_value += transfer["transfer_value"]

                # Send trade to this recipient
                try:
                    print("\n")
                    logger.info(
                        f"Sending {len(all_items)} items from {donor_username} to {recipient_username} (value: ₹{total_value:.2f})"
                    )

                    trade_offer_id = await send_trade(
                        client, all_items, total_value, trade_url, donor_username
                    )

                    # Record results for each transfer in this batch
                    for transfer in recipient_transfers:
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

                    # Record failure for each transfer in this batch
                    for transfer in recipient_transfers:
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
            # Logout after all transfers for this donor are complete
            if client:
                try:
                    await save_cookies_and_close_session(client)
                    logger.trace(f"Logged out from {donor_username}")
                except Exception as e:
                    logger.error(f"Error during final logout for {donor_username}: {e}")

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
                f"- {trade['account']} → {trade.get('recipient', 'unknown')}: {trade['items_count']} items, ₹{trade['value']:.2f}"
            )
            if "error" in trade:
                logger.error(f"  Error: {trade['error']}")

    return trade_results


def get_unique_items(account_data_list: list[dict[str, Any]]) -> set[str]:
    """Get unique item names from all accounts."""
    names = set()

    for acc in account_data_list:
        for item in acc["listable_items"]:
            names.add(item["name"])
        for item in acc["non_listable_items"]:
            names.add(item["name"])

    return names


async def run_items_trader(
    autoaccept_trades: bool = False, autoconfirm: bool = False
) -> bool:
    """Main function to select and send items from farming accounts to main account.
    By default trade sending requires confirmation and receiving also requires confirmation."""
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
        listable_value_native = 0
        non_listable_value_native = 0

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
            non_listable_value_native += to_convert

        balance_converted = await convert(
            from_currency=account_data["currency"],
            to_currency="INR",
            amount=get_steam_balance(account_data["account"]["steam_username"]),
        )

        account_data["listable_value"] = listable_value
        account_data["non_listable_value"] = non_listable_value
        account_data["total_value"] = (
            listable_value + non_listable_value + balance_converted
        )  # Updated to include the steam balance
        account_data["total_value_native"] = (
            listable_value_native
            + non_listable_value_native
            + get_steam_balance(account_data["account"]["steam_username"])
        )

    # Calculate totals
    total_listable_value = sum(data["listable_value"] for data in account_data_list)
    total_inventory_value = sum(data["total_value"] for data in account_data_list)
    total_tradable_value = total_listable_value

    for data in account_data_list:
        if data["pass_value"] is None:
            data["pass_value"] = 0

    print("\n")
    logger.info("--- Inventory Summary ---")
    logger.info(f"Total tradable inventory value: ₹{total_tradable_value:.2f}")
    logger.info(f"Total inventory value: ₹{total_inventory_value:.2f}")

    if total_tradable_value == 0:
        logger.warning(
            "Total tradable value across all accounts is 0, exiting sender..."
        )
        return True

    # Create a balanced transfer plan
    transfer_plan = await select_items_for_balanced_transfer(
        account_data_list, autoconfirm
    )

    if not transfer_plan:
        logger.info("Transfer cancelled.")
        return False

    # Execute the transfer plan
    await execute_transfer_plan(transfer_plan)

    receivers = [
        plan["receiving_username"]
        for plan in transfer_plan
        if plan.get("receiving_username")
    ]

    # If autoaccept trades is on then automatically accept the trades after they're sent
    if autoaccept_trades:
        logger.trace("Waiting 10 seconds before accepting trades...")
        await asyncio.sleep(10)  # Wait for all trades to be sent

        await accept_trades_multiple_accounts(receivers)

    else:
        logger.info("Please go to the receiving accounts to accept the trades:")

        receiver_counts = Counter(receivers)
        for receiver, count in receiver_counts.items():
            trade_word = "trade" if count == 1 else "trades"
            logger.info(f" - {count} {trade_word} sent to {receiver}")

    return True


if __name__ == "__main__":
    asyncio.run(run_items_trader())
