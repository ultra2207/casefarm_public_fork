import asyncio
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
    get_account_inventory_database,
    get_all_steam_accounts,
    get_db_price,
    update_account_inventory_value,
    update_prices_from_market,
)
from utils.items_data_updater import update_items
from utils.logger import get_custom_logger

logger = get_custom_logger()


async def value_calculator(steam_username=None) -> bool:
    all_accounts = get_all_steam_accounts()

    if steam_username:
        # This block handles calculation for a single specified user
        total_value = 0
        await update_items(steam_usernames=[steam_username])
        inv = get_account_inventory_database(steam_username)
        items = list(inv.keys())

        if items:
            await update_prices_from_market(
                items_by_currency={"USD": items},
                override_armoury_only=True,
                update_prices_in_usd=True,
            )
            for item_name, quantity in inv.items():
                item_price = await get_db_price(item_name, currency="USD")
                total_value += item_price * quantity

        # Convert USD to INR and display with ₹ symbol
        converted_value = await convert("USD", "INR", total_value)

        print("\n\n\n")
        logger.info(
            f"Account {steam_username} inventory value with steam tax: ₹{converted_value:.2f}"
        )
        update_account_inventory_value(steam_username, converted_value)

    else:
        selected_accounts = [acc for acc in all_accounts if acc["prime"]]
        print("\n")
        logger.info(
            f"Fetching inventory values for {len(selected_accounts)} specified prime accounts..."
        )

        # await update_items()

        for acc in selected_accounts:
            total_value = 0
            current_username = acc["steam_username"]

            inv = get_account_inventory_database(current_username)
            items = list(inv.keys())

            if not items:
                logger.info(
                    f"Account {current_username} has an empty inventory. Skipping."
                )
                update_account_inventory_value(current_username, 0)
                continue

            await update_prices_from_market(
                items_by_currency={"USD": items},
                override_armoury_only=True,
                update_prices_in_usd=True,
            )

            for item_name, quantity in inv.items():
                item_price = await get_db_price(item_name, currency="USD")
                total_value += item_price * quantity

            # Convert USD to INR and display with ₹ symbol

            converted_value = await convert("USD", "INR", total_value)
            print("\n\n\n")
            logger.info(
                f"Account {current_username} inventory value: ₹{converted_value:.2f}"
            )
            update_account_inventory_value(current_username, converted_value)

    return True


if __name__ == "__main__":
    asyncio.run(value_calculator())  # By default it updates for all
