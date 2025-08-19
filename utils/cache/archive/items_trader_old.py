import asyncio
import json
import os
import re
import subprocess
import sys
import time
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

from database import get_trade_details
from utils.trade_acceptor import accept_trades_account


async def run_botlooter(
    input_usernames: list[str],
    output_username: str,
    max_retries: int = 3,
    timeout: int = 60,
    autoaccept_trades: bool = False,
) -> bool:
    """
    Runs the botlooter executable with the specified input usernames and output username.

    Args:
        input_usernames (list[str]): List of usernames to filter from all_accounts.txt which will be used for trade sending
        output_username (str): Username for the output account to receive trades
        max_retries (int) (optional, default = 3): Maximum number of retries if the process fails
        timeout (int) (optional, default = 60): Timeout in seconds for the process to respond
        autoaccept_trades (bool) (optional, default = False): Flag to run trade acceptor after successful run

    Returns:
        Bool: Success or Failure
    """

    # Define file paths
    base_dir: str = r"C:\Users\Sivasai\Documents\GitHub\CaseFarm\utils\botlooter"
    all_accounts_path: str = os.path.join(base_dir, "all_accounts.txt")
    trade_accounts_path: str = os.path.join(base_dir, "trade_sending_accounts.txt")
    botlooter_exe: str = os.path.join(base_dir, "BotLooter.exe")
    logger.debug(f"Using botlooter from: {botlooter_exe}")

    # Read all accounts file
    try:
        with open(all_accounts_path, "r") as file:
            all_accounts: list[str] = file.readlines()
        logger.trace(f"Read {len(all_accounts)} accounts from all_accounts.txt")
    except FileNotFoundError:
        logger.error(f"Error: File {all_accounts_path} not found")
        return False

    # Filter accounts based on input usernames
    filtered_accounts: list[str] = []
    for line in all_accounts:
        line = line.strip()
        if not line:
            continue

        username: str = line.split(":")[0]
        if username in input_usernames:
            filtered_accounts.append(line)

    logger.debug(
        f"Filtered {len(filtered_accounts)} accounts from {len(all_accounts)} total accounts"
    )

    # Write filtered accounts to trade_sending_accounts.txt
    with open(trade_accounts_path, "w") as file:
        for account in filtered_accounts:
            file.write(f"{account}\n")
    logger.debug(
        f"Wrote {len(filtered_accounts)} filtered accounts to {trade_accounts_path}"
    )

    # update the config file
    trade_url: str = get_trade_details(output_username)["trade_url"]
    logger.debug(f"Retrieved trade URL for {output_username}")

    # Define the path to the config file
    config_file_path: str = r"C:\Users\Sivasai\Documents\GitHub\CaseFarm\utils\botlooter\BotLooter.Config.json"

    # Load the existing configuration
    with open(config_file_path, "r") as file:
        config_data: dict[str, Any] = json.load(file)
    logger.trace("Loaded existing BotLooter configuration")

    # Update the trade URL with the new one
    config_data["LootTradeOfferUrl"] = trade_url
    logger.debug(f"Updated trade URL in config to: {trade_url}")

    # Write the updated configuration back to the file
    with open(config_file_path, "w") as file:
        json.dump(config_data, file, indent=4)
    logger.debug("Wrote updated configuration back to file")

    for attempt in range(1, max_retries + 1):
        logger.info(f"Attempt {attempt}/{max_retries}")

        # Run BotLooter.exe with the correct working directory
        process = subprocess.Popen(
            [botlooter_exe],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.PIPE,
            universal_newlines=True,
            cwd=base_dir,
        )
        logger.debug(f"Started BotLooter process with PID: {process.pid}")

        last_output_time: float = time.time()
        unsuccessful_trades: int = 0
        successful_trades: int = 0
        process_stuck: bool = False

        try:
            # Read output line by line with timeout check
            while process.poll() is None:
                line: str = process.stdout.readline()

                if line:
                    logger.info(line.strip())  # Log the BotLooter output
                    last_output_time = time.time()

                    # Check for trade statistics
                    if "Unsuccessful trades:" in line:
                        match = re.search(r"Unsuccessful trades: (\d+)", line)
                        if match:
                            unsuccessful_trades = int(match.group(1))
                            logger.debug(
                                f"Detected {unsuccessful_trades} unsuccessful trades"
                            )

                    if "Successful trades:" in line:
                        match = re.search(r"Successful trades: (\d+)", line)
                        if match:
                            successful_trades = int(match.group(1))
                            logger.debug(
                                f"Detected {successful_trades} successful trades"
                            )
                else:
                    # Check for timeout - no output for specified time
                    if time.time() - last_output_time > timeout:
                        logger.warning(
                            f"Process appears to be stuck (no output for {timeout} seconds). Restarting..."
                        )
                        process_stuck = True
                        break
                    time.sleep(0.1)  # Small sleep to prevent CPU hogging

        except Exception as e:
            logger.error(f"Error reading output: {e}")
            process_stuck = True

        # Terminate the process if it's stuck
        if process_stuck or process.poll() is None:
            try:
                logger.warning("Terminating stuck process")
                process.terminate()
                time.sleep(2)
                if process.poll() is None:
                    logger.warning("Process did not terminate gracefully, killing it")
                    process.kill()
            except Exception as e:
                logger.error(f"Error while terminating process: {e}")
                pass

        # Check if successful
        if not process_stuck and unsuccessful_trades == 0:
            # Running the trade acceptor if autoaccept_trades is True
            if autoaccept_trades:
                logger.info("Running trade acceptor...")
                await accept_trades_account(output_username)

            logger.success("BotLooter process completed successfully")
            return True

        # Process failed, prepare for retry
        logger.warning(
            f"Process failed. Stats: Successful: {successful_trades}, Unsuccessful: {unsuccessful_trades}"
        )
        if attempt < max_retries:
            logger.info("Retrying in 3 seconds...")
            time.sleep(3)

    logger.error("Maximum retries reached. Process could not complete successfully.")
    return False


async def main() -> None:
    """
    Main function to run the BotLooter automation tool.
    """
    logger.info("BotLooter Automation Tool")
    logger.info("-------------------------")

    input_usernames: list[str] = ["lyingcod491"]
    output_username: str = "mellowSnail894"

    if not input_usernames:
        logger.warning("No usernames provided. Exiting.")
        return False

    logger.info(f"Items trader is processing {len(input_usernames)} usernames...")
    result: str = await run_botlooter(
        input_usernames, output_username, autoaccept_trades=True
    )

    logger.info(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
