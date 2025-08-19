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


import logging

import aiohttp

logging.getLogger("asyncio").setLevel(logging.CRITICAL)
import asyncio
import json
import re
import urllib.parse

# File paths
CS2_FILE_PATH = r"C:\Users\Sivasai\Documents\GitHub\CaseFarm\new_accounts_pipeline\cache\cs2names.txt"
OUTPUT_FILE_PATH = r"C:\Users\Sivasai\Documents\GitHub\CaseFarm\new_accounts_pipeline\cache\item_ids.json"

# Steam market app IDs
CS2_APP_ID = "730"

# Regex pattern to extract the item_id from the HTML
ITEM_ID_REGEX = r"Market_LoadOrderSpread\(\s*(\d+)\s*\)"


# Read names from files
async def read_names(file_path: str) -> list[str]:
    with open(file_path, "r") as f:
        return [line.strip() for line in f.readlines()]


# Fetch HTML for a given market hash name and app id, and extract item_id
async def fetch_item_id(
    session: aiohttp.ClientSession, market_hash_name: str, app_id: str
) -> dict | None:
    encoded_name = urllib.parse.quote(market_hash_name)
    url = f"https://steamcommunity.com/market/listings/{app_id}/{encoded_name}"
    async with session.get(url) as response:
        html_content = await response.text()
        with open("output.html", "w", encoding="utf-8") as f:
            f.write(html_content)
        # Extract the item ID using regex
        match = re.search(ITEM_ID_REGEX, html_content)
        if match:
            item_id = match.group(1)
            logger.info(f"Found item_id: {item_id} for {market_hash_name}")
            return {"market_hash_name": market_hash_name, "item_id": item_id}
        else:
            logger.error(f"No item_id found for {market_hash_name}")
            return None


# Main function
async def main() -> None:
    # Read item names
    cs2_names: list[str] = await read_names(CS2_FILE_PATH)
    item_list: list[dict] = []

    # Start an aiohttp session
    async with aiohttp.ClientSession() as session:
        # Process CS2 items one by one with a 0.5-second delay
        for name in cs2_names:
            item_data = await fetch_item_id(session, name, CS2_APP_ID)
            if item_data:
                item_list.append(item_data)
            await asyncio.sleep(0.5)  # Delay to avoid hitting rate limits

    # Save the extracted item data to a JSON file
    with open(OUTPUT_FILE_PATH, "w", encoding="utf-8") as json_file:
        json.dump(item_list, json_file, ensure_ascii=False, indent=4)

    logger.info(f"Item IDs saved to {OUTPUT_FILE_PATH}")


# Run the script
if __name__ == "__main__":
    asyncio.run(main())
