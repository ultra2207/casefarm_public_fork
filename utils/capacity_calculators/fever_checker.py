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
from datetime import datetime, timedelta

# Rewrite this with aiosteampy when u have the time


def parse_date(date_str: str) -> datetime:
    """
    Parses a date string in the format "Oct 10 2024 01: +0"
    and returns a datetime object (ignoring the timezone).
    """
    # Expected parts: ["Oct", "10", "2024", "01:", "+0"]
    parts = date_str.split()
    if len(parts) < 5:
        logger.error(f"Unexpected date format: {date_str}")
        raise ValueError(f"Unexpected date format: {date_str}")
    month, day, year, hour_with_colon, _ = parts
    hour = hour_with_colon.rstrip(":")
    clean_date_str = f"{month} {day} {year} {hour}"
    return datetime.strptime(clean_date_str, "%b %d %Y %H")


def analyze_prices(data: dict[str, list[list]]) -> None:
    prices = data.get("prices", [])
    if not prices:
        logger.warning("No price data available.")
        return

    # Parse entries into (datetime, price, sales) tuples.
    parsed_entries: list[tuple[datetime, float, int]] = []
    for entry in prices:
        date_str, price, sales = entry
        try:
            dt = parse_date(date_str)
        except Exception as e:
            logger.error(f"Error parsing date '{date_str}': {e}")
            continue
        parsed_entries.append((dt, price, int(sales)))

    if not parsed_entries:
        logger.warning("No valid price entries after parsing dates.")
        return

    # Sort entries in ascending order (oldest to latest).
    parsed_entries.sort(key=lambda x: x[0])
    # The latest entry determines our "now".
    now = parsed_entries[-1][0]

    # Define thresholds relative to "now"
    recent_threshold = now - timedelta(days=30)
    overall_threshold = now - timedelta(days=120)

    # Walk upward from the bottom to collect recent entries (1 month)
    recent_entries: list[tuple[datetime, float, int]] = []
    for entry in reversed(parsed_entries):
        if entry[0] >= recent_threshold:
            recent_entries.append(entry)
        else:
            break
    # Since we iterated in reverse, restore chronological order:
    recent_entries.reverse()

    # Similarly, walk upward for overall entries (4 months)
    overall_entries: list[tuple[datetime, float, int]] = []
    for entry in reversed(parsed_entries):
        if entry[0] >= overall_threshold:
            overall_entries.append(entry)
        else:
            break
    overall_entries.reverse()

    # Fallback logic if no entries were collected in a period:
    if not recent_entries:
        logger.info(
            "No data found for the last 1 month. Using all available data for recent statistics."
        )
        recent_entries = parsed_entries
    if not overall_entries:
        logger.info(
            "No data found for the last 4 months. Using all available data for overall statistics."
        )
        overall_entries = parsed_entries

    def compute_stats(
        entries: list[tuple[datetime, float, int]],
    ) -> tuple[float, float, int, float]:
        total_sales = sum(sales for _, _, sales in entries)
        total_price = sum(price * sales for _, price, sales in entries)
        avg_price = total_price / total_sales

        # Calculate period covered by these entries.
        period_days = (entries[-1][0] - entries[0][0]).days
        weeks = period_days / 7
        weekly_sales = total_sales / weeks

        return avg_price, weekly_sales, period_days, weeks

    recent_stats = compute_stats(recent_entries)
    overall_stats = compute_stats(overall_entries)

    logger.info("Recent Statistics:")
    logger.info(f"  Recent average price: ₹{recent_stats[0]:.2f}")
    logger.info(
        f"  Recent weekly sales: {recent_stats[1]:.2f} (over {recent_stats[2]} days, ~{recent_stats[3]:.1f} weeks)"
    )
    print("\n")
    logger.info("Overall Statistics:")
    logger.info(f"  Average price: ₹{overall_stats[0]:.2f}")
    logger.info(
        f"  Weekly sales: {overall_stats[1]:.2f} (over {overall_stats[2]} days, ~{overall_stats[3]:.1f} weeks)"
    )

    # Adding a trace log statement
    logger.trace("Price analysis completed successfully.")


# Read JSON and analyze prices from the correct file path.
with open(
    r"C:\Users\Sivasai\Documents\GitHub\CaseFarm\utils\cache\price_histories\Fever_Case.json",
    "r",
    encoding="utf-8",
) as f:
    data = json.load(f)

analyze_prices(data)
