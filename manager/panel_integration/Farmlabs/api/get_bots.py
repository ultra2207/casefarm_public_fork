import json
import logging

import aiohttp

logging.getLogger("asyncio").setLevel(logging.CRITICAL)
import asyncio
import sys

import aiofiles
import yaml
from bs4 import BeautifulSoup
from cookies_updater import refresh_farmlabs_cookies


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

from database import update_account_details_farmlabs


async def scrape_farmlabs_bots() -> list[dict[str, str]] | None:
    """
    Scrapes bot data from the FarmLabs dashboard and updates the database with the scraped data.

    Returns:
        list[dict[str, str]] | None: A list of bot data dictionaries if successful, otherwise None.
    """
    # URL to scrape
    url: str = "https://dashboard.farmlabs.dev/bots"
    logger.info(f"Starting scraping bots from {url}")

    # Refresh cookies first
    await refresh_farmlabs_cookies()
    logger.debug("Refreshed FarmLabs cookies")

    # Load cookies from file
    try:
        async with aiofiles.open(
            r"C:\Users\Sivasai\Documents\GitHub\CaseFarm\manager\panel_integration\farmlabs\api\cache\cookies.txt",
            "r",
        ) as f:
            cookie_content: str = await f.read()
            cookies: dict[str, str] = json.loads(cookie_content)
        logger.debug("Successfully loaded cookies from file")
    except Exception as e:
        logger.critical(f"Failed to load cookies from file: {e}")
        raise Exception(f"Failed to load cookies from file: {e}")

    # Make the GET request with cookies using aiohttp
    try:
        async with aiohttp.ClientSession(cookies=cookies) as session:
            async with session.get(url) as response:
                # Check if the request was successful
                if response.status == 200:
                    html_content: str = await response.text()
                    logger.debug("Successfully retrieved HTML content from the URL")

                    # Parse the HTML content
                    soup: BeautifulSoup = BeautifulSoup(html_content, "html.parser")

                    # Extract bot information
                    bot_data: list[dict[str, str]] = []

                    # Find all table rows
                    rows = soup.find_all("tr", class_="fi-ta-row")
                    logger.trace(f"Found {len(rows)} rows in the HTML content")

                    for row in rows:
                        # Extract bot_id from href attribute
                        links = row.find_all("a", href=True)
                        bot_id: str | None = None
                        for link in links:
                            if "/bots/" in link["href"]:
                                # Extract bot_id from URL
                                bot_id = link["href"].split("/bots/")[1].split("/")[0]
                                break

                        if bot_id:
                            # Extract steam_username
                            username_cell = row.find(
                                "td", class_="fi-table-cell-steam-username"
                            )
                            steam_username: str | None = (
                                username_cell.find(
                                    "span", class_="fi-ta-text-item-label"
                                ).text.strip()
                                if username_cell
                                else None
                            )

                            # Extract level
                            level_cell = row.find("td", class_="fi-table-cell-level")
                            level: str | None = (
                                level_cell.find(
                                    "span", class_="fi-ta-text-item-label"
                                ).text.strip()
                                if level_cell
                                else None
                            )

                            # Extract XP
                            xp_cell = row.find("td", class_="fi-table-cell-xp")
                            xp: str | None = (
                                xp_cell.find(
                                    "span", class_="fi-ta-text-item-label"
                                ).text.strip()
                                if xp_cell
                                else None
                            )

                            # Extract status
                            status_cell = row.find("td", class_="fi-table-cell-status")
                            status: str | None = (
                                status_cell.find("span", class_="truncate").text.strip()
                                if status_cell
                                else None
                            )

                            bot_info: dict[str, str] = {
                                "bot_id": bot_id,
                                "steam_username": steam_username,
                                "level": level,
                                "xp": xp,
                                "status": status,
                            }

                            bot_data.append(bot_info)
                            logger.trace(f"Extracted bot info: {bot_info}")

                            # Update database with the extracted information
                            if steam_username:
                                update_result: bool = update_account_details_farmlabs(
                                    steam_username=steam_username,
                                    bot_id=bot_id,
                                    level=level,
                                    xp=xp,
                                    status=status,
                                )
                                if update_result:
                                    logger.info(
                                        f"Updated database for {steam_username}"
                                    )
                                else:
                                    logger.warning(
                                        f"Failed to update database for {steam_username}"
                                    )

                    logger.info(
                        f"Successfully scraped {len(bot_data)} bots from FarmLabs"
                    )
                    return bot_data
                else:
                    logger.error(
                        f"Failed to retrieve the page. Status code: {response.status}"
                    )
                    return None
    except Exception as e:
        logger.error(f"An error occurred during the request: {e}")
        return None


if __name__ == "__main__":
    asyncio.run(scrape_farmlabs_bots())
