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
import sqlite3

from playwright.async_api import async_playwright


def get_xp_level(steam_username: str) -> int:
    # Path to the SQLite database
    db_path = r"C:\Users\Sivasai\Documents\GitHub\CaseFarm\database\db\database.db"

    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Query to fetch xp_level based on steam_username
        query = "SELECT xp_level FROM users WHERE steam_username = ?"
        cursor.execute(query, (steam_username,))

        # Fetch the result
        result = cursor.fetchone()

        # If result is found, return xp_level; otherwise, return default value of 1
        return result[0] if result else 1

    except sqlite3.Error as e:
        logger.error(f"database error: {e}")
        return 1  # Return default value in case of an error

    finally:
        # Ensure the connection is closed
        if conn:
            conn.close()


async def add_armoury_farm_bot_job(
    steam_username: str, map_type: str = "defusal_group_sigma", intensity: str = "clara"
) -> bool:
    current_xp_level = get_xp_level(steam_username)
    logger.debug(f"Retrieved XP level for {steam_username}: {current_xp_level}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        # Create a new context and page
        context = await browser.new_context()
        page = await context.new_page()

        # Navigate to FarmLabs dashboard
        await page.goto("https://dashboard.farmlabs.dev/")
        logger.trace("Navigated to FarmLabs dashboard")

        # Wait for and interact with login elements
        try:
            email_address_selector = r"#data\.email"
            password_selector = r"#data\.password"

            # Get credentials from environment variables for security
            email_id = "sivasai2207@gmail.com"
            password = "password"

            checkbox_selector = r"#data\.remember"
            sign_in_selector = r"#form > div.fi-form-actions > div > button"

            await page.wait_for_selector(email_address_selector, timeout=10000)
            await page.fill(email_address_selector, email_id)

            await page.wait_for_selector(password_selector, timeout=10000)
            await page.fill(password_selector, password)

            await page.wait_for_selector(checkbox_selector, timeout=10000)
            await page.click(checkbox_selector)

            await page.wait_for_selector(sign_in_selector, timeout=10000)
            await page.click(sign_in_selector)

            logger.info("Login form submitted")

        except Exception as e:
            logger.warning(f"Notice: Login elements not found as expected: {e}")

        # Wait for the page to fully load
        await page.wait_for_load_state("networkidle")

        # Check if we need to log in and wait for user to do so if needed
        try:
            login_element = await page.query_selector(
                'input[type="email"], input[type="password"], button:has-text("Log in")'
            )

            if login_element:
                logger.warning(
                    "⚠️ Please log in to FarmLabs in the opened browser window"
                )

                # Wait for login to complete (timeout after 2 minutes)
                await page.wait_for_function(
                    """
                    () => {
                        // Check for elements that would indicate successful login
                        return !document.querySelector('input[type="email"]') && 
                            !document.querySelector('input[type="password"]') &&
                            !document.querySelector('button:has-text("Log in")');
                    }
                    """,
                    timeout=120000,
                )

                # Wait a bit more for post-login redirects
                await page.wait_for_load_state("networkidle")
                logger.success("Login completed successfully")

        except Exception as e:
            logger.warning(f"Warning during login detection: {e}")

        try:
            # Navigate to bot jobs page
            logger.info("Navigating to bot jobs page")
            await page.goto("https://dashboard.farmlabs.dev/bot-jobs")
            await page.wait_for_load_state("networkidle")

            # Click on "New bot job" button
            logger.info("Clicking 'New bot job' button")
            new_bot_job_selector = 'span.fi-btn-label:has-text("New bot job")'
            await page.wait_for_selector(new_bot_job_selector, timeout=30000)
            await page.click(new_bot_job_selector)
            await page.wait_for_load_state("networkidle")

            logger.info(f"Selecting bot for username: {steam_username}")
            await page.click("div.choices__inner")

            # Type the username in the opened search field
            await asyncio.sleep(0.5)  # Brief pause to ensure field is ready
            await page.keyboard.type(steam_username)

            # Wait 5 seconds as specified
            await asyncio.sleep(5)

            # Press Enter to select the bot
            await page.keyboard.press("Enter")

            await asyncio.sleep(1)  # Short wait for selection to process

            # Tab and down arrow navigation as mentioned in the comment
            await page.keyboard.press("Tab")
            await asyncio.sleep(0.2)
            await page.keyboard.press("ArrowDown")
            await asyncio.sleep(0.2)
            await page.keyboard.press("ArrowDown")
            await asyncio.sleep(0.2)

            # Set intensity based on parameter
            logger.info(f"Setting intensity to: {intensity}")

            if intensity.lower() == "noob":
                await page.wait_for_selector(
                    r"#form > div.grid.grid-cols-\[--cols-default\].lg\:grid-cols-\[--cols-lg\].fi-fo-component-ctn.gap-6 > div:nth-child(6) > div > div > div > div > div > div > div > div > div:nth-child(1) > div > div > div.grid.auto-cols-fr.gap-y-2 > div > div:nth-child(1) > label > span"
                )
                await page.click(
                    r"#form > div.grid.grid-cols-\[--cols-default\].lg\:grid-cols-\[--cols-lg\].fi-fo-component-ctn.gap-6 > div:nth-child(6) > div > div > div > div > div > div > div > div > div:nth-child(1) > div > div > div.grid.auto-cols-fr.gap-y-2 > div > div:nth-child(1) > label > span"
                )

            elif intensity.lower() == "clara":
                await page.wait_for_selector(
                    r"#form > div.grid.grid-cols-\[--cols-default\].lg\:grid-cols-\[--cols-lg\].fi-fo-component-ctn.gap-6 > div:nth-child(6) > div > div > div > div > div > div > div > div > div:nth-child(1) > div > div > div.grid.auto-cols-fr.gap-y-2 > div > div:nth-child(3) > label > span"
                )
                await page.click(
                    r"#form > div.grid.grid-cols-\[--cols-default\].lg\:grid-cols-\[--cols-lg\].fi-fo-component-ctn.gap-6 > div:nth-child(6) > div > div > div > div > div > div > div > div > div:nth-child(1) > div > div > div.grid.auto-cols-fr.gap-y-2 > div > div:nth-child(3) > label > span"
                )

            elif intensity.lower() == "normal":
                # it defaults to normal
                logger.trace("Using default 'normal' intensity")
                pass

            else:
                logger.error("Wrong intennsity passed, returning...")
                return False

            # Select map type based on parameter
            logger.info(f"Setting map type to: {map_type}")
            # Map selection based on the map_type parameter
            if map_type == "defusal_group_sigma":
                map_selector = 'input[type="checkbox"][value="defusal_group_sigma"][wire\\:model="data.job_data.allowed_maps"]'
                await page.wait_for_selector(map_selector)
                await page.click(map_selector)
            elif map_type == "defusal_group_delta":
                map_selector = 'input[type="checkbox"][value="defusal_group_delta"][wire\\:model="data.job_data.allowed_maps"]'
                await page.wait_for_selector(map_selector)
                await page.click(map_selector)
            elif map_type == "dust_2":
                map_selector = 'input[type="checkbox"][value="dust_2"][wire\\:model="data.job_data.allowed_maps"]'
                await page.wait_for_selector(map_selector)
                await page.click(map_selector)
            elif map_type == "hostage_group":
                map_selector = 'input[type="checkbox"][value="hostage_group"][wire\\:model="data.job_data.allowed_maps"]'
                await page.wait_for_selector(map_selector)
                await page.click(map_selector)
            else:
                logger.warning(f"Map type '{map_type}' not recognized, using default")
                default_map_selector = 'input[type="checkbox"][value="defusal_group_sigma"][wire\\:model="data.job_data.allowed_maps"]'
                await page.wait_for_selector(default_map_selector)
                await page.click(default_map_selector)

            final_level = current_xp_level + 1
            # Set target level and XP
            logger.info(f"Setting target level to: {final_level}")
            level_selector = r"#data\.job_data\.target_level"
            xp_selector = r"#data\.job_data\.target_xp"

            await page.wait_for_selector(level_selector)
            await page.fill(level_selector, str(final_level))

            await page.wait_for_selector(xp_selector)
            await page.fill(xp_selector, "1")

            await asyncio.sleep(1)

            # Click Create button
            logger.info("Creating bot job")
            create_button_selector = 'button:has-text("Create")'
            await page.wait_for_selector(create_button_selector)
            await page.click(create_button_selector)

            # Wait for confirmation
            await page.wait_for_load_state("networkidle")
            logger.success(f"Successfully created bot job for {steam_username}")
            return True

        except Exception as e:
            logger.error(f"Error occurred during bot job creation: {e}")
            return False


# Example usage
async def main() -> None:
    result = await add_armoury_farm_bot_job(
        steam_username="lyingcod491",
        map_type="defusal_group_sigma",
        intensity="clara",  # Can be 'clara', 'normal', or 'noob'
    )
    logger.info(f"Job creation successful: {result}")


if __name__ == "__main__":
    asyncio.run(main())
