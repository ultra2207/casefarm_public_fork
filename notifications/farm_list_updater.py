import asyncio
import sqlite3
import sys

import aiohttp
import yaml


def load_config():
    config_path = r"C:\Users\Sivasai\Documents\GitHub\CaseFarm\config.yaml"
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    return config


_config = load_config()
ROOT_DIR = _config["ROOT_DIR"]
sys.path.insert(0, ROOT_DIR)

from accounts_manager.utils.wallet_balance_updater import update_steam_wallet_balances
from utils.logger import get_custom_logger

logger = get_custom_logger()


class TickTickFarmingManager:
    def __init__(self):
        self.client_id = "355V0WfCiJv8JrypgG"
        self.client_secret = "3#!^j!YE2GI691N00g+&KGtinoiI7(JJ"
        self.access_token = None
        self.base_url = "https://api.ticktick.com/open/v1"
        self.db_path = (
            r"C:\Users\Sivasai\Documents\GitHub\CaseFarm\database\db\database.db"
        )
        self.token_file = r"C:\Users\Sivasai\Documents\GitHub\CaseFarm\notifications\ticktick_token.txt"
        self.casefarm_project_id = None

    def load_access_token(self):
        """Load access token from file."""
        try:
            with open(self.token_file, "r") as f:
                self.access_token = f.read().strip()
            logger.info("Access token loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load access token: {e}")
            raise

    async def get_casefarm_project_id(self):
        """Find and cache the CaseFarm project ID."""
        if self.casefarm_project_id:
            return self.casefarm_project_id

        try:
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/project", headers=headers
                ) as response:
                    if response.status == 200:
                        projects = await response.json()
                        for project in projects:
                            if project.get("name") == "CaseFarm":
                                self.casefarm_project_id = project["id"]
                                logger.trace(
                                    f"Found CaseFarm project ID: {self.casefarm_project_id}"
                                )
                                return self.casefarm_project_id

                        logger.warning(
                            "CaseFarm project not found - tasks will go to inbox"
                        )
                        return None
                    else:
                        logger.error(f"Failed to get projects: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Error getting CaseFarm project ID: {e}")
            return None

    def get_eligible_accounts(self):
        """Get accounts eligible for armoury farming."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Query for accounts that are armoury enabled and have enough balance for 5 pass
            query = """
            SELECT id, steam_username, steam_balance, pass_value, 
                   (steam_balance / pass_value) as affordable_passes
            FROM accounts 
            WHERE is_armoury = 1 
            AND pass_value > 0
            AND steam_balance >= (1 * pass_value)
            AND steam_username IS NOT NULL
            AND steam_username != ''
            ORDER BY affordable_passes DESC
            """

            cursor.execute(query)
            accounts = cursor.fetchall()
            conn.close()

            logger.info(f"Found {len(accounts)} eligible accounts for farming:")
            for account in accounts:
                (
                    account_id,
                    steam_username,
                    steam_balance,
                    pass_value,
                    affordable_passes,
                ) = account
                logger.info(
                    f"Username: {steam_username}, "
                    f"Balance: {steam_balance}, "
                    f"Pass Value: {pass_value}, "
                    f"Affordable Passes: {affordable_passes}"
                )
            return accounts

        except Exception as e:
            logger.error(f"Error querying database: {e}")
            return []

    async def create_farming_task(
        self, username, account_id, balance, pass_value, affordable_passes
    ):
        """Create a new farming task with user-readable waiting time."""
        try:
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            }

            # Get current time in IST timezone with user-friendly format
            from datetime import datetime

            import pytz

            ist = pytz.timezone("Asia/Kolkata")
            now_ist = datetime.now(ist)

            # Format: "11:30 AM 30 June"
            time_part = now_ist.strftime("%I:%M %p")  # 11:30 AM
            date_part = now_ist.strftime("%d %B")  # 30 June
            formatted_datetime = f"{time_part} {date_part}"

            # Create task description with waiting time
            task_description = f"""Can afford: {int(affordable_passes)} passes\n**Waiting since {formatted_datetime}**"""

            task_data = {
                "title": f"💎 Farming: {username}",
                "desc": task_description,
                "priority": 3,  # Changed to medium priority (0=None, 1=Low, 3=Medium, 5=High)
                "sortOrder": -1,
                "items": [
                    {
                        "title": f"Bought {int(affordable_passes)} armoury passes",
                        "status": 0,
                    },
                    {"title": "Started FarmLabs farm job", "status": 0},
                    {"title": "Farm job in progress", "status": 0},
                    {"title": "Farming and items redeeming finished", "status": 0},
                ],
            }

            # Add project ID if CaseFarm project exists
            if self.casefarm_project_id:
                task_data["projectId"] = self.casefarm_project_id

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/task", headers=headers, json=task_data
                ) as response:
                    if response.status == 200:
                        await response.json()
                        logger.info(
                            f"✅ Created farming task for {username} (waiting since {formatted_datetime})"
                        )
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(
                            f"❌ Failed to create task for {username}: {response.status} - {error_text}"
                        )
                        return False
        except Exception as e:
            logger.error(f"Error creating task for {username}: {e}")
            return False

    async def update_farming_list(self):
        """Create farming tasks for all eligible accounts (simplified version)."""
        try:
            # Get CaseFarm project ID first
            await self.get_casefarm_project_id()

            # Get eligible accounts
            eligible_accounts = self.get_eligible_accounts()

            if not eligible_accounts:
                logger.info("No eligible accounts found for farming")
                return

            # Create tasks for all eligible accounts
            created_count = 0

            logger.info(
                f"Creating farming tasks for {len(eligible_accounts)} eligible accounts..."
            )

            for (
                account_id,
                username,
                balance,
                pass_value,
                affordable_passes,
            ) in eligible_accounts:
                success = await self.create_farming_task(
                    username, account_id, balance, pass_value, affordable_passes
                )
                if success:
                    created_count += 1

                # Add small delay to avoid rate limiting
                await asyncio.sleep(0.3)

            logger.info("📊 Farming list creation summary:")
            logger.info(f"   • Created: {created_count} new tasks")
            logger.info(f"   • Total eligible accounts: {len(eligible_accounts)}")

        except Exception as e:
            logger.error(f"Error updating farming list: {e}")


async def update_farm_list(update_wallet_balances: bool = True) -> bool:
    """Main function to update Steam wallet balances and create farming tasks."""
    try:
        if update_wallet_balances:
            logger.info("🚀 Starting Steam wallet balance update...")
            await update_steam_wallet_balances()
            logger.info("✅ Steam wallet balance update completed successfully.")
        else:
            logger.info(
                "ℹ️ Skipping wallet balance update (update_wallet_balances=False)"
            )

        logger.info("🎯 Creating farming tasks in TickTick...")
        farming_manager = TickTickFarmingManager()
        farming_manager.load_access_token()
        await farming_manager.update_farming_list()
        logger.info("✅ Farming task creation completed successfully.")
        return True
    except Exception as e:
        logger.error(f"❌ An error occurred during the update: {e}")
        return False


if __name__ == "__main__":
    asyncio.run(update_farm_list())
