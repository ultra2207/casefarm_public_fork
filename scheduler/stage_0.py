# The optional running of the schedule generator (becomes necessary if using scheuduler to autorun the farm)
# This need not be run if stage_1 is run manually
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

from utils.schedule_generator import generate_schedule

if __name__ == "__main__":
    predicted_times = asyncio.run(generate_schedule())
