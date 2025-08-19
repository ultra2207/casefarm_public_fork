import asyncio
import logging
import random
import sqlite3
import time

import aiohttp
from aiosteampy import Currency, SteamClient, SteamPublicClient
from aiosteampy.constants import AppContext
from aiosteampy.ext.user_agents import UserAgentsService
from aiosteampy.models import EconItem, ItemOrdersHistogram
from aiosteampy.utils import patch_session_with_http_proxy

logging.getLogger("asyncio").setLevel(logging.CRITICAL)
import os
import sys
from typing import Any, Callable, Union

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
from utils.proxy import generate_proxy

logger = get_custom_logger()

import json
from pathlib import Path

from aiosteampy.helpers import restore_from_cookies
from aiosteampy.utils import get_jsonable_cookies
from tenacity import retry, stop_after_attempt, wait_exponential

from database.utils.account_utils import get_all_steam_accounts, get_specific_items


def load_config() -> dict:
    config_path = r"C:\Users\Sivasai\Documents\GitHub\CaseFarm\config.yaml"
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    return config


_config = load_config()

PRICES_DB_PATH = r"C:\Users\Sivasai\Documents\GitHub\CaseFarm\database\db\prices.db"
PERCENTAGE_OF_LOWEST_BUY_THRESHOLD = _config.get("PERCENTAGE_OF_LOWEST_BUY_THRESHOLD")
USE_PROXIES = _config.get("USE_PROXIES")
OUTDATED_TIME_SECONDS = _config.get("OUTDATED_TIME_SECONDS")
OUTDATED_TIME_SECONDS_MAIN = _config.get("OUTDATED_TIME_SECONDS_MAIN")
GET_INVENTORY_COUNT = _config.get("GET_INVENTORY_COUNT")
PRICE_SEMAPHORE = _config.get("PRICE_SEMAPHORE")
COOKIE_CACHE_DIR = _config.get(
    "COOKIE_CACHE_DIR",
    r"C:\Users\Sivasai\Documents\GitHub\CaseFarm\utils\cache\cookies",
)
MAX_RETRIES = _config.get("STEAM_API_CALL_MAX_RETRIES", 3)

# Define functions that should use a simple retry instead of a session refresh
SPECIAL_CASES = {"login", "logout", "close"}

helper_retry_decorator = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,  # Reraise the exception after the final attempt fails
)


def _recreate_client_from_existing(existing_client: SteamClient) -> SteamClient:
    """
    Creates a new SteamClient instance by copying credentials from an existing one.
    This is used to create a fresh client object for retries.
    This function does not perform I/O and does not need a retry decorator.
    """
    logger.debug(f"Re-creating client instance for {existing_client.username}")
    return SteamClient(
        steam_id=existing_client.steam_id,
        username=existing_client.username,
        password=getattr(existing_client, "_password", ""),
        shared_secret=getattr(existing_client, "_shared_secret", ""),
        identity_secret=getattr(existing_client, "_identity_secret", None),
        api_key=getattr(existing_client, "_api_key", None),
        trade_token=getattr(existing_client, "trade_token", None),
        language=existing_client.language,
        wallet_currency=existing_client.wallet_currency,
        wallet_country=existing_client.wallet_country,
        tz_offset=existing_client.tz_offset,
        user_agent=getattr(existing_client, "user_agent", None),
        # Note: proxy settings are part of the session and will be handled by cookie restoration
    )


@helper_retry_decorator
async def get_client_from_cookies(client_to_recreate: SteamClient) -> SteamClient:
    """
    Creates a new client instance and restores its session from cached cookies.
    Retries on failure using an exponential backoff.
    """
    username = client_to_recreate.username
    cookie_cache_path = Path(COOKIE_CACHE_DIR) / f"{username}_cookies.json"

    # Create a new client instance with the same credentials
    new_client = _recreate_client_from_existing(client_to_recreate)

    if cookie_cache_path.is_file():
        logger.info(f"Attempting to restore session from cookies for '{username}'.")
        with cookie_cache_path.open("r") as f:
            cookies = json.load(f)
        await restore_from_cookies(cookies, new_client)
    else:
        # If cookies are somehow missing, fall back to a full login.
        # The retry decorator will handle failures in this login attempt.
        logger.warning(
            f"No cookies found for '{username}' during retry. Performing a full login."
        )
        await new_client.login()

    return new_client


@helper_retry_decorator
async def save_cookies_and_close_session(client: SteamClient) -> None:
    """
    Saves the client's session cookies to a file and closes the session.
    Retries on failure (e.g., file write error) using an exponential backoff.
    """
    if not client or not client.session or client.session.closed:
        return

    username = client.username
    cookie_cache_path = Path(COOKIE_CACHE_DIR) / f"{username}_cookies.json"

    logger.info(f"Saving cookies for '{username}' and closing session.")
    with cookie_cache_path.open("w") as f:
        json.dump(get_jsonable_cookies(client.session), f, indent=4)


# --- Main Retry Function ---


async def steam_api_call_with_retry(
    func: Callable[..., Any],
    *args: Any,
    max_retries: int = 3,
    **kwargs: Any,
) -> Any:
    """
    Execute a Steam API call with a sophisticated, self-contained retry mechanism.

    Args:
        func: The async function to call (a method of a SteamClient or SteamPublicClient instance).
        *args: Arguments to pass to the function.
        max_retries: Maximum number of retry attempts.
        **kwargs: Keyword arguments to pass to the function.

    Returns:
        The result of the function call.
    """
    retries = 0
    client = func.__self__  # Get the client instance the method is bound to

    while True:
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            error_message = str(e).lower()
            if (
                "no longer in your inventory" in error_message
                or "you already have a listing for this item pending confirmation"
                in error_message
            ):
                client_name = (
                    client.username
                    if isinstance(client, SteamClient)
                    else "SteamPublicClient"
                )
                logger.error(f"Non-retriable error for {client_name}: {e}")
                raise

            if retries >= max_retries:
                client_name = (
                    client.username
                    if isinstance(client, SteamClient)
                    else "SteamPublicClient"
                )
                logger.error(
                    f"Max retries reached for {func.__name__} on account {client_name}. Raising exception."
                )
                raise

            retries += 1
            func_name = func.__name__

            client_name = (
                client.username
                if isinstance(client, SteamClient)
                else "SteamPublicClient"
            )
            logger.warning(
                f"Error on attempt {retries - 1} for '{func_name}' on account {client_name}: {e}. "
                f"Starting retry {retries}/{max_retries}..."
            )

            if func_name in SPECIAL_CASES:
                wait_time = retries * random.uniform(15, 25)
                logger.info(
                    f"Performing simple retry. Waiting {wait_time:.2f} seconds."
                )
                await asyncio.sleep(wait_time)
            else:
                if isinstance(client, SteamClient):
                    # SteamClient path - existing logic
                    logger.info(
                        f"Performing session refresh retry for {client.username}. Re-creating client."
                    )

                    # Save the old client's session and close it
                    await save_cookies_and_close_session(client)

                    # Create a new client instance and restore its session from the saved cookies
                    client = await get_client_from_cookies(client)

                    # Re-bind the function to the new client instance for the next attempt
                    func = getattr(client, func_name)

                    wait_time = random.uniform(10, 20)
                    logger.info(
                        f"New client session created for {client.username}. Waiting {wait_time:.2f} seconds."
                    )
                    await asyncio.sleep(wait_time)

                elif isinstance(client, SteamPublicClient):
                    # SteamPublicClient path - simple session recreation
                    logger.info(
                        "Performing session refresh retry for SteamPublicClient. Re-creating client."
                    )

                    wait_time = random.uniform(10, 20)
                    await asyncio.sleep(wait_time)

                    # Close old session
                    await client.session.close()

                    # Generate new session and create new client
                    session = generate_session()
                    client = SteamPublicClient(session=session, country="US")
                    logger.trace("Created new Steam Public client")

                    # Re-bind the function to the new client instance
                    func = getattr(client, func_name)

                else:
                    # Unintended usage - unknown client class
                    logger.critical(
                        f"Unrecognized client type {type(client)}. Cannot retry."
                    )
                    raise TypeError(
                        f"Unrecognized client type {type(client)} in steam_api_call_with_retry"
                    )


# Cache for exchange rates to reduce API calls
_exchange_rate_cache = {}
_cache_expiry = {}
_cache_duration = 3600  # 1 hour in seconds
_cache_lock = asyncio.Lock()


async def convert(
    from_currency: str, to_currency: str, amount: Union[int, float]
) -> Union[int, float]:
    """Convert an amount from one currency to another with caching."""
    if isinstance(amount, int):
        amount_type = "int"
    elif isinstance(amount, float):
        amount_type = "float"

    from_currency = from_currency.lower()
    to_currency = to_currency.lower()

    try:
        if from_currency == to_currency:
            return amount

        cache_key = f"{from_currency}_{to_currency}"
        current_time = time.time()
        exchange_rate = None

        async with _cache_lock:
            if (
                cache_key in _exchange_rate_cache
                and cache_key in _cache_expiry
                and current_time < _cache_expiry[cache_key]
            ):
                exchange_rate = _exchange_rate_cache[cache_key]

        if exchange_rate is None:
            url = f"https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/{from_currency}.json"
            logger.trace(f"Fetching exchange rate from {url}")
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        raise Exception(f"HTTP error: {response.status}")
                    data = await response.json()

            if from_currency not in data:
                raise Exception(
                    f"Currency {from_currency} not found in available rates"
                )
            rates = data[from_currency]

            if to_currency not in rates:
                raise Exception(f"Currency {to_currency} not found in available rates")

            exchange_rate = rates[to_currency]
            async with _cache_lock:
                _exchange_rate_cache[cache_key] = exchange_rate
                _cache_expiry[cache_key] = current_time + _cache_duration

        converted_amount = amount * exchange_rate
        if amount_type == "int":
            return int(round(converted_amount))
        else:  # amount_type == 'float'
            return float(converted_amount)
    except Exception as e:
        logger.warning(f"Conversion error: {str(e)}, retrying...")
        await asyncio.sleep(1)
        try:
            async with aiohttp.ClientSession() as session:
                backup_url = (
                    f"https://open.er-api.com/v6/latest/{from_currency.upper()}"
                )
                async with session.get(backup_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("result") == "success":
                            rates = data.get("rates", {})
                            if to_currency.upper() in rates:
                                rate = rates[to_currency.upper()]
                                converted_amount = amount * rate
                                return (
                                    int(round(converted_amount))
                                    if amount_type == "int"
                                    else float(converted_amount)
                                )
        except Exception as e:
            raise Exception(f"Conversion error: {str(e)}")


def generate_session(use_proxies=USE_PROXIES) -> aiohttp.ClientSession:
    if use_proxies:
        session = patch_session_with_http_proxy(
            aiohttp.ClientSession(raise_for_status=True), generate_proxy()
        )
    else:
        session = aiohttp.ClientSession(raise_for_status=True)

    return session


def update_price_in_db(
    market_hash_name: str, price: float, currency: str
) -> int | None:
    """
    Update the price and timestamp for an item in the prices database.

    Args:
        market_hash_name (str): The market hash name of the item
        price (float): The new price to set
        currency (str): The 3 letter currency string to get the column to update price

    Returns:
        int: 0 if a new column was created, None otherwise
    """
    db_path = PRICES_DB_PATH
    column_name = f"buy_order_price_{currency.lower()}"

    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if the column exists
        cursor.execute("PRAGMA table_info(prices)")
        columns = [info[1] for info in cursor.fetchall()]

        column_created = False
        if column_name not in columns:
            # Create the column if it doesn't exist
            query = f"ALTER TABLE prices ADD COLUMN {column_name} REAL"
            cursor.execute(query)
            column_created = True

        current_time = int(time.time())

        # Update the price in the appropriate column
        query = (
            f"UPDATE prices set {column_name} = ?, time = ? WHERE market_hash_name = ?"
        )
        cursor.execute(query, (price, current_time, market_hash_name))

        conn.commit()

        if column_created:
            return 0
        return None

    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        return None
    finally:
        if conn:
            conn.close()


CS2_APP_ID = "730"

# Configuration
LOCAL_FILE_PATH = (
    r"C:\Users\Sivasai\Documents\GitHub\CaseFarm\utils\cache\miscellaneous\730.json"
)
REMOTE_JSON_URL = "https://raw.githubusercontent.com/EricZhu-42/SteamTradingSite-ID-Mapper/main/steam/730.json"


async def load_local_json():
    """Load the local JSON cache file."""
    try:
        with open(LOCAL_FILE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as e:
        logger.error(f"Failed to read local JSON file: {e}")
        return {}


async def save_local_json(data):
    """Save data to the local JSON cache file."""
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(LOCAL_FILE_PATH), exist_ok=True)
        with open(LOCAL_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info("Local JSON file updated successfully.")
    except Exception as e:
        logger.error(f"Failed to save local JSON file: {e}")


async def fetch_remote_json(session):
    """Fetch the remote JSON data from GitHub."""
    try:
        async with session.get(REMOTE_JSON_URL) as response:
            if response.status == 200:
                remote_data = await response.json()
                logger.info("Fetched remote JSON data successfully.")
                return remote_data
            else:
                logger.error(f"Failed to fetch remote JSON, status: {response.status}")
                return {}
    except Exception as e:
        logger.error(f"Exception during remote JSON fetch: {e}")
        return {}


async def fetch_item_id(market_hash_name: str) -> int | None:
    """
    Fetch item_id (name_id) for a given market_hash_name.

    Args:
        market_hash_name: The English name of the item to lookup

    Returns:
        int: The name_id if found, None if not found

    Raises:
        ValueError: If item is not found even after updating cache
    """
    async with aiohttp.ClientSession() as session:
        # Load local JSON cache
        data = await load_local_json()

        # Search for item by en_name
        key_found = None
        for key, value in data.items():
            if value.get("en_name") == market_hash_name:
                key_found = key
                break

        # If found locally and has name_id
        if key_found and "name_id" in data[key_found]:
            item_id = data[key_found]["name_id"]
            logger.info(
                f"Found item_id: {item_id} for {market_hash_name} from local cache"
            )
            return item_id  # Return just the item_id, not a dict

        # Not found locally - fetch remote data and update cache
        logger.warning(
            f"Item_id not found for {market_hash_name} in local cache, fetching remote JSON..."
        )
        remote_data = await fetch_remote_json(session)

        if remote_data:
            # Update local data with remote data
            data.update(remote_data)
            await save_local_json(data)

            # Search again in updated data
            for key, value in data.items():
                if value.get("en_name") == market_hash_name and "name_id" in value:
                    item_id = value["name_id"]
                    logger.info(
                        f"Found item_id: {item_id} for {market_hash_name} after updating cache"
                    )
                    return item_id  # Return just the item_id, not a dict

        # Still not found - critical error
        logger.critical(
            f"Critical: item_id not found for {market_hash_name} even after updating cache"
        )
        raise ValueError(f"item_id not found for {market_hash_name}")


def get_item_id_from_db(market_hash_name: str) -> int:
    conn = sqlite3.connect(PRICES_DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT item_id FROM prices WHERE market_hash_name = ?", (market_hash_name,)
        )
        result = cursor.fetchone()
        if result:
            return result[0]
        raise Exception(f"Item '{market_hash_name}' not found in database")
    finally:
        conn.close()


async def add_to_db(
    market_hash_name: str, client: SteamClient | None = None, currency: str = "INR"
) -> None:
    """Adds the item with this market_hash_name to the db if it does not already exist."""
    # Simply call add_multiple_to_db with a single item
    logger.trace(f"Adding {market_hash_name} to database with currency {currency}")
    await add_multiple_to_db([market_hash_name], client, currencies=[currency])


def is_price_outdated(timestamp: int) -> bool:
    current_time = int(time.time())
    return (current_time - timestamp) > OUTDATED_TIME_SECONDS


def is_price_outdated_main(timestamp: int) -> bool:
    current_time = int(time.time())
    return (current_time - timestamp) > OUTDATED_TIME_SECONDS_MAIN


async def get_db_price(
    market_hash_name: str, client: SteamClient | None = None, currency: str = "INR"
) -> float:
    """Get the price of an item from the database using the market hash name. The option to update the price using the passed client is also present. It defaults to null.

    Note: Price is stored in cents in the database for compatibility reasons,
    so the returned value is divided by 100 to convert to the main currency unit.

    If the item is not already in the db, it is added. If the item is not one of the main items, it's price is also updated. Multiple prices for multiple different currencies are stored, pass the currency to get the price of that specific currency.
    """

    main_items = [
        "Dreams & Nightmares Case",
        "Kilowatt Case",
        "Revolution Case",
        "Fracture Case",
        "Recoil Case",
        "Gallery Case",
        "Fever Case",
    ]

    column_name = f"buy_order_price_{currency.lower()}"

    # Check if the column exists, create it if it doesn't
    conn = sqlite3.connect(PRICES_DB_PATH)
    cursor = conn.cursor()

    # Check if the column exists
    cursor.execute("PRAGMA table_info(prices)")
    columns = [info[1] for info in cursor.fetchall()]

    if column_name not in columns:
        # Create the column if it doesn't exist
        query = f"ALTER TABLE prices ADD COLUMN {column_name} REAL"
        cursor.execute(query)
        conn.commit()
        logger.info(f"Created new column {column_name} in prices table")

    # Check if the item exists in the database
    cursor.execute(
        f"SELECT {column_name} FROM prices WHERE market_hash_name = ?",
        (market_hash_name,),
    )
    result = cursor.fetchone()
    conn.close()

    if result is not None:
        # Item exists in the database

        # Check if price is None for the given currency
        if result[0] is None:
            # Price is None, so we need to update the price directly
            # without fetching item_id again since the item already exists
            logger.info(
                f"Item {market_hash_name} exists but {currency} price is None, updating price"
            )

            # Get the item_id from the database since the item already exists
            item_id = get_item_id_from_db(market_hash_name)
            new_price = await get_single_item_price(
                item_id=item_id, client=client, currency=currency
            )
            update_price_in_db(market_hash_name, new_price, currency)
            logger.trace(
                f"{market_hash_name} price updated to {new_price / 100:.2f} {currency} (was None)"
            )

            # Get the updated price from the database
            conn = sqlite3.connect(PRICES_DB_PATH)
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT {column_name} FROM prices WHERE market_hash_name = ?",
                (market_hash_name,),
            )
            result = cursor.fetchone()
            conn.close()

            return result[0] / 100  # Convert from cents to main currency unit

        # Price exists and is not None, check if it needs updating
        is_main_item = market_hash_name in main_items

        conn = sqlite3.connect(PRICES_DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT {column_name}, time FROM prices WHERE market_hash_name = ?",
            (market_hash_name,),
        )
        db_result = cursor.fetchone()
        conn.close()

        # Check if price needs to be updated
        price_outdated = (
            is_price_outdated_main(db_result[1])
            if is_main_item
            else is_price_outdated(db_result[1])
        )

        if db_result and not price_outdated:
            logger.trace(
                f"Using cached price for {market_hash_name}: {db_result[0] / 100} {currency}"
            )
            return db_result[0] / 100  # Return existing price if it's recent

        # Price is outdated, update it
        item_id = get_item_id_from_db(market_hash_name)
        new_price = await get_single_item_price(
            item_id=item_id, client=client, currency=currency
        )
        update_price_in_db(market_hash_name, new_price, currency)
        logger.trace(
            f"{market_hash_name} price updated to {new_price / 100:.2f} {currency}"
        )

        # Get the updated price from the database
        conn = sqlite3.connect(PRICES_DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT {column_name} FROM prices WHERE market_hash_name = ?",
            (market_hash_name,),
        )
        result = cursor.fetchone()
        conn.close()

        return result[0] / 100  # Convert from cents to main currency unit
    else:
        # Item doesn't exist in the database at all
        logger.info(f"Item {market_hash_name} not found in database, adding it now")
        if client:
            await add_to_db(market_hash_name, client, currency=currency)
        else:
            await add_to_db(market_hash_name, currency=currency)

        # Get the added price from the database
        conn = sqlite3.connect(PRICES_DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT {column_name} FROM prices WHERE market_hash_name = ?",
            (market_hash_name,),
        )
        result = cursor.fetchone()
        conn.close()

        if result and result[0] is not None:
            return result[0] / 100  # Convert from cents to main currency unit
        else:
            error_msg = f"Item still does not exist in the db or {currency} price is not available"
            logger.error(error_msg)
            raise Exception(error_msg)


async def get_db_price_usd_public(market_hash_name: str) -> float:
    """Get the price of an item from the database using the market hash name.

    Note: Price is stored in cents in the database for compatibility reasons,
    so the returned value is divided by 100 to convert to the main currency unit.

    If the item is not already in the db, it is added. If the item is not one of the main items, its price is also updated. Multiple prices for multiple different currencies are stored.
    This func is only for getting the USD price, refer to get_db_price to get prices in different currencies.
    """

    main_items = [
        "Dreams & Nightmares Case",
        "Kilowatt Case",
        "Revolution Case",
        "Fracture Case",
        "Recoil Case",
        "Gallery Case",
        "Fever Case",
    ]

    currency = "USD"
    column_name = f"buy_order_price_{currency.lower()}"

    # Check if the column exists, create it if it doesn't
    conn = sqlite3.connect(PRICES_DB_PATH)
    cursor = conn.cursor()

    # Check if the column exists
    cursor.execute("PRAGMA table_info(prices)")
    columns = [info[1] for info in cursor.fetchall()]

    if column_name not in columns:
        # Create the column if it doesn't exist
        query = f"ALTER TABLE prices ADD COLUMN {column_name} REAL"
        cursor.execute(query)
        conn.commit()
        logger.info(f"Created new column {column_name} in prices table")

    # Check if the item exists in the database
    cursor.execute(
        f"SELECT {column_name} FROM prices WHERE market_hash_name = ?",
        (market_hash_name,),
    )
    result = cursor.fetchone()
    conn.close()

    if result is not None:
        # Item exists in the database

        # Check if price is None for USD
        if result[0] is None:
            # Price is None, so we need to update the price directly
            # without adding the item again since it already exists
            logger.info(
                f"Item {market_hash_name} exists but USD price is None, updating price"
            )

            # Get the item_id from the database since the item already exists
            item_id = get_item_id_from_db(market_hash_name)
            new_price = await get_single_item_price_usd_public(item_id=item_id)
            update_price_in_db(market_hash_name, new_price, currency)
            logger.trace(
                f"{market_hash_name} price updated to {new_price / 100:.2f} {currency} (was None)"
            )

            # Get the updated price from the database
            conn = sqlite3.connect(PRICES_DB_PATH)
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT {column_name} FROM prices WHERE market_hash_name = ?",
                (market_hash_name,),
            )
            result = cursor.fetchone()
            conn.close()

            return result[0] / 100  # Convert from cents to main currency unit

        # Price exists and is not None, check if it needs updating
        is_main_item = market_hash_name in main_items

        conn = sqlite3.connect(PRICES_DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT {column_name}, time FROM prices WHERE market_hash_name = ?",
            (market_hash_name,),
        )
        db_result = cursor.fetchone()
        conn.close()

        # Check if price needs to be updated
        price_outdated = (
            is_price_outdated_main(db_result[1])
            if is_main_item
            else is_price_outdated(db_result[1])
        )

        if db_result and not price_outdated:
            logger.trace(
                f"Using cached price for {market_hash_name}: {db_result[0] / 100} {currency}"
            )
            return db_result[0] / 100  # Return existing price if it's recent

        # Price is outdated, update it
        item_id = get_item_id_from_db(market_hash_name)
        new_price = await get_single_item_price_usd_public(item_id=item_id)
        update_price_in_db(market_hash_name, new_price, currency)
        logger.trace(
            f"{market_hash_name} price updated to {new_price / 100:.2f} {currency}"
        )

        # Get the updated price from the database
        conn = sqlite3.connect(PRICES_DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT {column_name} FROM prices WHERE market_hash_name = ?",
            (market_hash_name,),
        )
        result = cursor.fetchone()
        conn.close()

        return result[0] / 100  # Convert from cents to main currency unit
    else:
        # Item doesn't exist in the database at all
        logger.info(f"Item {market_hash_name} not found in database, adding it now")
        await add_to_db(market_hash_name, currency=currency)

        # Get the added price from the database
        conn = sqlite3.connect(PRICES_DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT {column_name} FROM prices WHERE market_hash_name = ?",
            (market_hash_name,),
        )
        result = cursor.fetchone()
        conn.close()

        if result and result[0] is not None:
            return result[0] / 100  # Convert from cents to main currency unit
        else:
            error_msg = f"Item still does not exist in the db or {currency} price is not available"
            logger.error(error_msg)
            raise Exception(error_msg)


async def get_single_item_price(
    item_id: int, client: SteamClient | None = None, currency: str = "INR"
) -> float:
    """
    Get the price of a single item using an account with matching currency.

    Args:
        item_id: The Steam item ID
        client: Optional existing Steam client
        currency: Currency code (e.g. "INR", "USD")

    Returns:
        float: The item price in the requested currency
    """
    created_client = False

    try:
        if not client:
            all_accounts = get_all_steam_accounts()
            user_agents = UserAgentsService()
            await user_agents.load()

            # Find accounts with matching currency
            if currency != "USD":
                matching_accounts = [
                    acc for acc in all_accounts if acc["currency"] == currency
                ]
            else:
                matching_accounts = [
                    acc
                    for acc in all_accounts
                    if acc.get("currency") == "USD" or acc.get("currency") is None
                ]

            # If no matching accounts found, use any account as fallback
            if not matching_accounts:
                logger.warning(
                    f"No accounts found with currency {currency}. Using fallback."
                )
                matching_accounts = all_accounts

            # Select a random account from matching accounts
            account = random.choice(matching_accounts)
            client = await get_client(account)
            created_client = True
            logger.trace(f"Created new Steam client for currency {currency}")

        # Get the price using the client

        logger.trace(f"Fetching histogram for item_id {item_id}")
        histogram_result = await steam_api_call_with_retry(
            client.get_item_orders_histogram, item_id
        )
        histogram: ItemOrdersHistogram = histogram_result
        highest_buy_order = (
            histogram[0].highest_buy_order or 0.03
        )  # Default to 0.03 if None as its lowest possible value
        new_price = max(
            highest_buy_order,
            PERCENTAGE_OF_LOWEST_BUY_THRESHOLD * histogram[0].lowest_sell_order,  # type: ignore
        )

        logger.trace(f"Got price {new_price} for item_id {item_id} in {currency}")

        return float(new_price)
    finally:
        # Clean up if we created the client
        if created_client:
            try:
                await save_cookies_and_close_session(client)
                logger.trace("Successfully logged out from Steam client")
            except Exception as e:
                logger.error(f"Logout error: {e}")


async def get_single_item_price_usd_public(item_id: int) -> float:
    """
    Get the price of a single item using a SteamPublicClient.

    Args:
        item_id: The Steam item ID

    Returns:
        float: The item price in USD
    """
    try:
        session = generate_session()
        client = SteamPublicClient(session=session, country="US")
        logger.trace("Created new Steam Public client")

        # Get the price using the client

        logger.trace(f"Fetching histogram for item_id {item_id}")
        histogram_result = await steam_api_call_with_retry(
            client.get_item_orders_histogram, item_id
        )
        histogram: ItemOrdersHistogram = histogram_result
        new_price = max(
            histogram[0].highest_buy_order,
            PERCENTAGE_OF_LOWEST_BUY_THRESHOLD * histogram[0].lowest_sell_order,  # type: ignore
        )
        logger.trace(f"Got price {new_price} for item_id {item_id} in USD")

        return float(new_price)

    except Exception as e:
        logger.error(f"Error getting item price using steam public client: {e}")

    finally:
        try:
            await session.close()
        except Exception as e:
            logger.error(f"Error while closing aiohttp session: {e}")


async def get_multiple_items_prices(
    item_ids: list[int],
    client: SteamClient | None = None,
    currencies: list[str] = ["INR"],
) -> dict[str, dict[int, float | None]]:
    """
    Fetch prices for multiple items efficiently across multiple currencies.

    Args:
        item_ids: list of item IDs to fetch prices for
        client: Authenticated Steam client
        currencies: list of currency codes to fetch prices for

    Returns:
        dict: Nested dictionary mapping currency -> item_id -> price
    """
    # Make a copy of currencies to avoid modifying the original parameter
    remaining_currencies = currencies.copy()

    # Initialize results dictionary
    prices_by_currency: dict[str, dict[int, float | None]] = {
        currency: {} for currency in currencies
    }
    logger.trace(
        f"Fetching prices for {len(item_ids)} items in {currencies} currencies"
    )

    # If client is provided, use it only for its configured currency
    if client:
        client_currency = client.wallet_currency.name  # Missing .name
        if client_currency in remaining_currencies:
            try:
                logger.trace(f"Using provided client for currency {client_currency}")
                # Fetch prices for all items with the provided client
                for item_id in item_ids:
                    try:
                        logger.trace(
                            f"Fetching histogram for item_id {item_id} with {client_currency}"
                        )
                        histogram_result = await steam_api_call_with_retry(
                            client.get_item_orders_histogram, item_id
                        )
                        histogram: ItemOrdersHistogram = histogram_result
                        price = max(
                            histogram[0].highest_buy_order,
                            PERCENTAGE_OF_LOWEST_BUY_THRESHOLD
                            * histogram[0].lowest_sell_order,  # type: ignore
                        )
                        prices_by_currency[client_currency][item_id] = float(price)
                        logger.trace(
                            f"Got price {price} for item_id {item_id} in {client_currency}"
                        )
                        await asyncio.sleep(0.5)  # Add delay to avoid rate limiting
                    except Exception as e:
                        logger.error(
                            f"Error fetching price for item ID {item_id} in {client_currency}: {e}"
                        )
                        prices_by_currency[client_currency][item_id] = None

            except Exception as e:
                logger.error(f"Error using provided client for {client_currency}: {e}")
            finally:
                # Always remove this currency from the list, even if there was an error
                remaining_currencies = [
                    c for c in remaining_currencies if c != client_currency
                ]
                logger.trace(
                    f"Removed {client_currency} from remaining currencies. Remaining: {remaining_currencies}"
                )

    all_accounts = get_all_steam_accounts()
    user_agents = UserAgentsService()
    await user_agents.load()

    # Async function to handle price fetching for one account
    async def fetch_prices_for_account(account, items, currency) -> None:
        try:
            currency_client = await get_client(account)
            logger.trace(f"Created new Steam client for currency {currency}")

            # Process items for this account concurrently with semaphore control
            tasks = []
            for item_id in items:
                tasks.append(fetch_price_for_item(currency_client, item_id, currency))

            results = await asyncio.gather(
                *tasks, return_exceptions=True
            )  # Handle exceptions properly
            for item_id, result in zip(items, results):
                if isinstance(result, Exception):
                    logger.error(
                        f"Error fetching price for item ID {item_id} in {currency}: {result}"
                    )
                    prices_by_currency[currency][item_id] = None
                else:
                    prices_by_currency[currency][item_id] = result

        except Exception as e:
            logger.error(f"Error fetching prices for {currency}: {e}")
            import traceback

            logger.error(traceback.format_exc())  # Missing traceback logging
            # Set all items for this account to None on account failure
            for item_id in items:
                prices_by_currency[currency][item_id] = None

    # Async function to fetch price for single item with semaphore
    async def fetch_price_for_item(client, item_id, currency) -> float | None:
        semaphore = asyncio.Semaphore(PRICE_SEMAPHORE)
        async with semaphore:  # Limit concurrent requests
            try:
                logger.trace(
                    f"Fetching histogram for item_id {item_id} with {currency}"
                )
                histogram_result = await steam_api_call_with_retry(
                    client.get_item_orders_histogram, item_id
                )
                histogram: ItemOrdersHistogram = histogram_result
                price = max(
                    histogram[0].highest_buy_order,
                    PERCENTAGE_OF_LOWEST_BUY_THRESHOLD * histogram[0].lowest_sell_order,  # type: ignore
                )
                logger.trace(f"Got price {price} for item_id {item_id} in {currency}")
                await asyncio.sleep(0.5)  # Missing delay to avoid rate limiting
                return float(price)
            except Exception as e:
                logger.error(
                    f"Error fetching price for item ID {item_id} in {currency}: {e}"
                )
                return None

    # Create tasks for all accounts across all currencies
    tasks = []
    for currency in remaining_currencies:
        # Find accounts matching this currency
        if currency != "USD":
            matching_accounts = [
                acc for acc in all_accounts if acc["currency"] == currency
            ]
        else:
            matching_accounts = [
                acc
                for acc in all_accounts
                if acc.get("currency") == "USD" or acc.get("currency") is None
            ]

        if not matching_accounts:
            logger.warning(
                f"No accounts found with currency {currency}. Skipping this currency."
            )  # Missing warning log
            continue

        # Split items evenly among accounts
        chunk_size = (len(item_ids) + len(matching_accounts) - 1) // len(
            matching_accounts
        )
        for i, account in enumerate(matching_accounts):
            items_chunk = item_ids[i * chunk_size : (i + 1) * chunk_size]
            if items_chunk:
                tasks.append(fetch_prices_for_account(account, items_chunk, currency))

    # Execute all account tasks concurrently
    await asyncio.gather(*tasks, return_exceptions=True)  # Handle exceptions properly

    logger.trace(
        "Completed fetching prices for all items and currencies"
    )  # Missing completion log
    return prices_by_currency


async def add_multiple_to_db(
    market_hash_names: list[str],
    client: SteamClient | None = None,
    currencies: list[str] = ["INR"],
) -> None:
    """
    Add multiple items to the database in a single transaction with support for multiple currencies.

    Args:
        market_hash_names: list of market hash names to add to the database
        client: Authenticated Steam client
        currencies: list of currency codes to fetch prices for
    """
    logger.trace(
        f"Adding {len(market_hash_names)} items to database with currencies: {currencies}"
    )

    try:
        if not client:
            all_accounts = get_all_steam_accounts()
            user_agents = UserAgentsService()
            await user_agents.load()

            # Use the first currency in the list to find a matching account
            primary_currency = currencies[0]
            matching_accounts = [
                acc for acc in all_accounts if acc["currency"] == primary_currency
            ]

            if not matching_accounts:
                logger.warning(
                    f"No accounts found with currency {primary_currency}. Using fallback."
                )
                matching_accounts = all_accounts

            account = random.choice(matching_accounts)
            client = await get_client(account)
            logger.trace(
                f"Created new Steam client for primary currency {primary_currency}"
            )
        # Get item IDs for all market hash names
        logger.trace(
            f"Fetching item IDs for {len(market_hash_names)} market hash names"
        )
        item_id_tasks = [fetch_item_id(name) for name in market_hash_names]
        item_ids = await asyncio.gather(*item_id_tasks)

        # Map market hash names to item IDs, c
        name_to_id = {
            name: item_id
            for name, item_id in zip(market_hash_names, item_ids)
            if item_id is not None
        }
        logger.trace(f"Successfully fetched {len(name_to_id)} item IDs")

        # Get prices for all item IDs for all currencies
        logger.trace(
            f"Fetching prices for {len(name_to_id)} items across {len(currencies)} currencies"
        )
        prices_by_currency = await get_multiple_items_prices(
            list(name_to_id.values()), client, currencies=currencies
        )

        # Current timestamp
        latest_time = int(time.time())

        # Connect to database
        conn = sqlite3.connect(PRICES_DB_PATH)
        cursor = conn.cursor()
        logger.trace("Connected to database")

        # Ensure all currency columns exist
        for currency in currencies:
            column_name = f"buy_order_price_{currency.lower()}"
            cursor.execute("PRAGMA table_info(prices)")
            columns = [info[1] for info in cursor.fetchall()]

            if column_name not in columns:
                cursor.execute(
                    f"ALTER TABLE prices ADD COLUMN {column_name} REAL DEFAULT 0"
                )
                conn.commit()
                logger.info(f"Created new column {column_name} in prices table")

        try:
            # For each item, create or update its record
            logger.trace(f"Starting database updates for {len(name_to_id)} items")
            for name, item_id in name_to_id.items():
                # First, ensure the item exists with basic info
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO prices (market_hash_name, item_id, time)
                    VALUES (?, ?, ?)
                    """,
                    (name, item_id, latest_time),
                )
                logger.trace(
                    f"Inserted/updated basic info for {name} with item_id {item_id}"
                )

                # Then update each currency price in separate statements
                for currency in currencies:
                    column_name = f"buy_order_price_{currency.lower()}"
                    currency_prices = prices_by_currency.get(currency, {})
                    price = currency_prices.get(item_id)

                    if price is not None:
                        cursor.execute(
                            f"""
                            UPDATE prices
                            set {column_name} = ?, time = ?
                            WHERE market_hash_name = ?
                            """,
                            (price, latest_time, name),
                        )
                        logger.trace(
                            f"{name} price updated to {price / 100:.2f} {currency}"
                        )

            conn.commit()
            logger.info(
                f"Successfully added/updated {len(name_to_id)} items with {len(currencies)} currencies in the database"
            )

        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
            conn.rollback()

        finally:
            conn.close()
            logger.trace("Database connection closed")

    except Exception as e:
        logger.error(f"Error in add_multiple_to_db: {e}")
        import traceback

        logger.error(traceback.format_exc())


async def update_prices_from_market(
    items_by_currency: dict[str, set[str] | list[str]],  # Accept both set and list
    override_armoury_only: bool = False,
    update_prices_in_usd: bool = False,
    multiple_clients: list[Any] | None = None,
) -> None:
    """
    Update item prices of the specified items in the database using market data.

    Args:
        items_by_currency: dict mapping currency codes to lists or sets of market hash names to update
        override_armoury_only: If True, only update prices for accounts that are marked as "prime" in the database.
        update_prices_in_usd: Will use all USD accounts to update the usd prices
        multiple_clients: U may choose to pass the clients that will be used to obtain all of the prices. Note that there
        should be enough accounts for all currencies.
    """
    main_items = [
        "Dreams & Nightmares Case",
        "Kilowatt Case",
        "Revolution Case",
        "Fracture Case",
        "Recoil Case",
        "Gallery Case",
        "Fever Case",
    ]

    # Extract all unique item names from all currencies
    all_item_names = set()
    for item_collection in items_by_currency.values():
        all_item_names.update(item_collection)  # Works with both sets and lists

    items = get_specific_items(all_item_names)
    currencies = set(items_by_currency.keys())

    # Handle the case where pre-logged-in clients are provided
    if multiple_clients is not None:
        logger.info(f"Using {len(multiple_clients)} pre-logged-in clients")

        # Group clients by currency - extract currency string from Currency enum
        clients_by_currency = {}
        for client in multiple_clients:
            # Extract currency string from Currency enum object (e.g., Currency.INR -> "INR")
            client_currency = client.wallet_currency.name
            if client_currency not in clients_by_currency:
                clients_by_currency[client_currency] = []
            clients_by_currency[client_currency].append(client)

        logger.trace(f"Available client currencies: {list(clients_by_currency.keys())}")

        # Validate that we have clients for all requested currencies (except USD)
        non_usd_currencies = currencies - {"USD"}
        missing_currencies = non_usd_currencies - set(clients_by_currency.keys())
        if missing_currencies:
            raise ValueError(
                f"No clients provided for currencies: {missing_currencies}"
            )

        available_clients_by_currency = {
            currency: clients_by_currency[currency]
            for currency in currencies
            if currency in clients_by_currency and currency != "USD"  # Skip USD
        }
    else:
        # Get accounts and create clients for each currency
        if update_prices_in_usd:
            all_accounts_total = get_all_steam_accounts()
            all_accounts = [
                acc
                for acc in all_accounts_total
                if acc.get("currency") == "USD" or acc.get("currency") is None
            ]
            # Override currencies to only USD when update_prices_in_usd is True
            currencies = {"USD"}
            items_by_currency = {"USD": list(all_item_names)}
        elif override_armoury_only:
            all_accounts_total = get_all_steam_accounts()
            all_accounts = [acc for acc in all_accounts_total if acc["prime"]]
        else:
            all_accounts_total = get_all_steam_accounts()
            all_accounts = [acc for acc in all_accounts_total if acc["is_armoury"]]

        # Group accounts by currency
        accounts_by_currency = {}
        for acc in all_accounts:
            acc_currency = acc["currency"]
            if acc_currency not in accounts_by_currency:
                accounts_by_currency[acc_currency] = []
            accounts_by_currency[acc_currency].append(acc)

        # Create clients for each currency (except USD)
        available_clients_by_currency = {}
        for currency in currencies:
            if currency == "USD":
                # Skip USD as we'll use public API for it
                continue

            matching_accounts = accounts_by_currency.get(currency, [])
            if not matching_accounts:
                logger.warning(
                    f"No accounts found with currency {currency}. Skipping this currency."
                )
                continue

            # Create clients for this currency
            currency_clients = []
            for acc in matching_accounts:
                client = await get_client(acc)
                currency_clients.append(client)

            available_clients_by_currency[currency] = currency_clients

    logger.trace(
        f"Updating prices for {len(all_item_names)} total items across {len(currencies)} currencies"
    )

    async def process_items_for_client(
        client, item_names_for_client, currency, semaphore=None
    ):
        try:
            logger.trace(f"Using logged-in client for currency {currency}")

            items_to_add = []
            update_tasks = []

            for name in item_names_for_client:
                data = items.get(name)
                if data is None:
                    logger.info(
                        f"Item '{name}' not found in database. Adding to batch list for {currency}..."
                    )
                    items_to_add.append(name)
                else:
                    is_main_item = name in main_items
                    price_outdated = (
                        is_price_outdated_main(data["time"])
                        if is_main_item
                        else is_price_outdated(data["time"])
                    )
                    if price_outdated:

                        async def update_single_item_price(name=name, data=data):
                            try:
                                logger.trace(
                                    f"Fetching histogram for {name} (ID: {data['item_id']})"
                                )
                                histogram = await steam_api_call_with_retry(
                                    client.get_item_orders_histogram, data["item_id"]
                                )
                                new_price = max(
                                    histogram[0].highest_buy_order,
                                    PERCENTAGE_OF_LOWEST_BUY_THRESHOLD
                                    * (histogram[0].lowest_sell_order or 0),
                                )
                                update_price_in_db(
                                    market_hash_name=name,
                                    price=new_price,
                                    currency=currency,
                                )
                                logger.trace(
                                    f"{name} price updated to {new_price / 100:.2f} {currency}"
                                    + (" (main item)" if is_main_item else "")
                                )
                                await asyncio.sleep(0.5)
                            except Exception as e:
                                logger.error(
                                    f"Error updating price for {name} in {currency}: {e}"
                                )

                        update_tasks.append(update_single_item_price())
                    else:
                        logger.trace(
                            f"Item '{name}' found: ID={data['item_id']}, Time={data['time']} - Price is up to date"
                            + (" (main item)" if is_main_item else "")
                        )

            # Run updates concurrently with semaphore control (per client)
            if update_tasks:
                sem = (
                    semaphore
                    if semaphore is not None
                    else asyncio.Semaphore(PRICE_SEMAPHORE)
                )

                async def sem_task(task):
                    async with sem:
                        await task

                await asyncio.gather(*(sem_task(t) for t in update_tasks))

            if items_to_add:
                logger.info(
                    f"Adding {len(items_to_add)} items to database in a batch for {currency}..."
                )
                await add_multiple_to_db(items_to_add, client, currencies=[currency])

        except Exception as e:
            logger.error(
                f"Error processing {currency} in update_prices_from_market: {e}"
            )
            import traceback

            logger.error(traceback.format_exc())

    for currency in currencies:
        logger.info(f"Processing items for currency: {currency}")

        # Get the item names for this specific currency
        currency_item_names = items_by_currency.get(currency, [])
        if not currency_item_names:
            logger.info(f"No items to process for currency {currency}")
            continue

        # Special handling for USD currency - use public API instead of logged-in clients
        if currency == "USD":
            logger.info(
                f"Using public API for USD currency with {len(currency_item_names)} items"
            )

            async def process_usd_items_with_semaphore(item_names, semaphore_limit=4):
                semaphore = asyncio.Semaphore(semaphore_limit)

                async def process_single_usd_item(name):
                    async with semaphore:
                        try:
                            # Use get_db_price_usd_public for USD items
                            await get_db_price_usd_public(name)
                            logger.trace(f"Updated USD price for {name}")
                        except Exception as e:
                            logger.error(f"Error updating USD price for {name}: {e}")

                tasks = [process_single_usd_item(name) for name in item_names]
                await asyncio.gather(*tasks, return_exceptions=True)

            await process_usd_items_with_semaphore(currency_item_names)
            continue

        matching_clients = available_clients_by_currency.get(currency, [])
        if not matching_clients:
            logger.error(
                f"No clients found for currency {currency}. Skipping this currency."
            )
            continue

        logger.info(
            f"Found {len(matching_clients)} clients for currency {currency} with {len(currency_item_names)} items"
        )

        # Split items among available clients
        split_items = [[] for _ in range(len(matching_clients))]
        for idx, name in enumerate(
            currency_item_names
        ):  # Works with both sets and lists
            split_items[idx % len(matching_clients)].append(name)

        tasks = []
        # All clients run concurrently, each client processes its items concurrently (semaphore=4)
        for client, names in zip(matching_clients, split_items):
            if names:  # Only process if there are items for this client
                semaphore = asyncio.Semaphore(4)
                tasks.append(
                    process_items_for_client(
                        client,
                        names,
                        currency,
                        semaphore=semaphore,
                    )
                )

        if tasks:
            await asyncio.gather(*tasks)


async def _initialize_steam_client(account: dict[str, Any]) -> SteamClient:
    """Helper function to create a SteamClient instance without logging in."""
    user_agents = UserAgentsService()
    await user_agents.load()
    try:
        wallet_currency = getattr(Currency, account["currency"])
        wallet_country = account["region"]
    except (AttributeError, TypeError):
        wallet_currency = Currency.INR
        logger.warning(
            f"Currency '{account['currency']}' not found, defaulting to INR."
        )
        wallet_country = "IN"
    session = generate_session()
    return SteamClient(
        steam_id=int(account["steam_id"]),
        username=account["steam_username"],
        password=account["steam_password"],
        shared_secret=account["steam_shared_secret"],
        identity_secret=account["steam_identity_secret"],
        session=session,
        user_agent=user_agents.get_random(),
        wallet_country=wallet_country,
        wallet_currency=wallet_currency,
    )


async def get_client(account: dict[str, Any]) -> SteamClient:
    """
    Initializes and logs in a SteamClient, using cached cookies if available.

    The caller is responsible for closing the session and saving cookies
    using the `save_cookies_and_close_session` function.

    Args:
        account: The account dictionary with credentials.

    Returns:
        A logged-in SteamClient instance.
    """
    username = account["steam_username"]
    cookie_cache_path = Path(COOKIE_CACHE_DIR) / f"{username}_cookies.json"

    # Create the client instance (not logged in yet)
    client = await _initialize_steam_client(account)

    # Attempt to log in from cookies or perform a fresh login
    if cookie_cache_path.is_file():
        logger.trace(f"Attempting to restore session from cookies for '{username}'.")
        with cookie_cache_path.open("r") as f:
            cookies = json.load(f)
        await restore_from_cookies(cookies, client)
    else:
        logger.info(f"No cookies found. Performing a full login for '{username}'.")
        await steam_api_call_with_retry(client.login)

    return client


async def get_full_inventory(
    client: SteamClient, app_context=AppContext.CS2, batch_size=GET_INVENTORY_COUNT
) -> list[EconItem]:
    """Paginates through inventory and gets all items.

    Args:
        client : logged in aiosteampy steam client
        app_context (optional): appcontext.cs2 by default
        batch_size (optional): the batch size per inventory request

    Returns:
        list[EconItem]: a list of Inventory items of type EconItem
    """
    contents: list[EconItem] = []
    last_asset_id = None

    while True:
        if last_asset_id is None:
            inv = await steam_api_call_with_retry(
                client.get_inventory, app_context=app_context, count=batch_size
            )
        else:
            inv = await steam_api_call_with_retry(
                client.get_inventory,
                app_context=app_context,
                count=batch_size,
                last_assetid=last_asset_id,
            )

        contents.extend(inv)

        # Break if we received less than 1000 items (last page)
        if len(inv) < 1000:
            break

        # Get the asset_id of the last item for next pagination
        last_asset_id = inv[-1].asset_id

    return contents


async def get_account_details(account: dict[str, Any]) -> dict[str, Any]:
    """
    Get the inventory for a single account, utilizing session cookie caching
    to minimize logins while fetching inventory every time.
    """
    username = account["steam_username"]
    logger.info(f"Processing account: {username}")
    active_armoury_passes = account["active_armoury_passes"]

    # --- Define cache paths (cookies only) ---
    cookie_cache_path = Path(COOKIE_CACHE_DIR) / f"{username}_cookies.json"

    # Ensure cache directory exists
    cookie_cache_path.parent.mkdir(parents=True, exist_ok=True)

    # Ensure cookie cache file exists
    if not cookie_cache_path.exists():
        cookie_cache_path.write_text("{}", encoding="utf-8")

    # --- Initialize client ---
    client = await _initialize_steam_client(account)

    # Initialize variables from account
    pass_value = account.get("pass_value", 0)
    fua_threshold = account["fua_threshold"]
    currency = account["currency"]
    region = account["region"]
    is_armoury = account["is_armoury"]

    try:
        # 1. LOG IN THE CLIENT (with cookie restoration if available)
        if cookie_cache_path.is_file():
            logger.trace(
                f"Attempting to restore session from cookies for '{username}'."
            )
            with cookie_cache_path.open("r", encoding="utf-8") as f:
                cookies = json.load(f)
            await restore_from_cookies(cookies, client)
        else:
            logger.info(f"No cookies found. Performing a full login for '{username}'.")
            await steam_api_call_with_retry(client.login)

        # 2. ALWAYS FETCH INVENTORY
        logger.info(f"Fetching inventory for '{username}'.")
        inv = await get_full_inventory(client)

        listable_items = []
        non_listable_items = []

        for item in inv[0]:
            item_dict = {"item": item, "name": item.description.market_hash_name}
            if item.description.marketable:
                listable_items.append(item_dict)
            else:
                non_listable_items.append(item_dict)

        logger.info(f"Found {len(listable_items)} listable items for '{username}'.")

        # 3. RETURN RESULT (same structure as original)
        return {
            "account": account,
            "listable_items": listable_items,
            "non_listable_items": non_listable_items,
            "active_armoury_passes": active_armoury_passes,
            "logged_in_client": client,
            "session": client.session,
            "currency": currency,
            "pass_value": pass_value,
            "region": region,
            "is_armoury": is_armoury,
            "fua_threshold": fua_threshold,
        }

    finally:
        # 4. ALWAYS SAVE COOKIES
        if client.session and not client.session.closed:
            logger.trace(f"Saving cookies for '{username}'.")
            with cookie_cache_path.open("w", encoding="utf-8") as f:
                json.dump(get_jsonable_cookies(client.session), f, indent=4)
