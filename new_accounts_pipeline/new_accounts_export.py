import csv
import sqlite3
import sys
from typing import Literal

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


def export_accounts_farmlabs(steam_usernames=None) -> Literal["farmlabs_export.csv"]:
    db_path = r"C:\Users\Sivasai\Documents\GitHub\CaseFarm\database\db\database.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    if steam_usernames:
        placeholders = ",".join("?" for _ in steam_usernames)
        query = f"""SELECT steam_username, steam_password, steam_shared_secret, steam_identity_secret
                    FROM accounts
                    WHERE steam_username IN ({placeholders})"""
        cursor.execute(query, steam_usernames)
    else:
        query = """SELECT steam_username, steam_password, steam_shared_secret, steam_identity_secret
                   FROM accounts
                   WHERE prime = 1"""
        cursor.execute(query)

    csv_file_path = r"C:\Users\Sivasai\Documents\GitHub\CaseFarm\new_accounts_pipeline\farmlabs_export.csv"

    with open(csv_file_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["username", "password", "shared_secret", "identity_secret"])
        writer.writerows(cursor.fetchall())

    conn.close()

    return csv_file_path


def create_standard_arb_export(
    steam_usernames=None,
) -> Literal["standard_arb_export.csv"]:
    db_path = r"C:\Users\Sivasai\Documents\GitHub\CaseFarm\database\db\database.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    if steam_usernames:
        placeholders = ",".join("?" for _ in steam_usernames)
        query = f"""SELECT steam_username, steam_password
                    FROM accounts
                    WHERE steam_username IN ({placeholders})"""
        cursor.execute(query, steam_usernames)
    else:
        query = """SELECT steam_username, steam_password
        FROM accounts
        WHERE is_armoury = 1 
        OR currency != 'USD'
        """
        cursor.execute(query)

    txt_file_path = r"C:\Users\Sivasai\Documents\GitHub\CaseFarm\new_accounts_pipeline\standard_arb_export.txt"

    with open(txt_file_path, "w", encoding="utf-8") as file:
        for username, password in cursor.fetchall():
            file.write(f"{username}:{password}\n")

    conn.close()

    csv_file_path = txt_file_path  # To keep the return value and logger consistent

    return csv_file_path


if __name__ == "__main__":
    # Example usage
    output_file_arb = create_standard_arb_export()
    logger.info("Files exported successfully.")
