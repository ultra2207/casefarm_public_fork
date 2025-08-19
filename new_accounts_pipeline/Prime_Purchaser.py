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

import pyperclip
from playwright.async_api import async_playwright
from steam_totp import generate_twofactor_code_for_time
from tqdm.asyncio import tqdm_asyncio

from database import (
    get_all_steam_accounts,
    get_steam_credentials,
    update_prime_status,
    update_steam_balance,
)

database_PATH: str = (
    r"C:\Users\Sivasai\Documents\GitHub\CaseFarm\database\db\database.db"
)

# XPaths and selectors for various elements on the Steam site.
username_xpath: str = "//html/body/div[1]/div[7]/div[6]/div[3]/div[1]/div/div/div/div[2]/div/form/div[1]/input"
password_xpath: str = "//html/body/div[1]/div[7]/div[6]/div[3]/div[1]/div/div/div/div[2]/div/form/div[2]/input"
sign_in_xpath: str = "//html/body/div[1]/div[7]/div[6]/div[3]/div[1]/div/div/div/div[2]/div/form/div[4]/button"
code_xpath: str = "//html/body/div[1]/div[7]/div[6]/div[3]/div[1]/div/div/div/div[2]/form/div/div[2]/div[1]/div/input[1]"

cs2_link: str = "https://store.steampowered.com/app/730/CounterStrike_2/"
add_to_cart_xpath: str = "//html/body/div[1]/div[7]/div[6]/div[3]/div[2]/div[1]/div[5]/div[2]/div[1]/div[2]/div[1]/div[2]/div/div[2]/a/span"
view_cart: str = "//html/body/div[3]/dialog/div/div[2]/div/div[3]/div/div[3]/button[2]"
CS2_PRICE: float = 1270.0
total_payment_xpath: str = "//html/body/div[1]/div[7]/div[6]/div[3]/div[2]/div/div[2]/div[3]/div[2]/div/div[1]/div[1]/div[2]"
continue_to_payments_xpath: str = "//html/body/div[1]/div[7]/div[6]/div[3]/div[2]/div/div[2]/div[3]/div[2]/div/div[1]/button"
accept_ssa_selector: str = "#accept_ssa"
purchase_button_xpath: str = "#purchase_button_bottom_text"


# btn_add_to_cart_54029 > span
# game_area_purchase > div.game_area_purchase_game_wrapper.dynamic_bundle_description.ds_no_flags > div > div.game_purchase_action > div:nth-child(2) > div:nth-child(2) > a > span
async def purchase_prime_for_account(
    page: async_playwright.Page, steam_username: str, wallet_balance: float
) -> bool:
    """Handles the CS2 purchase flow for a single Steam account."""

    creds = get_steam_credentials(steam_username)
    if not creds:
        logger.error(f"No credentials found for {steam_username}")
        return False

    steam_password: str = creds["steam_password"]
    steam_shared_secret: str = creds["steam_shared_secret"]
    two_factor_code: str = generate_twofactor_code_for_time(steam_shared_secret)

    await page.goto("https://store.steampowered.com/login")

    await page.wait_for_selector(username_xpath)
    await page.fill(username_xpath, steam_username)

    await page.wait_for_selector(password_xpath)
    await page.fill(password_xpath, steam_password)
    await page.click(sign_in_xpath)

    # Using pyperclip to copy 2FA code to clipboard and then paste it
    await page.wait_for_selector(code_xpath)
    pyperclip.copy(two_factor_code)
    await page.click(code_xpath)
    await page.keyboard.press("Control+V")
    await page.wait_for_load_state("networkidle")

    await page.goto(cs2_link)
    await page.wait_for_selector(add_to_cart_xpath)

    await page.click(add_to_cart_xpath)

    await page.wait_for_selector(view_cart)
    await page.click(view_cart)

    await page.wait_for_selector(total_payment_xpath)
    total_payment_text: str = await page.inner_text(total_payment_xpath)
    total_price: float = float(re.sub(r"[^\d.]", "", total_payment_text))
    if total_price != CS2_PRICE:
        logger.warning(f"Price mismatch for {steam_username}, skipping purchase.")
        return False

    await page.wait_for_selector(continue_to_payments_xpath)
    await page.click(continue_to_payments_xpath)

    await page.wait_for_selector(accept_ssa_selector)
    await page.click(accept_ssa_selector)

    await page.wait_for_selector(purchase_button_xpath)
    await page.click(purchase_button_xpath)

    await page.wait_for_load_state("networkidle")
    wallet_balance -= CS2_PRICE
    update_steam_balance(steam_username, wallet_balance)
    logger.info(f"{steam_username} completed purchase. New balance: {wallet_balance}")
    return True


async def main() -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        accounts = get_all_steam_accounts()

        for account in tqdm_asyncio(accounts, desc="Processing accounts"):
            steam_username: str = account["steam_username"]
            wallet_balance: float = account["steam_balance"]
            page = await browser.new_page()
            try:
                success: bool = await purchase_prime_for_account(
                    page, steam_username, wallet_balance
                )
                if success:
                    update_prime_status(steam_username, True)
            finally:
                await page.close()

        await browser.close()
    logger.trace("CS2 Prime purchase automation completed")


if __name__ == "__main__":
    asyncio.run(main())
