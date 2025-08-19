import asyncio
import sys

import yaml
from email_code_outlook import get_2fa_code_outlook
from playwright.async_api import async_playwright


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


link = "https://login.live.com/"
email_id_xpath = "//html/body/div[1]/div/div/div/div[2]/div[1]/div/div/div/div[1]/div[2]/div/div/div/form/div[2]/div/div/input"
next_button_xpath = "//html/body/div[1]/div/div/div/div[2]/div[1]/div/div/div/div[1]/div[2]/div/div/div/form/div[4]/div/div/div/div/button"
email_password_xpath = "//html/body/div[1]/div/div/div/div[2]/div[1]/div/div/div/div/div[2]/div[2]/div/form/div[3]/div/div/input"
sign_in_button_xpath = "//html/body/div[1]/div/div/div/div[2]/div[1]/div/div/div/div/div[2]/div[2]/div/form/div[5]/div/div/div/div/button"

# Possible buttons
terms_button_xpath = "//html/body/div[2]/div/div/div/div[2]/div[1]/div/div/div/div/div[2]/div[2]/div/form/div[4]/div/div/div/div/button"
possible_button_xpath = "//html/body/div/div/div[2]/button/span/span/span"
not_stay_signed_in_button_xpath = "//html/body/div[1]/div/div/div/div[2]/div[1]/div/div/div/div/div[2]/div[2]/div/form/div[3]/div[2]/div/div[1]/button"

microsoft_account_word_xpath = "//html/body/div/div[2]/div/div[2]/div/div[1]/div[2]/div/div/div/div/div/div[1]/div/div/div/a"
mail_link = "https://outlook.live.com/mail/0/"
skip_2fa_button_xpath = "//html/body/div[1]/div/div/div[2]/div/div[1]/div[2]/div/div[2]/div/div/div/section/div/form/div[5]/a"
outlook_word_xpath = "//html/body/div[1]/div/div[1]/div/div/div[1]/div[2]/div/div/div/div/div/div[1]/div[1]/div[2]/div/a/span"

account_verification_word_xpath = "//html/bod   /div[1]/div/div/div[2]/div/div[1]/div[2]/div/div[2]/div/div/div/section/div/form/p"
confirmation_account_path = "//html/body/div[1]/div/div/div[2]/div/div[1]/div[2]/div/div[2]/div/div/div/section/div/form/div[3]/div/input"
confirmation_email = "bootykimani011980@outlook.com"

confirmation_next_xpath = "//html/body/div[1]/div/div/div[2]/div/div[1]/div[2]/div/div[2]/div/div/div/section/div/form/div[6]/div/div"
confirmation_code_path = "//html/body/div[1]/div/div/div[2]/div/div[1]/div[2]/div/div[2]/section/div/form/div[2]/div[2]/input"
confirmation_next_2_xpath = "//html/body/div[1]/div/div/div[2]/div/div[1]/div[2]/div/div[2]/section/div/form/div[5]/div/div/input"

email_content_xpath_template = "//html/body/div[1]/div/div[2]/div/div[2]/div[2]/div[1]/div/div/div[3]/div/div/div[1]/div[2]/div/div/div/div/div/div/div/div[{i}]/div/div"

trash_account_xpath_1 = "//html/body/div[1]/div/div/div[2]/div/div[1]/div[2]/div/div[2]/div/div/div/form/div/div[1]"

disabled_confirmation_xpath = "//html/body/div/div[7]/div[6]/div[1]/div/h2"

# for adding steamguard
start = "Please provide the following code to your mobile app to complete adding your authenticator:"
end = r"This email is automatically"

# for the phone number
start_2 = "Here is the code you need to change your Steam login credentials:"
end_2 = r"If you are not"


async def get_2fa_code_steamguard(email_id, email_password) -> str | None:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False, timeout=120000)
        context = await browser.new_context()
        page = await context.new_page()

        # Navigate to login page
        await page.goto(link, timeout=120000)

        # Enter email ID
        await page.fill(email_id_xpath, email_id, timeout=120000)
        await page.click(next_button_xpath, timeout=120000)

        # Enter password
        await page.fill(email_password_xpath, email_password, timeout=120000)
        await page.click(sign_in_button_xpath, timeout=120000)

        # Handle possible buttons
        while True:
            if await page.is_visible(outlook_word_xpath, timeout=120000):
                break

            if await page.is_visible(trash_account_xpath_1, timeout=120000):
                # Check if the content is "Help us protect your account"
                element_content = await page.inner_text(trash_account_xpath_1)
                if "Help us protect your account" in element_content:
                    logger.error("Outlook account is trash. Skipping to next account.")
                    # You can use `continue` to skip to the next iteration if inside a loop
                    break

            if await page.is_visible(terms_button_xpath, timeout=120000):
                await page.click(terms_button_xpath, timeout=120000)

            if await page.is_visible(possible_button_xpath, timeout=120000):
                await page.click(possible_button_xpath, timeout=120000)
            if await page.is_visible(not_stay_signed_in_button_xpath, timeout=120000):
                await page.click(not_stay_signed_in_button_xpath, timeout=120000)
            if await page.is_visible(microsoft_account_word_xpath, timeout=120000):
                await page.goto(mail_link, timeout=120000)

            if await page.is_visible(skip_2fa_button_xpath, timeout=120000):
                if await page.is_visible(skip_2fa_button_xpath, timeout=12000):
                    await page.click(skip_2fa_button_xpath, timeout=120000)
                else:
                    # verify logic here
                    await page.fill(
                        confirmation_account_path, confirmation_email, timeout=120000
                    )
                    await page.click(confirmation_next_xpath, timeout=120000)
                    confirm_code = get_2fa_code_outlook()  # input(f"Please enter the confirmation code manually from {confirmation_email}")
                    await page.fill(
                        confirmation_code_path, confirm_code, timeout=120000
                    )
                    await page.click(confirmation_next_2_xpath, timeout=120000)
            await asyncio.sleep(2)

        # Check up to the first 5 emails for 2FA code
        for i in range(2, 7):
            email_content_xpath = email_content_xpath_template.format(i=i)
            if await page.is_visible(email_content_xpath, timeout=120000):
                email_content = await page.text_content(
                    email_content_xpath, timeout=120000
                )
                if start in email_content:
                    start_index = email_content.index(start) + len(start)
                    end_index = email_content.index(end, start_index)
                    possible_code = email_content[start_index:end_index].strip().split()

                    for code in reversed(possible_code):
                        if code.isalnum() and len(code) == 5 and code.isupper():
                            await browser.close()
                            return code

        await browser.close()
        return None


async def get_2fa_code_phno(email_id, email_password) -> str | None:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False, timeout=120000)
        context = await browser.new_context()
        page = await context.new_page()

        # Navigate to login page
        await page.goto(link, timeout=120000)

        # Enter email ID
        await page.fill(email_id_xpath, email_id, timeout=120000)
        await page.click(next_button_xpath, timeout=120000)

        # Enter password
        await page.fill(email_password_xpath, email_password, timeout=120000)
        await page.click(sign_in_button_xpath, timeout=120000)

        # Handle possible buttons
        while True:
            if await page.is_visible(outlook_word_xpath, timeout=120000):
                break

            if await page.is_visible(trash_account_xpath_1, timeout=120000):
                # Check if the content is "Help us protect your account"
                element_content = await page.inner_text(trash_account_xpath_1)
                if "Help us protect your account" in element_content:
                    logger.error("Outlook account is trash. Skipping to next account.")
                    # You can use `continue` to skip to the next iteration if inside a loop
                    break

            if await page.is_visible(terms_button_xpath, timeout=120000):
                await page.click(terms_button_xpath, timeout=120000)

            if await page.is_visible(possible_button_xpath, timeout=120000):
                await page.click(possible_button_xpath, timeout=120000)
            if await page.is_visible(not_stay_signed_in_button_xpath, timeout=120000):
                await page.click(not_stay_signed_in_button_xpath, timeout=120000)
            if await page.is_visible(microsoft_account_word_xpath, timeout=120000):
                await page.goto(mail_link, timeout=120000)

            if await page.is_visible(skip_2fa_button_xpath, timeout=120000):
                if await page.is_visible(skip_2fa_button_xpath, timeout=12000):
                    await page.click(skip_2fa_button_xpath, timeout=120000)
                else:
                    # verify logic here
                    await page.fill(
                        confirmation_account_path, confirmation_email, timeout=120000
                    )
                    await page.click(confirmation_next_xpath, timeout=120000)
                    confirm_code = get_2fa_code_outlook()  # input(f"Please enter the confirmation code manually from {confirmation_email}")
                    await page.fill(
                        confirmation_code_path, confirm_code, timeout=120000
                    )
                    await page.click(confirmation_next_2_xpath, timeout=120000)
            await asyncio.sleep(2)

        # Check up to the first 5 emails for 2FA code
        for i in range(2, 7):
            email_content_xpath = email_content_xpath_template.format(i=i)
            if await page.is_visible(email_content_xpath, timeout=120000):
                email_content = await page.text_content(
                    email_content_xpath, timeout=120000
                )

                if start_2 in email_content:
                    start_index_2 = email_content.index(start_2) + len(start_2)
                    end_index_2 = email_content.index(end_2, start_index_2)
                    possible_code_final = (
                        email_content[start_index_2:end_index_2].strip().split()
                    )

                    for code in reversed(possible_code_final):
                        if code.isalnum() and len(code) == 5 and code.isupper():
                            await browser.close()
                            return code

        await browser.close()
        return None
