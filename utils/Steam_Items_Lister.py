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
import logging
import random
from collections import defaultdict

import aiohttp
from aiosteampy import AppContext, SteamClient
from aiosteampy.ext.user_agents import UserAgentsService

logging.getLogger("asyncio").setLevel(logging.CRITICAL)
import math
import os
from contextlib import redirect_stderr, redirect_stdout

from tqdm.asyncio import tqdm_asyncio

from database import (
    convert,
    get_account_details,
    get_all_steam_accounts,
    get_client,
    get_db_price,
    get_full_inventory,
    get_steam_balance,
    steam_api_call_with_retry,
    update_prices_from_market,
    update_steam_balance,
)

with open(os.devnull, "w") as devnull:
    with redirect_stdout(devnull), redirect_stderr(devnull):
        # Import OR-Tools while suppressing output.
        from ortools.sat.python import cp_model

# Since this code sells instantly to buy orders, its recommended to get the best time to sell using the scheduler and then run the code at that time.
# selling immediately when items become available is not recommended


# Load constants from config.yaml
def load_config() -> dict:
    config_path = r"C:\Users\Sivasai\Documents\GitHub\CaseFarm\config.yaml"
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    return config


_config = load_config()

# Steam Items Lister Constants (loaded from config.yaml)
MULTIPLIER = _config.get("STEAM_ITEMS_LISTER_MULTIPLIER") - 10e-5
MAX_CLEANUP_ATTEMPTS = _config.get("MAX_CLEANUP_ATTEMPTS")
INITIAL_CLEANUP_PRICE_MULTIPLIER = _config.get("INITIAL_CLEANUP_PRICE_MULTIPLIER")
CLEANUP_PRICE_DECREMENT = _config.get("CLEANUP_PRICE_DECREMENT")
ACCOUNT_INVENTORY_SEMAPHORE = _config.get("ACCOUNT_INVENTORY_SEMAPHORE_STEAM_ITEMS")
MAX_ITEMS_LIMIT = _config.get("MAX_ITEMS_LIMIT")
MIN_SELLING_TIME = _config.get("MIN_SELLING_TIME", 30)  # Default to 30 seconds
MAX_SELLING_TIME_WAIT = _config.get("MAX_SELLING_TIME_WAIT")
NUM_PASSES_REQUIRED = _config.get("NUM_PASSES_REQUIRED")

# Global variable for tqdm progress bar
processing_listings_progress = None

# Global lock for updating the tqdm progress bar
processing_listings_lock = asyncio.Lock()

processing_listings_total_items = 0


async def get_market_listings(client: SteamClient) -> list:
    """
    Process all market listings for CS2.
    """
    logger.info("Fetching CS2 market listings...")

    try:
        i = 0
        all_listings: list = []
        while True:
            listings = await steam_api_call_with_retry(client.get_my_listings, start=i)

            active_listings = listings[0]
            all_listings.extend(active_listings)
            if len(active_listings) < 100:
                break
            else:
                i += 100

            logger.debug(
                f"Retrieved page with {len(listings)} listings. Total so far: {len(all_listings)}"
            )

        return all_listings

    except Exception as e:
        logger.error(f"Error occurred while processing market listings: {e}")
        raise


def select_items_to_sell(
    items_by_price: dict, target_amount: float
) -> tuple[list, float, str]:
    """
    Select optimal items to sell to meet target amount with minimal overshoot.
    Prices are scaled by 100 before running the CP-SAT solver.
    If MAX_ITEMS_LIMIT is None or 0, no limit is applied to the number of items.

    Args:
        items_by_price: A dictionary mapping original prices (float) to lists of corresponding items.
        target_amount: Required selling amount in original currency (float).

    Returns:
        A tuple (selected_items, total_value, status) where:
          selected_items: List of items chosen.
          total_value: Total selling value in original currency (after conversion).
          status: "OPTIMAL", "FEASIBLE", "INFEASIBLE", or "UNKNOWN".
    """
    price_scale: int = 100  # Multiply all prices by 100 to convert to integer (cents)
    # Convert the target amount: use ceil so that even a fraction results in a higher target
    int_target: int = int(math.ceil(target_amount * price_scale))

    # Create a CP-SAT model.
    model = cp_model.CpModel()

    # Create variables for each unique price group.
    # We also keep the original price along with the scaled integer price.
    item_vars: dict = {}
    unique_items: list = []  # List of tuples: (original_price, int_price, count, items)
    for i, (price, items) in enumerate(items_by_price.items()):
        int_price = int(round(price * price_scale))
        count = len(items)
        item_vars[i] = model.NewIntVar(0, count, f"item_{i}")
        unique_items.append((price, int_price, count, items))

    # Constraint: total value in integer units must meet or exceed the target.
    total_value_int = sum(
        int_price * item_vars[i] for i, (_, int_price, _, _) in enumerate(unique_items)
    )
    model.Add(total_value_int >= int_target)

    # Only apply the item limit constraint if MAX_ITEMS_LIMIT is not None and > 0
    if MAX_ITEMS_LIMIT is not None and MAX_ITEMS_LIMIT > 0:
        total_items = sum(item_vars[i] for i in range(len(unique_items)))
        model.Add(total_items <= MAX_ITEMS_LIMIT)

    # Objective: minimize the overshoot, i.e. the excess over the target.
    model.Minimize(total_value_int - int_target)

    # Solve the model.
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 30.0  # Increase timeout if needed.
    status = solver.Solve(model)

    # Process solution.
    if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        selected_items: list = []
        total_value_int_result: int = 0
        for i, (orig_price, int_price, count, items) in enumerate(unique_items):
            selected_count = solver.Value(item_vars[i])
            if selected_count > 0:
                selected_items.extend(items[:selected_count])
                total_value_int_result += int_price * selected_count
        # Convert the total value back to the original currency units.
        total_value: float = total_value_int_result / price_scale
        if status == cp_model.OPTIMAL:
            return selected_items, total_value, "OPTIMAL"
        else:
            return selected_items, total_value, "FEASIBLE"
    elif status == cp_model.INFEASIBLE:
        return [], 0, "INFEASIBLE"
    else:
        return [], 0, "UNKNOWN"


async def execute_selling(
    account_data_list: list, sell_all_items: bool = False
) -> list:
    """
    Select items from accounts to sell based on wallet balance requirements.
    If sell_all_items is True, all available listable items are sold regardless of wallet balance.
    If sell_all_items is False, items are sold only to meet the required armoury value.
    If MAX_ITEMS_LIMIT is None or 0, no limit is applied to the number of items.
    """
    # Store the items to be sold from each account
    selling_plan: list = []
    print("\n")
    logger.info("--- Wallet Balance Analysis ---")

    # Process each account sequentially
    for account_data in account_data_list:
        account = account_data["account"]
        account_username: str = account["steam_username"]
        listable_value = account_data["listable_value"]
        num_active_passes: int = account_data["active_armoury_passes"]
        armoury_bool: int = account["is_armoury"]
        client = account_data["logged_in_client"]
        pass_value: float = account_data["pass_value"]
        currency: str = account_data["currency"]

        # Get current wallet balance
        wallet_balance_cents_initial = await steam_api_call_with_retry(
            client.get_wallet_balance
        )
        wallet_balance_initial: float = wallet_balance_cents_initial / 100

        # Calculate armoury value (amount needed for passes)
        if pass_value is None:
            pass_value = 0
        armoury_value: float = 5 * pass_value if armoury_bool else 0

        # Convert to INR for display purposes
        wallet_balance_inr = await convert(
            from_currency=currency, to_currency="INR", amount=wallet_balance_initial
        )
        armoury_value_inr = await convert(
            from_currency=currency, to_currency="INR", amount=armoury_value
        )

        print("\n")
        logger.info(f"Account: {account_username}")
        logger.info(
            f"  Current wallet balance: {currency} {wallet_balance_initial:.2f} (₹{wallet_balance_inr:.2f})"
        )
        logger.info(
            f"  Armoury value threshold: {currency} {armoury_value:.2f} (₹{armoury_value_inr:.2f})"
        )

        # Skip processing if wallet balance meets the threshold and we're not selling all items
        if wallet_balance_initial >= armoury_value and not sell_all_items:
            logger.info("  Status: SKIPPED - Wallet balance already sufficient")
            continue

        # Calculate required selling amount including a 15% tax buffer (only relevant when not selling all)
        if not sell_all_items:
            required_selling: float = (armoury_value - wallet_balance_initial) * 1.15
            required_selling_inr = await convert(
                from_currency=currency, to_currency="INR", amount=required_selling
            )
            logger.info(
                f"  Required selling value: {currency} {required_selling:.2f} (₹{required_selling_inr:.2f})"
            )

        # Group items by price for the solver (or for straightforward selection)
        items_by_price: dict = {}
        for item_data in account_data["listable_items"]:
            price = item_data["price"]
            if price not in items_by_price:
                items_by_price[price] = []
            items_by_price[price].append(item_data["item"])

        # Calculate total listable value
        total_listable_value: float = sum(
            price * len(items) for price, items in items_by_price.items()
        )
        total_listable_inr = await convert(
            from_currency=currency, to_currency="INR", amount=total_listable_value
        )
        logger.info(
            f"  Total listable value: {currency} {total_listable_value:.2f} (₹{total_listable_inr:.2f})"
        )

        # If there are no items available to sell, skip this account
        # Check if account has active listings before deciding to skip
        has_active_listings = False
        try:
            active_listings = await get_market_listings(client=client)
            has_active_listings = len(active_listings) > 0
        except Exception as e:
            logger.warning(f"  Could not check active listings: {e}")

        # If there are no items available to sell AND no active listings, skip this account
        if not items_by_price and not has_active_listings:
            logger.info("  Status: No items available to sell and no active listings")
            continue
        elif not items_by_price and has_active_listings:
            logger.info(
                "  Status: No inventory items but has active listings - processing for cleanup"
            )
            items_to_sell = []  # Empty list since no inventory items to sell
        else:
            # Normal processing continues below...

            # Determine items to sell based on sell_all_items flag
            if sell_all_items:
                logger.info("  Selling all available items")
                all_items: list = []
                for items in items_by_price.values():
                    all_items.extend(items)

                # Only limit to MAX_ITEMS_LIMIT if it exists and > 0
                if (
                    MAX_ITEMS_LIMIT is not None
                    and MAX_ITEMS_LIMIT > 0
                    and len(all_items) > MAX_ITEMS_LIMIT
                ):
                    logger.info(
                        f"  Limiting to {MAX_ITEMS_LIMIT} items due to MAX_ITEMS_LIMIT"
                    )
                    items_to_sell = all_items[:MAX_ITEMS_LIMIT]
                    # Recalculate selling value for the limited items
                    total_selling_value = 0
                    # Use item IDs to track selected items
                    selected_ids = set(id(item) for item in items_to_sell)
                    for price, items_list in items_by_price.items():
                        for item in items_list:
                            if id(item) in selected_ids:
                                total_selling_value += price
                else:
                    items_to_sell = all_items
                    total_selling_value = total_listable_value
            else:
                # Only sell what's needed to meet armoury requirements
                # Check if even selling everything won't meet the requirement
                if total_listable_value < required_selling:
                    # Sell everything since total value is less than requirement
                    all_items: list = []
                    for items in items_by_price.values():
                        all_items.extend(items)

                    # Only limit to MAX_ITEMS_LIMIT if it exists and > 0
                    if (
                        MAX_ITEMS_LIMIT is not None
                        and MAX_ITEMS_LIMIT > 0
                        and len(all_items) > MAX_ITEMS_LIMIT
                    ):
                        logger.info(
                            f"  Limiting to {MAX_ITEMS_LIMIT} items due to MAX_ITEMS_LIMIT"
                        )
                        items_to_sell = all_items[:MAX_ITEMS_LIMIT]
                        # Recalculate selling value for the limited items
                        total_selling_value = 0
                        # Use item IDs to track selected items
                        selected_ids = set(id(item) for item in items_to_sell)
                        for price, items_list in items_by_price.items():
                            for item in items_list:
                                if id(item) in selected_ids:
                                    total_selling_value += price
                    else:
                        items_to_sell = all_items
                        total_selling_value = total_listable_value

                    logger.critical(
                        f"  CRITICAL: Even selling all items (worth {currency} {total_selling_value:.2f}) won't meet required amount ({currency} {required_selling:.2f})."
                    )
                else:
                    # We have sufficient total value; use optimization solver to find minimal combination
                    logger.info(
                        "  Running optimization solver to find minimal item combination..."
                    )
                    try:
                        items_to_sell, total_selling_value, status = (
                            select_items_to_sell(items_by_price, required_selling)
                        )
                        if status == "OPTIMAL":
                            logger.success(
                                f"  Found optimal item combination worth {currency} {total_selling_value}"
                            )
                        elif status == "FEASIBLE":
                            logger.info(
                                f"  Found feasible (but possibly not optimal) item combination worth {currency} {total_selling_value}"
                            )
                        elif status == "INFEASIBLE":
                            logger.error(
                                "  ERROR: Solver reported infeasibility – falling back to selling all items as a precaution."
                            )
                            all_items: list = []
                            for items in items_by_price.values():
                                all_items.extend(items)

                            # Only limit to MAX_ITEMS_LIMIT if it exists and > 0
                            if (
                                MAX_ITEMS_LIMIT is not None
                                and MAX_ITEMS_LIMIT > 0
                                and len(all_items) > MAX_ITEMS_LIMIT
                            ):
                                logger.info(
                                    f"  Limiting to {MAX_ITEMS_LIMIT} items due to MAX_ITEMS_LIMIT"
                                )
                                items_to_sell = all_items[:MAX_ITEMS_LIMIT]
                                # Recalculate selling value for the limited items
                                total_selling_value = 0
                                # Use item IDs to track selected items
                                selected_ids = set(id(item) for item in items_to_sell)
                                for price, items_list in items_by_price.items():
                                    for item in items_list:
                                        if id(item) in selected_ids:
                                            total_selling_value += price
                            else:
                                items_to_sell = all_items
                                total_selling_value = total_listable_value
                        else:  # UNKNOWN
                            logger.warning(
                                "  WARNING: Solver did not return a valid solution within time; using greedy approach..."
                            )
                            items_to_sell: list = []
                            total_selling_value: float = 0
                            sorted_price_items = sorted(
                                [
                                    (price, items)
                                    for price, items in items_by_price.items()
                                ],
                                key=lambda x: x[0],
                            )
                            for price, items in sorted_price_items:
                                for item in items:
                                    # Skip MAX_ITEMS_LIMIT check if it's None or 0
                                    if MAX_ITEMS_LIMIT is None or MAX_ITEMS_LIMIT <= 0:
                                        if total_selling_value < required_selling:
                                            items_to_sell.append(item)
                                            total_selling_value += price
                                        else:
                                            break
                                    else:
                                        if (
                                            total_selling_value < required_selling
                                            and len(items_to_sell) < MAX_ITEMS_LIMIT
                                        ):
                                            items_to_sell.append(item)
                                            total_selling_value += price
                                        else:
                                            break
                                if (total_selling_value >= required_selling) or (
                                    MAX_ITEMS_LIMIT is not None
                                    and MAX_ITEMS_LIMIT > 0
                                    and len(items_to_sell) >= MAX_ITEMS_LIMIT
                                ):
                                    break
                            logger.info(
                                f"Greedy approach found items worth {currency} {total_selling_value}"
                            )
                            # Only check MAX_ITEMS_LIMIT if it exists and > 0
                            if (
                                MAX_ITEMS_LIMIT is not None
                                and MAX_ITEMS_LIMIT > 0
                                and len(items_to_sell) == MAX_ITEMS_LIMIT
                                and total_selling_value < required_selling
                            ):
                                logger.warning(
                                    f"  Reached MAX_ITEMS_LIMIT of {MAX_ITEMS_LIMIT} items, but total value ({currency} {total_selling_value}) is still below required amount ({currency} {required_selling})."
                                )
                    except Exception as e:
                        logger.error(
                            f"  ERROR: Exception during optimization: {str(e)}"
                        )
                        logger.info("  Falling back to greedy approach...")
                        items_to_sell: list = []
                        total_selling_value: float = 0
                        sorted_price_items = sorted(
                            [(price, items) for price, items in items_by_price.items()],
                            key=lambda x: x[0],
                        )
                        for price, items in sorted_price_items:
                            for item in items:
                                # Skip MAX_ITEMS_LIMIT check if it's None or 0
                                if MAX_ITEMS_LIMIT is None or MAX_ITEMS_LIMIT <= 0:
                                    if total_selling_value < required_selling:
                                        items_to_sell.append(item)
                                        total_selling_value += price
                                    else:
                                        break
                                else:
                                    if (
                                        total_selling_value < required_selling
                                        and len(items_to_sell) < MAX_ITEMS_LIMIT
                                    ):
                                        items_to_sell.append(item)
                                        total_selling_value += price
                                    else:
                                        break
                            if (total_selling_value >= required_selling) or (
                                MAX_ITEMS_LIMIT is not None
                                and MAX_ITEMS_LIMIT > 0
                                and len(items_to_sell) >= MAX_ITEMS_LIMIT
                            ):
                                break
                        logger.info(
                            f"  Greedy approach after exception found items worth {currency} {total_selling_value}"
                        )
                        # Only check MAX_ITEMS_LIMIT if it exists and > 0
                        if (
                            MAX_ITEMS_LIMIT is not None
                            and MAX_ITEMS_LIMIT > 0
                            and len(items_to_sell) == MAX_ITEMS_LIMIT
                            and total_selling_value < required_selling
                        ):
                            logger.warning(
                                f"  Reached MAX_ITEMS_LIMIT of {MAX_ITEMS_LIMIT} items, but total value ({currency} {total_selling_value}) is still below required amount ({currency} {required_selling})."
                            )

            # Add the selling plan for this account if there are items to sell
            if items_to_sell or has_active_listings:
                selling_plan.append(
                    {
                        "account_data": account_data,
                        "username": account_username,
                        "listable_value": listable_value,
                        "armoury_value": armoury_value,
                        "wallet_balance": wallet_balance_initial,
                        "num_active_passes": num_active_passes,
                        "items_to_sell": items_to_sell,
                        "selling_value": total_selling_value,
                        "client": client,
                        "currency": currency,
                    }
                )

    # Calculate total selling value for all accounts
    total_selling_converted: float = (
        sum(
            [
                await convert(
                    from_currency=plan["currency"],
                    to_currency="INR",
                    amount=plan["selling_value"],
                )
                for plan in selling_plan
            ]
        )
        if selling_plan
        else 0
    )
    print("\n")
    # Print the final selling plan
    logger.info("--- Selling Plan ---")
    if not selling_plan:
        logger.info("No items to sell from any account.")
        return selling_plan

    logger.info(
        f"Total items to be sold: {sum(len(plan['items_to_sell']) for plan in selling_plan)}"
    )
    global processing_listings_total_items
    processing_listings_total_items = sum(
        len(plan["items_to_sell"]) for plan in selling_plan
    )

    logger.info(f"Total selling value: ₹{total_selling_converted:.2f}")
    print("\n")
    logger.info("Per-Account Breakdown:")
    for plan in selling_plan:
        print("\n")
        logger.info(f"{plan['username']}:")
        logger.info(
            f"  Wallet balance: {plan['currency']} {plan['wallet_balance']} (₹{await convert(from_currency=plan['currency'], to_currency='INR', amount=plan['wallet_balance']):.2f})"
        )
        logger.info(
            f"  Armoury value threshold: {plan['currency']} {plan['armoury_value']} (₹{await convert(from_currency=plan['currency'], to_currency='INR', amount=plan['armoury_value']):.2f})"
        )
        logger.info(
            f"  Items to be sold: {len(plan['items_to_sell'])} (₹{await convert(from_currency=plan['currency'], to_currency='INR', amount=plan['selling_value']):.2f})"
        )

        if plan["items_to_sell"]:
            logger.info("  Items:")
            item_counts: dict = defaultdict(int)
            item_values: dict = {}
            item_values_inr: dict = {}

            for item in plan["items_to_sell"]:
                name = item.description.market_hash_name
                item_counts[name] += 1
                if name not in item_values:
                    price = await get_db_price(
                        name, client=plan["client"], currency=plan["currency"]
                    )
                    item_values[name] = price
                    item_values_inr[name] = await convert(
                        from_currency=plan["currency"], to_currency="INR", amount=price
                    )

            for name, count in item_counts.items():
                logger.info(
                    f"    • {name} x {count} (₹{(item_values_inr[name] * count):.2f})"
                )

    async def process_account_plan(plan: dict) -> dict | None:
        if not plan["items_to_sell"]:
            return None

        account = plan["account_data"]["account"]
        username: str = account["steam_username"]
        client = plan["client"]

        client_recreated: bool = False
        if not client:
            client = await get_client(client)

            logger.trace(
                f"Successfully recreated client and logged in to account {username}"
            )
            client_recreated = True

        result: dict = {
            "account": username,
            "items_count": len(plan["items_to_sell"]),
            "planned_value": await convert(
                from_currency=plan["currency"],
                to_currency="INR",
                amount=plan["selling_value"],
            ),
            "actual_value": 0,  # Will be updated with actual sold value
            "success": False,
            "currency": plan["currency"],
        }

        try:
            print("\n")
            logger.info(
                f"Selling {len(plan['items_to_sell'])} items on account {username} (value: ₹{await convert(from_currency=plan['currency'], to_currency='INR', amount=plan['selling_value']):.2f})"
            )
            if client_recreated:
                sess = client.session  # type: ignore
            else:
                sess = plan["account_data"]["session"]

            session = sess

            try:
                (
                    success,
                    listed_items_price_converted,
                ) = await sell_immediately_manager_thread(
                    client, session, plan["items_to_sell"], username, account
                )

                # Calculate actual sold value by subtracting unsold value from planned value
                sold_value_converted: float = (
                    MULTIPLIER * result["planned_value"] - listed_items_price_converted
                ) / MULTIPLIER

                result["actual_value"] = sold_value_converted
                result["success"] = success
                result["items_unsold_value"] = listed_items_price_converted

                # If some items were sold but not all, consider it a partial success
                if sold_value_converted > 0 and not success:
                    result["partial_success"] = True

            except Exception as e:
                logger.error(f"Error listing sell from {username}: {e}")
                result["error"] = str(e)

        except Exception as e:
            logger.error(f"process account plain failed with exception: {e}")

        return result

    sell_results: list = []
    tasks: list = []

    # Create tasks for each plan
    for plan in selling_plan:
        tasks.append(process_account_plan(plan))

    # Execute all tasks concurrently with a progress bar
    for result in await tqdm_asyncio.gather(*tasks, desc="Processing accounts"):
        if result:  # Skip None results
            sell_results.append(result)

    # Add at the end of execute_selling function, right before return sell_results
    print("\n")
    logger.info("--- Final Wallet Balance Status ---")

    insufficient_accounts: list = []

    # Check final wallet balance for each account
    for plan in selling_plan:
        # Get the latest wallet balance
        client = plan["client"]
        username: str = plan["username"]
        currency: str = plan["currency"]
        armoury_value: float = plan["armoury_value"]

        try:
            wallet_balance_final: float = get_steam_balance(username)

            # Convert to INR for consistent display
            wallet_balance_inr = await convert(
                from_currency=currency, to_currency="INR", amount=wallet_balance_final
            )

            armoury_value_inr = await convert(
                from_currency=currency, to_currency="INR", amount=armoury_value
            )

            # Calculate percentage
            percentage: float = (
                (wallet_balance_final / armoury_value) * 100
                if armoury_value > 0
                else 100
            )
            # Print the status
            print("\n")
            logger.info(f"{username}:")
            logger.info(
                f"  Final wallet balance: {currency} {wallet_balance_final} (₹{wallet_balance_inr:.2f})"
            )
            logger.info(
                f"  Armoury value threshold: {currency} {armoury_value} (₹{armoury_value_inr:.2f})"
            )
            logger.info(f"  Balance percentage: {percentage:.2f}%")

            # Track accounts with insufficient balance
            if percentage < 100:
                insufficient_accounts.append(
                    {
                        "username": username,
                        "wallet_balance": wallet_balance_final,
                        "wallet_balance_inr": wallet_balance_inr,
                        "armoury_value": armoury_value,
                        "armoury_value_inr": armoury_value_inr,
                        "percentage": percentage,
                        "currency": currency,
                    }
                )
        except Exception as e:
            print("\n")
            logger.error(f"{username}:")
            logger.error(f"  Error getting final wallet balance: {e}")

    # Print warnings for accounts with insufficient balance
    if insufficient_accounts:
        print("\n")
        logger.warning("--- INSUFFICIENT WALLET BALANCE WARNING ---")
        for account in insufficient_accounts:
            logger.warning(
                f"WARNING: {account['username']} has only {account['percentage']:.2f}% of required armoury value"
            )
            logger.warning(
                f"  Wallet balance: {account['currency']} {account['wallet_balance']} (₹{account['wallet_balance_inr']:.2f})"
            )
            logger.warning(
                f"  Required: {account['currency']} {account['armoury_value']} (₹{account['armoury_value_inr']:.2f})"
            )
            logger.warning(
                f"  Missing: {account['currency']} {account['armoury_value'] - account['wallet_balance']} (₹{(account['armoury_value_inr'] - account['wallet_balance_inr']):.2f})"
            )

    return sell_results


async def sell_immediately_manager_thread(
    client: SteamClient,
    session: aiohttp.ClientSession,
    items_to_sell: list,
    username: str,
    account: dict,
) -> tuple[bool, float]:
    """
    Handles selling items in a separate thread. It sells items immediately by fulfilling buy orders.
    Will attempt up to 6 rounds of selling (initial + 5 possible cleanup rounds).

    Args:
        client: The SteamClient instance
        session: The session object
        items_to_sell: List of items to sell
        username: Username for the account
        account: the account dictionary

    Returns:
        bool: True if all items were successfully sold, False otherwise
    """

    def calculate_wait_time(cleanup_attempt: int) -> float:
        """
        Calculate the wait time for a cleanup attempt.
        The wait time increases uniformly from MIN_SELLING_TIME to MAX_SELLING_TIME_WAIT
        based on the cleanup attempt number.

        Args:
            cleanup_attempt: The current cleanup attempt number (1-based)

        Returns:
            The wait time in seconds
        """
        if MAX_CLEANUP_ATTEMPTS <= 1:
            return MIN_SELLING_TIME

        # Calculate the increment per attempt
        time_increment = (MAX_SELLING_TIME_WAIT - MIN_SELLING_TIME) / (
            MAX_CLEANUP_ATTEMPTS - 1
        )

        # Calculate wait time: starts at MIN_SELLING_TIME for attempt 1,
        # increases uniformly to MAX_SELLING_TIME_WAIT for the final attempt
        wait_time = MIN_SELLING_TIME + (cleanup_attempt - 1) * time_increment

        # Ensure we don't exceed the maximum
        return min(wait_time, MAX_SELLING_TIME_WAIT)

    # List of main items
    main_items: list[str] = [
        "Dreams & Nightmares Case",
        "Kilowatt Case",
        "Revolution Case",
        "Fracture Case",
        "Recoil Case",
        "Gallery Case",
        "Fever Case",
    ]

    non_main_items_found_final_check: bool = False

    # Track how many cleanup attempts we've made
    cleanup_attempts: int = 0

    # Price multiplier values
    initial_price_multiplier = INITIAL_CLEANUP_PRICE_MULTIPLIER
    price_decrement = CLEANUP_PRICE_DECREMENT

    (
        cancelled_old_listings,
        old_listed_items_price_converted,
    ) = await cancel_sell_listings(client, main_items, username, account)

    if cancelled_old_listings:
        logger.warning(
            f"Cancelled old listings worth ₹{old_listed_items_price_converted:.2f}"
        )  # Initial check for old listings

    # Initial selling attempt (no price multiplier for first attempt)
    await sell_items_batch(client, items_to_sell.copy(), account)

    # Continue with cleanup rounds if needed
    cleanup_needed: bool = True
    listed_items_price_converted: float = 0

    while cleanup_needed and cleanup_attempts < MAX_CLEANUP_ATTEMPTS:
        cleanup_attempts += 1

        # Calculate progressive wait time based on cleanup attempt
        wait_time = calculate_wait_time(cleanup_attempts)

        logger.info(
            f"Waiting {wait_time:.1f} seconds before cleanup attempt {cleanup_attempts}..."
        )
        await asyncio.sleep(wait_time)  # Progressive wait time

        # Check if any non-main items remain unsold
        cleanup_needed, listed_items_price_converted = await cancel_sell_listings(
            client, main_items, username, account
        )

        if cleanup_needed:
            # Calculate price multiplier for this cleanup round
            price_multiplier = initial_price_multiplier - (
                (cleanup_attempts - 1) * price_decrement
            )

            logger.info(
                f"Starting cleanup round {cleanup_attempts} with price multiplier {price_multiplier:.2f}..."
            )
            # Get fresh inventory and try selling again with reduced price multiplier
            items_to_process = await get_listable_inventory(client)
            await sell_items_batch(client, items_to_process, account, price_multiplier)

    # Update wallet balance when finished
    wallet_balance_cents_final = await steam_api_call_with_retry(
        client.get_wallet_balance
    )
    wallet_balance_final = wallet_balance_cents_final / 100
    update_steam_balance(username, wallet_balance_final)

    cleanup_needed_final, listed_items_price_converted = await cancel_sell_listings(
        client, main_items, username, account
    )

    non_main_items_found_final_check = cleanup_needed_final

    # Only return True if all items were successfully sold
    return (
        not non_main_items_found_final_check,
        listed_items_price_converted,
    )


# non_main_items_found_final_check is True if there are still unsold items


async def get_listable_inventory(client: SteamClient) -> list:
    """Get all marketable items from inventory"""
    inv = await get_full_inventory(client)
    listable_items: list = []

    for item in inv[0]:
        if item.description.marketable:
            listable_items.append(
                {
                    "item": item,
                    "name": item.description.market_hash_name,
                    "asset_id": item.asset_id,
                }
            )

    return listable_items


async def sell_items_batch(
    client: SteamClient,
    items_to_process: list,
    account: dict,
    price_multiplier: float = 1,
) -> None:
    """Process and sell items up to MAX_ITEMS_LIMIT in the provided list"""
    not_in_inventory_error_count: dict = {}

    async def sell_single_item(item_data, client: SteamClient) -> None:
        """Process and sell a single item"""
        if isinstance(item_data, dict):
            item = item_data["item"]
            name = item_data["name"]
            asset_id = item_data["asset_id"]
        else:
            item = item_data
            name = item.description.market_hash_name
            asset_id = item.asset_id

        # Calculate price
        latest_price = price_multiplier * (
            await get_db_price(name, client=client, currency=account["currency"])
        )
        latest_price = latest_price * MULTIPLIER
        latest_price_cents = math.ceil(latest_price * 100)
        latest_price_converted = await convert(
            from_currency=account["currency"],
            to_currency="INR",
            amount=latest_price_cents / 100,
        )

        try:
            sell_offer_id = await steam_api_call_with_retry(
                client.place_sell_listing,
                obj=item,
                price=latest_price_cents,
                app_context=AppContext.CS2,
                confirm=True,
            )
            await asyncio.sleep(0.1)
            if sell_offer_id:
                logger.info(
                    f"Inventory item {name} placed on sale for ₹{round(latest_price_converted, 2)}"
                )

                if item_data in items_to_process:  # Check if still in list
                    items_to_process.remove(item_data)
                    if asset_id in not_in_inventory_error_count:
                        del not_in_inventory_error_count[asset_id]

                # Acquire lock and update the global tqdm progress bar
                async with processing_listings_lock:
                    if processing_listings_progress is not None:
                        processing_listings_progress.update(1)
            else:
                logger.warning(f"Item {name} could not be listed.")
                if item_data in items_to_process:  # Check if still in list
                    items_to_process.remove(item_data)
                    items_to_process.append(item_data)
                await asyncio.sleep(1)

        except Exception as e:
            if "no longer in your inventory" in str(e).lower():
                await handle_inventory_error(
                    client,
                    items_to_process,
                    asset_id,
                    name,
                    not_in_inventory_error_count,
                )
            elif (
                "you already have a listing for this item pending confirmation"
                in str(e).lower()
            ):
                await handle_listing_confirmation_error(
                    client,
                    asset_id,
                )
            else:
                logger.error(f"Error while selling {name}: {e}")
                if item_data in items_to_process:  # Check if still in list
                    items_to_process.remove(item_data)
                    items_to_process.append(item_data)
                await asyncio.sleep(15)

    # Process items one by one in a sequential loop
    count = 0
    while items_to_process:
        if (
            MAX_ITEMS_LIMIT is not None
            and MAX_ITEMS_LIMIT > 0
            and count >= MAX_ITEMS_LIMIT
        ):
            break
        current_item = items_to_process[0]  # Get the first item
        await sell_single_item(current_item, client)
        count += 1


async def handle_listing_confirmation_error(
    client: SteamClient,
    asset_id: str,
) -> bool:
    """Handles the specific case of You already have a listing for this item pending confirmation where item is listed but is not confirmed and
    program tries to list the next item.
    """
    confirmation = await steam_api_call_with_retry(
        client.confirm_sell_listing, obj=asset_id, app_context=AppContext.CS2
    )

    if confirmation:
        return True
    else:
        return False


async def handle_inventory_error(
    client: SteamClient,
    items_to_process: list,
    asset_id: str,
    name: str,
    not_in_inventory_error_count: dict,
) -> None:
    """Handle the specific case of "no longer in inventory" errors"""
    # Initialize or increment error counter for this asset
    if asset_id not in not_in_inventory_error_count:
        not_in_inventory_error_count[asset_id] = 1
    else:
        not_in_inventory_error_count[asset_id] += 1

    error_count = not_in_inventory_error_count[asset_id]
    logger.warning(f"'No longer in inventory' error for {name} (attempt {error_count})")

    # First time: Just move to end of queue
    if error_count == 1:
        logger.info(f"First error occurrence for {name}, moving to end of queue")
        current_item = items_to_process.pop(0)
        items_to_process.append(current_item)

    # Second or third time: Wait and check inventory
    elif error_count in [2, 3]:
        wait_time = random.uniform(5, 10)
        logger.info(
            f"{'Second' if error_count == 2 else 'Third'} occurrence for {name}. "
            f"Waiting {wait_time:.2f} seconds to check inventory..."
        )
        await asyncio.sleep(wait_time)

        # Check if item is truly in inventory
        await check_item_in_inventory(
            client, items_to_process, asset_id, name, not_in_inventory_error_count
        )

    # Fourth time: Give up
    else:
        logger.critical(
            f"ALERT: Item {name} (asset ID: {asset_id}) failed to sell after 4 attempts"
        )
        logger.error(
            "This item may be stuck in the system. Removing from processing queue."
        )
        items_to_process.pop(0)
        del not_in_inventory_error_count[asset_id]


async def check_item_in_inventory(
    client: SteamClient,
    items_to_process: list,
    asset_id: str,
    name: str,
    not_in_inventory_error_count: dict,
) -> None:
    """Check if an item actually exists in inventory"""
    try:
        inventory = await get_full_inventory(client)
        item_exists = any(inv_item.asset_id == asset_id for inv_item in inventory[0])

        if not item_exists:
            logger.info(
                f"Item {name} (asset ID: {asset_id}) verified as no longer in inventory, assuming sold"
            )
            items_to_process.pop(0)
            del not_in_inventory_error_count[asset_id]
        else:
            logger.info(f"Item {name} still in inventory, trying again after delay")
            await asyncio.sleep(random.uniform(3, 5))
            # Keep at front of queue to try again
    except Exception as inv_error:
        logger.error(f"Error checking inventory: {inv_error}")
        # Move to end of queue if we couldn't check inventory
        current_item = items_to_process.pop(0)
        items_to_process.append(current_item)


async def cancel_sell_listings(
    client: SteamClient, main_items: list[str], username: str, account: dict
) -> tuple[bool, float]:
    """Check active listings and cancel any non-main items"""
    active_listings = await get_market_listings(client=client)
    listed_items: list = []
    listed_items_price_converted: float = 0

    non_main_items_found: bool = False
    if active_listings:
        for listing in active_listings:
            if listing.item.description.market_hash_name:
                """not in main_items for now this is being commented out and unused as relisting of main items has been found to be necessary
                even after 45 seconds of waiting. the overall code structure is not being changed so that it can be easily commented back in if needed"""
                logger.warning(
                    f"Item {listing.item.description.market_hash_name} remains unsold on account {username}. Cancelling..."
                )
                await steam_api_call_with_retry(client.cancel_sell_listing, obj=listing)

                async with processing_listings_lock:
                    if processing_listings_progress is not None:
                        processing_listings_progress.update(-1)

                non_main_items_found = True
                # Convert price to INR
                converted_listing_price = await convert(
                    from_currency=account["currency"],
                    to_currency="INR",
                    amount=listing.price / 100,
                )
                listed_items_price_converted += converted_listing_price

                listed_items.append(
                    {
                        "listing": listing,
                        "listing_id": listing.id,
                        "price": converted_listing_price,
                        "name": listing.item.description.market_hash_name,
                    }
                )

    return non_main_items_found, listed_items_price_converted


def get_unique_items(account_data_list: list) -> set:
    names: set = set()

    for acc in account_data_list:
        for item in acc["listable_items"]:
            names.add(item["name"])

    return names


import asyncio
from typing import Callable, Optional


async def items_lister(
    steam_usernames: list | None = None,
    sell_all_items: bool = False,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> bool:
    global \
        processing_listings_progress, \
        processing_listings_total_items, \
        processing_listings_lock
    """
    Main function to select and list items on farming accounts.

    Args:
        steam_usernames (list, optional): List of Steam usernames to process.
        progress_callback (Callable, optional): Function to call with progress updates (current, total, status).
    """

    # Progress monitoring coroutine
    async def monitor_progress():
        last_progress = 0
        while True:
            try:
                async with processing_listings_lock:
                    if processing_listings_progress is None:
                        break
                    current_progress = processing_listings_progress.n
                    total_progress = processing_listings_progress.total

                if current_progress > last_progress:
                    if progress_callback:
                        progress_callback(
                            current_progress, total_progress, "Listing items"
                        )
                    last_progress = current_progress

                # Check if completed
                if current_progress >= total_progress:
                    break

                await asyncio.sleep(0.5)  # Check every 500ms
            except Exception as e:
                logger.error(f"Progress monitoring error: {e}")
                break

    # Report initial progress
    if progress_callback:
        progress_callback(0, 0, "Initializing...")

    user_agents = UserAgentsService()
    await user_agents.load()
    all_accounts = get_all_steam_accounts()

    # Set active_armoury_passes to 5 for all accounts
    for acc in all_accounts:
        acc["active_armoury_passes"] = NUM_PASSES_REQUIRED

    # Filter accounts based on steam_usernames or get all armoury accounts
    if steam_usernames:
        selected_accounts = [
            acc
            for acc in all_accounts
            if acc["steam_username"] in steam_usernames and acc["is_armoury"]
        ]
        print("\n")
        logger.info(
            f"Fetching inventory data for {len(selected_accounts)} specified armoury accounts..."
        )
    else:
        selected_accounts = [acc for acc in all_accounts if acc["is_armoury"]]
        print("\n")
        logger.info(f"Processing all {len(selected_accounts)} armoury pass accounts...")

    if progress_callback:
        progress_callback(0, 0, "Fetching inventory data...")

    account_data_list: list = []

    async def process_accounts_inventory(selected_accounts) -> list:
        semaphore = asyncio.Semaphore(ACCOUNT_INVENTORY_SEMAPHORE)
        account_data_list = []

        async def process_account(account) -> dict:
            async with semaphore:
                logger.info(f"Getting inventory for {account['steam_username']}...")
                account_data = await get_account_details(account)
                return account_data

        tasks = [process_account(account) for account in selected_accounts]
        for future in tqdm_asyncio.as_completed(tasks):
            account_data = await future
            account_data_list.append(account_data)

        return account_data_list

    account_data_list = await process_accounts_inventory(selected_accounts)

    if progress_callback:
        progress_callback(0, 0, "Processing inventory data...")

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

    if progress_callback:
        progress_callback(0, 0, "Calculating item values...")

    # Update prices and calculate values for all accounts
    for account_data in account_data_list:
        listable_value: float = 0

        for item in account_data["listable_items"]:
            price = await get_db_price(
                item["name"],
                client=account_data["logged_in_client"],
                currency=account_data["currency"],
            )
            item["price"] = price
            listable_value += price

        account_data["listable_value"] = listable_value
        account_data["listable_value_converted"] = await convert(
            from_currency=account_data["currency"],
            to_currency="INR",
            amount=listable_value,
        )

    # Calculate totals
    total_listable_value_converted: float = sum(
        data["listable_value_converted"] for data in account_data_list
    )

    total_active_armoury_passes: int = sum(
        data["active_armoury_passes"] for data in account_data_list
    )
    print("\n")
    logger.info("--- Inventory Summary ---")
    logger.info(
        f"Total listable inventory value: ₹{total_listable_value_converted:.2f}"
    )
    logger.info(f"Total armory passes: {total_active_armoury_passes}")

    # =================================================================
    # FIXED TQDM CODE - MOVED HERE AFTER INVENTORY SUMMARY
    # =================================================================

    # Calculate total items to process BEFORE initializing progress bar
    if progress_callback:
        progress_callback(0, 0, "Calculating items to process...")

    # Calculate total items that will be processed
    processing_listings_total_items = 0
    for account_data in account_data_list:
        # Count items that have a price > 0 (items that will actually be listed)
        items_to_sell = [
            item
            for item in account_data["listable_items"]
            if item["price"] and item["price"] > 0
        ]
        processing_listings_total_items += len(items_to_sell)

    # Initialize the progress bar with the correct total
    async with processing_listings_lock:
        if processing_listings_progress is not None:
            processing_listings_progress.close()

        processing_listings_progress = tqdm_asyncio(
            total=processing_listings_total_items,
            desc="Processing Listings",
            unit="items",
        )

    if progress_callback:
        progress_callback(
            0, processing_listings_total_items, "Starting item listings..."
        )

    # Start progress monitoring before executing selling
    monitor_task = None
    if progress_callback and processing_listings_total_items > 0:
        monitor_task = asyncio.create_task(monitor_progress())

    try:
        # Execute selling (this function updates the global tqdm progress bar)
        results = await execute_selling(account_data_list, sell_all_items)
    finally:
        # Stop progress monitoring
        if monitor_task:
            monitor_task.cancel()
            try:
                await monitor_task
            except asyncio.CancelledError:
                pass

    print("\n")

    # Check for errors in results
    errors = [r for r in results if r.get("error")]

    if errors:
        logger.error(f"Errors count: {len(errors)}")
        for err in errors:
            logger.error(f"Account: {err['account']}, Error: {err['error']}")
        if progress_callback:
            progress_callback(
                processing_listings_total_items,
                processing_listings_total_items,
                f"Completed with {len(errors)} errors",
            )
    else:
        logger.success(" All Done.")
        if progress_callback:
            progress_callback(
                processing_listings_total_items,
                processing_listings_total_items,
                "All items listed successfully!",
            )

    # Close progress bar
    async with processing_listings_lock:
        if processing_listings_progress is not None:
            processing_listings_progress.close()
            processing_listings_progress = None

    if errors:
        return False
    else:
        return True


if __name__ == "__main__":
    asyncio.run(items_lister())
