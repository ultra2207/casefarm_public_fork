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


async def run_new_bots_update_job(steam_usernames: list[str]) -> bool:
    logger.trace("Starting run_new_bots_update_job coroutine")
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

            logger.trace("Opening bot selection dropdown")
            await page.click("div.choices__inner")

            for steam_username in steam_usernames:
                logger.trace(f"Processing username: {steam_username}")
                # Type the username in the opened search field
                await asyncio.sleep(0.5)
                await page.keyboard.type(steam_username)

                logger.trace("Waiting 5 seconds for search results")
                await asyncio.sleep(5)

                # Press Enter to select the bot
                logger.trace("Selecting bot with Enter key")
                await page.keyboard.press("Enter")
                await asyncio.sleep(1)

            # Tab and down arrow navigation
            logger.trace("Performing keyboard navigation")
            await page.keyboard.press("Tab")
            await asyncio.sleep(0.2)
            await page.keyboard.press("ArrowDown")
            await asyncio.sleep(0.2)
            await page.keyboard.press("ArrowDown")
            await asyncio.sleep(0.2)

            # Click Create button
            logger.info("Creating bot job")
            create_button_selector: str = 'button:has-text("Create")'
            await page.wait_for_selector(create_button_selector)
            await page.click(create_button_selector)

            logger.trace("Waiting for final networkidle state")
            await page.wait_for_load_state("networkidle")
            logger.info("Bot job creation completed successfully")
            return True

        except Exception as e:
            logger.error(f"Error occurred during bot creation: {e}")
            return False


async def main() -> None:
    logger.trace("Starting main coroutine")
    steam_usernames: list[str] = ["lyingcod491"]
    result: bool = await run_new_bots_update_job(steam_usernames)
    logger.info(f"Job creation result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
