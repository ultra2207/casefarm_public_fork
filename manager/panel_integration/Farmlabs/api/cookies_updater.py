import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import yaml
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


async def refresh_farmlabs_cookies() -> None:
    """Refresh FarmLabs authentication cookies and store them with metadata."""
    logger.trace("Starting refresh_farmlabs_cookies workflow")

    cookies_dir = Path(
        r"C:\Users\Sivasai\Documents\GitHub\CaseFarm\manager\panel_integration\farmlabs\api\cache"
    )
    cookies_dir.mkdir(parents=True, exist_ok=True)
    cookies_file = cookies_dir / "cookies.txt"
    metadata_file = cookies_dir / "cookies_metadata.json"

    should_refresh: bool = True
    if cookies_file.exists() and metadata_file.exists():
        try:
            with open(metadata_file, "r") as f:
                metadata: dict = json.load(f)
                last_update_timestamp: float = metadata.get("last_update_timestamp", 0)
                current_time: float = time.time()

                if current_time - last_update_timestamp < 7080:
                    logger.info(
                        f"Cookies are still fresh. Last updated: {metadata.get('last_update_human')}"
                    )
                    should_refresh = False
        except Exception as e:
            logger.warning(f"Error reading metadata: {e}", exc_info=True)

    if not should_refresh:
        return

    logger.info("Initiating cookie refresh process")

    async with async_playwright() as p:
        logger.trace("Launching headless Chromium browser")
        browser = await p.chromium.launch(headless=True)

        logger.trace("Creating new browser context")
        context = await browser.new_context()
        page = await context.new_page()

        logger.trace("Navigating to FarmLabs dashboard")
        await page.goto("https://dashboard.farmlabs.dev/")

        try:
            logger.trace("Attempting automatic login")
            await _perform_automatic_login(page)
        except Exception as e:
            logger.warning(f"Login elements not found: {e}")
            await _handle_manual_login(page)

        logger.trace("Extracting valid cookies")
        cookies: list[dict] = await context.cookies()  # type: ignore
        cookie_dict: dict[str, str] = {
            cookie["name"]: cookie["value"]
            for cookie in cookies
            if cookie.get("domain", "").endswith("farmlabs.dev")
        }

        logger.trace("Persisting cookies to disk")
        _save_cookies(cookies_file, cookie_dict, metadata_file)

        logger.info(f"Cookies refreshed at: {datetime.utcnow().isoformat()}")
        await browser.close()


async def _perform_automatic_login(page) -> None:
    """Handle automated form-based login."""
    selectors = {
        "email": r"#data\.email",
        "password": r"#data\.password",
        "checkbox": r"#data\.remember",
        "sign_in": r"#form > div.fi-form-actions > div > button",
    }

    credentials = {"email": "sivasai2207@gmail.com", "password": "password"}

    for field, selector in selectors.items():
        logger.trace(f"Waiting for {field} selector")
        await page.wait_for_selector(selector)

        if field in credentials:
            await page.fill(selector, credentials[field])
        else:
            await page.click(selector)


async def _handle_manual_login(page) -> None:
    """Handle manual login scenario with user interaction."""
    logger.warning("Manual login required - please authenticate in the browser window")

    try:
        await page.wait_for_function(
            """
            () => !document.querySelector('input[type="email"], input[type="password"], button:has-text("Log in")')
            """,
            timeout=120000,
        )
        logger.trace("Detected successful manual login")
        await page.wait_for_load_state("networkidle")
    except Exception as e:
        logger.error(f"Login timeout or failure: {e}")
        raise


def _save_cookies(
    cookies_file: Path, cookie_dict: dict[str, str], metadata_file: Path
) -> None:
    """Persist cookies and metadata to filesystem."""
    with open(cookies_file, "w") as f:
        json.dump(cookie_dict, f, indent=2)

    metadata = {
        "last_update_timestamp": time.time(),
        "last_update_human": datetime.utcnow().isoformat(),
    }

    with open(metadata_file, "w") as f:
        json.dump(metadata, f, indent=2)


if __name__ == "__main__":
    asyncio.run(refresh_farmlabs_cookies())
