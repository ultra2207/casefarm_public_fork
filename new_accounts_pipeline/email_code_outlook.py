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

link: str = "https://login.live.com/"
email_id_xpath: str = "//html/body/div[1]/div/div/div/div[2]/div[1]/div/div/div/div[1]/div[2]/div/div/div/form/div[2]/div/div/input"
next_button_xpath: str = "//html/body/div[1]/div/div/div/div[2]/div[1]/div/div/div/div[1]/div[2]/div/div/div/form/div[4]/div/div/div/div/button"
email_password_xpath: str = "//html/body/div[1]/div/div/div/div[2]/div[1]/div/div/div/div/div[2]/div[2]/div/form/div[3]/div/div/input"
sign_in_button_xpath: str = "//html/body/div[1]/div/div/div/div[2]/div[1]/div/div/div/div/div[2]/div[2]/div/form/div[5]/div/div/div/div/button"

# Possible buttons
terms_button_xpath: str = "//html/body/div[2]/div/div/div/div[2]/div[1]/div/div/div/div/div[2]/div[2]/div/form/div[4]/div/div/div/div/button"
possible_button_xpath: str = "//html/body/div/div/div[2]/button/span/span/span"
not_stay_signed_in_button_xpath: str = "//html/body/div[1]/div/div/div/div[2]/div[1]/div/div/div/div/div[2]/div[2]/div/form/div[3]/div[2]/div/div[1]/button"

microsoft_account_word_xpath: str = "//html/body/div/div[2]/div/div[2]/div/div[1]/div[2]/div/div/div/div/div/div[1]/div/div/div/a"
mail_link: str = "https://outlook.live.com/mail/0/"
skip_2fa_button_xpath: str = "//html/body/div[1]/div/div/div[2]/div/div[1]/div[2]/div/div[2]/div/div/div/section/div/form/div[5]/a"
outlook_word_xpath: str = "//html/body/div[1]/div/div[1]/div/div/div[1]/div[2]/div/div/div/div/div/div[1]/div[1]/div[2]/div/a/span"

account_verification_word_xpath: str = "//html/bod   /div[1]/div/div/div[2]/div/div[1]/div[2]/div/div[2]/div/div/div/section/div/form/p"
confirmation_account_path: str = "//html/body/div[1]/div/div/div[2]/div/div[1]/div[2]/div/div[2]/div/div/div/section/div/form/div[3]/div/input"
confirmation_email: str = "bootykimani011980@outlook.com"

confirmation_next_xpath: str = "//html/body/div[1]/div/div/div[2]/div/div[1]/div[2]/div/div[2]/div/div/div/section/div/form/div[6]/div/div"
confirmation_code_path: str = "//html/body/div[1]/div/div/div[2]/div/div[1]/div[2]/div/div[2]/section/div/form/div[2]/div[2]/input"
confirmation_next_2_xpath: str = "//html/body/div[1]/div/div/div[2]/div/div[1]/div[2]/div/div[2]/section/div/form/div[5]/div/div/input"

email_content_xpath_template: str = "//html/body/div[1]/div[2]/div[2]/div/div[2]/div[2]/div[1]/div/div/div[3]/div/div/div[1]/div[2]/div/div/div/div/div/div/div/div[{i}]/div/div[2]"
start: str = "Security code:"

end: str = r"Only enter this code"


async def get_2fa_code_outlook(
    email_id: str = "bootykimani011980@outlook.com", email_password: str = "QVJNklBnK5Q"
) -> str | None:
    logger.info(f"Starting Outlook login process for email: {email_id}")
    async with async_playwright() as pw:
        browser: Browser = await pw.chromium.launch(headless=False, timeout=120000)
        logger.debug("Browser launched")
        context: BrowserContext = await browser.new_context()
        page: Page = await context.new_page()

        # Navigate to login page
        logger.debug(f"Navigating to {link}")
        await page.goto(link, timeout=120000)

        # Enter email ID
        logger.debug(f"Entering email: {email_id}")
        await page.fill(email_id_xpath, email_id, timeout=120000)
        await page.click(next_button_xpath, timeout=120000)

        # Enter password
        logger.debug("Entering password")
        await page.fill(email_password_xpath, email_password, timeout=120000)
        await page.click(sign_in_button_xpath, timeout=120000)

        # Handle possible buttons
        logger.debug("Handling potential dialogs and navigation steps")
        while True:
            if await page.is_visible(outlook_word_xpath, timeout=120000):
                logger.info("Successfully reached Outlook inbox")
                break

            if await page.is_visible(terms_button_xpath, timeout=120000):
                logger.debug("Clicking terms button")
                await page.click(terms_button_xpath, timeout=120000)

            elif await page.is_visible(possible_button_xpath, timeout=120000):
                logger.debug("Clicking possible additional button")
                await page.click(possible_button_xpath, timeout=120000)

            elif await page.is_visible(not_stay_signed_in_button_xpath, timeout=120000):
                logger.debug("Clicking 'Don't stay signed in' button")
                await page.click(not_stay_signed_in_button_xpath, timeout=120000)

            elif await page.is_visible(microsoft_account_word_xpath, timeout=120000):
                logger.debug("Redirecting to mail link")
                await page.goto(mail_link, timeout=120000)

            if await page.is_visible(account_verification_word_xpath, timeout=120000):
                logger.debug("Account verification detected")
                if await page.is_visible(skip_2fa_button_xpath, timeout=12000):
                    logger.debug("Skipping 2FA verification")
                    await page.click(skip_2fa_button_xpath, timeout=120000)

            await asyncio.sleep(2)

        # Check up to the first 5 emails for 2FA code
        logger.info("Searching emails for 2FA code")
        for i in range(2, 7):
            email_content_xpath = email_content_xpath_template.format(i=i)
            if await page.is_visible(email_content_xpath, timeout=120000):
                logger.debug(f"Checking email #{i - 1}")
                email_content = await page.text_content(
                    email_content_xpath, timeout=120000
                )
                if start in email_content:
                    logger.debug("Found email with security code")
                    start_index = email_content.index(start) + len(start)
                    end_index = email_content.index(end, start_index)
                    possible_code = email_content[start_index:end_index].strip().split()

                    for code in reversed(possible_code):
                        if code.isalnum() and len(code) == 6:
                            logger.success(f"Found valid 2FA code: {code}")
                            await browser.close()
                            return code

        logger.error("No valid 2FA code found in emails")
        await browser.close()
        return None
