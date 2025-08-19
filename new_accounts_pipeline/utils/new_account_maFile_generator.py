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


import json
import os
from typing import Any, Dict, List, Optional, Set

from tqdm import tqdm

from database import get_all_steam_accounts

# Directory where maFiles will be stored
MA_FILES_DIR: str = r"C:\Users\Sivasai\Documents\GitHub\CaseFarm\utils\cache\maFiles"
ALL_ACCOUNTS_TXT: str = (
    r"C:\Users\Sivasai\Documents\GitHub\CaseFarm\utils\botlooter\all_accounts.txt"
)


def create_ma_files() -> None:
    """
    Create .maFile files for Steam accounts with mobile authenticator data.

    Format:
    {username}.maFile: {
        "shared_secret": "megd9gV5b9zDszsHhIX+TLTJDLU=",
        "account_name": "ckxo3cwy4ygmrrfa9bf0de4pqicm",
        "token_gid": "379649271336386a",
        "identity_secret": "ykrdQNYX3I8SanM2OkTN+rEpgNg=",
        "steamid": "76561199705373654"
    }
    """
    # Ensure the maFiles directory exists
    os.makedirs(MA_FILES_DIR, exist_ok=True)
    logger.trace(f"Created directory: {MA_FILES_DIR}")

    # Get all Steam accounts from the database
    steam_accounts: List[Dict[str, Any]] = get_all_steam_accounts()

    # Check if accounts were retrieved successfully
    if not steam_accounts:
        logger.error("No Steam accounts found in the database.")
        return

    logger.info(f"Retrieved {len(steam_accounts)} accounts from the database.")

    # Track success and failure counts
    success_count: int = 0
    skip_count: int = 0

    # Process each account and create/update .maFile
    for account in tqdm(steam_accounts, desc="Creating .maFile files"):
        username: Optional[str] = account.get("steam_username")

        # Skip accounts without a username
        if not username:
            logger.warning("Skipping account with no username")
            skip_count += 1
            continue

        # Skip accounts without required Steam Guard mobile authenticator details
        if (
            not account.get("steam_shared_secret")
            or not account.get("steam_identity_secret")
            or not account.get("steam_id")
        ):
            logger.warning(
                f"Skipping {username}: Missing required Steam Guard mobile authenticator details."
            )
            skip_count += 1
            continue

        # Create the .maFile content
        ma_file_content: Dict[str, str] = {
            "shared_secret": account.get("steam_shared_secret"),
            "account_name": username,
            "token_gid": account.get("trade_token"),
            "identity_secret": account.get("steam_identity_secret"),
            "steamid": str(
                account.get("steam_id")
            ),  # Convert to string if it's an integer
        }

        # Write the .maFile
        ma_file_path: str = os.path.join(MA_FILES_DIR, f"{username}.maFile")
        try:
            with open(ma_file_path, "w") as f:
                json.dump(ma_file_content, f, indent=4)
            success_count += 1
            logger.debug(f"Created .maFile for {username}")
        except Exception as e:
            logger.error(f"Error creating .maFile for {username}: {e}")
            skip_count += 1

    logger.success(
        f"Finished creating .maFile files. Success: {success_count}, Skipped: {skip_count}"
    )


def update_accounts_txt() -> None:
    """
    Update all_accounts.txt with username:password pairs.
    Reads existing accounts into a set to ensure no duplicates,
    then adds new accounts and writes the unique set back to the file.
    """
    # Get all Steam accounts from the database
    steam_accounts: List[Dict[str, Any]] = get_all_steam_accounts()

    # Check if accounts were retrieved successfully
    if not steam_accounts:
        logger.error("No Steam accounts found in the database.")
        return

    # First, read existing accounts into a set (if file exists)
    unique_accounts: Set[str] = set()
    if os.path.exists(ALL_ACCOUNTS_TXT):
        with open(ALL_ACCOUNTS_TXT, "r") as f:
            for line in f:
                line = line.strip()
                if line:  # Skip empty lines
                    unique_accounts.add(line)
        logger.debug(f"Read {len(unique_accounts)} existing accounts from file")

    # Add new accounts to the set
    new_accounts_count: int = 0
    for account in steam_accounts:
        username: Optional[str] = account.get("steam_username")
        password: Optional[str] = account.get("steam_password")
        if username and password:
            account_entry: str = f"{username}:{password}"
            if account_entry not in unique_accounts:
                new_accounts_count += 1
            unique_accounts.add(account_entry)

    # Write the unique set of accounts back to the file
    with open(ALL_ACCOUNTS_TXT, "w") as f:
        for account in unique_accounts:
            f.write(f"{account}\n")

    logger.info(
        f"Updated {ALL_ACCOUNTS_TXT} with {len(unique_accounts)} unique accounts ({new_accounts_count} new)."
    )


def generate_files() -> None:
    create_ma_files()
    update_accounts_txt()
    logger.info("Completed Steam account file generation.")


if __name__ == "__main__":
    generate_files()
