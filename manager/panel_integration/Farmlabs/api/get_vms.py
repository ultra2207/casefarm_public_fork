import json
import logging

import aiohttp

logging.getLogger("asyncio").setLevel(logging.CRITICAL)
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

from database import update_vms_database


async def scrape_farmlabs_machines() -> bool:
    """
    Scrapes machine data from the FarmLabs dashboard and updates the database.

    Returns:
        bool: True if scraping was successful, False otherwise.
    """
    # URL to scrape
    url: str = "https://dashboard.farmlabs.dev/machines"
    logger.info(f"Starting scraping machines from {url}")

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

                    # Parse the HTML content directly
                    soup: BeautifulSoup = BeautifulSoup(html_content, "html.parser")
                    logger.trace("Parsed HTML content with BeautifulSoup")

                    # List to store machine details
                    machines: list[dict[str, str | None]] = []

                    # Find all table rows (each row represents a machine)
                    rows = soup.find_all("tr", class_=lambda c: c and "fi-ta-row" in c)
                    logger.trace(f"Found {len(rows)} machine rows in the HTML content")

                    for row in rows:
                        # Extract machine details
                        machine: dict[str, str | None] = {}

                        # Extract name
                        name_cell = row.find("td", class_="fi-table-cell-name")
                        if name_cell:
                            name_span = name_cell.find(
                                "span", class_="fi-ta-text-item-label"
                            )
                            if name_span:
                                machine["name"] = name_span.text.strip()

                        # Extract ID
                        id_cell = row.find("td", class_="fi-table-cell-id")
                        if id_cell:
                            id_span = id_cell.find(
                                "span", class_="fi-ta-text-item-label"
                            )
                            if id_span:
                                machine["id"] = id_span.text.strip()

                        # Extract current bot job
                        bot_job_cell = row.find(
                            "td", class_="fi-table-cell-current-bot-job.type"
                        )
                        if bot_job_cell:
                            bot_job_text = bot_job_cell.get_text(strip=True)
                            machine["current_bot_job"] = (
                                bot_job_text if bot_job_text else None
                            )

                        # Extract status
                        status_cell = row.find("td", class_="fi-table-cell-status")
                        if status_cell:
                            status_span = status_cell.find("span", class_="truncate")
                            if status_span:
                                machine["status"] = status_span.text.strip().lower()
                        else:
                            machine["status"] = "offline"  # Default status if not found
                            logger.debug(
                                "No status found for machine, setting default: offline"
                            )

                        # Add machine to list if it has at least id and name
                        if "id" in machine and "name" in machine:
                            machines.append(machine)
                            logger.trace(
                                f"Added machine to list: {machine['name']} (ID: {machine['id']})"
                            )

                    # Update the database with the scraped machines
                    await update_machines_in_database(machines)
                    logger.success(
                        f"Successfully scraped {len(machines)} machines from FarmLabs"
                    )

                    return True
                else:
                    logger.error(f"Request failed with status code: {response.status}")
                    return False

    except Exception as e:
        logger.error(f"An error occurred during the request: {e}")
        return False


async def update_machines_in_database(machines: list[dict[str, str | None]]) -> None:
    """
    Update the database with the scraped machine information.

    Args:
        machines (list): List of machine dictionaries with name, id, current_bot_job, and status
    """
    success_count: int = 0
    error_count: int = 0

    for machine in machines:
        try:
            # Ensure we have the required fields
            if "name" not in machine or "id" not in machine or "status" not in machine:
                logger.warning(f"Skipping machine with incomplete data: {machine}")
                continue

            # Call the update_vms_database function with the correct parameter order
            result: bool = update_vms_database(
                name=machine["name"],
                id=machine["id"],
                status=machine["status"],
                current_bot_job=machine.get("current_bot_job"),
            )

            if result:
                success_count += 1
                logger.debug(
                    f"Successfully updated machine {machine['name']} in database"
                )
            else:
                error_count += 1
                logger.warning(
                    f"Failed to update machine {machine['name']} in database"
                )

        except Exception as e:
            logger.error(
                f"Error updating machine {machine.get('name', 'unknown')}: {e}"
            )
            error_count += 1

    logger.info(
        f"Database update complete. Success: {success_count}, Errors: {error_count}"
    )
