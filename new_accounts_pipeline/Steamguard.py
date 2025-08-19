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

import asyncio
import os
import re
from typing import Any, Dict, List, Optional

from utils.logger import get_custom_logger

logger = get_custom_logger()

from email_code import get_2fa_code_steamguard
from guard_utils import phone_number_remover
from steamguard import LoginConfirmType, SteamMobile

from database import read_steamgaurd_accounts_into_database

# Global file lock for concurrent operations
file_lock: asyncio.Lock = asyncio.Lock()

# Progress tracking callback (will be set by API server)
progress_callback: Optional[callable] = None


def set_progress_callback(callback: callable) -> None:
    """Set the progress callback function for real-time updates"""
    global progress_callback
    progress_callback = callback


async def emit_progress(
    message: str, progress: int, stage: str, level: str = "INFO"
) -> None:
    """Emit progress update if callback is set"""
    if progress_callback:
        await progress_callback(message, progress, stage, level)


async def process_account(
    line: str, semaphore: asyncio.Semaphore, account_index: int, total_accounts: int
) -> bool:
    """
    Process a single account line with progress tracking

    Args:
        line: Account line from file
        semaphore: Semaphore for concurrency control
        account_index: Current account index (0-based)
        total_accounts: Total number of accounts

    Returns:
        bool: True if successful, False otherwise
    """
    async with semaphore:
        try:
            content_before_split: str = line.strip()
            if not content_before_split:
                return False

            # Remove any parenthesis and their contents for parsing
            content: str = content_before_split.split("(")[0].strip()

            # Parse account information
            try:
                steam_part, email_part = content.split("|")
                steam_username, steam_password = [
                    x.strip() for x in steam_part.split(":")
                ]
                email_id, email_password = [x.strip() for x in email_part.split(":")]
            except ValueError:
                logger.error(f"Invalid account format in line: {line.strip()}")
                await emit_progress(
                    f"Skipped invalid format: {line[:20]}...", 0, "Processing", "ERROR"
                )
                return False

            logger.info(
                f"Processing account {account_index + 1}/{total_accounts}: {steam_username}"
            )
            await emit_progress(
                f"Processing account: {steam_username} ({account_index + 1}/{total_accounts})",
                int((account_index / total_accounts) * 80) + 10,  # 10-90% range
                "Processing",
            )

            # Handle phone number removal if present
            phone_match = re.search(r"\((\d+)\)", content_before_split)
            if phone_match:
                logger.info(f"Removing phone number for {steam_username}")
                removed: bool = await phone_number_remover(
                    steam_username, steam_password, email_id, email_password
                )
                if not removed:
                    logger.warning(
                        f"Phone number could not be removed for {steam_username}. Skipping."
                    )
                    await emit_progress(
                        f"Failed to remove phone for {steam_username}",
                        0,
                        "Processing",
                        "WARNING",
                    )
                    return False

            # Initialize Steam Mobile authenticator
            mobile: SteamMobile = SteamMobile(steam_username, steam_password)
            mobile.default_folder = r"C:\Users\Sivasai\AppData\Roaming\steamguard"

            # Steam authentication process
            logger.info(f"Connecting to Steam for {steam_username}")
            mobile.get_steampowered()
            mobile.get_steamcommunity()

            code_type: LoginConfirmType = mobile.login()

            if code_type == LoginConfirmType.none:
                mobile.confirm_login()
            elif code_type == LoginConfirmType.mobile:
                mobile_code: str = mobile.generate_steam_guard_code()
                if not mobile_code:
                    logger.error(
                        f"Could not generate Steam Guard code for {steam_username}"
                    )
                    await emit_progress(
                        f"Failed to generate code for {steam_username}",
                        0,
                        "Processing",
                        "ERROR",
                    )
                    return False
                mobile.confirm_login(mobile_code)

            # Add mobile authenticator
            logger.info(f"Adding mobile authenticator for {steam_username}")
            mobile.add_mobile_auth()

            # Export mobile data
            data_mobile = mobile.export_mobile()

            # Get email confirmation code
            logger.info(f"Getting email confirmation code for {steam_username}")
            email_code_confirm: str = await get_2fa_code_steamguard(
                email_id, email_password
            )

            if not email_code_confirm:
                logger.error(
                    f"Could not get email confirmation code for {steam_username}"
                )
                await emit_progress(
                    f"Failed to get email code for {steam_username}",
                    0,
                    "Processing",
                    "ERROR",
                )
                return False

            # Confirm mobile authenticator
            mobile.add_mobile_auth_confirm(email_code_confirm)
            mobile.save_exported_data(data_mobile, f"{mobile.account_name}_mobile.json")

            logger.info(f"Successfully generated mobile auth for {steam_username}")
            await emit_progress(
                f"Completed: {steam_username}", 0, "Processing", "SUCCESS"
            )

            # Remove processed line from remaining file
            await remove_processed_account(steam_username)

            return True

        except Exception as e:
            logger.error(
                f"Error processing account {steam_username if 'steam_username' in locals() else 'unknown'}: {e}"
            )
            await emit_progress(
                f"Error processing account: {str(e)[:50]}...", 0, "Processing", "ERROR"
            )
            return False


async def remove_processed_account(steam_username: str) -> None:
    """Remove processed account from the remaining file"""
    try:
        async with file_lock:
            remaining_file = r"new_accounts_pipeline\hexogen_remaining.txt"
            if os.path.exists(remaining_file):
                with open(remaining_file, "r") as f:
                    lines: List[str] = f.readlines()

                # Filter out the processed account
                updated_lines = [
                    line
                    for line in lines
                    if not line.strip().startswith(f"{steam_username}:")
                ]

                with open(remaining_file, "w") as f:
                    f.writelines(updated_lines)

                logger.trace(f"Removed {steam_username} from remaining accounts file")
    except Exception as e:
        logger.error(f"Error removing processed account {steam_username}: {e}")


async def load_accounts(hexogen_file_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load and process Steam Guard accounts with progress tracking

    Args:
        hexogen_file_path: Optional path to hexogen file

    Returns:
        Dict containing processing results
    """
    try:
        # Set file paths
        if hexogen_file_path is None:
            hexogen_path = r"new_accounts_pipeline\hexogen.txt"
            hexogen_remaining_path = r"new_accounts_pipeline\hexogen_remaining.txt"
        else:
            hexogen_path = hexogen_file_path
            path_parts = os.path.splitext(hexogen_file_path)
            hexogen_remaining_path = f"{path_parts[0]}_remaining{path_parts[1]}"

        logger.info(f"Starting account loading process: {hexogen_path}")
        await emit_progress("Initializing account loading process", 5, "Initializing")

        # Create remaining file if it doesn't exist
        if not os.path.exists(hexogen_remaining_path):
            if not os.path.exists(hexogen_path):
                error_msg = f"Hexogen file not found at {hexogen_path}!"
                logger.critical(error_msg)
                await emit_progress(error_msg, 0, "Error", "ERROR")
                raise FileNotFoundError(error_msg)

            logger.info("Creating remaining accounts file from source")
            with open(hexogen_path, "r", encoding="utf-8") as source:
                with open(hexogen_remaining_path, "w", encoding="utf-8") as target:
                    target.write(source.read())

        # Read accounts to process
        with open(hexogen_remaining_path, "r", encoding="utf-8") as f:
            lines: List[str] = f.readlines()

        # Filter out empty lines
        valid_lines = [line for line in lines if line.strip()]
        total_accounts = len(valid_lines)

        if total_accounts == 0:
            logger.info("No accounts to process")
            await emit_progress("No accounts found to process", 100, "Complete", "INFO")
            return {
                "status": "success",
                "accounts_processed": 0,
                "message": "No accounts to process",
            }

        logger.info(f"Found {total_accounts} accounts to process")
        await emit_progress(
            f"Found {total_accounts} accounts to process", 10, "Processing"
        )

        # Create semaphore for concurrency control
        semaphore: asyncio.Semaphore = asyncio.Semaphore(3)

        # Process accounts with progress tracking
        successful_count = 0
        failed_count = 0

        # Create tasks with index tracking
        tasks = []
        for index, line in enumerate(valid_lines):
            task = process_account(line, semaphore, index, total_accounts)
            tasks.append(task)

        # Execute all tasks and collect results
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Count successful and failed processes
        for result in results:
            if isinstance(result, Exception):
                failed_count += 1
                logger.error(f"Task failed with exception: {result}")
            elif result is True:
                successful_count += 1
            else:
                failed_count += 1

        logger.info(
            f"Account processing completed. Success: {successful_count}, Failed: {failed_count}"
        )
        await emit_progress("Reading accounts into database", 95, "Database")

        # Read processed accounts into database
        try:
            read_steamgaurd_accounts_into_database(hexogen_path)
            logger.info("Successfully read accounts into database")
        except Exception as e:
            logger.error(f"Error reading accounts into database: {e}")
            await emit_progress(f"Database error: {str(e)}", 95, "Database", "ERROR")

        # Final completion
        completion_message = (
            f"Processing complete! Success: {successful_count}, Failed: {failed_count}"
        )
        logger.info(completion_message)
        await emit_progress(completion_message, 100, "Complete", "SUCCESS")

        return {
            "status": "success",
            "accounts_processed": successful_count,
            "accounts_failed": failed_count,
            "total_accounts": total_accounts,
            "message": completion_message,
        }

    except Exception as e:
        error_message = f"Fatal error in load_accounts: {str(e)}"
        logger.critical(error_message)
        await emit_progress(error_message, 0, "Error", "ERROR")
        raise


if __name__ == "__main__":
    asyncio.run(load_accounts())
