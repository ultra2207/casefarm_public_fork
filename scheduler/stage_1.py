# Night running stage that kicks off the farm (stage 1)
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

from tenacity import retry, retry_if_result, stop_after_attempt, wait_fixed

from database import get_all_steam_accounts
from notifications.farm_list_updater import update_farm_list
from utils.steam_items_lister import items_lister

# Retry decorator for core functions
# Retries on exceptions (default behavior) and when function returns False
retry_core_function = retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(3),  # Wait 3 seconds between retries
    retry=retry_if_result(lambda result: result is False),
    reraise=True,
)


@retry_core_function
async def items_lister_with_retry() -> bool:
    return await items_lister()


@retry_core_function
async def update_farm_list_with_retry() -> bool:
    return await update_farm_list()


async def main() -> None:
    logger.info("Starting stage 1: Items lister, Farm list updater...")

    # --- START: Added Code ---
    # 1. Get the initial state of all accounts
    logger.trace("Fetching initial wallet balances...")
    try:
        initial_accounts_list = get_all_steam_accounts()
        # Convert to a dictionary for easy lookup
        initial_accounts = {acc["steam_username"]: acc for acc in initial_accounts_list}
        logger.success("Successfully fetched initial account states.")
    except Exception as e:
        logger.critical(f"Failed to fetch initial account data from database: {e}")
        return  # Exit if we can't get initial data
    # --- END: Added Code ---

    # Track success status and error messages for each stage
    stage_results = {
        "items_lister": {"success": False, "error": None},
        "farm_list_updater": {"success": False, "error": None},
    }

    print("\n")
    # Items lister
    logger.info("Starting items lister...")
    try:
        success = await items_lister_with_retry()
        if success:
            logger.success(f"Items lister completed successfully: {success}")
            stage_results["items_lister"]["success"] = True
        else:
            error_msg = f"Items lister failed after retries: {success}"
            logger.error(error_msg)
            stage_results["items_lister"]["error"] = error_msg
    except Exception as e:
        error_msg = f"Items lister failed after 3 attempts: {e}"
        logger.critical(error_msg, exc_info=True)
        stage_results["items_lister"]["error"] = error_msg
        # We don't raise here, to allow the summary to run

    print("\n")
    # Farm list updater
    logger.info("Starting farm list updater...")
    try:
        success = await update_farm_list_with_retry()
        if success:
            logger.success(f"Farm list updater completed successfully: {success}")
            stage_results["farm_list_updater"]["success"] = True
        else:
            error_msg = f"Farm list updater failed after retries: {success}"
            logger.error(error_msg)
            stage_results["farm_list_updater"]["error"] = error_msg
        logger.info(
            "Please check TickTick for list of accounts that need armoury pass farming."
        )
    except Exception as e:
        error_msg = f"Farm list updater failed after 3 attempts: {e}"
        logger.critical(error_msg, exc_info=True)
        stage_results["farm_list_updater"]["error"] = error_msg
        # We don't raise here, to allow the summary to run

    # 2. Get final account state and compare balances
    print("\n")
    logger.info("Checking for wallet balance updates...")
    try:
        final_accounts = get_all_steam_accounts()
        balance_changed_count = 0
        for final_account in final_accounts:
            username = final_account["steam_username"]
            initial_account = initial_accounts.get(username)

            if not initial_account:
                logger.critical(f"Account '{username}' is new. Skipping balance check.")
                continue

            initial_balance = initial_account["steam_balance"]
            final_balance = final_account["steam_balance"]

            if initial_balance != final_balance:
                balance_changed_count += 1
                pass_value = final_account.get("pass_value")
                passes_to_buy_str = "N/A (pass value not set)"

                # Calculate how many passes can be bought
                if pass_value and pass_value > 0:
                    passes_to_buy = int(final_balance / pass_value)
                    passes_to_buy_str = str(passes_to_buy)

                logger.info(
                    f"✅ Account '{username}': Balance changed! "
                    f"New Balance: {final_balance:.2f} {final_account.get('currency', '')}. "
                    f"Passes to Buy: {passes_to_buy_str}"
                )

        if balance_changed_count == 0:
            logger.info("No wallet balance changes were detected for any account.")
        else:
            logger.success(
                f"Detected balance changes for {balance_changed_count} account(s)."
            )

    except Exception as e:
        logger.error(f"Could not check for balance changes due to an error: {e}")

    # Final stage 1 summary
    print("\n")
    all_successful = all(stage_results[stage]["success"] for stage in stage_results)

    if all_successful:
        logger.success(
            "Stage 1 completed successfully - All components (Items lister, Farm list updater) completed successfully."
        )
    else:
        failed_stages = []
        for stage, result in stage_results.items():
            if not result["success"]:
                failed_stages.append(
                    f"{stage.replace('_', ' ').title()}: {result['error']}"
                )

        logger.error(
            f"Stage 1 completed with failures. Failed components: {'; '.join(failed_stages)}"
        )


if __name__ == "__main__":
    asyncio.run(main())
