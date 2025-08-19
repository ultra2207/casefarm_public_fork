import asyncio
import logging

import aiohttp

logging.getLogger("asyncio").setLevel(logging.CRITICAL)
import re
import sys
from typing import Any, TypedDict

import pycountry
import yaml
from aiohttp import ClientTimeout
from bs4 import BeautifulSoup
from fake_useragent import UserAgent


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


def get_currency_name(code: str) -> str:
    try:
        currency = pycountry.currencies.get(alpha_3=code)
        return currency.name if currency else "Unknown Currency"
    except (AttributeError, KeyError):
        return "Unknown Currency"


ua = UserAgent()


async def fetch_prices() -> list[str]:
    url: str = "https://steamassets.com/"
    headers: dict[str, str] = {"User-Agent": ua.chrome}

    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            timeout = ClientTimeout(total=30)
            async with session.get(url, timeout=timeout) as response:
                if response.status == 200:
                    html: str = await response.text()
                    soup: BeautifulSoup = BeautifulSoup(html, "html.parser")
                    target_divs = soup.select(
                        "body > main > div:nth-child(18) > div.list-prices > div"
                    )
                    prices: list[str] = []
                    for div in target_divs:
                        spans = div.find_all("span")
                        for span in spans:
                            prices.append(span.text.strip())
                    return prices
                else:
                    logger.error(f"Failed to fetch data: Status code {response.status}")
                    return []
    except aiohttp.ClientError as e:
        logger.error(f"Client error occurred: {e}")
        return []
    except asyncio.TimeoutError:
        logger.error("Request timed out")
        return []
    except Exception as e:
        logger.exception(f"An unexpected error occurred: {e}")
        return []


async def get_currency_rates() -> dict[str, float]:
    url: str = "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/inr.json"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data: dict[str, Any] = await response.json()
            return data["inr"]


class PriceData(TypedDict):
    currency: str
    original_price: float
    inr_price: float


async def checker() -> None:
    raw_prices: list[str] = await fetch_prices()
    prices_data: dict[str, float] = {}
    for price_str in raw_prices:
        match = re.search(r"([A-Z]{3}): ([\d\.]+)", price_str)
        if match:
            currency: str = match.group(1)
            price: float = float(match.group(2))
            prices_data[currency] = price

    rates: dict[str, float] = await get_currency_rates()
    inr_prices: list[PriceData] = []
    for currency, price in prices_data.items():
        if currency == "INR":
            inr_price: float = price
        else:
            currency_lower: str = currency.lower()
            if currency_lower in rates:
                inr_price = price / rates[currency_lower]
            else:
                logger.warning(f"Currency {currency} not found in rates data")
                continue

        inr_prices.append(
            {"currency": currency, "original_price": price, "inr_price": inr_price}
        )

    inr_prices.sort(key=lambda x: x["inr_price"])

    logger.info("Cheapest 5 options:")
    for i in range(min(5, len(inr_prices))):
        item: PriceData = inr_prices[i]
        currency_name: str = get_currency_name(item["currency"])
        logger.info(
            f"{i + 1}. {item['currency']} ({currency_name}): {item['original_price']} = ₹{item['inr_price']:.2f}"
        )
    indian_price: PriceData | None = next(
        (item for item in inr_prices if item["currency"] == "INR"), None
    )

    if indian_price:
        print("\n")
        logger.info(f"Actual Indian price: ₹{indian_price['inr_price']:.2f}")

        if inr_prices[0]["currency"] != "INR":
            rupee_difference: float = (
                indian_price["inr_price"] - inr_prices[0]["inr_price"]
            )
            percent_difference: float = (
                rupee_difference / inr_prices[0]["inr_price"]
            ) * 100
            cheapest_currency_name: str = get_currency_name(inr_prices[0]["currency"])
            logger.info(
                f"Indian price is ₹{rupee_difference:.2f} (or {percent_difference:.2f}%) more expensive than the cheapest option ({inr_prices[0]['currency']} - {cheapest_currency_name})"
            )


if __name__ == "__main__":
    asyncio.run(checker())
