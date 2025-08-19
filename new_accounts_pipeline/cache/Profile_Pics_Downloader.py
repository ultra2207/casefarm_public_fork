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


import os

from cheesechaser.datapool import SafebooruWebpDataPool


def download_safebooru_images(batch_size: int) -> None:
    """
    Downloads images from SafebooruWebpDataPool based on the last stored ID.

    Args:
        batch_size (int): The number of new images to download.
    """
    dst_dir = r"C:\Pics\Unused"

    id_file = os.path.join(dst_dir, "last_downloaded_id.txt")

    hf_token = "blank"  # Replace with your actual Hugging Face token

    # Ensure destination directory exists
    os.makedirs(dst_dir, exist_ok=True)
    logger.trace(f"Ensured destination directory exists: {dst_dir}")

    # Read last downloaded ID
    if os.path.exists(id_file):
        with open(id_file, "r") as f:
            last_id = int(f.read().strip())
        logger.debug(f"Read last downloaded ID: {last_id}")
    else:
        last_id = 0  # Default starting ID
        logger.debug("No previous ID found, starting from 0")

    new_start = last_id
    new_end = int(
        new_start + (batch_size * 1.5)
    )  # Get 1.5x the batch size to account for missing images

    # Initialize data pool
    pool = SafebooruWebpDataPool(hf_token=hf_token)
    logger.debug("Initialized SafebooruWebpDataPool")

    # Download images
    logger.info(f"Starting download of images from ID {new_start} to {new_end}")
    pool.batch_download_to_directory(
        resource_ids=range(new_start, new_end), dst_dir=dst_dir
    )

    # Update the last downloaded ID
    with open(id_file, "w") as f:
        f.write(str(new_start + batch_size - 1))

    logger.info(
        f"Downloaded images from {new_start} to {new_end}. Updated last_downloaded_id.txt to {new_start + batch_size}."
    )


# Example usage
if __name__ == "__main__":
    batch_size = 200

    download_safebooru_images(batch_size)
