# This stage will involve monitoring the accounts for pass completion, then cancelling the farm jobs and then finally
# closing the passes and then using the reccomender to figure out which item to redeem, that item is then redeemed.
# Note: this stage is not complete, for now only has reccomender

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

from tenacity import retry, stop_after_attempt, wait_fixed

from accounts_manager.utils.armoury_redemption_reccomender import reccomender

# Retry decorator for core functions
# Retries on exceptions (default behavior) and when function returns False
retry_core_function = retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(3),  # Wait 3 seconds between retries
    reraise=True,
)


@retry_core_function
async def run_reccomender() -> bool:
    logger.info("Running redemption reccomender...")
    print("\n")
    item = await reccomender()
    if not item:
        logger.warning("Reccomender returned no item")
        return False
    return True


async def main() -> None:
    try:
        success = await run_reccomender()
        if not success:
            logger.error("Stage 2 did not complete successfully")
            sys.exit(1)
    except Exception:
        logger.exception("Unhandled error in stage 2")
        sys.exit(1)
    print("\n")
    logger.info(
        "Stage 2 (partial stage, only has redemption reccomender with everything else manual) completed successfully."
    )


if __name__ == "__main__":
    asyncio.run(main())
