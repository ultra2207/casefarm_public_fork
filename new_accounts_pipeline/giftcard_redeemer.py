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


import csv
import re
from typing import List, Tuple

import steam
from tqdm import tqdm

from database import (
    get_steam_balance,
    get_steam_credentials,
    region_data_update_account,
    update_steam_balance,
)


def add_balance_wtih_giftcards(steam_username: str, amount: int) -> bool:
    """
    Redeems giftcards and adds their total value to the specified Steam account's balance.

    After a giftcard is redeemed, it is removed from giftcards.csv and appended to used_giftcards.csv.
    """

    initial_balance = get_steam_balance(steam_username)
    # Retrieve account credentials and existing balance from the DB
    credentials = get_steam_credentials(steam_username)
    if not credentials:
        logger.error(f"Credentials for {steam_username} not found.")
        return False

    steam_password: str = credentials["steam_password"]
    steam_identity_secret: str = credentials["steam_identity_secret"]
    steam_shared_secret: str = credentials["steam_shared_secret"]

    def compute_optimal_combo(
        giftcards: List[Tuple[str, int]], target: int
    ) -> Tuple[List[Tuple[str, int]] | None, int | None]:
        """
        Computes an optimal combination of giftcards that reaches or exceeds the target amount.
        """
        dp = {0: ([], 0)}
        for code, value in giftcards:
            new_dp = dp.copy()
            for s, (combo, count_150) in dp.items():
                new_sum = s + value
                new_combo = combo + [(code, value)]
                new_count = count_150 + (1 if value == 150 else 0)
                if new_sum not in new_dp:
                    new_dp[new_sum] = (new_combo, new_count)
                else:
                    if new_count > new_dp[new_sum][1]:
                        new_dp[new_sum] = (new_combo, new_count)
            dp = new_dp

        valid_sums = [s for s in dp if s >= target]
        if not valid_sums:
            return None, None
        best_sum = min(valid_sums)
        return dp[best_sum][0], best_sum

    class MyClient(steam.Client):
        async def on_ready(self) -> None:
            logger.info(f"Logged in as {self.user}")
            logger.info("Redeeming giftcards...")

            # Define file paths
            giftcards_file = r"C:\Users\Sivasai\Documents\GitHub\CaseFarm\new_accounts_pipeline\giftcards.csv"
            used_giftcards_file = r"C:\Users\Sivasai\Documents\GitHub\CaseFarm\new_accounts_pipeline\used_giftcards.csv"

            # Helper function to remove a giftcard from the CSV
            def remove_giftcard_from_csv(file_path: str, code: str, value: int) -> None:
                rows = []
                removed = False
                try:
                    with open(file_path, newline="") as csvfile:
                        reader = csv.reader(csvfile)
                        for row in reader:
                            if not row or len(row) < 2:
                                continue
                            row_code = row[0].strip()
                            try:
                                row_value = int(row[1].strip())
                            except ValueError:
                                continue
                            # Remove only the first matching occurrence
                            if not removed and row_code == code and row_value == value:
                                removed = True
                                continue
                            rows.append(row)
                    with open(file_path, "w", newline="") as csvfile:
                        writer = csv.writer(csvfile)
                        writer.writerows(rows)
                except Exception as e:
                    logger.error(f"Error updating file {file_path}: {e}")

            # Helper function to append a used giftcard to the CSV
            def add_used_giftcard_to_csv(file_path: str, code: str, value: int) -> None:
                try:
                    with open(file_path, "a", newline="") as csvfile:
                        writer = csv.writer(csvfile)
                        writer.writerow([code, value])
                except Exception as e:
                    logger.error(f"Error writing to file {file_path}: {e}")

            # Load giftcards from CSV
            giftcards: List[Tuple[str, int]] = []
            try:
                with open(giftcards_file, newline="") as csvfile:
                    reader = csv.reader(csvfile)
                    for row in reader:
                        if not row or len(row) < 2:
                            continue
                        code = row[0].strip()
                        try:
                            value = int(row[1].strip())
                        except ValueError:
                            continue
                        giftcards.append((code, value))
                logger.trace(f"Loaded {len(giftcards)} gift cards from file")
            except Exception as e:
                logger.error(f"Error reading giftcards file: {e}")
                await self.close()

            # Compute the optimal combination of giftcards to cover the target amount
            combo, combo_sum = compute_optimal_combo(giftcards, amount)
            if combo is None:
                logger.critical(
                    "Not enough giftcards available to cover the requested amount."
                )
                await self.close()

            logger.info(
                f"Redeeming giftcards with total value {combo_sum} (target was {amount})."
            )
            # Redeem each giftcard in the chosen combination with a progress bar
            for code, value in tqdm(combo, desc="Redeeming giftcards", unit="card"):
                logger.debug(f"Redeeming giftcard {code} (value {value})...")
                try:
                    resp = await self.wallet.add(code)
                except ValueError as e:
                    logger.error(f"Failed to redeem giftcard {code}: {e}")
                    await self.close()

                if resp.get("success") != 1:
                    logger.error(
                        f"Failed to redeem gift card, success code: {resp.get('success')}"
                    )
                    await self.close()

                balance_str = resp["formattednewwalletbalance"]
                # Remove any characters that are not digits or a dot
                clean_str = re.sub(r"[^0-9.]", "", balance_str)
                current_balance = float(clean_str)
                # After successful redemption, update CSV files
                remove_giftcard_from_csv(giftcards_file, code, value)
                add_used_giftcard_to_csv(used_giftcards_file, code, value)

            # Update the steam balance in the database
            new_balance = current_balance
            update_steam_balance(steam_username, new_balance)
            region_data_update_account(
                steam_username=steam_username, currency_code="IDR", region="ID"
            )
            logger.info(f"Balance updated to: {new_balance}")
            await self.close()

    # Create and run the client (this call blocks until completion)
    client = MyClient()
    try:
        client.run(
            steam_username,
            steam_password,
            shared_secret=steam_shared_secret,
            identity_secret=steam_identity_secret,
        )
    except Exception as e:
        logger.error(f"Error during client execution: {e}")

    final_balance = get_steam_balance(steam_username)

    if final_balance >= initial_balance + amount:
        logger.success(
            f"Balance successfully updated from {initial_balance} to {final_balance}"
        )
        return True
    else:
        logger.error(
            f"Failed to update balance. Initial: {initial_balance}, Final: {final_balance}, Target: {initial_balance + amount}"
        )
        return False


# Example usage:
if __name__ == "__main__":
    steam_username = "mellowSnail894"
    amount_to_add = 12000
    success = add_balance_wtih_giftcards(steam_username, amount_to_add)
    if success:
        logger.info("Balance successfully updated.")
    else:
        logger.error("Failed to update balance.")
