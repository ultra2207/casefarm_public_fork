import json
import os
import sys
import time
from datetime import datetime, timedelta

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


#########################
# Helper Functions
#########################

# rewrite this with aiosteampy when u have the time


def parse_date(date_str: str) -> datetime:
    """
    Parses a date string in the format "Oct 10 2024 01: +0"
    and returns a datetime object (ignoring the timezone).
    """
    parts = date_str.split()
    if len(parts) < 5:
        raise ValueError(f"Unexpected date format: {date_str}")
    month, day, year, hour_with_colon, _ = parts
    hour = hour_with_colon.rstrip(":")
    clean_date_str = f"{month} {day} {year} {hour}"
    return datetime.strptime(clean_date_str, "%b %d %Y %H")


def analyze_prices(data: dict, verbose: bool = True, label: str = "") -> dict | None:
    """
        Processes the given data's "prices" list and computes only two key statistics
        for two periods:
          - Recent: Last 1 month (or fallback to all available data)
          - Overall: Last 4 months (or fallback to all available data)
    ...     For each period, it calculates:...       - Weighted Average Price = sum(price * volume) / sum(volume)
          - Weekly Sales = sum(volume) * (7 / ((365/12))) for recent
                          or sum(volume) * (7 / ((365/12) * 4)) for overall

        Returns a dictionary with the results for both periods along with the total volume,
        which is used for combining statistics later.
    """
    prices = data.get("prices", [])
    if not prices:
        if verbose:
            logger.warning(f"No price data available for {label}.")
        return None

    parsed_entries = []
    for entry in prices:
        date_str, price, sales = entry
        try:
            dt = parse_date(date_str)
        except Exception as e:
            logger.error(f"Error parsing date '{date_str}': {e}")
            continue
        # Ensure price is a float and sales (volume) is an int.
        parsed_entries.append((dt, float(price), int(sales)))

    if not parsed_entries:
        if verbose:
            logger.warning(f"No valid entries for {label}.")
        return None

    # Sort entries by date (oldest to newest)
    parsed_entries.sort(key=lambda x: x[0])
    now = parsed_entries[-1][0]

    # Define thresholds: recent = last 30 days, overall = last 120 days.
    recent_threshold = now - timedelta(days=30)
    overall_threshold = now - timedelta(days=121)

    recent_entries = [entry for entry in parsed_entries if entry[0] >= recent_threshold]
    if not recent_entries:
        # Fallback: use all available data if no recent entries.
        logger.debug(f"No recent entries for {label}, using all available data.")
        recent_entries = parsed_entries

    overall_entries = [
        entry for entry in parsed_entries if entry[0] >= overall_threshold
    ]
    if not overall_entries:
        logger.debug(f"No overall entries for {label}, using all available data.")
        overall_entries = parsed_entries

    # Compute statistics for recent period.
    total_volume_recent = sum(sales for _, _, sales in recent_entries)
    if total_volume_recent > 0:
        weighted_avg_price_recent = (
            sum(price * sales for _, price, sales in recent_entries)
            / total_volume_recent
        )
    else:
        weighted_avg_price_recent = 0
    # Weekly sales for recent: scale total volume by 7/(365/12).
    weekly_sales_recent = total_volume_recent * (7 / (365 / 12))

    # Compute statistics for overall period.
    total_volume_overall = sum(sales for _, _, sales in overall_entries)
    if total_volume_overall > 0:
        weighted_avg_price_overall = (
            sum(price * sales for _, price, sales in overall_entries)
            / total_volume_overall
        )
    else:
        weighted_avg_price_overall = 0
    # Weekly sales for overall: scale total volume by 7/((365/12)*4)
    weekly_sales_overall = total_volume_overall * (7 / ((365 / 12) * 4))

    if verbose:
        logger.info("Overall Statistics :")
        logger.info(f"  Weighted Average Price: ₹{weighted_avg_price_overall:.2f}")
        logger.info(f"  Weekly Sales: {weekly_sales_overall:.2f}")
        logger.info("Recent Statistics:")
        logger.info(f"  Weighted Average Price: ₹{weighted_avg_price_recent:.2f}")
        logger.info(f"  Weekly Sales: {weekly_sales_recent:.2f}")

    return {
        "overall": {
            "weighted_avg_price": weighted_avg_price_overall,
            "weekly_sales": weekly_sales_overall,
        },
        "recent": {
            "weighted_avg_price": weighted_avg_price_recent,
            "weekly_sales": weekly_sales_recent,
        },
    }


def fetch_update(
    case: str, price_histories_dir: str, base_url: str, cookies: dict, headers: dict
) -> dict | None:
    """
    Checks if a price_history file for the given case exists or is older than 30 minutes.
    If needed, fetches updated data from the URL and saves it.
    Returns the JSON data (or None if failed).
    """
    file_name = f"{case.replace(' ', '_')}.json"
    file_path = os.path.join(price_histories_dir, file_name)
    update_file = False

    if not os.path.exists(file_path):
        logger.debug(f"File doesn't exist for {case}, will fetch new data.")
        update_file = True
    else:
        file_age = (time.time() - os.path.getmtime(file_path)) / 60  # in minutes
        if file_age > 30:
            logger.debug(
                f"File for {case} is {file_age:.1f} minutes old, will fetch new data."
            )
            update_file = True
        else:
            logger.debug(f"File for {case} is {file_age:.1f} minutes old, still fresh.")

    if update_file:
        print("\n")
        logger.info(f"Fetching data for: {case}")
        params = {
            "appid": "730",
            "market_hash_name": case,
        }
        response = requests.get(
            base_url, params=params, cookies=cookies, headers=headers
        )
        if response.status_code == 200:
            data = response.json()
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            logger.info(f"Saved: {file_path}")
            return data
        else:
            logger.error(
                f"Failed to fetch data for {case} - Status Code: {response.status_code}"
            )
            if os.path.exists(file_path):
                logger.warning(f"Using existing cached data for {case}")
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return data
            return None
    else:
        print("\n")
        logger.info(f"Using price_historiesd data for: {case}")
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data


def combine_stats(stats_list: list[dict]) -> dict:
    combined_weighted_avg_price = sum(
        s["weighted_avg_price"] * s["weekly_sales"] for s in stats_list
    ) / sum(s["weekly_sales"] for s in stats_list)
    combined_weekly_sales = sum(s["weekly_sales"] for s in stats_list)
    return {
        "weighted_avg_price": combined_weighted_avg_price,
        "weekly_sales": combined_weekly_sales,
    }


#########################
# Main Integration Code
#########################


def main() -> None:
    # Ensure price_histories directory exists.
    price_histories_dir = (
        r"C:\Users\Sivasai\Documents\GitHub\CaseFarm\utils\cache\price_histories"
    )
    os.makedirs(price_histories_dir, exist_ok=True)
    logger.debug(f"Using price histories directory: {price_histories_dir}")

    # Define all cases for data fetching
    all_cases = [
        "Fracture Case",
        "Dreams & Nightmares Case",
        "Recoil Case",
        "Kilowatt Case",
        "Revolution Case",
        "Gallery Case",
        "Fever Case",
    ]
    logger.debug(f"Will process {len(all_cases)} cases: {', '.join(all_cases)}")

    # Define cases to include in combined calculations (excluding Gallery and Fever)
    cases_for_combined_stats = [
        "Fracture Case",
        "Dreams & Nightmares Case",
        "Recoil Case",
        "Kilowatt Case",
        "Revolution Case",
    ]
    logger.debug(
        f"Will include {len(cases_for_combined_stats)} cases in combined stats: {', '.join(cases_for_combined_stats)}"
    )

    # Steam market URL and request parameters.
    base_url = "https://steamcommunity.com/market/pricehistory/"
    cookies = {
        "timezoneOffset": "19800,0",
        "browserid": "264122989725161991",
        "sessionid": "7f50cbec9b4167bcefb8ccf4",
        "webTradeEligibility": "%7B%22allowed%22%3A1%2C%22allowed_at_time%22%3A0%2C%22steamguard_required_days%22%3A15%2C%22new_device_cooldown_days%22%3A0%2C%22time_checked%22%3A1746128311%7D",
        "steamLoginSecure": "76561199557379295%7C%7CeyAidHlwIjogIkpXVCIsICJhbGciOiAiRWREU0EiIH0.eyAiaXNzIjogInI6MDAxNF8yNUIxRjFFMF8xMThFMCIsICJzdWIiOiAiNzY1NjExOTk1NTczNzkyOTUiLCAiYXVkIjogWyAid2ViOmNvbW11bml0eSIgXSwgImV4cCI6IDE3NDYyODM1MjMsICJuYmYiOiAxNzM3NTU2NjI5LCAiaWF0IjogMTc0NjE5NjYyOSwgImp0aSI6ICIwMDEyXzI2M0FGNTQ2XzI5QUFDIiwgIm9hdCI6IDE3MzcyMzM3MjksICJydF9leHAiOiAxNzU1MDc3MzUzLCAicGVyIjogMCwgImlwX3N1YmplY3QiOiAiMTA0LjI4LjI1Mi4xNzUiLCAiaXBfY29uZmlybWVyIjogIjEwNC4yOC4yNTIuMTc1IiB9.TB5NJn_EvjT8RorQo_POCnGmGcZLGFoo1ufBaUKV-AVWIeCi5XB77YHQaI7XjSihUfwgKnB0kFAIaW-dSXFqCg",
        "steamCountry": "IN%7Cb83c60484852a257cbbb98cd272d5e10",
    }
    headers = {
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
    }

    # Fetch/update data for all cases.
    case_data = {}
    for case in all_cases:
        data = fetch_update(case, price_histories_dir, base_url, cookies, headers)
        if data:
            case_data[case] = data

    # Analyze each case separately.
    # We store the computed stats (for each period) to combine later.
    individual_recent_stats = []
    individual_overall_stats = []

    for case in all_cases:
        if case in case_data:
            print("\n")
            logger.info(f"--- Analyzing data for {case} ---")
            stats = analyze_prices(case_data[case], verbose=True, label=case)
            if stats:
                # Only include in combined stats if not Gallery or Fever case
                if case in cases_for_combined_stats:
                    individual_recent_stats.append(stats["recent"])
                    individual_overall_stats.append(stats["overall"])
        else:
            logger.warning(f"No data available for {case}.")

    # Combine statistics from active cases.
    # For overall period:
    combined_overall = combine_stats(individual_overall_stats)
    print("\n")
    logger.info(
        "=== Combined Overall Statistics for Active Cases (excluding Gallery and Fever Cases) ==="
    )
    logger.info(
        f"Combined Weighted Average Price: ₹{combined_overall['weighted_avg_price']:.2f}"
    )
    logger.info(f"Combined Weekly Sales: {combined_overall['weekly_sales']:.2f}")

    # For recent period:
    combined_recent = combine_stats(individual_recent_stats)
    print("\n")
    logger.info(
        "=== Combined Recent Statistics for Active Cases (excluding Gallery and Fever Cases) ==="
    )
    logger.info(
        f"Combined Weighted Average Price: ₹{combined_recent['weighted_avg_price']:.2f}"
    )
    logger.info(f"Combined Weekly Sales: {combined_recent['weekly_sales']:.2f}")


if __name__ == "__main__":
    main()
