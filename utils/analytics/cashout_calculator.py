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
from accounts_manager.utils import update_steam_wallet_balances
from database import convert, get_all_steam_accounts
from utils.inventory_value_calculator import value_calculator
from utils.logger import get_custom_logger

logger = get_custom_logger()

PRIME_SOLD_PRICE = 14  # $14 selling price for prime accounts
PENDING_PASSES = 20.337  # This is a hardcoded value representing the number of pending Armoury Passes
# calculate this using mix of pending wallet balance and unredeemed Armoury stars

# calculates the cashout value of all steam accounts in the database if u turn everything into prime accounts and sell all


async def calculate_cashout(update: bool = True) -> int | float:
    if update:
        # Update steam wallet balances for all accounts
        logger.info("Updating steam wallet balances...")
        await update_steam_wallet_balances()
        logger.info("Steam wallet balances updated successfully.")
        logger.info("Updating inventory values...")
        await value_calculator()
        logger.info("Inventory values updated successfully.")

    # Fetch all accounts from database
    accounts = get_all_steam_accounts()

    # Convert each account's steam balance to INR and sum them
    total_steam_bal_inr = 0
    for account in accounts:
        balance = account["steam_balance"] or 0
        currency = account["currency"]
        if balance > 0 and currency:
            # Convert balance from account's currency to INR
            balance_inr = await convert(
                from_currency=currency, to_currency="INR", amount=balance
            )
            total_steam_bal_inr += balance_inr

    total_items_value_inr = 0
    for account in accounts:
        inventory_value = account["inventory_value"] or 0
        currency = account["currency"]  # Fixed: get currency for each account
        if inventory_value > 0:
            total_items_value_inr += (
                inventory_value  # The inventory values are already in INR
            )

    # Conversion factors (these are applied to INR values now)
    redemption_profitability = 1.2345
    steam_tax = 1.15
    # Apply conversion factors to the INR totals
    converted_bal = total_steam_bal_inr * redemption_profitability
    items_value_converted = total_items_value_inr / steam_tax

    # Additional calculations (not from database)
    pending_armoury_passes = PENDING_PASSES  # hardcoded by user
    additional_value_from_remaining_passes = await convert(
        from_currency="VND",
        to_currency="INR",
        amount=(400000 * pending_armoury_passes * (redemption_profitability)),
    )

    # Calculate prime accounts value
    prime_account_value_usd = PRIME_SOLD_PRICE
    prime_accounts_count = sum(1 for account in accounts if account["prime"])
    total_prime_value_usd = prime_accounts_count * prime_account_value_usd
    existing_prime_accounts_value = await convert(
        from_currency="USD", to_currency="INR", amount=total_prime_value_usd
    )

    total_available_steam_balance = (
        converted_bal + items_value_converted + additional_value_from_remaining_passes
    )

    # Calculate how many new accounts can be created
    real_money_conversion_factor = (1.15 / 1.0585) * 0.7
    prime_real_money_cost = 430.65
    prime_steam_balance_cost = 820

    # Calculate total cost per prime account in steam balance terms
    # Real money cost needs to be converted to steam balance equivalent
    real_money_cost_in_steam_balance = (
        prime_real_money_cost / real_money_conversion_factor
    )
    total_cost_per_prime_in_steam_balance = (
        prime_steam_balance_cost + real_money_cost_in_steam_balance
    )

    # Calculate how many prime accounts can be bought (fractional allowed)
    new_prime_accounts_possible = (
        total_available_steam_balance / total_cost_per_prime_in_steam_balance
    )

    # Calculate the value of new prime accounts that can be bought
    new_prime_accounts_value_usd = new_prime_accounts_possible * prime_account_value_usd
    new_prime_accounts_value_inr = await convert(
        from_currency="USD", to_currency="INR", amount=new_prime_accounts_value_usd
    )

    # Total prime accounts value (existing + new)
    total_prime_accounts_value = (
        existing_prime_accounts_value + new_prime_accounts_value_inr
    )

    # Print results
    logger.info("=== STEAM ACCOUNT ANALYSIS ===")
    logger.info(f"Total Steam Balance (INR): {total_steam_bal_inr:,.2f}")
    logger.info(f"Total Items Value (INR): {total_items_value_inr:,.2f}")
    logger.info(f"Converted Balance (INR): {converted_bal:,.2f}")
    logger.info(f"Items Value Converted (INR): {items_value_converted:,.2f}")
    logger.info(
        f"Additional Value from Passes (INR): {additional_value_from_remaining_passes:,.2f}"
    )
    logger.info(
        f"Total Available Steam Balance (INR): {total_available_steam_balance:,.2f}"
    )
    logger.info("\n=== PRIME ACCOUNTS ===")
    logger.info(f"Existing Prime Accounts: {prime_accounts_count}")
    logger.info(
        f"Existing Prime Accounts Value (INR): {existing_prime_accounts_value:,.2f}"
    )
    logger.info(f"New Prime Accounts Possible: {new_prime_accounts_possible:.4f}")
    logger.info(f"New Prime Accounts Value (INR): {new_prime_accounts_value_inr:,.2f}")
    print("\n")
    logger.success(f"Total Cashout Value (INR): {total_prime_accounts_value:,.2f}")

    return total_prime_accounts_value


if __name__ == "__main__":
    import asyncio

    asyncio.run(calculate_cashout(update=False))
