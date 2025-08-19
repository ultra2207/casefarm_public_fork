import secrets
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


def generate_proxies(num_proxies: int = 50, session_time: int = 20) -> list[str]:
    """
    Generates dynamic proxies in the specified format with secure session strings.

    Args:
        num_proxies: Number of proxies to generate (default: 50)
        session_time: Session duration in minutes (default: 20)

    Returns:
        List of proxy strings in format:
        http://ultra2207_pool-dc_session-{16char_hex}_sesstime-{time}:Riya1588789@proxy.suborbit.al:1337
    """
    proxies = []
    for _ in range(num_proxies):
        # Generate 16-character lowercase alphanumeric session string
        session_id = secrets.token_hex(8)  # 8 bytes = 16 hex characters

        proxy = (
            f"http://ultra2207_pool-dc_session-{session_id}_sesstime-{session_time}:"
            f"Riya1588789@proxy.suborbit.al:1337"
        )
        proxies.append(proxy)

    return proxies


def generate_proxy(session_time: int = 20) -> str:
    return generate_proxies(num_proxies=1, session_time=session_time)[0]


# Example usage
if __name__ == "__main__":
    proxy = generate_proxy()
    logger.info(proxy)
