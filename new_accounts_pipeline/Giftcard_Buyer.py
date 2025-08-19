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
import csv
import os

import psutil
import pyperclip
from playwright.async_api import BrowserContext, Page, async_playwright


def close_chrome() -> None:
    try:
        # Iterate through all running processes
        for proc in psutil.process_iter():
            # Check if process name contains 'chrome'
            if "chrome" in proc.name().lower():
                # Terminate the process
                proc.terminate()
        logger.info("All Chrome instances have been closed.")
    except Exception as e:
        logger.error(f"An error occurred while closing Chrome: {e}")


async def buy_giftcards(num_12000_idr_giftcards: int = 7) -> None:
    logger.info(f"Starting purchase of {num_12000_idr_giftcards} Steam gift cards")
    async with async_playwright() as p:
        close_chrome()

        logger.debug("Launching Chrome with persistent context")
        browser: BrowserContext = await p.chromium.launch_persistent_context(
            user_data_dir="C:/Users/Sivasai/AppData/Local/Google/Chrome/User Data",
            headless=False,
            executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        )
        page: Page = await browser.new_page()

        link: str = "https://moogold.com/product/steam-gift-card-idr/"
        checkout_link: str = "https://moogold.com/checkout/"

        add_first_giftcard_xpath: str = "//html/body/div[1]/main/div/div/div[2]/div/div[8]/div[2]/ul/li[1]/div/div/div[2]/div[2]/div/button[1]/span[1]/svg"
        copy_button: str = "//html/body/div[1]/html/div[3]/div[1]/div/div/div[2]/div[2]/div/div[2]/div/div[3]/div[2]/div/div/div/div/div/div[1]/button/span/span/p"
        plus_button: str = "//html/body/div/main/form/div[1]/div[1]/ul/li/div/div[2]/div[2]/div[1]/button[2]/span"
        disagree_checkbox: str = (
            "//html/body/div/main/form/div[2]/div[4]/div/label/span[1]"
        )
        proceed_to_checkout: str = "//html/body/div/main/form/div[2]/div[1]/button/span"
        upi_xpath: str = "//html/body/div/main/form/div/div[1]/ul/li[2]/button/span"

        # payer details
        payer_name: str = "#payerName"
        payer_surname: str = "#payerSurname"
        # payer_phno = "#phoneNumber"  # not needed
        payer_upi_id: str = "#providerPayerId"
        street_name: str = "#billingAddress"
        street_number: str = "#billingStreetNumber"
        flat_number: str = "#flatOther"
        postcode: str = "#billingZipCode"
        city: str = "#billingCity"

        logger.debug(f"Navigating to gift card page: {link}")
        await page.goto(link)

        logger.debug("Waiting for add first gift card button")
        await page.wait_for_selector(add_first_giftcard_xpath)
        await page.click(add_first_giftcard_xpath)
        logger.info("Added first gift card to cart")

        # wait for <a class="w6wAha" href="/checkout"><span>View cart</span></a> this href to appear

        logger.debug(f"Navigating to checkout page: {checkout_link}")
        await page.goto(checkout_link)

        logger.debug("Waiting for plus button")
        await page.wait_for_selector(plus_button)

        logger.debug(f"Adding {num_12000_idr_giftcards - 1} more gift cards")
        for i in range(num_12000_idr_giftcards - 1):
            await asyncio.sleep(0.1)
            await page.wait_for_selector(plus_button)
            await page.click(plus_button)
            logger.trace(f"Added gift card #{i + 2}")

        logger.debug("Clicking disagree checkbox")
        await page.wait_for_selector(disagree_checkbox)
        await page.click(disagree_checkbox)

        logger.debug("Proceeding to checkout")
        await page.wait_for_selector(proceed_to_checkout)
        await page.click(proceed_to_checkout)

        logger.debug("Selecting UPI payment method")
        await page.wait_for_selector(upi_xpath)
        await page.click(upi_xpath)

        logger.debug("Filling out payer details")
        await page.wait_for_selector(payer_name)
        await page.fill(payer_name, "Sivasai")

        await page.wait_for_selector(payer_surname)
        await page.fill(payer_surname, "B")

        await page.wait_for_selector(payer_upi_id)
        await page.fill(payer_upi_id, "sivasai2207@okhdfcbank")

        await page.wait_for_selector(street_name)
        await page.fill(street_name, "VIT Vellore")

        await page.wait_for_selector(street_number)
        await page.fill(street_number, "VIT street")

        await page.wait_for_selector(flat_number)
        await page.fill(flat_number, "Mens hostel")

        await page.wait_for_selector(postcode)
        await page.fill(postcode, "632014")

        await page.wait_for_selector(city)
        await page.fill(city, "Vellore")

        logger.info("Filled all payer details, waiting for copy button")

        # Wait for the "Copy" button to appear and click it
        await page.wait_for_selector(copy_button)
        await page.click(copy_button)
        logger.debug("Clicked copy button for gift card code")

        # Optional: wait briefly to ensure the clipboard has the updated value
        await page.wait_for_timeout(1000)  # wait for 1 second

        # Retrieve the clipboard content using pyperclip
        giftcard_code: str = pyperclip.paste()
        logger.debug("Retrieved gift card code from clipboard")

        # Ensure the directory exists
        os.makedirs("new_accounts_pipeline", exist_ok=True)
        csv_path: str = os.path.join("new_accounts_pipeline", "giftcards.csv")

        # Save the gift card code and its value to the CSV file (no header)
        with open(csv_path, mode="a", newline="") as csv_file:
            csv_writer = csv.writer(csv_file)
            csv_writer.writerow([giftcard_code, 12000])
        logger.success(f"Saved gift card code to {csv_path} with value 12000")

        logger.info("Gift card purchase completed successfully.")
        await browser.close()


asyncio.run(buy_giftcards())
