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

import asyncio
import random
from typing import Any, Dict, List, Optional

from aiosteampy import App
from aiosteampy.ext.user_agents import UserAgentsService
from playwright.async_api import async_playwright

from database import get_all_steam_accounts, get_client, steam_api_call_with_retry

# code is very rough, not meant for production


async def get_floats(inspect_urls: List[str]) -> List[str]:
    results: List[str] = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Headed mode
        page = await browser.new_page()
        await page.goto("https://csfloat.com/checker")
        for url in inspect_urls:
            # Fill the input box with the inspect URL
            input_locator = "//html/body/app-root/div/div[2]/app-checker-home/div/div/div[3]/div/mat-form-field/div[1]/div[2]/div[1]/input"
            await page.fill(input_locator, url)
            await page.keyboard.press("Enter")
            # Wait for the float value to appear (adjust timeout as needed)
            float_locator = "body > app-root > div > div.content > app-checker-home > div > div > div.content > div.ng-star-inserted > app-checker-item > div > div.details > div.float > item-float-bar > div > div.text-info.ng-star-inserted > div.mat-mdc-tooltip-trigger.wear"
            await asyncio.sleep(1)  # Wait for the page to load
            await page.wait_for_selector(float_locator, timeout=10000)
            float_value = await page.locator(float_locator).inner_text()
            results.append(float_value)
        await browser.close()
    logger.trace("get_floats function completed")
    return results


async def get_floats_parallel(
    inspect_urls: List[str], num_windows: int = 10
) -> List[Optional[str]]:
    """Process URLs in parallel across multiple browser contexts."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)

        # Create a semaphore to limit the number of concurrent contexts
        semaphore = asyncio.Semaphore(num_windows)
        results: List[Optional[str]] = [None] * len(inspect_urls)

        async def worker(url: str, index: int) -> None:
            async with semaphore:
                context = await browser.new_context()
                try:
                    page = await context.new_page()
                    await page.goto("https://csfloat.com/checker")

                    # Fill the input box with the inspect URL
                    input_locator = "//html/body/app-root/div/div[2]/app-checker-home/div/div/div[3]/div/mat-form-field/div[1]/div[2]/div[1]/input"
                    await page.fill(input_locator, url)
                    await page.keyboard.press("Enter")

                    # Wait for the float value to appear
                    float_locator = "body > app-root > div > div.content > app-checker-home > div > div > div.content > div.ng-star-inserted > app-checker-item > div > div.details > div.float > item-float-bar > div > div.text-info.ng-star-inserted > div.mat-mdc-tooltip-trigger.wear"
                    await page.wait_for_selector(float_locator, timeout=10000)
                    float_value = await page.locator(float_locator).inner_text()

                    results[index] = float_value
                finally:
                    await context.close()

        # Create tasks for each URL
        tasks = [
            asyncio.create_task(worker(url, i)) for i, url in enumerate(inspect_urls)
        ]

        # Wait for all tasks to complete
        await asyncio.gather(*tasks)
        await browser.close()
        logger.trace(
            f"get_floats_parallel completed processing {len(inspect_urls)} URLs"
        )
        return results


# url = steam://rungame/730/76561202255233023/+csgo_econ_action_preview%20M649191534747709563A43673263409D5235087553574725316


async def float_get_account_info(account: Dict[str, Any]) -> None:
    """Get the inventory and currently listed items for a single account without calculating prices."""
    username: str = account["steam_username"]
    pass_value: int = account["pass_value"]

    if not pass_value:
        pass_value = 0

    client = await get_client(account)

    listings = await steam_api_call_with_retry(
        client.get_item_listings,
        app=App.CS2,
        obj="M4A4 | Temukau (Field-Tested)",
        count=100,
        start=0,
    )

    urls: List[str] = []

    for listing in listings[0]:
        item = listing.item
        inspect_url = item.inspect_url
        urls.append(inspect_url)

    float_values = await get_floats_parallel(urls)

    logger.debug(float_values.sort())

    logger.info(f"Account: {username} - fetched successfully.")


async def main() -> None:
    user_agents = UserAgentsService()
    await user_agents.load()
    all_accounts = get_all_steam_accounts()
    prime_accounts = [acc for acc in all_accounts if acc["prime"]]
    acc = random.choice(prime_accounts)

    await float_get_account_info(acc)
    logger.trace("Steam inventory checking process completed")


if __name__ == "__main__":
    asyncio.run(main())
