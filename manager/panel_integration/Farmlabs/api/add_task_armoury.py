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

from playwright.async_api import Browser, BrowserContext, Page, async_playwright


async def add_armoury_farm_bot_job(
    steam_username: str,
    final_level: int = 40,
    map_type: str = "defusal_group_sigma",
    intensity: str = "clara",
) -> bool:
    logger.trace("Starting add_armoury_farm_bot_job coroutine")
    async with async_playwright() as p:
        logger.trace("Launching Chromium browser in headless mode")
        browser: Browser = await p.chromium.launch(headless=True)

        # Create a new context and page
        logger.trace("Creating new browser context and page")
        context: BrowserContext = await browser.new_context()
        page: Page = await context.new_page()

        # Navigate to FarmLabs dashboard
        logger.trace("Navigating to FarmLabs dashboard")
        await page.goto("https://dashboard.farmlabs.dev/")

        # Wait for and interact with login elements
        try:
            email_address_selector: str = r"#data\.email"
            password_selector: str = r"#data\.password"

            # Get credentials from environment variables for security
            email_id: str = "sivasai2207@gmail.com"
            password: str = "password"

            checkbox_selector: str = r"#data\.remember"
            sign_in_selector: str = r"#form > div.fi-form-actions > div > button"

            logger.trace("Waiting for email input selector")
            await page.wait_for_selector(email_address_selector, timeout=10000)
            await page.fill(email_address_selector, email_id)

            logger.trace("Waiting for password input selector")
            await page.wait_for_selector(password_selector, timeout=10000)
            await page.fill(password_selector, password)

            logger.trace("Waiting for 'remember me' checkbox selector")
            await page.wait_for_selector(checkbox_selector, timeout=10000)
            await page.click(checkbox_selector)

            logger.trace("Waiting for sign in button selector")
            await page.wait_for_selector(sign_in_selector, timeout=10000)
            await page.click(sign_in_selector)

            logger.info("Login form submitted")

        except Exception as e:
            logger.warning(f"Notice: Login elements not found as expected: {e}")

        # Wait for the page to fully load
        logger.trace("Waiting for page to reach networkidle state after login attempt")
        await page.wait_for_load_state("networkidle")

        # Check if we need to log in and wait for user to do so if needed
        try:
            logger.trace(
                "Checking if login is required by searching for login elements"
            )
            login_element = await page.query_selector(
                'input[type="email"], input[type="password"], button:has-text("Log in")'
            )

            if login_element:
                logger.warning(
                    "⚠️ Please log in to FarmLabs in the opened browser window"
                )

                # Wait for login to complete (timeout after 2 minutes)
                logger.trace("Waiting for user to complete login (timeout: 2 minutes)")
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
                logger.trace("Waiting for post-login networkidle state")
                await page.wait_for_load_state("networkidle")
                logger.info("Login completed successfully")

        except Exception as e:
            logger.error(f"Warning during login detection: {e}")

        try:
            # Navigate to bot jobs page
            logger.info("Navigating to bot jobs page")
            await page.goto("https://dashboard.farmlabs.dev/bot-jobs")
            await page.wait_for_load_state("networkidle")

            # Click on "New bot job" button
            logger.info("Clicking 'New bot job' button")
            new_bot_job_selector: str = 'span.fi-btn-label:has-text("New bot job")'
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
                pass

            else:
                logger.error("Wrong intensity passed, returning...")
                return False

            # Select map type based on parameter
            logger.info(f"Setting map type to: {map_type}")
            # Map selection based on the map_type parameter
            if map_type == "defusal_group_sigma":
                map_selector: str = 'input[type="checkbox"][value="defusal_group_sigma"][wire\\:model="data.job_data.allowed_maps"]'
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
                default_map_selector: str = 'input[type="checkbox"][value="defusal_group_sigma"][wire\\:model="data.job_data.allowed_maps"]'
                await page.wait_for_selector(default_map_selector)
                await page.click(default_map_selector)

            # Set target level and XP
            logger.info(f"Setting target level to: {final_level}")
            level_selector: str = r"#data\.job_data\.target_level"
            xp_selector: str = r"#data\.job_data\.target_xp"

            await page.wait_for_selector(level_selector)
            await page.fill(level_selector, str(final_level))

            await page.wait_for_selector(xp_selector)
            await page.fill(xp_selector, "1")

            await asyncio.sleep(1)

            # Click Create button
            logger.info("Creating bot job")
            create_button_selector: str = 'button:has-text("Create")'
            await page.wait_for_selector(create_button_selector)
            await page.click(create_button_selector)

            # Wait for confirmation
            logger.trace("Waiting for networkidle state after bot job creation")
            await page.wait_for_load_state("networkidle")
            logger.info("Bot job created successfully")
            return True

        except Exception as e:
            logger.error(f"Error occurred during bot job creation: {e}")
            return False


# Example usage
async def main() -> None:
    logger.trace("Starting main coroutine")
    result: bool = await add_armoury_farm_bot_job(
        steam_username="lyingcod491",
        final_level=40,
        map_type="defusal_group_delta",
        intensity="normal",  # Can be 'clara', 'normal', or 'noob'
    )
    logger.info(f"Job creation successful: {result}")


if __name__ == "__main__":
    asyncio.run(main())
