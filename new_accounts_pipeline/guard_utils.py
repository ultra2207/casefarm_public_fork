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
import re

from email_code import get_2fa_code_phno
from playwright.async_api import async_playwright


def remove_phno_from_hexogen_list(
    username: str, file_path: str = "new_accounts_pipeline/hexogen_remaining.txt"
) -> bool:
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            lines = file.readlines()

        found = False
        updated_lines: list[str] = []

        for line in lines:
            if line.startswith(username + ":"):
                found = True
                # Replace phone number inside brackets with 'no_phone'
                line = re.sub(r"\(\d+\)", "(no_phone)", line)
            updated_lines.append(line)

        if not found:
            logger.error("username not found in hexogen list")
            return False

        with open(file_path, "w", encoding="utf-8") as file:
            file.writelines(updated_lines)

        return True  # No print if successful
    except Exception:
        logger.error("username not found in hexogen list")
        return False


async def phone_number_remover(
    username: str, password: str, email_id: str, email_password: str
) -> bool:
    login_link = "https://store.steampowered.com/login/"

    # XPaths for login
    username_xpath = "//html/body/div[1]/div[7]/div[6]/div[3]/div[1]/div/div/div/div[2]/div/form/div[1]/input"
    password_xpath = "//html/body/div[1]/div[7]/div[6]/div[3]/div[1]/div/div/div/div[2]/div/form/div[2]/input"
    sign_in_xpath = "//html/body/div[1]/div[7]/div[6]/div[3]/div[1]/div/div/div/div[2]/div/form/div[4]/button"

    # URL and XPaths for phone removal
    remove_phone_link = "https://store.steampowered.com/phone/manage"
    remove_phone_button_xpath = (
        "//html/body/div[1]/div[7]/div[6]/div[4]/div/div[2]/div[4]/div[2]/a/span"
    )

    # XPaths for the 2FA/email code part
    no_more_access_selector = "#wizard_contents > div > a:nth-child(5) > span"
    send_code_selector = "#wizard_contents > div > a:nth-child(4) > span"
    code_input_xpath = (
        "//html/body/div[1]/div[7]/div[2]/div[4]/div/div[2]/div/div[4]/form/input[1]"
    )
    continue_button_xpath = "//html/body/div[1]/div[7]/div[2]/div[4]/div/div[2]/div/div[4]/form/div[3]/input"
    remove_phone_number_xpath = (
        "//html/body/div[1]/div[7]/div[2]/div[4]/div/div[2]/div/form/div[2]/input"
    )

    async with async_playwright() as p:
        # Launch the browser with headless=False
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        # ----- LOGIN STEP -----
        await page.goto(login_link)
        # Wait for the username field to appear then fill in credentials
        await page.wait_for_selector(username_xpath)
        await page.fill(username_xpath, username)
        await page.wait_for_selector(password_xpath)
        await page.fill(password_xpath, password)
        await asyncio.sleep(0.1)
        await page.wait_for_selector(sign_in_xpath)
        await page.click(sign_in_xpath)
        # Wait for network to be idle to ensure login completes
        await page.wait_for_load_state("networkidle")

        # ----- NAVIGATE TO PHONE MANAGEMENT -----
        await page.goto(remove_phone_link)
        await page.wait_for_load_state("networkidle")

        # Click the button to remove the phone
        await page.wait_for_selector(remove_phone_button_xpath)
        await page.click(remove_phone_button_xpath)
        await page.wait_for_load_state("networkidle")

        # ----- HANDLE 2FA / EMAIL CODE -----
        # Click the element to indicate no more access (which triggers the email code prompt)
        await page.wait_for_selector(no_more_access_selector)
        await page.click(no_more_access_selector)
        await page.wait_for_load_state("networkidle")

        try:
            if await page.wait_for_selector("#error_description", timeout=3000):
                logger.error("Error: The phone number could not be removed.")
                await browser.close()
                return False
        except Exception:
            pass

        await page.wait_for_selector(send_code_selector)
        await page.click(send_code_selector)
        await page.wait_for_load_state("networkidle")

        try:
            if await page.wait_for_selector("#error_description", timeout=3000):
                logger.error("Error: The phone number could not be removed.")
                await browser.close()
                return False
        except Exception:
            pass

        # Retrieve the 2FA code from email using your helper
        code = await get_2fa_code_phno(email_id, email_password)
        # Input the 2FA code into the form
        await page.wait_for_selector(code_input_xpath)
        await page.fill(code_input_xpath, code)
        await asyncio.sleep(0.1)
        await page.click(continue_button_xpath)
        await page.wait_for_load_state("networkidle")

        # ----- CONFIRM PHONE REMOVAL -----
        await page.wait_for_selector(remove_phone_number_xpath)
        await page.click(remove_phone_number_xpath)
        await page.wait_for_load_state("networkidle")

        # Finally, wait for the confirmation link to appear
        # This link indicates that the phone has been removed (i.e. user can now add a new phone)
        await page.wait_for_selector(
            'a[href="https://store.steampowered.com/phone/add"]', timeout=60000
        )
        remove_phno_from_hexogen_list(username)
        await browser.close()
        logger.trace("phone_number_remover function executed")
        return True
