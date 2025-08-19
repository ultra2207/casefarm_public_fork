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

from playwright.async_api import async_playwright

from database import cancel_bot_job_db, delete_bot_job


async def cancel_and_delete_bot_job(job_id: str) -> bool:
    """
    Navigates to the FarmLabs dashboard, logs in, cancels a specific bot job,
    and then deletes it.

    Args:
        job_id (str): The ID of the bot job to cancel and delete.

    Returns:
        bool: True if the operation was successful, False otherwise.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        # Create a new context and page
        context = await browser.new_context()
        page = await context.new_page()

        # Navigate to FarmLabs dashboard
        await page.goto("https://dashboard.farmlabs.dev/")
        logger.info("Navigated to FarmLabs dashboard")

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
            logger.debug("Filled email address")

            await page.wait_for_selector(password_selector, timeout=10000)
            await page.fill(password_selector, password)
            logger.debug("Filled password")

            await page.wait_for_selector(checkbox_selector, timeout=10000)
            await page.click(checkbox_selector)
            logger.debug("Clicked remember me checkbox")

            await page.wait_for_selector(sign_in_selector, timeout=10000)
            await page.click(sign_in_selector)
            logger.info("Clicked sign-in button")

            logger.info("Login form submitted")

        except Exception as e:
            logger.warning(f"Notice: Login elements not found as expected: {e}")

        # Wait for the page to fully load
        await page.wait_for_load_state("networkidle")
        logger.trace("Waited for network idle state after initial load")

        # Check if we need to log in and wait for user to do so if needed
        try:
            login_element = await page.query_selector(
                'input[type="email"], input[type="password"], button:has-text("Log in")'
            )

            if login_element:
                logger.info("⚠️ Please log in to FarmLabs in the opened browser window")

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
                logger.info("Login completed successfully")

        except Exception as e:
            logger.warning(f"Warning during login detection: {e}")

        try:
            # Navigate to bot jobs page
            logger.info("Navigating to bot jobs page")
            await page.goto("https://dashboard.farmlabs.dev/bot-jobs")
            await page.wait_for_load_state("networkidle")

            cancel_button_selector = (
                f"button[wire\\:click=\"mountTableAction('cancel', '{job_id}')\"]"
            )

            logger.info(f"Attempting to cancel job with ID: {job_id}")

            # Wait for the button to appear and click it
            await page.wait_for_selector(cancel_button_selector, timeout=10000)
            await page.click(cancel_button_selector)

            confirm_cancel_button_selector = 'button:has-text("cancel it")'
            await page.wait_for_selector(confirm_cancel_button_selector)
            await page.click(confirm_cancel_button_selector)

            logger.success(f"Successfully clicked cancel button for job ID: {job_id}")

            await page.wait_for_load_state("networkidle")
            await cancel_bot_job_db(job_id)
            logger.info(f"Successfully cancelled job in database for job ID: {job_id}")

            delete_button_selector = (
                f"button[wire\\:click=\"mountTableAction('delete', '{job_id}')\"]"
            )
            await page.wait_for_selector(delete_button_selector, timeout=10000)
            await page.click(delete_button_selector)

            confirm_delete_button_selector = 'button:has-text("Confirm")'
            await page.wait_for_selector(confirm_delete_button_selector)
            await page.click(confirm_delete_button_selector)

            await page.wait_for_load_state("networkidle")
            await delete_bot_job(job_id)
            logger.info(f"Successfully deleted job in database for job ID: {job_id}")

            return True

        except Exception as e:
            logger.error(f"Error occurred during bot creation: {e}")
            return False


async def main() -> None:
    """
    Main function to run the cancel_and_delete_bot_job function with a specific job ID.
    """
    result: bool = await cancel_and_delete_bot_job(
        job_id="9e4eb4ce-be80-427e-a956-9438b3e402f2"
    )
    logger.info(f"Result of cancel and delete operation: {result}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
