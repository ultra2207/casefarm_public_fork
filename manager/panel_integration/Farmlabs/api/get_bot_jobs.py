import json
import logging

import aiohttp

logging.getLogger("asyncio").setLevel(logging.CRITICAL)
import asyncio
import re
import sys
from typing import Any

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

from database import create_bot_job, update_existing_bot_job


async def scrape_farmlabs_botjobs() -> None:
    """
    Scrapes bot job data from the FarmLabs dashboard and saves it to the database.
    """
    # URL to scrape
    url: str = "https://dashboard.farmlabs.dev/bot-jobs"
    logger.info(f"Starting scraping bot jobs from {url}")

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
    async with aiohttp.ClientSession(cookies=cookies) as session:
        async with session.get(url) as response:
            # Check if the request was successful
            if response.status == 200:
                html_content: str = await response.text()
                logger.debug("Successfully retrieved HTML content from the URL")

                # Parse the HTML content
                soup: BeautifulSoup = BeautifulSoup(html_content, "html.parser")

                # Find all bot jobs
                bot_jobs: list[dict[str, Any]] = []

                # Find all cells that contain bot job IDs
                job_cells = soup.find_all(
                    "td", {"class": re.compile(r"fi-table-cell-bot\.steam-username")}
                )

                for job_cell in job_cells:
                    job_data: dict[str, Any] = {}

                    # Get the parent row
                    row = job_cell.parent

                    # Extract bot job ID from the href in the first cell
                    job_link = job_cell.find("a", href=True)
                    if job_link:
                        job_id: str = job_link["href"].split("/")[-2]
                        job_data["job_id"] = job_id

                    # Extract account name
                    account_element = job_cell.select_one(".fi-ta-text-item-label")
                    if account_element:
                        job_data["account"] = account_element.text.strip()

                    # Extract job type from the next cell
                    type_cell = row.find(
                        "td", {"class": re.compile(r"fi-table-cell-type")}
                    )
                    if type_cell:
                        type_element = type_cell.select_one(".fi-ta-text-item-label")
                        if type_element:
                            job_data["job_type"] = type_element.text.strip()

                    # Extract assigned machine
                    machine_cell = row.find(
                        "td",
                        {"class": re.compile(r"fi-table-cell-assigned-machine\.name")},
                    )
                    if machine_cell:
                        machine_link = machine_cell.find("a", href=True)
                        if machine_link:
                            machine_id: str = machine_link["href"].split("/")[-2]
                            job_data["machine_id"] = machine_id

                            machine_element = machine_cell.select_one(
                                ".fi-ta-text-item-label"
                            )
                            if machine_element:
                                job_data["machine_name"] = machine_element.text.strip()

                    # Extract created at time
                    created_cell = row.find(
                        "td", {"class": re.compile(r"fi-table-cell-created-at")}
                    )
                    if created_cell:
                        created_element = created_cell.select_one(
                            ".fi-ta-text-item-label"
                        )
                        if created_element:
                            job_data["created_at"] = created_element.text.strip()

                    # Extract start time
                    start_cell = row.find(
                        "td", {"class": re.compile(r"fi-table-cell-start-time")}
                    )
                    if start_cell:
                        start_element = start_cell.select_one(".fi-ta-text-item-label")
                        if start_element:
                            job_data["started_at"] = start_element.text.strip()
                        else:
                            job_data["started_at"] = None

                    # Extract completion time
                    completion_cell = row.find(
                        "td", {"class": re.compile(r"fi-table-cell-completion-time")}
                    )
                    if completion_cell:
                        completion_element = completion_cell.select_one(
                            ".fi-ta-text-item-label"
                        )
                        if completion_element:
                            job_data["completed_at"] = completion_element.text.strip()
                        else:
                            job_data["completed_at"] = None

                    # Extract status
                    status_cell = row.find(
                        "td", {"class": re.compile(r"fi-table-cell-status")}
                    )
                    if status_cell:
                        status_element = status_cell.select_one(".fi-badge")
                        if status_element:
                            status_text: str = status_element.get_text(strip=True)
                            job_data["status"] = status_text

                    bot_jobs.append(job_data)
                logger.trace(f"Extracted {len(bot_jobs)} bot jobs from HTML content")

                # Save to database
                await save_to_database(bot_jobs)

                # Print the results
                logger.info(f"Found {len(bot_jobs)} bot jobs:")
                for job in bot_jobs:
                    print("\n")
                    logger.info(f"Job ID: {job.get('job_id')}")
                    logger.info(f"Account: {job.get('account')}")
                    logger.info(f"Job Type: {job.get('job_type')}")
                    logger.info(
                        f"Machine: {job.get('machine_name', 'Not assigned')} (ID: {job.get('machine_id', 'N/A')})"
                    )
                    logger.info(f"Created At: {job.get('created_at')}")
                    logger.info(f"Started At: {job.get('started_at', 'Not started')}")
                    logger.info(
                        f"Completed At: {job.get('completed_at', 'Not completed')}"
                    )
                    logger.info(f"Status: {job.get('status', 'Unknown')}")
            else:
                logger.error(
                    f"Failed to retrieve the page. Status code: {response.status}"
                )


async def save_to_database(bot_jobs: list[dict[str, Any]]) -> None:
    """
    Save the scraped bot jobs to the database.
    If a bot job already exists (based on bot_job_id), update it instead of creating a new one.

    Args:
        bot_jobs (list[dict[str, Any]]): list of bot job data dictionaries
    """
    for job in bot_jobs:
        try:
            job_id: str = job.get("job_id")

            # Check if the job already exists and update it if it does
            job_updated: bool = update_existing_bot_job(
                bot_job_id=job_id,
                bot_username=job.get("account"),
                job_type=job.get("job_type"),
                assigned_machine=job.get("machine_id"),
                created_at=job.get("created_at"),
                start_time=job.get("started_at"),
                completion_time=job.get("completed_at"),
                status=job.get("status"),
            )

            if job_updated:
                logger.info(f"Updated existing job {job_id} in database")
            else:
                # Job doesn't exist, create a new one
                create_bot_job(
                    bot_job_id=job_id,
                    bot_username=job.get("account"),
                    job_type=job.get("job_type"),
                    assigned_machine=job.get("machine_id"),
                    created_at=job.get("created_at"),
                    start_time=job.get("started_at"),
                    completion_time=job.get("completed_at"),
                    status=job.get("status"),
                )
                logger.info(f"Created new job {job_id} in database")
        except Exception as e:
            logger.error(f"Error saving job {job.get('job_id')} to database: {e}")


# To run this function
if __name__ == "__main__":
    asyncio.run(scrape_farmlabs_botjobs())
