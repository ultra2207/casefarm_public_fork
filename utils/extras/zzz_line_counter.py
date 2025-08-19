import os
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


def count_lines(file_path) -> int:
    """Counts the number of lines in a file after removing empty lines from the top and bottom."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as file:
            lines = file.readlines()

        # Remove empty lines from the top
        while lines and not lines[0].strip():
            lines.pop(0)

        # Remove empty lines from the bottom
        while lines and not lines[-1].strip():
            lines.pop()

        # Count remaining lines
        return len(lines)
    except Exception as e:
        logger.error(f"Could not read file {file_path}: {e}")
        return 0


def count_python_lines(directory) -> list:
    """
    Walks through a directory, counts non-empty lines in all .py files,
    and ignores the .venv and node_modules folders. Collects data in a list.
    """
    file_line_counts = []
    for root, dirs, files in os.walk(directory):
        # Skip .venv directory
        if ".venv" in dirs:
            dirs.remove(".venv")

        # Skip node_modules directory
        if "node_modules" in dirs:
            dirs.remove("node_modules")

        if "archive" in dirs:
            dirs.remove(
                "archive"
            )  # not to be counted or printed as these are irrelevant

        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                try:
                    lines = count_lines(file_path)
                    file_line_counts.append((file_path, lines))
                except Exception as e:
                    logger.error(f"Error processing file {file_path}: {e}")

    return file_line_counts


def line_counter_main() -> None:
    directory = r"C:\Users\Sivasai\Documents\GitHub\CaseFarm"

    if os.path.isdir(directory):
        file_line_counts = count_python_lines(directory)
        sorted_file_line_counts = sorted(
            file_line_counts, key=lambda x: x[1], reverse=True
        )

        # Print all files except __init__.py
        for file_path, lines in sorted_file_line_counts:
            if os.path.basename(file_path) != "__init__.py":
                logger.info(f"{file_path}: {lines} lines")

        total_project_lines = sum(lines for _, lines in file_line_counts)
        print("\n")
        logger.info(f"Total lines in the project's Python files: {total_project_lines}")
    else:
        logger.error(f"Error: Directory not found - {directory}")


if __name__ == "__main__":
    line_counter_main()
