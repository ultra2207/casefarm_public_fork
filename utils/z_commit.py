import os
import subprocess
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


from extras.zzz_line_counter import line_counter_main

# Use this to update all dependencies, clean up the code and commit and push the repo with the commit message "Dependencies updated".
# Should be run either weekly or monthly
# to update nodejs call its function in main using run_nodejs_upgrade() while running vscode in admin mode


def run_command_in_directory(directory: str, command: str) -> None:
    if not os.path.isdir(directory):
        logger.error(f"Directory not found: {directory}")
        return
    original_dir = os.getcwd()
    try:
        os.chdir(directory)
        logger.info(f"Running '{command}' in {directory}")
        subprocess.call(command, shell=True)
    except Exception as e:
        logger.error(f"Error in {directory}: {e}")
    finally:
        os.chdir(original_dir)


def run_bun_updates(directories: list[str]) -> None:
    subprocess.call("bun upgrade", shell=True)  # First upgrade bun itself

    for directory in directories:
        run_command_in_directory(directory, "bun update")  # Then update dependencies


def run_cargo_updates(directories: list[str]) -> None:
    subprocess.run("rustup update", shell=True)  # Update rust itself
    subprocess.run(
        "cargo install-update -a", shell=True
    )  # Update all globally installed cargo packages

    for directory in directories:
        run_command_in_directory(directory, "cargo update")


def run_nodejs_upgrade() -> None:
    """Contains all operations to be performed with admin privileges"""

    try:
        subprocess.run(
            ["choco", "upgrade", "nodejs"],
        )

    except subprocess.CalledProcessError as e:
        logger.error(f"Error running Chocolatey: {e}")
        logger.error(f"Output: {e.stdout}")
        logger.error(f"Error: {e.stderr}")


def commit_and_push_changes(
    repo_dir: str, commit_message: str = "dependencies updated"
) -> bool:
    """
    Add, commit, and push all changes in the git repository
    """
    if not os.path.isdir(repo_dir):
        logger.error(f"Repository directory not found: {repo_dir}")
        return False

    original_dir = os.getcwd()
    try:
        os.chdir(repo_dir)

        # Check if there are any changes to commit
        result = subprocess.run(
            "git status --porcelain", shell=True, capture_output=True, text=True
        )
        if not result.stdout.strip():
            logger.info("No changes to commit.")
            return False

        # Add all changes
        logger.info(f"Adding all changes in {repo_dir}")
        subprocess.call("git add .", shell=True)

        # Commit changes
        logger.info(f"Committing changes with message: '{commit_message}'")
        subprocess.call(f'git commit -m "{commit_message}"', shell=True)

        # Push changes to remote repository
        logger.info("Pushing changes to remote repository...")
        push_result = subprocess.run(
            "git push", shell=True, capture_output=True, text=True
        )
        if push_result.returncode != 0:
            logger.error(f"Error pushing changes: {push_result.stderr}")
            return False

        logger.success("Changes committed and pushed successfully.")
        print("\n\n")
        line_counter_main()
        return True

    except Exception as e:
        logger.error(f"Error in git operations: {e}")
        return False

    finally:
        os.chdir(original_dir)


def main() -> None:
    # Directories for bun update
    bun_dirs: list[str] = [
        r"C:\Users\Sivasai\Documents\GitHub\CaseFarm\manager\webapp",
        r"C:\Users\Sivasai\Documents\GitHub\CaseFarm\manager\clients\pc_client",
        r"C:\Users\Sivasai\Documents\GitHub\CaseFarm\manager\clients\vm_client",
        r"C:\Users\Sivasai\Documents\GitHub\CaseFarm\manager\clients\dashboard",
    ]

    logger.info("Starting bun updates...")
    run_bun_updates(bun_dirs)

    # Directories for cargo update
    cargo_dirs: list[str] = [
        r"C:\Users\Sivasai\Documents\GitHub\CaseFarm\manager\clients\dashboard\src-tauri",
        r"C:\Users\Sivasai\Documents\GitHub\CaseFarm\manager\clients\pc_client\src-tauri",
        r"C:\Users\Sivasai\Documents\GitHub\CaseFarm\manager\clients\vm_client\src-tauri",
    ]

    logger.info("Starting cargo updates...")
    run_cargo_updates(cargo_dirs)

    main_dir: str = r"C:\Users\Sivasai\Documents\GitHub\CaseFarm"
    logger.info("Starting uv updates...")
    run_command_in_directory(main_dir, "uv sync --upgrade")

    logger.info("All updates completed.")

    logger.info("Running ruff and codespell for preprocessing...")

    run_command_in_directory(main_dir, "ruff format .")
    run_command_in_directory(main_dir, "ruff check --fix --extend-select=I .")
    run_command_in_directory(main_dir, "codespell -w")

    logger.info("Committing and pushing changes to git repository...")
    commit_and_push_changes(main_dir)

    logger.trace("Update and maintenance process completed")


if __name__ == "__main__":
    main()
