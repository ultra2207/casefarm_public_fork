import json
import sys

import pandas as pd
import requests

# Add the requested import statements
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


# List of URLs and IDs
urls: list[tuple[str, int]] = [
    ("missing-link-charms", 330),
    ("small-arms-charms", 331),
    ("the-overpass-2024-collection", 334),
    ("the-graphic-design-collection", 335),
    ("the-sport-field-collection", 336),
    ("elemental-craft-stickers-collection", 338),
    ("character-craft-stickers-collection", 337),
]

# Gallery Case ID
gallery_case_id: int = 332

cookies: dict[str, str] = {
    "garequest": "true",
}

headers: dict[str, str] = {
    "accept": "*/*",
    "accept-language": "en-US,en;q=0.9",
    "cache-control": "no-cache",
    "pragma": "no-cache",
    "priority": "u=1, i",
    "referer": "https://csroi.com/item/the-overpass-2024-collection",
    "sec-ch-ua": '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
}


# Fetch ROI data for an item
def fetch_roi_data(item_id: int) -> list | None:
    url: str = f"https://csroi.com/pastData/{item_id}/steam/ROI.json"
    try:
        response = requests.get(url, cookies=cookies, headers=headers)
        response.raise_for_status()
        logger.debug(f"Successfully retrieved ROI data for item ID {item_id}")
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching data for item ID {item_id}: {e}")
        return None


def fetch_case_and_key_costs(case_id: int) -> tuple[list | None, list | None]:
    case_cost_url: str = f"https://csroi.com/pastData/{case_id}/steam/CaseCost.json"
    key_cost_url: str = f"https://csroi.com/pastData/{case_id}/steam/KeyCost.json"

    try:
        case_response = requests.get(case_cost_url, cookies=cookies, headers=headers)
        case_response.raise_for_status()
        case_costs = case_response.json()
        logger.debug(f"Successfully retrieved case cost data for case ID {case_id}")

        key_response = requests.get(key_cost_url, cookies=cookies, headers=headers)
        key_response.raise_for_status()
        key_costs = key_response.json()
        logger.debug(f"Successfully retrieved key cost data for case ID {case_id}")

        return case_costs, key_costs

    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching case/key costs for case ID {case_id}: {e}")
        return None, None


# Calculate final case cost and return ROI
def calculate_final_case_cost(case_costs: list, key_costs: list) -> list:
    case_df = pd.DataFrame(case_costs, columns=["timestamp", "case_cost"])
    key_df = pd.DataFrame(key_costs, columns=["timestamp", "key_cost"])

    # Convert timestamps to datetime objects
    case_df["timestamp"] = pd.to_datetime(case_df["timestamp"], unit="s")
    key_df["timestamp"] = pd.to_datetime(key_df["timestamp"], unit="s")

    # Merge based on timestamp
    merged_df = pd.merge(case_df, key_df, on="timestamp", how="inner")
    logger.trace(f"Merged dataframe has {len(merged_df)} rows")

    # Calculate net cost: (case_cost - key_cost) / tax_rate
    merged_df["roi"] = (
        merged_df["case_cost"] - merged_df["key_cost"]
    ) / 0.8  # Divide by 0.8 to get the roi considering cost is $0.8

    # Convert timestamps back to integers for JSON serialization
    result: list = []
    for index, row in merged_df.iterrows():
        unix_timestamp = int(row["timestamp"].timestamp())
        net_cost = row["roi"]
        result.append([unix_timestamp, net_cost])

    return result


# Collect data for all items
all_data: dict[str, list] = {}

# First fetch gallery case data specifically
logger.info("Fetching gallery case data")
case_costs, key_costs = fetch_case_and_key_costs(gallery_case_id)
if case_costs and key_costs:
    all_data["gallery-case"] = calculate_final_case_cost(case_costs, key_costs)
    logger.success("Successfully fetched and calculated data for gallery-case")
else:
    logger.error("Failed to fetch data for gallery-case")

# Then fetch all other items
logger.info("Fetching data for all other items")
for item_name, item_id in urls:
    logger.info(f"Processing {item_name} with ID {item_id}")
    data = fetch_roi_data(item_id)
    if data:
        all_data[item_name] = data
        logger.success(f"Successfully fetched data for {item_name}")
    else:
        logger.error(f"Failed to fetch data for {item_name}")

# Save all_data to rois.json
with open("rois.json", "w") as f:
    json.dump({k.replace("-", "_"): v for k, v in all_data.items()}, f, indent=4)
logger.success("Data successfully saved to rois.json")
