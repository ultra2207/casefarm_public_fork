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
import os
import re
import shutil

import pyperclip
from playwright.async_api import async_playwright
from steam_totp import generate_twofactor_code_for_time
from tqdm.asyncio import tqdm_asyncio

from database import get_all_steam_accounts, update_steam_avatar_path, update_steam_id

username_xpath: str = "//html/body/div[1]/div[7]/div[6]/div[3]/div[1]/div/div/div/div[2]/div/form/div[1]/input"
password_xpath: str = "//html/body/div[1]/div[7]/div[6]/div[3]/div[1]/div/div/div/div[2]/div/form/div[2]/input"
sign_in_xpath: str = "//html/body/div[1]/div[7]/div[6]/div[3]/div[1]/div/div/div/div[2]/div/form/div[4]/button"
enter_code_xpath: str = "//html/body/div[1]/div[7]/div[6]/div[3]/div[1]/div/div/div/div[2]/div/div[3]/div/div"
code_xpath: str = "//html/body/div[1]/div[7]/div[6]/div[3]/div[1]/div/div/div/div[2]/form/div/div[2]/div[1]/div/input[1]"
account_button_link: str = "//html/body/div[1]/div[7]/div[1]/div/div[3]/div/button"
account_link: str = "https://store.steampowered.com/account/"
steam_id_xpath: str = "//html/body/div[1]/div[7]/div[6]/div[3]/div/div[2]"
profile_edit_link: str = "https://steamcommunity.com/profiles/{}/edit/avatar"
upload_avatar_xpath: str = "//html/body/div[1]/div[7]/div[4]/div/div[2]/div/div/div[3]/div[2]/div[2]/div/div[1]/div[3]/div[2]/button"
save_xpath: str = "//html/body/div[1]/div[7]/div[4]/div/div[2]/div/div/div[3]/div[2]/div[2]/div/div[2]/button[1]"

# Directories for avatar images
UNUSED_PICS_DIR: str = "C:\\Pics\\Unused"
USED_PICS_DIR: str = "C:\\Pics\\Used"

semaphore = asyncio.Semaphore(5)


def check_needs_avatar(account: dict) -> bool:
    """Check if an account needs an avatar (avatar_path is not set)."""
    return not account.get("steam_avatar_path")


async def process_account(account: dict, avatar_path: str) -> bool:
    """
    Process a single account: login, extract Steam ID, upload pre-assigned avatar, and update the database.
    """
    async with semaphore:
        username: str = account["steam_username"]
        password: str = account["steam_password"]
        shared_secret: str = account["steam_shared_secret"]

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context()
            page = await context.new_page()

            try:
                # Login flow
                await page.goto("https://store.steampowered.com/login")
                await page.fill(username_xpath, username)
                await page.fill(password_xpath, password)
                await page.click(sign_in_xpath)
                await page.wait_for_load_state("networkidle")

                enter_code_element = await page.query_selector(enter_code_xpath)
                if enter_code_element:
                    await page.click(enter_code_xpath)

                guard_code = generate_twofactor_code_for_time(shared_secret)
                pyperclip.copy(guard_code)

                await page.wait_for_selector(code_xpath)
                await page.click(code_xpath)
                await page.keyboard.press("Control+v")

                await asyncio.sleep(5)
                await page.wait_for_selector(account_button_link)

                # Navigate to account page to extract Steam ID
                await page.goto(account_link)
                await page.wait_for_selector(steam_id_xpath)
                steam_id_element = await page.query_selector(steam_id_xpath)
                if not steam_id_element:
                    logger.error(f"Could not find Steam ID for account: {username}")
                    return False

                steam_id_text = await steam_id_element.inner_text()
                steam_id_match = re.search(r"Steam ID: (\d+)", steam_id_text)
                if not steam_id_match:
                    logger.error(
                        f"Could not extract Steam ID from text: {steam_id_text}"
                    )
                    return False

                steam_id = steam_id_match.group(1)
                update_steam_id(username, steam_id)

                # Navigate to profile edit page
                profile_url = profile_edit_link.format(steam_id)
                await page.goto(profile_url)
                await page.wait_for_selector(upload_avatar_xpath)

                # Make file input visible for upload
                await page.evaluate("""() => {
                    const fileInputs = document.querySelectorAll('input[type="file"]');
                    for (const input of fileInputs) {
                        input.style.opacity = 1;
                        input.style.display = 'block';
                        input.style.visibility = 'visible';
                        input.style.position = 'fixed';
                        input.style.top = '0';
                        input.style.left = '0';
                        input.style.zIndex = '9999';
                    }
                }""")

                # Upload the pre-assigned avatar
                file_input = await page.query_selector('input[type="file"]')
                await file_input.set_input_files(avatar_path)
                await page.evaluate("""() => {
                    const input = document.querySelector('input[type="file"]');
                    if (input) {
                        input.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                }""")
                await asyncio.sleep(2)

                # Enable and click the save button
                try:
                    await page.keyboard.press("Escape")
                    await asyncio.sleep(0.25)

                    await page.evaluate(
                        """(xpath) => {
                        const saveButton = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                        if (saveButton && saveButton.disabled) {
                            saveButton.removeAttribute('disabled');
                        }
                    }""",
                        save_xpath,
                    )
                    await asyncio.sleep(1)

                    await page.click(save_xpath)
                    await asyncio.sleep(10)  # u need a really long sleep for safety
                    await page.wait_for_load_state("networkidle")
                except Exception as e:
                    logger.error(f"Error clicking save button for {username}: {str(e)}")
                    return False

                # Move the avatar file to the used directory and update the database
                filename = os.path.basename(avatar_path)
                used_path = os.path.join(USED_PICS_DIR, filename)
                shutil.move(avatar_path, used_path)
                update_steam_avatar_path(username, used_path)
                logger.success(f"Successfully processed account {username}")
                return True

            except Exception as e:
                logger.error(f"Error processing account {username}: {str(e)}")
                return False
            finally:
                await browser.close()


async def main() -> None:
    accounts = get_all_steam_accounts()
    accounts_to_process = [acc for acc in accounts if check_needs_avatar(acc)]

    if not accounts_to_process:
        logger.info("No accounts need processing")
        return

    # Pre-allocate avatars for each account by sorting available images in ascending order.
    unused_avatars = [f for f in os.listdir(UNUSED_PICS_DIR) if f.endswith(".webp")]
    unused_avatars.sort(
        key=lambda f: int(f.split(".")[0])
        if f.split(".")[0].isdigit()
        else float("inf")
    )

    if len(unused_avatars) < len(accounts_to_process):
        logger.critical("Error: Not enough unused avatar images for all accounts")
        sys.exit(1)

    # Assign each account its respective avatar image.
    for account, avatar_filename in zip(accounts_to_process, unused_avatars):
        account["preallocated_avatar"] = os.path.join(UNUSED_PICS_DIR, avatar_filename)

    # Launch tasks with a 5-second delay between each launch.
    tasks = []
    for i, account in enumerate(accounts_to_process):
        if i > 0:
            await asyncio.sleep(5)  # Wait 5 seconds between launches.
        task = asyncio.create_task(
            process_account(account, account["preallocated_avatar"])
        )
        tasks.append(task)

    # Wait for all tasks to complete using the asynchronous version of tqdm.
    results = await tqdm_asyncio.gather(*tasks, desc="Processing Accounts")
    logger.trace("All account processing tasks completed")

    successful = sum(1 for result in results if result)
    logger.info(
        f"Successfully processed {successful} out of {len(accounts_to_process)} accounts"
    )


if __name__ == "__main__":
    asyncio.run(main())
