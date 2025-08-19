# For this code the database is not updated. Instead, the bot job is updated and run immediately and then when its refleteed on farmlabs as completed, the items database is updated.
import asyncio
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


async def update_claim_tasks(usernames):
    # for each username in usernames, it updates the claim task using the recommended indices
    return True


# still needs work
async def main():
    result = await update_claim_tasks()
    logger.info(result)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
