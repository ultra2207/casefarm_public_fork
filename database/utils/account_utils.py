import json
import os
import sqlite3
import sys
from typing import Any

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


# database files
DB_FILE = r"C:\Users\Sivasai\Documents\GitHub\CaseFarm\database\db\database.db"
PRICES_DB_PATH = r"C:\Users\Sivasai\Documents\GitHub\CaseFarm\database\db\prices.db"


# Updates trade token
def update_trade_token(steam_username: str, trade_token: str) -> None:
    """
    Update trade token for a specific Steam account.

    Args:
        steam_username (str): Steam username to update
        trade_token (str): New trade token
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute(
        """
    UPDATE accounts
    SET trade_token = ?
    WHERE steam_username = ?
    """,
        (trade_token, steam_username),
    )

    conn.commit()
    conn.close()


# Updates trade URL
def update_trade_url(steam_username: str, trade_url: str) -> None:
    """
    Update trade URL for a specific Steam account.

    Args:
        steam_username (str): Steam username to update
        trade_url (str): New trade URL
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute(
        """
    UPDATE accounts
    SET trade_url = ?
    WHERE steam_username = ?
    """,
        (trade_url, steam_username),
    )

    conn.commit()
    conn.close()


# get trade details (trade url and token)
def get_trade_details(steam_username: str) -> dict[str, Any] | None:
    """
    Retrieve trade URL and token for a specific Steam account.

    Args:
        steam_username (str): Steam username to look up

    Returns:
        tuple: A json with keys trade_token and trade_url
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute(
        """
    SELECT trade_token, trade_url
    FROM accounts
    WHERE steam_username = ?
    """,
        (steam_username,),
    )

    result = cursor.fetchone()
    conn.close()

    if result:
        return {"trade_token": result[0], "trade_url": result[1]}
    else:
        return None


# Update Prime Status
def update_prime_status(steam_username: str, new_prime: bool) -> None:
    """
    Update Prime status for a Steam account.

    Args:
        steam_username (str): Steam username to update
        new_prime (bool): New prime status (True/False)
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute(
        """
    UPDATE accounts
    SET prime = ?
    WHERE steam_username = ?
    """,
        (1 if new_prime else 0, steam_username),
    )

    conn.commit()
    conn.close()


# Update Armoury Passes
def update_active_armoury_passes(steam_username: str, new_passes: int) -> None:
    """
    Update the number of armoury passes for a Steam account.

    Args:
        steam_username (str): Steam username to update
        new_passes (int): Number of new passes (must be between 0 and 5)

    Note:
        Function will return early if new_passes is not within valid range
    """
    if not (0 <= new_passes <= 5):
        logger.error("Invalid number of armoury passes! Must be between 0 and 5.")
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute(
        """
    UPDATE accounts
    SET active_armoury_passes = ?
    WHERE steam_username = ?
    """,
        (new_passes, steam_username),
    )

    conn.commit()
    conn.close()


# Update Steam Balance
def update_steam_balance(steam_username: str, new_balance: float) -> None:
    """
    Update Steam wallet balance for a specific account.

    Args:
        steam_username (str): Steam username to update
        new_balance (float): New Steam wallet balance
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute(
        """
    UPDATE accounts
    SET steam_balance = ?
    WHERE steam_username = ?
    """,
        (float(new_balance), steam_username),
    )

    conn.commit()
    conn.close()


def read_steamgaurd_cli_accounts_into_database() -> None:
    """
    Read Steam Guard CLI accounts from hexogen.txt and maFiles directory into database.

    Process:
    1. Reads account credentials from hexogen.txt
    2. Processes .maFile files from steamguard-cli directory
    3. Combines data and updates database with account details

    Note:
        Requires hexogen.txt in new_accounts_pipeline directory and
        maFiles in the steamguard-cli AppData directory
    """
    # Step 1: Read hexogen.txt and store credentials using lower-case keys.
    hexogen_path = os.path.join("new_accounts_pipeline", "hexogen.txt")
    hexogen_data = {}
    with open(hexogen_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            # Remove extra tokens like "(NO_PHONE)" by taking only the first token.
            main_part = line.split()[0]
            # Expected format: username:steam_password|email_id:email_password
            parts = main_part.split(":")
            if len(parts) < 3:
                logger.error(f"Skipping invalid line: {line}")
                continue
            username = parts[0].strip()
            # Use lower-case key for case-insensitive matching.
            key = username.lower()
            subparts = parts[1].split("|")
            if len(subparts) < 2:
                logger.error(
                    f"Skipping invalid steam_password|email_id segment: {parts[1]}"
                )
                continue
            steam_password = subparts[0].strip()
            email_id = subparts[1].strip()
            email_password = parts[2].strip()
            hexogen_data[key] = {
                "steam_password": steam_password,
                "email_id": email_id,
                "email_password": email_password,
            }

    # Step 2: Process each CLI account JSON file from the maFiles directory.
    ma_files_directory = r"C:\Users\Sivasai\AppData\Roaming\steamguard-cli\maFiles"
    for filename in os.listdir(ma_files_directory):
        if filename.endswith(".maFile"):
            filepath = os.path.join(ma_files_directory, filename)
            try:
                with open(filepath, "r") as jf:
                    data = json.load(jf)
            except Exception as e:
                logger.error(f"Error loading JSON from {filename}: {e}")
                continue

            username = data.get("account_name")
            if not username:
                logger.error(f"No account_name found in {filename}")
                continue

            # Normalize username for matching.
            key = username.lower()
            if key not in hexogen_data:
                logger.error(f"No hexogen data found for username: {username}")
                continue

            credentials = hexogen_data[key]
            shared_secret = data.get("shared_secret")
            identity_secret = data.get("identity_secret")
            access_token = None
            refresh_token = None
            tokens = data.get("tokens", {})
            if isinstance(tokens, dict):
                access_token = tokens.get("access_token")
                refresh_token = tokens.get("refresh_token")
            steam_id = data.get("steam_id")

            # Step 3: Update the database.
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()

            # Using 'cli' as the steamguard type for CLI accounts.
            sql = """
            INSERT INTO accounts (
                steam_username, steam_password, email_id, email_password, steamguard,
                steam_shared_secret, steam_identity_secret, access_token, refresh_token, steam_id
            )
            VALUES (?, ?, ?, ?, 'mobile', ?, ?, ?, ?, ?)
            ON CONFLICT(steam_username) DO UPDATE SET
                steam_password=excluded.steam_password,
                email_id=excluded.email_id,
                email_password=excluded.email_password,
                steamguard=excluded.steamguard,
                steam_shared_secret=excluded.steam_shared_secret,
                steam_identity_secret=excluded.steam_identity_secret,
                access_token=excluded.access_token,
                refresh_token=excluded.refresh_token,
                steam_id=excluded.steam_id
            """
            try:
                cursor.execute(
                    sql,
                    (
                        username,
                        credentials["steam_password"],
                        credentials["email_id"],
                        credentials["email_password"],
                        shared_secret,
                        identity_secret,
                        access_token,
                        refresh_token,
                        steam_id,
                    ),
                )
                conn.commit()
                logger.info(f"Updated CLI account for username: {username}")
            except Exception as e:
                logger.critical(f"database error for {username}: {e}")
            finally:
                conn.close()


def read_steamgaurd_accounts_into_database(hexogen_path=None) -> None:
    """
    Read Steam Guard mobile accounts from hexogen.txt and _mobile.json files into database.
    Updates existing entries instead of creating duplicates.
    """
    # Step 1: Use default path if no path is provided
    if hexogen_path is None:
        hexogen_path = os.path.join("new_accounts_pipeline", "hexogen.txt")

    accounts_data = {}

    try:
        with open(hexogen_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                main_part = line.split()[0]
                parts = main_part.split(":")
                if len(parts) < 3:
                    logger.error(f"Skipping invalid line: {line}")
                    continue
                username = parts[0]
                subparts = parts[1].split("|")
                if len(subparts) < 2:
                    logger.error(
                        f"Skipping invalid steam_password|email_id segment: {parts[1]}"
                    )
                    continue
                steam_password = subparts[0]
                email_id = subparts[1]
                email_password = parts[2]
                accounts_data[username] = {
                    "steam_password": steam_password,
                    "email_id": email_id,
                    "email_password": email_password,
                }
    except FileNotFoundError:
        logger.error(f"Error: Could not find hexogen.txt at {hexogen_path}")
        return

    # Step 2: Process _mobile.json files and update database
    json_directory = r"C:\Users\Sivasai\AppData\Roaming\steamguard"
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # Ensure the table exists with the new schema
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY,
                steam_username TEXT UNIQUE,
                steam_password TEXT,
                email_id TEXT,
                email_password TEXT,
                prime INTEGER DEFAULT 0,
                active_armoury_passes INTEGER DEFAULT 0,
                steamguard TEXT,
                steam_balance REAL DEFAULT 0,
                steam_shared_secret TEXT,
                steam_identity_secret TEXT,
                access_token TEXT,
                refresh_token TEXT,
                steam_id TEXT,
                trade_token TEXT,
                trade_url TEXT,
                steam_avatar_path TEXT,
                bot_id TEXT,
                num_armoury_stars INTEGER DEFAULT 0,
                xp_level INTEGER DEFAULT 0,
                service_medal TEXT DEFAULT NULL,
                status TEXT DEFAULT 'inactive',
                xp INTEGER DEFAULT 0,
                region TEXT,
                currency TEXT,
                pass_value REAL DEFAULT 0,
                pua INTEGER DEFAULT 0,
                fua INTEGER DEFAULT 0,
                vac_ban INTEGER DEFAULT 0
            )
        """)

        # Create triggers for data validation
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS enforce_region_format
            BEFORE UPDATE OF region ON accounts
            FOR EACH ROW
            WHEN NEW.region IS NOT NULL AND (LENGTH(NEW.region) != 2 OR NEW.region != UPPER(NEW.region))
            BEGIN
                SELECT RAISE(ABORT, 'Region must be exactly 2 uppercase letters');
            END;
        """)

        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS enforce_region_format_insert
            BEFORE INSERT ON accounts
            FOR EACH ROW
            WHEN NEW.region IS NOT NULL AND (LENGTH(NEW.region) != 2 OR NEW.region != UPPER(NEW.region))
            BEGIN
                SELECT RAISE(ABORT, 'Region must be exactly 2 uppercase letters');
            END;
        """)

        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS enforce_currency_format
            BEFORE UPDATE OF currency ON accounts
            FOR EACH ROW
            WHEN NEW.currency IS NOT NULL AND (LENGTH(NEW.currency) != 3 OR NEW.currency != UPPER(NEW.currency))
            BEGIN
                SELECT RAISE(ABORT, 'Currency must be exactly 3 uppercase letters');
            END;
        """)

        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS enforce_currency_format_insert
            BEFORE INSERT ON accounts
            FOR EACH ROW
            WHEN NEW.currency IS NOT NULL AND (LENGTH(NEW.currency) != 3 OR NEW.currency != UPPER(NEW.currency))
            BEGIN
                SELECT RAISE(ABORT, 'Currency must be exactly 3 uppercase letters');
            END;
        """)

        for filename in os.listdir(json_directory):
            if not filename.endswith("_mobile.json"):
                continue

            filepath = os.path.join(json_directory, filename)

            try:
                with open(filepath, "r") as jf:
                    data = json.load(jf)

                username = filename[: -len("_mobile.json")]

                if username not in accounts_data:
                    logger.error(f"No hexogen data found for username: {username}")
                    continue

                account_details = accounts_data[username]
                shared_secret = data.get("shared_secret")
                identity_secret = data.get("identity_secret")

                # Check if account exists
                cursor.execute(
                    "SELECT id FROM accounts WHERE steam_username = ?", (username,)
                )
                result = cursor.fetchone()
                exists = result is not None

                # Begin transaction
                cursor.execute("BEGIN TRANSACTION")

                if exists:
                    # Update existing account
                    sql = """
                    UPDATE accounts SET
                        steam_password = ?,
                        email_id = ?,
                        email_password = ?,
                        steamguard = 'mobile',
                        steam_shared_secret = ?,
                        steam_identity_secret = ?
                    WHERE steam_username = ?
                    """
                    cursor.execute(
                        sql,
                        (
                            account_details["steam_password"],
                            account_details["email_id"],
                            account_details["email_password"],
                            shared_secret,
                            identity_secret,
                            username,
                        ),
                    )
                else:
                    # Insert new account with default values for new fields
                    sql = """
                    INSERT INTO accounts (
                        steam_username, steam_password, email_id, email_password, steamguard,
                        steam_shared_secret, steam_identity_secret, prime, active_armoury_passes,
                        steam_balance, status
                    )
                    VALUES (?, ?, ?, ?, 'mobile', ?, ?, 0, 0, 0.0, 'new')
                    """
                    cursor.execute(
                        sql,
                        (
                            username,
                            account_details["steam_password"],
                            account_details["email_id"],
                            account_details["email_password"],
                            shared_secret,
                            identity_secret,
                        ),
                    )

                # Commit transaction
                conn.commit()

                action = "Updated" if exists else "Inserted new"
                logger.info(f"{action} account for username: {username}")

            except json.JSONDecodeError:
                logger.error(f"Error: Invalid JSON in file {filename}")
                continue
            except sqlite3.Error as e:
                logger.critical(f"Database error for {username}: {e}")  # type: ignore
                if conn:
                    conn.rollback()
                continue

    except sqlite3.Error as e:
        logger.critical(f"Database error: {e}")
    finally:
        if conn:
            conn.close()


def get_steam_balance(steam_username: str) -> float:
    """
    Retrieve Steam wallet balance from the database for a given username.

    Args:
        steam_username (str): The Steam username to look up

    Returns:
        float: The Steam wallet balance

    Raises:
        Exception: If balance is not found for the username
    """
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        query = "SELECT steam_balance FROM accounts WHERE steam_username = ?"
        cursor.execute(query, (steam_username,))
        result = cursor.fetchone()

        if result is None:
            raise Exception(f"No balance found for username: {steam_username}")

        return float(result[0])

    except sqlite3.Error as e:
        raise Exception(f"database error: {str(e)}")

    finally:
        if conn:  # type: ignore
            conn.close()


def get_all_items() -> dict:
    """
    Connect to prices.db and return a dictionary
    of market_hash_name to item_id mappings.

    Returns:
        dict: A dictionary with market_hash_name as keys and item_id as values
    """
    # Define the path to the database
    db_path = PRICES_DB_PATH

    # Create a connection to the database
    conn = None
    result = {}

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Execute query to get market_hash_name and item_id
        cursor.execute("SELECT market_hash_name, item_id FROM prices")

        # Fetch all results and add to dictionary
        for row in cursor.fetchall():
            market_hash_name, item_id = row
            result[market_hash_name] = item_id

    except sqlite3.Error as e:
        logger.critical(f"database error: {e}")
    finally:
        if conn:
            conn.close()

    return result


def get_main_items() -> dict:
    """
    Connect to prices.db and return a dictionary
    of market_hash_name to item_id mappings for main items only.

    Returns:
        dict: A dictionary with market_hash_name as keys and item_id as values
              for the specified main items.
    """
    # Define the path to the database
    db_path = PRICES_DB_PATH

    # List of main items to filter
    main_items = [
        "Dreams & Nightmares Case",
        "Kilowatt Case",
        "Revolution Case",
        "Fracture Case",
        "Recoil Case",
        "Gallery Case",
    ]

    # Create a connection to the database
    conn = None
    result = {}

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Use a parameterized query to filter by main items
        query = """
            SELECT market_hash_name, item_id 
            FROM prices 
            WHERE market_hash_name IN ({})
        """.format(
            ",".join("?" for _ in main_items)
        )  # Dynamically generate placeholders

        cursor.execute(query, main_items)

        # Fetch all results and add to dictionary
        for row in cursor.fetchall():
            market_hash_name, item_id = row
            result[market_hash_name] = item_id

    except sqlite3.Error as e:
        logger.critical(f"database error: {e}")
    finally:
        if conn:
            conn.close()

    return result


def get_specific_items(item_names) -> dict[Any, None]:
    """
    Connect to prices.db and return a dictionary
    of market_hash_name to item_id and time mappings for the specified items.

    Args:
        item_names (set): A set of market_hash_names to filter by.

    Returns:
        dict: A dictionary with market_hash_name as keys and a dict containing
              'item_id' and 'time' as values for the specified items.
              If an item is not found, its value will be None.
    """
    db_path = PRICES_DB_PATH
    conn = None
    result = {name: None for name in item_names}

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        query = """
            SELECT market_hash_name, item_id, time 
            FROM prices 
            WHERE market_hash_name IN ({})
        """.format(",".join("?" for _ in item_names))

        cursor.execute(query, list(item_names))

        for row in cursor.fetchall():
            market_hash_name, item_id, timestamp = row
            result[market_hash_name] = {"item_id": item_id, "time": timestamp}  # type: ignore

    except sqlite3.Error as e:
        logger.critical(f"database error: {e}")
    finally:
        if conn:
            conn.close()

    return result


def get_steam_credentials(steam_username: str) -> dict[str, str]:
    """
    Retrieve Steam credentials from the database for a given username.

    Args:
        steam_username (str): The Steam username to look up

    Returns:
        Dict containing 'steam_password' and 'steam_shared_secret' and 'steam_identity_secret' and 'steam_id' (int)

    Raises:
        Exception: If credentials are not found for the username
    """

    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        query = """
        SELECT steam_password, steam_shared_secret, steam_identity_secret , steam_id
        FROM accounts 
        WHERE steam_username = ?
        """

        cursor.execute(query, (steam_username,))
        result = cursor.fetchone()

        if result is None:
            raise Exception(f"No credentials found for username: {steam_username}")

        credentials = {
            "steam_password": result[0],
            "steam_shared_secret": result[1],
            "steam_identity_secret": result[2],
            "steam_id": result[3],
        }

        return credentials

    except sqlite3.Error as e:
        raise Exception(f"database error: {str(e)}")

    finally:
        if conn:  # type: ignore
            conn.close()


def update_steam_avatar_path(username: str, avatar_path: str) -> bool:
    """
    Updates the steam_avatar_path for the specified account.

    Args:
        username (str): The Steam account username
        avatar_path (str): The path to the avatar file

    Returns:
        bool: True if successful, False otherwise
    """

    conn = None
    success = False

    try:
        # Connect to the database
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # Update the steam_avatar_path
        cursor.execute(
            "UPDATE accounts SET steam_avatar_path = ? WHERE steam_username = ?",
            (avatar_path, username),
        )

        # Commit the changes
        conn.commit()
        success = True

    except sqlite3.Error as e:
        logger.critical(f"database error updating avatar path: {e}")

    finally:
        # Close the connection
        if conn:
            conn.close()

    return success


def update_steam_id(steam_username: str, new_steam_id: int) -> None:
    """
    Updates the steam_id for a given steam_username in the database.

    :param db_file: Path to the SQLite database file.
    :param steam_username: The username to search for.
    :param new_steam_id: The new steam_id to update.
    """

    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE accounts SET steam_id = ? WHERE steam_username = ?",
            (new_steam_id, steam_username),
        )

        if cursor.rowcount == 0:
            logger.error("No matching username found.")
        else:
            pass

        conn.commit()
    except sqlite3.Error as e:
        logger.critical(f"SQLite error: {e}")
    finally:
        if conn:  # type: ignore
            conn.close()


def get_num_armoury_stars(username: str) -> int:
    """
    Fetches the number of armoury stars for the given Steam username.

    :param username: Steam username to look up
    :return: Number of armoury stars or None if not found



    """
    try:
        # Connect to the database
        conn = sqlite3.connect("DB_FILE")
        cursor = conn.cursor()

        # Execute the query
        cursor.execute(
            "SELECT num_armoury_stars FROM accounts WHERE steam_username = ?",
            (username,),
        )
        result = cursor.fetchone()

        # Close the connection
        conn.close()

        # Return the number of armoury stars if found, else None
        return result[0] if result else None  # type: ignore
    except sqlite3.Error as e:
        logger.critical(f"database error: {e}")
        return None  # type: ignore


def get_num_active_armoury_passes(username: str) -> int:
    """
    Fetches the number of armoury passes for the given Steam username.

    :param username: Steam username to look up
    :return: Number of armoury passes or 0 if not found
    """
    try:
        # Connect to the database
        conn = sqlite3.connect("DB_FILE")
        cursor = conn.cursor()

        # Execute the query
        cursor.execute(
            "SELECT active_armoury_passes FROM accounts WHERE steam_username = ?",
            (username,),
        )
        result = cursor.fetchone()

        # Close the connection
        conn.close()

        # Return the number of armoury passes if found, else None
        return result[0] if result else 0
    except sqlite3.Error as e:
        logger.critical(f"database error: {e}")
        return 0


def get_armoury_pass_value(username: str) -> float:
    """
    Fetches the number of armoury passes for the given Steam username.

    :param username: Steam username to look up
    :return: Number of armoury passes or None if not found



    """
    try:
        # Connect to the database
        conn = sqlite3.connect("DB_FILE")
        cursor = conn.cursor()

        # Execute the query
        cursor.execute(
            "SELECT pass_value FROM accounts WHERE steam_username = ?", (username,)
        )
        result = cursor.fetchone()

        # Close the connection
        conn.close()

        # Return the number of armoury passes if found, else 0
        return result[0] if result else 0
    except sqlite3.Error as e:
        logger.critical(f"database error: {e}")
        return 0


def update_pua_status(
    steam_username: str, pua_status: int, set_fua: bool = False
) -> bool:
    """
    Updates the PUA (Partially Upgraded Account) status for a specific Steam account in the database.

    This function updates the pua_status of the steam_username account. It ensures only one account
    can have PUA status at a time, and validates that no account has both PUA and FUA set to 1
    simultaneously. It also handles FUA status updates based on the logic:
    - If PUA is set to 1: FUA is automatically set to 0
    - If PUA is set to 0: FUA can optionally be set to 1 using the set_fua parameter

    Args:
        steam_username (str): The Steam username of the account to update (must exist in database).
        pua_status (int): The new PUA status value (0 = No PUA, 1 = PUA).
        set_fua (bool): If True and pua_status is 0, sets FUA to 1. Default is False.

    Returns:
        bool: True if the update was successful, False if an error occurred or no rows were affected.

    Raises:
        sqlite3.Error: If a database error occurs, it prints the error message and returns False.

    Example:
        # Set account as PUA (automatically removes PUA from other accounts)
        success = update_pua_status("player123", 1)
        if success:
            print("PUA status updated successfully")

        # Remove PUA status and set as FUA
        success = update_pua_status("player123", 0, set_fua=True)
        if success:
            print("PUA status removed and FUA status set successfully")
    """

    conn = None
    try:
        # Connect to the database
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # Validate database state before update
        cursor.execute("SELECT COUNT(*) FROM accounts WHERE pua = 1")
        pua_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM accounts WHERE pua = 1 AND fua = 1")
        invalid_count = cursor.fetchone()[0]

        if pua_count > 1:
            logger.error(
                f"Database integrity error: {pua_count} accounts have PUA=1, should be at most 1"
            )
            return False

        if invalid_count > 0:
            logger.error(
                f"Database integrity error: {invalid_count} accounts have both PUA=1 and FUA=1"
            )
            return False

        # Check if the target account exists
        cursor.execute(
            "SELECT steam_username FROM accounts WHERE steam_username = ?",
            (steam_username,),
        )
        if not cursor.fetchone():
            logger.warning(f"No account found with steam_username: {steam_username}")
            return False

        if pua_status == 1:
            # When setting PUA to 1, first remove PUA from all other accounts
            cursor.execute(
                "UPDATE accounts SET pua = 0 WHERE steam_username != ?",
                (steam_username,),
            )

            # Set the target account's PUA to 1 and FUA to 0
            cursor.execute(
                """
                UPDATE accounts 
                SET pua = 1, fua = 0 
                WHERE steam_username = ?
                """,
                (steam_username,),
            )

        elif pua_status == 0:
            # When setting PUA to 0, handle FUA based on set_fua parameter
            if set_fua:
                cursor.execute(
                    """
                    UPDATE accounts 
                    SET pua = 0, fua = 1 
                    WHERE steam_username = ?
                    """,
                    (steam_username,),
                )
            else:
                cursor.execute(
                    """
                    UPDATE accounts 
                    SET pua = 0 
                    WHERE steam_username = ?
                    """,
                    (steam_username,),
                )
        else:
            logger.error(f"Invalid PUA status value: {pua_status}. Must be 0 or 1")
            return False

        # Validate database state after update
        cursor.execute("SELECT COUNT(*) FROM accounts WHERE pua = 1")
        pua_count_after = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM accounts WHERE pua = 1 AND fua = 1")
        invalid_count_after = cursor.fetchone()[0]

        if pua_count_after > 1:
            logger.error(
                f"Post-update validation failed: {pua_count_after} accounts have PUA=1"
            )
            conn.rollback()
            return False

        if invalid_count_after > 0:
            logger.error(
                f"Post-update validation failed: {invalid_count_after} accounts have both PUA=1 and FUA=1"
            )
            conn.rollback()
            return False

        # Commit the changes
        conn.commit()

        # Check if any rows were affected
        if cursor.rowcount == 0:
            logger.warning(
                f"No rows were affected for steam_username: {steam_username}"
            )
            return False

        # Log the successful update
        if pua_status == 1:
            logger.info(
                f"Successfully updated PUA status to 1 for account: {steam_username} (FUA set to 0)"
            )
        else:
            fua_msg = " and FUA set to 1" if set_fua else ""
            logger.info(
                f"Successfully updated PUA status to 0 for account: {steam_username}{fua_msg}"
            )

        return True

    except sqlite3.Error as e:
        logger.critical(f"Database error while updating PUA status: {e}")
        if conn:
            conn.rollback()
        return False

    finally:
        if conn:
            conn.close()


def get_all_steam_accounts() -> list[dict[str, Any]] | list:
    """
    Retrieves all Steam account records from the 'accounts' table in the database.

    This function connects to the database specified by the global DB_FILE variable,
    fetches all Steam account entries, and returns them as a list of dictionaries.
    Each dictionary contains all columns from the table with the column names as keys.

    Returns:
        list: A list of dictionaries, where each dictionary represents a row from the accounts table.
        Each dictionary contains:
            - id (int): Unique identifier for the account.
            - steam_username (str): Steam account username (unique, not null).
            - steam_password (str): Steam account password (not null).
            - email_id (str): Email address linked to the Steam account (not null).
            - email_password (str): Password for the linked email (not null).
            - prime (bool): Whether the account has Prime status (0 = No, 1 = Yes, default 0).
            - active_armoury_passes (int): Number of available Armoury Passes (0-5, default 0).
            - steamguard (str): Type of Steam Guard protection ('email' or 'mobile', default 'email').
            - steam_balance (float): Current Steam Wallet balance (default 0.0).
            - steam_shared_secret (str or None): Shared secret for Steam mobile authenticator (optional).
            - steam_identity_secret (str or None): Identity secret for Steam confirmations (optional).
            - access_token (str or None): Access token for authentication (optional).
            - refresh_token (str or None): Refresh token for authentication (optional).
            - steam_id (int or None): Steam ID of the account (optional).
            - trade_token (str or None): Trade token for Steam trading (optional).
            - trade_url (str or None): Trade URL for the Steam account (optional).
            - steam_avatar_path (str or None): Path to the Steam avatar image (optional).
            - phno_linked (bool): Whether a phone number is linked (0 = No, 1 = Yes, default 1).
            - region (str): 2 letter country code of the account (default NULL).
            - currency (str): Currency of the account (default NULL). Is a 3 digit code.
            - pass_value (float): Armoury pass value. (default NULL)
            - pua (bool): Whether the account is partially upgraded or not
            - fua (bool): Whether the account is fully upgraded or not
            - vac_ban (bool): Whether the account has received a VAC ban or not (default 0)
            - is_armoury (bool): whether the account is an armoury pass account or not
            - inventory_value (float): value of all items based on steam prices before steam selling taxes
            - fua_threshold (int): multiple of the armoury pass value required for account to reach fua status
    Raises:
        sqlite3.Error: If a database error occurs, it prints the error message.

    Example:
        accounts = get_all_steam_accounts()
        for account in accounts:
            print(account["steam_username"], account["steam_avatar_path"])
    """

    conn = None
    try:
        # Connect to the database
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # Explicitly selecting each column (avoiding "SELECT *")
        cursor.execute("""
            SELECT 
                id, steam_username, steam_password, email_id, email_password, 
                prime, active_armoury_passes, steamguard, steam_balance, 
                steam_shared_secret, steam_identity_secret, access_token, 
                refresh_token, steam_id, trade_token, trade_url, 
                steam_avatar_path, region, currency, pass_value, pua, fua, is_armoury, inventory_value, fua_threshold
            FROM accounts
        """)

        # Fetch all rows and convert each row to a dictionary
        rows = cursor.fetchall()
        accounts = [
            {
                "id": row[0],
                "steam_username": row[1],
                "steam_password": row[2],
                "email_id": row[3],
                "email_password": row[4],
                "prime": bool(row[5]),
                "active_armoury_passes": row[6],
                "steamguard": row[7],
                "steam_balance": row[8],
                "steam_shared_secret": row[9],
                "steam_identity_secret": row[10],
                "access_token": row[11],
                "refresh_token": row[12],
                "steam_id": row[13],
                "trade_token": row[14],
                "trade_url": row[15],
                "steam_avatar_path": row[16],
                "region": row[17],
                "currency": row[18],
                "pass_value": row[19],
                "pua": row[20],
                "fua": row[21],
                "is_armoury": row[22],
                "inventory_value": row[23],
                "fua_threshold": row[24],
            }
            for row in rows
        ]

        return accounts

    except sqlite3.Error as e:
        logger.critical(f"database error: {e}")
        return []

    finally:
        if conn:
            conn.close()


def get_steam_id(steam_username) -> int | None:
    """
    Gets the steam_id for a given steam_username from the database.

    Parameters:
        steam_username (str): The Steam username to look up
        DB_FILE (str): The path to the SQLite database file

    Returns:
        int: The steam_id as an integer, or None if not found
    """
    try:
        # Connect to the SQLite database
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # Execute query to find the steam_id for the given username
        cursor.execute(
            "SELECT steam_id FROM accounts WHERE steam_username = ?", (steam_username,)
        )

        # Fetch the result
        result = cursor.fetchone()

        # Close the connection
        conn.close()

        # If result exists, convert to int and return
        if result and result[0]:
            return int(result[0])
        else:
            return None

    except sqlite3.Error as e:
        logger.critical(f"database error: {e}")
        return None
    except Exception as e:
        logger.error(f"Error: {e}")
        return None


def update_num_armoury_stars(steam_username: str, stars: int) -> None:
    try:
        conn = sqlite3.connect(
            DB_FILE
        )  # Ensure DB_FILE is defined globally or passed in
        cursor = conn.cursor()

        # Update the num_armoury_stars for the given username
        cursor.execute(
            """
            UPDATE accounts
            SET num_armoury_stars = ?
            WHERE steam_username = ?
        """,
            (stars, steam_username),
        )

        conn.commit()
        logger.info("Update successful") if cursor.rowcount > 0 else logger.info(
            "No records updated"
        )

    except sqlite3.Error as e:
        logger.critical("SQLite error:", e)
    finally:
        conn.close()  # type: ignore


def region_data_update_account(
    steam_username: str, currency_code: str, region: str = None
) -> bool:
    """
    Update the region and currency fields for a specific account in the database.

    Args:
        currency_code (str): ISO 4217 currency code (e.g., "IDR" for Indonesian Rupiah).
        steam_username (str): The steam_username of the account to update.
        region (str): ISO 3166-1 alpha-2 country code (optional, defaults to None).

    Returns:
        bool: True if successful, False otherwise.
    """
    try:
        # Connect to the SQLite database
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # Update query
        update_query = """
        UPDATE accounts 
        SET region = ?, currency = ? 
        WHERE steam_username = ?
        """

        # Execute the query
        cursor.execute(update_query, (region, currency_code.upper(), steam_username))

        # Check if the account was found and updated
        if cursor.rowcount == 0:
            logger.error(f"No account found with username: {steam_username}")
            conn.close()
            return False

        # Commit changes and close connection
        conn.commit()
        cursor.close()
        conn.close()

        logger.info(
            f"Updated account {steam_username} with region: {region}, currency: {currency_code.upper()}"
        )
        return True

    except Exception as e:
        logger.error(f"Error updating account: {e}")
        return False


def refresh_items_database(items_list, steam_username) -> bool:
    """
    Completely refresh items for a specific steam_username by:
    1. Deleting all existing items for that username
    2. Inserting all new items from the items_list
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Enable foreign key support
    cursor.execute("PRAGMA foreign_keys = ON;")

    try:
        # First, delete all existing items for this username
        cursor.execute("DELETE FROM items WHERE steam_username = ?", (steam_username,))
        deleted_count = cursor.rowcount
        logger.debug(f"Deleted {deleted_count} existing items for {steam_username}")

        # Then, insert all new items
        if items_list:
            # Prepare data for batch insert
            batch_data = [
                (
                    item["asset_id"],
                    item["market_hash_name"],
                    item["tradable_after_ist"],
                    item["tradable_after_unix"],
                    steam_username,
                    item["tradable"],
                    item["marketable"],
                    item["last_updated_unix"],
                    item["last_updated_ist"],
                )
                for item in items_list
            ]

            # Execute batch insert
            cursor.executemany(
                """
            INSERT INTO items 
            (asset_id, market_hash_name, tradable_after_ist, tradable_after_unix, steam_username, tradable, marketable, last_updated_unix, last_updated_ist)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                batch_data,
            )

            logger.debug(f"Added {len(batch_data)} new items for {steam_username}")
        else:
            logger.debug(f"No new items to add for {steam_username}")

        conn.commit()
        return True

    except sqlite3.Error as e:
        logger.error(f"Database error while refreshing items for {steam_username}: {e}")
        conn.rollback()
        return False

    finally:
        conn.close()


def update_account_inventory_value(steam_username: str, total_value: str) -> bool:
    """Updates inventory value of an account

    Args:
        steam_username (str)
        total_value (str): total value of all inventory items before tax
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        # Update query
        update_query = """
        UPDATE accounts 
        SET inventory_value = ? WHERE steam_username = ?
        """

        # Execute the query
        cursor.execute(update_query, (total_value, steam_username))
        conn.commit()
        cursor.close()
        conn.close()

        logger.info(
            f"Updated account {steam_username} with new inventory value of: ₹{total_value:.2f}"
        )

        return True

    except Exception as e:
        logger.error(f"Error updating account inventory value {steam_username}: {e}")
        return False


def get_account_inventory_database(steam_username: str) -> dict[str, int]:
    """ "gets the account inventory as a list of dicts with their market hash name and the count

    :param steam_username"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        query = "SELECT market_hash_name, steam_username FROM items where steam_username = ?"
        cursor.execute(query, (steam_username,))
        # Fetch all rows and convert each row to a dictionary
        rows = cursor.fetchall()
        items_dict = {}
        for row in rows:
            if row[0] not in items_dict:
                items_dict[row[0]] = 1
            else:
                items_dict[row[0]] += 1

        return items_dict

    except Exception as e:
        logger.error(f"Error during db operation {e}")
