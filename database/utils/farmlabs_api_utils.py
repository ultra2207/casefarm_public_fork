import sqlite3
import sys
from typing import Any

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


# database files
DB_FILE = r"C:\Users\Sivasai\Documents\GitHub\CaseFarm\database\db\database.db"
PRICES_DB_PATH = r"C:\Users\Sivasai\Documents\GitHub\CaseFarm\database\db\prices.db"


def get_vm_by_username(steam_username: str) -> list[dict[str, Any]]:
    """Get VMs for an account."""
    with sqlite3.connect(DB_FILE) as conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT m.*
                FROM machines m
                JOIN bot_jobs bj ON m.current_bot_job = bj.bot_job_id
                JOIN accounts a ON bj.bot_id = a.bot_id
                WHERE a.steam_username = ?
            """,
                (steam_username,),
            )
            rows = cursor.fetchall()
            columns = [description[0] for description in cursor.description]

            # Convert rows to structured JSON
            vms: list[dict[str, Any]] = []
            for row in rows:
                vm = dict(zip(columns, row))
                vms.append(vm)

            logger.trace(f"Retrieved {len(vms)} VMs for account {steam_username}")
            return vms
        except sqlite3.Error as e:
            logger.error(f"Error fetching VMs: {e}")
            return []


def set_bot_id(steam_username: str, bot_id: str) -> bool:
    """Set bot_id for an account."""
    with sqlite3.connect(DB_FILE) as conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE accounts SET bot_id = ? WHERE steam_username = ?",
                (bot_id, steam_username),
            )
            conn.commit()
            logger.trace(f"Set bot_id {bot_id} for account {steam_username}")
            return True
        except sqlite3.Error as e:
            logger.error(f"Error setting bot_id: {e}")
            return False


def add_vm_initial(name: str) -> bool:
    """Add a new VM with only a name."""
    with sqlite3.connect(DB_FILE) as conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO machines (name)
                VALUES (?)
            """,
                (name,),
            )
            conn.commit()
            logger.info(f"New VM added with name '{name}'.")
            return True
        except sqlite3.Error as e:
            logger.error(f"Error adding VM: {e}")
            return False


def update_vm(
    id: int,
    linked: bool | None = None,
    current_bot_job: str | None = None,
    status: str | None = None,
) -> bool:
    """Update a VM."""
    with sqlite3.connect(DB_FILE) as conn:
        try:
            cursor = conn.cursor()
            updates: list[str] = []
            params: list[Any] = []

            if linked is not None:
                updates.append("linked = ?")
                params.append(linked)
            if current_bot_job:
                updates.append("current_bot_job = ?")
                params.append(current_bot_job)
            if status:
                if status not in ["Online", "Offline"]:
                    logger.warning(f"Invalid status: {status}")
                    raise ValueError("Invalid status")
                updates.append("status = ?")
                params.append(status)

            if not updates:
                logger.warning("No fields to update.")
                return False

            update_sql = "UPDATE machines SET " + ", ".join(updates) + " WHERE id = ?"
            params.append(id)

            cursor.execute(update_sql, params)
            conn.commit()
            logger.trace(f"Updated VM {id} with {', '.join(updates)}")
            return True
        except sqlite3.Error as e:
            logger.error(f"Error updating VM: {e}")
            return False


def delete_vm(id: int) -> bool:
    """Delete a VM."""
    with sqlite3.connect(DB_FILE) as conn:
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM machines WHERE id = ?", (id,))
            conn.commit()
            logger.info(f"Deleted VM with ID {id}")
            return True
        except sqlite3.Error as e:
            logger.error(f"Error deleting VM: {e}")
            return False


def update_bot_job(
    bot_job_id: str,
    start_time: str | None = None,
    completion_time: str | None = None,
    status: str | None = None,
) -> bool:
    """Update a bot job."""
    with sqlite3.connect(DB_FILE) as conn:
        try:
            cursor = conn.cursor()
            updates: list[str] = []
            params: list[Any] = []

            if start_time:
                updates.append("start_time = ?")
                params.append(start_time)
            if completion_time:
                updates.append("completion_time = ?")
                params.append(completion_time)
            if status:
                if status not in ["Completed", "Pending", "In Progress", "Cancelled"]:
                    logger.warning(f"Invalid status: {status}")
                    raise ValueError("Invalid status")
                updates.append("status = ?")
                params.append(status)

            if not updates:
                logger.warning("No fields to update.")
                return False

            update_sql = (
                "UPDATE bot_jobs SET " + ", ".join(updates) + " WHERE bot_job_id = ?"
            )
            params.append(bot_job_id)

            cursor.execute(update_sql, params)
            conn.commit()
            logger.trace(f"Updated bot job {bot_job_id} with {', '.join(updates)}")
            return True
        except sqlite3.Error as e:
            logger.error(f"Error updating bot job: {e}")
            return False


def cancel_bot_job_db(bot_job_id: str) -> bool:
    """Cancel a bot job by setting its status to 'Cancelled'."""
    with sqlite3.connect(DB_FILE) as conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE bot_jobs SET status = 'Cancelled' WHERE bot_job_id = ?",
                (bot_job_id,),
            )
            conn.commit()
            rows_affected = cursor.rowcount
            if rows_affected > 0:
                logger.info(f"Bot job {bot_job_id} cancelled successfully.")
                return True
            else:
                logger.warning(f"Bot job {bot_job_id} not found.")
                return False
        except sqlite3.Error as e:
            logger.error(f"Error cancelling bot job: {e}")
            return False


def get_bot_jobs_by_username(steam_username: str) -> list[dict[str, Any]]:
    """Get bot jobs for an account."""
    with sqlite3.connect(DB_FILE) as conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT bj.*
                FROM bot_jobs bj
                JOIN accounts a ON bj.bot_id = a.bot_id
                WHERE a.steam_username = ?
            """,
                (steam_username,),
            )
            rows = cursor.fetchall()
            columns = [description[0] for description in cursor.description]

            # Convert rows to structured JSON
            bot_jobs: list[dict[str, Any]] = []
            for row in rows:
                bot_job = dict(zip(columns, row))
                bot_jobs.append(bot_job)

            logger.trace(
                f"Retrieved {len(bot_jobs)} bot jobs for account {steam_username}"
            )
            return bot_jobs
        except sqlite3.Error as e:
            logger.error(f"Error fetching bot jobs: {e}")
            return []


def add_bot_job(bot_job_id: str, bot_id: str, bot_username: str, type: str) -> bool:
    """Add a new bot job."""
    with sqlite3.connect(DB_FILE) as conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO bot_jobs (bot_job_id, bot_id, bot_username, type)
                VALUES (?, ?, ?, ?)
            """,
                (bot_job_id, bot_id, bot_username, type),
            )
            conn.commit()
            logger.info(
                f"Added new bot job {bot_job_id} of type {type} for bot {bot_id}"
            )
            return True
        except sqlite3.Error as e:
            logger.error(f"Error adding bot job: {e}")
            return False


def get_db_connection() -> sqlite3.Connection:
    """Establish a connection to the database."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


# CREATE functions


def create_bot_job(
    bot_job_id: str,
    bot_username: str,
    job_type: str,
    bot_id: str | None = None,
    assigned_machine: str | None = None,
    created_at: str | None = None,
    start_time: str | None = None,
    completion_time: str | None = None,
    status: str | None = None,
) -> str:
    """
    Create a new bot job in the database.

    Args:
        bot_username: The username of the bot (required) - This is the primary foreign key
            used to reference the accounts table
        job_type: The type of job to create (required)
        bot_id: The ID of the bot
            Default: NULL if not provided (bot_username is the preferred foreign key)
        assigned_machine: The machine assigned to this job
            Default: NULL if not provided
        created_at: Custom creation timestamp in ISO format
            Default: CURRENT_TIMESTAMP if not provided
        start_time: Custom start timestamp in ISO format
            Default: NULL if not provided
        completion_time: Custom completion timestamp in ISO format
            Default: NULL if not provided
        status: Job status ('Completed', 'Pending', 'In Progress', 'Cancelled')
            Default: 'Pending' if not provided

    Returns:
        The newly created bot_job_id

    Note:
        - bot_username is the preferred foreign key for referencing the accounts table
        - If optional fields are not provided, the database will use its default values:
        - bot_id: NULL
        - assigned_machine: NULL
        - created_at: CURRENT_TIMESTAMP
        - start_time: NULL
        - completion_time: NULL
        - status: 'Pending'
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Build the query dynamically based on which fields are provided
    fields = ["bot_job_id", "bot_username", "type"]
    values = [bot_job_id, bot_username, job_type]

    if bot_id is not None:
        fields.append("bot_id")
        values.append(bot_id)

    if assigned_machine is not None:
        fields.append("assigned_machine")
        values.append(assigned_machine)

    if created_at is not None:
        fields.append("created_at")
        values.append(created_at)

    if start_time is not None:
        fields.append("start_time")
        values.append(start_time)

    if completion_time is not None:
        fields.append("completion_time")
        values.append(completion_time)

    if status is not None:
        fields.append("status")
        values.append(status)

    placeholders = ", ".join(["?"] * len(values))
    field_names = ", ".join(fields)

    query = f"INSERT INTO bot_jobs ({field_names}) VALUES ({placeholders})"

    cursor.execute(query, values)
    conn.commit()
    conn.close()

    logger.trace(
        f"Created new bot job {bot_job_id} of type {job_type} for {bot_username}"
    )
    return bot_job_id


def get_bot_job(bot_job_id: str) -> dict[str, Any] | None:
    """
    Retrieve a specific bot job by ID.

    Args:
        bot_job_id: The ID of the bot job to retrieve

    Returns:
        dictionary containing job details or None if not found
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM bot_jobs WHERE bot_job_id = ?", (bot_job_id,))
    job = cursor.fetchone()

    conn.close()

    if job:
        logger.trace(f"Retrieved bot job {bot_job_id}")
        return dict(job)

    logger.trace(f"Bot job {bot_job_id} not found")
    return None


def get_bot_jobs_by_status(status: str) -> list[dict[str, Any]]:
    """
    Retrieve all bot jobs with a specific status.

    Args:
        status: The status to filter by ('Completed', 'Pending', 'In Progress', 'Cancelled')

    Returns:
        list of dictionaries containing job details
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM bot_jobs WHERE status = ?", (status,))
    jobs = cursor.fetchall()

    conn.close()

    result = [dict(job) for job in jobs]
    logger.trace(f"Retrieved {len(result)} bot jobs with status '{status}'")
    return result


def get_bot_jobs_by_bot_id(bot_id: str) -> list[dict[str, Any]]:
    """
    Retrieve all jobs for a specific bot.

    Args:
        bot_id: The ID of the bot

    Returns:
        list of dictionaries containing job details
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM bot_jobs WHERE bot_id = ?", (bot_id,))
    jobs = cursor.fetchall()

    conn.close()

    result = [dict(job) for job in jobs]
    logger.trace(f"Retrieved {len(result)} bot jobs for bot ID {bot_id}")
    return result


def get_pending_jobs() -> list[dict[str, Any]]:
    """
    Retrieve all pending jobs.

    Returns:
        list of dictionaries containing pending job details
    """
    return get_bot_jobs_by_status("Pending")


def get_in_progress_jobs() -> list[dict[str, Any]]:
    """
    Retrieve all in-progress jobs.

    Returns:
        list of dictionaries containing in-progress job details
    """
    return get_bot_jobs_by_status("In Progress")


def get_jobs_by_machine(machine_id: str) -> list[dict[str, Any]]:
    """
    Retrieve all jobs assigned to a specific machine.

    Args:
        machine_id: The ID of the machine

    Returns:
        list of dictionaries containing job details
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM bot_jobs WHERE assigned_machine = ?", (machine_id,))
    jobs = cursor.fetchall()

    conn.close()

    result = [dict(job) for job in jobs]
    logger.trace(f"Retrieved {len(result)} bot jobs for machine {machine_id}")
    return result


def update_job_status(
    bot_job_id: str,
    status: str,
    start_time: str | None = None,
    completion_time: str | None = None,
    assigned_machine: str | None = None,
) -> bool:
    """
    Update the status and related fields of a bot job.

    Args:
        bot_job_id: The ID of the bot job
        status: The new status ('Completed', 'Pending', 'In Progress', 'Cancelled')
        start_time: (Optional) Custom start timestamp (ISO format)
        completion_time: (Optional) Custom completion timestamp (ISO format)
        assigned_machine: (Optional) Machine to assign to this job

    Returns:
        True if successful, False otherwise
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Build the query dynamically based on which fields are provided
    update_fields = ["status = ?"]
    update_values = [status]

    if start_time is not None:
        update_fields.append("start_time = ?")
        update_values.append(start_time)
    elif status == "In Progress" and start_time is None:
        update_fields.append("start_time = CURRENT_TIMESTAMP")

    if completion_time is not None:
        update_fields.append("completion_time = ?")
        update_values.append(completion_time)
    elif status == "Completed" and completion_time is None:
        update_fields.append("completion_time = CURRENT_TIMESTAMP")

    if assigned_machine is not None:
        update_fields.append("assigned_machine = ?")
        update_values.append(assigned_machine)

    update_clause = ", ".join(update_fields)
    update_values.append(bot_job_id)  # For the WHERE clause

    try:
        cursor.execute(
            f"UPDATE bot_jobs SET {update_clause} WHERE bot_job_id = ?", update_values
        )
        conn.commit()
        success = cursor.rowcount > 0
        if success:
            logger.trace(f"Updated job {bot_job_id} status to {status}")
        else:
            logger.warning(f"Failed to update job {bot_job_id} - job not found")
    except sqlite3.Error as e:
        logger.error(f"Error updating job status: {e}")
        success = False
    finally:
        conn.close()

    return success


def update_existing_bot_job(
    bot_job_id: str,
    bot_username: str,
    job_type: str,
    assigned_machine: str | None = None,
    created_at: str | None = None,
    start_time: str | None = None,
    completion_time: str | None = None,
    status: str | None = None,
) -> bool:
    """
    Check if a bot job exists and update it if it does.

    Args:
        bot_job_id: The ID of the bot job
        bot_username: The username of the bot
        job_type: The type of job
        assigned_machine: The machine assigned to this job
        created_at: Creation timestamp
        start_time: Start timestamp
        completion_time: Completion timestamp
        status: Job status

    Returns:
        True if job was updated, False if job doesn't exist
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if the job exists
    cursor.execute(
        "SELECT bot_job_id FROM bot_jobs WHERE bot_job_id = ?", (bot_job_id,)
    )
    job_exists = cursor.fetchone() is not None

    if job_exists:
        # Build the update query
        updates = []
        params = []

        if bot_username:
            updates.append("bot_username = ?")
            params.append(bot_username)

        if job_type:
            updates.append("type = ?")
            params.append(job_type)

        if assigned_machine is not None:
            updates.append("assigned_machine = ?")
            params.append(assigned_machine)

        if created_at is not None:
            updates.append("created_at = ?")
            params.append(created_at)

        if start_time is not None:
            updates.append("start_time = ?")
            params.append(start_time)

        if completion_time is not None:
            updates.append("completion_time = ?")
            params.append(completion_time)

        if status is not None:
            updates.append("status = ?")
            params.append(status)

        if updates:
            update_sql = (
                "UPDATE bot_jobs SET " + ", ".join(updates) + " WHERE bot_job_id = ?"
            )
            params.append(bot_job_id)

            cursor.execute(update_sql, params)
            conn.commit()
            logger.trace(f"Updated existing bot job {bot_job_id}")

        conn.close()
        return True

    logger.trace(f"Bot job {bot_job_id} not found for update")
    conn.close()
    return False


# DELETE FUNCTIONS


def delete_bot_job(bot_job_id: str) -> bool:
    """
    Delete a bot job from the database.

    Args:
        bot_job_id: The ID of the bot job to delete

    Returns:
        True if successful, False otherwise
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM bot_jobs WHERE bot_job_id = ?", (bot_job_id,))
        conn.commit()
        success = cursor.rowcount > 0
        if success:
            logger.info(f"Deleted bot job {bot_job_id}")
        else:
            logger.warning(f"Failed to delete bot job {bot_job_id} - job not found")
        return success
    except sqlite3.Error as e:
        logger.error(f"Error deleting bot job {bot_job_id}: {e}")
        return False
    finally:
        conn.close()


def delete_completed_jobs() -> int:
    """
    Delete all completed jobs.

    Returns:
        Number of jobs deleted
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM bot_jobs WHERE status = 'Completed'")
        deleted_count = cursor.rowcount
        conn.commit()
        logger.info(f"Deleted {deleted_count} completed bot jobs")
        return deleted_count
    except sqlite3.Error as e:
        logger.error(f"Error deleting completed jobs: {e}")
        return 0
    finally:
        conn.close()


# UTILITY FUNCTIONS


def get_job_count_by_status() -> dict[str, int]:
    """
    Get a count of jobs grouped by status.

    Returns:
        dictionary with status as key and count as value
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT status, COUNT(*) as count FROM bot_jobs GROUP BY status")
        results = cursor.fetchall()
        conn.close()

        counts = {row["status"]: row["count"] for row in results}
        logger.trace(f"Job counts by status: {counts}")
        return counts
    except sqlite3.Error as e:
        logger.error(f"Error getting job counts: {e}")
        return {}
    finally:
        if conn:
            conn.close()


def get_avg_job_completion_time() -> float:
    """
    Calculate the average time to complete jobs (in seconds).

    Returns:
        Average completion time in seconds
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT AVG(JULIANDAY(completion_time) - JULIANDAY(start_time)) * 86400 as avg_time
            FROM bot_jobs
            WHERE status = 'Completed' AND start_time IS NOT NULL AND completion_time IS NOT NULL
            """
        )
        result = cursor.fetchone()
        avg_time = (
            result["avg_time"] if result and result["avg_time"] is not None else 0.0
        )
        logger.trace(f"Average job completion time: {avg_time:.2f} seconds")
        return avg_time
    except sqlite3.Error as e:
        logger.error(f"Error calculating average completion time: {e}")
        return 0.0
    finally:
        conn.close()


def update_account_details_farmlabs(
    steam_username: str,
    bot_id: str | None = None,
    level: str | int | None = None,
    xp: str | int | None = None,
    status: str | None = None,
) -> bool:
    """
    Updates account details in the accounts table using steam_username as reference.

    Args:
        steam_username: The steam username to identify the account
        bot_id: Bot ID to update
        level: XP level to update
        xp: XP value to update
        status: Status to update

    Returns:
        True if update was successful, False otherwise
    """
    conn = None
    try:
        # Connect to the database
        conn = sqlite3.connect(DB_FILE)  # Fixed DB_FILE reference
        cursor = conn.cursor()

        # Check if the account exists
        cursor.execute(
            "SELECT 1 FROM accounts WHERE steam_username = ?", (steam_username,)
        )
        if not cursor.fetchone():
            logger.warning(
                f"Account with steam_username '{steam_username}' does not exist"
            )
            return False

        # Build the update query dynamically based on provided parameters
        update_parts = []
        params = []

        if bot_id is not None:
            update_parts.append("bot_id = ?")
            params.append(bot_id)

        if level is not None:
            update_parts.append("xp_level = ?")
            params.append(int(level))

        if xp is not None:
            update_parts.append("xp = ?")
            params.append(xp)

        if status is not None:
            update_parts.append("status = ?")
            params.append(status)

        if not update_parts:
            logger.warning("No fields to update")
            return False

        # Complete the query
        query = (
            f"UPDATE accounts SET {', '.join(update_parts)} WHERE steam_username = ?"
        )
        params.append(steam_username)

        # Execute the update
        cursor.execute(query, params)

        # Commit the changes
        conn.commit()
        logger.info(f"Successfully updated account details for {steam_username}")
        return True

    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        return False
    finally:
        if conn:
            conn.close()


def update_vms_database(
    name: str, id: str, status: str, current_bot_job: str | None = None
) -> bool:
    """
    Update a VM in the database or create a new one if it doesn't exist.

    Args:
        name: The name of the VM
        id: The ID of the VM
        status: The VM status ('Online' or 'Offline') - required
        current_bot_job: The current bot job ID, if any

    Returns:
        True if operation was successful, False otherwise
    """
    with sqlite3.connect(DB_FILE) as conn:
        try:
            cursor = conn.cursor()

            # Normalize status to ensure it's properly capitalized
            status = status.capitalize()
            if status not in ["Online", "Offline"]:
                logger.warning(
                    f"Invalid status '{status}'. Must be 'Online' or 'Offline'."
                )
                return False

            # Check if VM exists by ID
            cursor.execute("SELECT id, name FROM machines WHERE id = ?", (id,))
            vm_by_id = cursor.fetchone()

            # Check if VM exists by name
            cursor.execute("SELECT id, name FROM machines WHERE name = ?", (name,))
            vm_by_name = cursor.fetchone()

            # Case 1: VM exists by ID
            if vm_by_id:
                logger.info(f"Updating VM with ID {id}")
                update_query = """
                    UPDATE machines 
                    SET name = ?, current_bot_job = ?, status = ?
                    WHERE id = ?
                """
                cursor.execute(update_query, (name, current_bot_job, status, id))

            # Case 2: VM exists by name but with different ID
            elif vm_by_name:
                existing_id = (
                    vm_by_name if isinstance(vm_by_name, tuple) else vm_by_name["id"]
                )
                logger.info(
                    f"Updating VM with name {name} (existing ID: {existing_id})"
                )
                update_query = """
                    UPDATE machines 
                    SET id = ?, current_bot_job = ?, status = ?
                    WHERE name = ?
                """
                cursor.execute(update_query, (id, current_bot_job, status, name))

            # Case 3: VM doesn't exist at all
            else:
                logger.info(f"Creating new VM with name {name} and ID {id}")
                insert_query = """
                    INSERT INTO machines (id, name, current_bot_job, status)
                    VALUES (?, ?, ?, ?)
                """
                cursor.execute(insert_query, (id, name, current_bot_job, status))

            conn.commit()
            logger.info(f"Successfully updated database for VM {name} (ID: {id})")
            return True

        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
            return False
