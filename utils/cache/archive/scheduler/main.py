import asyncio
import json
import os
import sys
from pathlib import Path

import yaml


def load_config():
    config_path = r"C:\Users\Sivasai\Documents\GitHub\CaseFarm\config.yaml"
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    return config


_config = load_config()
ROOT_DIR = _config["ROOT_DIR"]
sys.path.insert(0, ROOT_DIR)

import time

from utils.logger import get_custom_logger

logger = get_custom_logger()

import atexit
from datetime import datetime

from apscheduler.jobstores.base import ConflictingIdError, JobLookupError
from sqlalchemy import Table
from tenacity import AsyncRetrying, Retrying, stop_after_attempt, wait_fixed

from database import get_all_steam_accounts
from utils.cache.archive.items_trader_pua_shelved import run_items_trader
from utils.schedule_generator import generate_schedule
from utils.steam_items_lister import items_lister


# Load constants from config.yaml
def load_config() -> dict:
    config_path = r"C:\Users\Sivasai\Documents\GitHub\CaseFarm\config.yaml"
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    return config


_config = load_config()
DEFAULT_SCHEDULE_GENERATION_TIME = _config.get(
    "DEFAULT_SCHEDULE_GENERATION_TIME", "7 PM"
)


def retry_call(func, *args, retries=3, delay=1.0, **kwargs):
    """Call any function with retry logic."""
    if asyncio.iscoroutinefunction(func):

        async def async_wrapper():
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(retries), wait=wait_fixed(delay)
            ):
                with attempt:
                    return await func(*args, **kwargs)

        return async_wrapper()
    else:
        retryer = Retrying(
            stop=stop_after_attempt(retries), wait=wait_fixed(delay), reraise=True
        )
        return retryer(func, *args, **kwargs)


from datetime import time as dt_time

import pytz
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED, EVENT_JOB_MISSED
from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger


# STANDALONE JOB FUNCTIONS - These don't reference any class instances
async def standalone_schedule_generation_task():
    """Standalone schedule generation task to avoid pickling issues"""
    logger.info("=== Starting standalone schedule generation task ===")

    try:
        logger.info("Time match detected! Proceeding with schedule generation...")

        logger.info("Calling generate_schedule function with retry logic")
        success = await retry_call(generate_schedule)

        if success:
            logger.info("Schedule generation completed successfully")
            logger.info("Proceeding to schedule selling task")
            await standalone_schedule_selling_task()
            logger.info("Selling task scheduling completed")
            return True
        else:
            logger.error("Schedule generation failed")
            return False

    except Exception as e:
        logger.error(f"Critical error in schedule generation task: {e}")
        logger.exception("Full traceback:")
        raise


async def standalone_schedule_selling_task():
    """Standalone selling task scheduling to avoid pickling issues"""
    logger.info("--- Starting selling task scheduling ---")

    json_path = (
        r"C:\Users\Sivasai\Documents\GitHub\CaseFarm\.venv\combined_forecast_data.json"
    )
    logger.info(f"Loading forecast data from: {json_path}")

    try:
        if not os.path.exists(json_path):
            logger.error(f"Forecast data file not found: {json_path}")
            return

        logger.debug("Reading forecast JSON file")
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        logger.info("Forecast data loaded successfully")
        logger.debug(f"Data keys: {list(data.keys())}")

        ensemble_data = data["recommended_selling_times"]["ensemble"]
        logger.info(f"Extracted {len(ensemble_data)} ensemble recommendations")

        chosen_time = calculate_optimal_selling_time(ensemble_data)
        logger.info(
            f"Optimal selling time calculated: {chosen_time['formatted_time']} (₹{chosen_time['price']:.2f})"
        )

        run_date = datetime.fromtimestamp(chosen_time["unix_timestamp"])
        logger.info(f"Converted to datetime: {run_date}")

        # Get global scheduler instance and schedule the selling job
        global casefarm_scheduler
        selling_job_id = "selling_task"

        try:
            existing_job = casefarm_scheduler.scheduler.get_job(selling_job_id)
            if existing_job:
                logger.info(
                    f"Removing existing selling job scheduled for: {existing_job.next_run_time}"
                )
                casefarm_scheduler.scheduler.remove_job(selling_job_id)
            else:
                logger.debug("No existing selling job found")
        except Exception as e:
            logger.warning(f"Error checking/removing existing job: {e}")

        logger.info(f"Scheduling new selling job for: {run_date}")
        try:
            casefarm_scheduler.scheduler.add_job(
                standalone_selling_task,
                trigger=DateTrigger(run_date=run_date),
                id=selling_job_id,
                args=[chosen_time],
                replace_existing=True,
            )
            logger.info(f"✓ Selling task successfully scheduled for {run_date}")

            new_job = casefarm_scheduler.scheduler.get_job(selling_job_id)
            if new_job:
                logger.info(
                    f"Job verification: Next run time is {new_job.next_run_time}"
                )
            else:
                logger.error("Job verification failed: Job not found after adding")

        except Exception as e:
            logger.error(f"Failed to schedule selling job: {e}")
            raise

    except Exception as e:
        logger.error(f"Unexpected error scheduling selling task: {e}")
        logger.exception("Full traceback:")


def calculate_optimal_selling_time(ensemble_data: list) -> dict:
    """Calculate optimal selling time - standalone function"""
    logger.info("--- Calculating optimal selling time ---")
    logger.debug(f"Input ensemble data length: {len(ensemble_data)}")

    ensemble = ensemble_data[:3]
    logger.debug(f"Using top 3 ensemble items: {len(ensemble)}")

    ensemble_sorted = sorted(ensemble, key=lambda x: x["unix_timestamp"])
    logger.debug("Sorted ensemble by timestamp")

    prices = [float(item["price"].replace("₹", "")) for item in ensemble_sorted]
    logger.info(f"Extracted prices: {prices}")

    best_price = max(prices)
    earliest_price = prices[0]
    logger.info(f"Best price: ₹{best_price:.2f}, Earliest price: ₹{earliest_price:.2f}")

    if earliest_price == best_price:
        chosen_time = ensemble_sorted[0]
        logger.info("Decision: Choosing earliest time as it has the best price")
    elif earliest_price >= best_price * 0.985:
        chosen_time = ensemble_sorted[0]
        logger.info(
            "Decision: Choosing earliest time as it's within 1.5% of best price"
        )
        logger.debug(
            f"Price difference: {(best_price - earliest_price) / best_price * 100:.2f}%"
        )
    else:
        best_index = prices.index(best_price)
        chosen_time = ensemble_sorted[best_index]
        logger.info("Decision: Choosing best price time")
        logger.debug(f"Best price index: {best_index}")

    logger.info(
        f"Selected time: {chosen_time['formatted_time']} with price {chosen_time['price']}"
    )
    return chosen_time


async def standalone_selling_task(chosen_time: dict):
    """Standalone selling task to avoid pickling issues"""
    logger.info("=== Starting comprehensive selling task ===")
    logger.info(f"Chosen time details: {chosen_time}")

    try:
        # 1. Run items lister
        logger.info("Phase 1: Starting items lister")
        logger.info(f"Target execution time: {chosen_time['formatted_time']}")

        logger.debug("Calling items_lister with retry logic")
        lister_success = await retry_call(items_lister)

        if lister_success:
            logger.info("✓ Items listing completed successfully")
        else:
            logger.error("✗ Items listing failed")

        # 2. Run items trader
        logger.info("Phase 2: Starting items trader")
        await standalone_items_trader_job()
        logger.info("Items trader phase completed")

        # 3. Balance check and armory pass purchasing
        logger.info("Phase 3: Starting balance check and armory pass purchasing")
        logger.debug("Retrieving accounts with sufficient balance")
        accounts_with_balance = standalone_balance_check()
        logger.info(
            f"Balance check completed: {len(accounts_with_balance)} eligible accounts"
        )

        if accounts_with_balance:
            logger.info(
                f"Processing armory pass purchases for {len(accounts_with_balance)} accounts"
            )

            for i, username in enumerate(accounts_with_balance, 1):
                logger.info(
                    f"Processing account {i}/{len(accounts_with_balance)}: {username}"
                )

                try:
                    purchase_success = standalone_purchase_armoury_passes_for_account(
                        username
                    )

                    if purchase_success:
                        logger.info(
                            f"✓ Successfully purchased armory passes for {username}"
                        )
                    else:
                        logger.warning(
                            f"✗ Failed to purchase armory passes for {username}"
                        )

                except Exception as e:
                    logger.error(f"Error processing account {username}: {e}")

        else:
            logger.info(
                "No accounts found with sufficient balance for armory pass purchases"
            )

        logger.info("=== Selling task completed successfully ===")
        return lister_success

    except Exception as e:
        logger.error(f"Critical error in selling task: {e}")
        logger.exception("Full traceback:")
        raise


async def standalone_items_trader_job():
    """Standalone items trader job"""
    logger.info("--- Starting items trader job ---")

    try:
        # Fresh database connection in job function

        logger.info("Executing items trader:")
        print("\n")
        result = await run_items_trader()

        logger.info(f"Items trader completed successfully: {result}")

    except Exception as e:
        logger.error(f"Items trader job failed: {e}")
        logger.exception("Full traceback:")
        raise


def standalone_balance_check(steam_usernames: list[str] | None = None) -> list:
    """Standalone balance check function"""
    logger.info("--- Starting balance check ---")

    try:
        # Fresh database connection
        logger.debug("Fetching all steam accounts for balance check")
        accounts = get_all_steam_accounts()
        logger.info(f"Retrieved {len(accounts)} accounts for balance analysis")

        result = []

        if steam_usernames:
            logger.info(f"Checking specific usernames: {steam_usernames}")
            accounts_checked = 0

            for acc in accounts:
                if acc["steam_username"] in steam_usernames:
                    accounts_checked += 1
                    logger.debug(
                        f"Checking balance for specified account: {acc['steam_username']}"
                    )

                    try:
                        balance = float(acc.get("steam_balance", 0))
                        pass_value = float(acc.get("pass_value", 0))
                        required_balance = 5 * pass_value

                        logger.debug(
                            f"Account {acc['steam_username']}: Balance=₹{balance:.2f}, Required=₹{required_balance:.2f}"
                        )

                        if balance >= required_balance:
                            result.append(acc["steam_username"])
                            logger.info(
                                f"✓ {acc['steam_username']} has sufficient balance"
                            )
                        else:
                            logger.debug(
                                f"✗ {acc['steam_username']} insufficient balance"
                            )

                    except Exception as e:
                        logger.warning(
                            f"Error checking balance for {acc['steam_username']}: {e}"
                        )

            logger.info(f"Checked {accounts_checked} specified accounts")

        else:
            logger.info("Checking all armory accounts")
            armory_accounts_found = 0

            for acc in accounts:
                if acc.get("is_armoury", False):
                    armory_accounts_found += 1
                    logger.debug(f"Checking armory account: {acc['steam_username']}")

                    try:
                        balance = float(acc.get("steam_balance", 0))
                        pass_value = float(acc.get("pass_value", 0))
                        required_balance = 5 * pass_value

                        logger.debug(
                            f"Account {acc['steam_username']}: Balance=₹{balance:.2f}, Required=₹{required_balance:.2f}"
                        )

                        if balance >= required_balance:
                            result.append(acc["steam_username"])
                            logger.info(
                                f"✓ {acc['steam_username']} has sufficient balance"
                            )
                        else:
                            logger.debug(
                                f"✗ {acc['steam_username']} insufficient balance"
                            )

                    except Exception as e:
                        logger.warning(
                            f"Error checking balance for {acc['steam_username']}: {e}"
                        )

            logger.info(f"Found and checked {armory_accounts_found} armory accounts")

        logger.info(
            f"Balance check completed: {len(result)} accounts with sufficient balance"
        )
        return result

    except Exception as e:
        logger.error(f"Error in balance check: {e}")
        logger.exception("Full traceback:")
        return []


def standalone_purchase_armoury_passes_for_account(steam_username: str) -> bool:
    """Standalone armory pass purchase function"""
    logger.info(f"--- Starting armory pass purchase for: {steam_username} ---")

    try:
        print("\n🎯 ARMORY PASS PURCHASE REQUIRED")
        print(f"Account: {steam_username}")
        print("Required: 5 Armory Passes")
        print("Please complete this purchase manually in Steam.\n")

        logger.info(
            f"Prompting user for manual purchase confirmation for {steam_username}"
        )

        while True:
            resp = (
                input("Did you successfully buy 5 passes? (y/yes, n/no, f/fail): ")
                .strip()
                .lower()
            )
            logger.debug(f"User response received: '{resp}'")

            if resp in ("y", "yes"):
                logger.info(
                    f"✓ User confirmed successful purchase for {steam_username}"
                )
                print(f"✓ Purchase confirmed for {steam_username}\n")
                return True

            elif resp in ("n", "no"):
                logger.warning(
                    f"✗ User reported insufficient funds for {steam_username}"
                )
                print(f"✗ Insufficient funds reported for {steam_username}\n")
                return False

            elif resp in ("f", "fail"):
                logger.error(f"✗ User reported purchase failure for {steam_username}")
                print(f"✗ Purchase failure reported for {steam_username}\n")
                return False

            else:
                logger.warning(f"Invalid user input received: '{resp}'")
                print(f"❌ Invalid input: '{resp}'. Please use y/yes, n/no, or f/fail.")

    except KeyboardInterrupt:
        logger.warning(f"User interrupted purchase process for {steam_username}")
        print(f"\n⚠️ Purchase process interrupted for {steam_username}")
        return False

    except Exception as e:
        logger.error(f"Error in purchase process for {steam_username}: {e}")
        print(f"❌ Error during purchase process: {e}")
        return False


async def health_check_task():
    """Enhanced standalone health check task with detailed job information"""
    logger.info("=== Starting comprehensive health check ===")

    try:
        # Check forecast file
        logger.info("Health check phase 1: Forecast data validation")
        json_path = r"C:\Users\Sivasai\Documents\GitHub\CaseFarm\.venv\combined_forecast_data.json"

        print("\n" + "=" * 90)
        print("🏥 CASEFARM HEALTH CHECK REPORT")
        print("=" * 90)

        print("\n📊 FORECAST DATA STATUS:")
        print("-" * 40)

        if os.path.exists(json_path):
            file_age = time.time() - os.path.getmtime(json_path)
            file_age_hours = file_age / 3600

            logger.info(f"Forecast file found, age: {file_age_hours:.1f} hours")

            if file_age > 86400:  # 24 hours
                logger.warning(
                    f"⚠️ Forecast data is stale: {file_age_hours:.1f} hours old"
                )
                print(f"⚠️  Status: STALE ({file_age_hours:.1f} hours old)")
                print("   Action Required: Update forecast data")
            else:
                logger.info(f"✓ Forecast data is fresh: {file_age_hours:.1f} hours old")
                print(f"✅ Status: FRESH ({file_age_hours:.1f} hours old)")
        else:
            logger.error("❌ Forecast data file not found")
            print("❌ Status: FILE NOT FOUND")
            print("   Action Required: Generate forecast data")

        # Enhanced scheduler status with running and scheduled jobs
        logger.info("Health check phase 2: Detailed scheduler status")
        print("\n� SCHEDULER STATUS:")
        print("-" * 40)

        global casefarm_scheduler
        jobs = casefarm_scheduler.scheduler.get_jobs()

        if not jobs:
            print("❌ No jobs currently scheduled")
            logger.warning("No jobs found in scheduler")
        else:
            ist_tz = pytz.timezone("Asia/Kolkata")
            current_time = datetime.now(ist_tz)

            # Separate running and scheduled jobs
            running_jobs = []
            scheduled_jobs = []
            overdue_jobs = []

            for job in jobs:
                if job.next_run_time:
                    time_until = (
                        job.next_run_time - datetime.now(job.next_run_time.tzinfo)
                    ).total_seconds()
                    if abs(time_until) < 60:  # Currently running (within 1 minute)
                        running_jobs.append(job)
                    elif time_until < 0:  # Overdue
                        overdue_jobs.append(job)
                    else:  # Scheduled for future
                        scheduled_jobs.append(job)
                else:
                    scheduled_jobs.append(job)  # No next run time

            print(
                f"📈 Total Jobs: {len(jobs)} | Running: {len(running_jobs)} | Scheduled: {len(scheduled_jobs)} | Overdue: {len(overdue_jobs)}"
            )

            # Show currently running jobs
            if running_jobs:
                print(f"\n🏃 CURRENTLY RUNNING JOBS ({len(running_jobs)}):")
                for job in running_jobs:
                    next_run_ist = job.next_run_time.astimezone(ist_tz)
                    print(f"   🔄 {job.id}")
                    print(f"      Function: {job.func.__name__}")
                    print(
                        f"      Started: {next_run_ist.strftime('%d-%m-%Y %I:%M %p')} IST"
                    )

            # Show overdue jobs
            if overdue_jobs:
                print(f"\n⚠️  OVERDUE JOBS ({len(overdue_jobs)}):")
                for job in overdue_jobs:
                    next_run_ist = job.next_run_time.astimezone(ist_tz)
                    time_until = (
                        job.next_run_time - datetime.now(job.next_run_time.tzinfo)
                    ).total_seconds()
                    print(f"   🚨 {job.id}")
                    print(f"      Function: {job.func.__name__}")
                    print(
                        f"      Was Due: {next_run_ist.strftime('%d-%m-%Y %I:%M %p')} IST"
                    )
                    print(f"      Overdue By: {abs(time_until) / 60:.0f} minutes")

            # Show next 5 upcoming scheduled jobs
            if scheduled_jobs:
                scheduled_sorted = sorted(
                    scheduled_jobs,
                    key=lambda x: x.next_run_time
                    if x.next_run_time
                    else datetime.max.replace(tzinfo=pytz.UTC),
                )
                upcoming_count = min(5, len(scheduled_sorted))

                print(f"\n📅 UPCOMING SCHEDULED JOBS (Next {upcoming_count}):")
                for i, job in enumerate(scheduled_sorted[:upcoming_count], 1):
                    if job.next_run_time:
                        next_run_ist = job.next_run_time.astimezone(ist_tz)
                        time_until = (
                            job.next_run_time - datetime.now(job.next_run_time.tzinfo)
                        ).total_seconds()

                        if time_until < 3600:  # Less than 1 hour
                            time_str = f"{time_until / 60:.0f} minutes"
                        elif time_until < 86400:  # Less than 1 day
                            time_str = f"{time_until / 3600:.1f} hours"
                        else:  # More than 1 day
                            time_str = f"{time_until / 86400:.1f} days"

                        print(f"   {i}. 📌 {job.id}")
                        print(f"      Function: {job.func.__name__}")
                        print(
                            f"      Next Run: {next_run_ist.strftime('%d-%m-%Y %I:%M %p')} IST"
                        )
                        print(f"      Time Until: {time_str}")
                        print(f"      Trigger: {str(job.trigger)}")
                    else:
                        print(f"   {i}. 📌 {job.id}")
                        print(f"      Function: {job.func.__name__}")
                        print("      Status: No next run time scheduled")

                if len(scheduled_sorted) > 5:
                    print(f"   ... and {len(scheduled_sorted) - 5} more scheduled jobs")

        # Database connectivity and scheduler database status
        print("\n💾 DATABASE STATUS:")
        print("-" * 40)

        logger.info("Health check phase 3: Database connectivity")
        try:
            test_accounts = get_all_steam_accounts()
            logger.info(f"✓ Database accessible: {len(test_accounts)} accounts found")
            print(f"✅ Main Database: Accessible ({len(test_accounts)} accounts)")
        except Exception as e:
            logger.error(f"❌ Database connectivity issue: {e}")
            print(f"❌ Main Database: Connection failed - {e}")

        # Check scheduler database with human-readable times
        try:
            from sqlalchemy import text

            engine = casefarm_scheduler.jobstores["default"].engine

            with engine.connect() as conn:
                # Query the scheduler database for job information
                query = text(
                    "SELECT id, human_readable_ist, next_run_time FROM apscheduler_jobs ORDER BY next_run_time ASC"
                )
                result = conn.execute(query)
                db_jobs = result.fetchall()

            print(f"✅ Scheduler Database: {len(db_jobs)} jobs persisted")

            if db_jobs:
                print("\n📝 PERSISTED JOBS IN DATABASE:")
                for job_row in db_jobs[:3]:  # Show first 3
                    job_id, human_time, unix_time = job_row
                    print(f"   📁 {job_id}")
                    print(f"      Human Time: {human_time or 'Not set'}")
                    print(f"      Unix Time: {unix_time}")

                if len(db_jobs) > 3:
                    print(f"   ... and {len(db_jobs) - 3} more persisted jobs")

        except Exception as e:
            logger.error(f"Error querying scheduler database: {e}")
            print(f"⚠️  Scheduler Database: Query failed - {e}")

        # System summary
        current_time = datetime.now(pytz.timezone("Asia/Kolkata"))
        print(
            f"\n🕐 Health check completed at: {current_time.strftime('%d-%m-%Y %I:%M %p')} IST"
        )
        print("=" * 90)
        logger.info("=== Health check completed ===")

    except Exception as e:
        logger.error(f"Critical error in health check: {e}")
        logger.exception("Full health check traceback:")
        print(f"❌ Critical error in health check: {e}")
        print("=" * 90)


import pickle

from apscheduler.util import maybe_ref
from sqlalchemy import Column, Float, LargeBinary, MetaData, String, create_engine


class ExtendedSQLAlchemyJobStore(SQLAlchemyJobStore):
    def __init__(
        self,
        url=None,
        engine=None,
        tablename="apscheduler_jobs",
        metadata=None,
        pickle_protocol=pickle.HIGHEST_PROTOCOL,
    ):
        self.pickle_protocol = pickle_protocol
        metadata = maybe_ref(metadata) or MetaData()

        if engine:
            self.engine = maybe_ref(engine)
        elif url:
            self.engine = create_engine(url, echo=False)
        else:
            raise ValueError('Need either "engine" or "url" defined')

        # Create custom table with human-readable IST column
        self.jobs_t = Table(
            tablename,
            metadata,
            Column("id", String(191), primary_key=True),
            Column("next_run_time", Float(25), index=True),
            Column("job_state", LargeBinary, nullable=False),
            Column("human_readable_ist", String(50), nullable=True),  # New column
        )

        # Create the table if it doesn't exist, and add the new column if missing
        try:
            metadata.create_all(self.engine)
            # Check if human_readable_ist column exists, if not add it
            from sqlalchemy import inspect, text

            try:
                inspector = inspect(self.engine)
                columns = [col["name"] for col in inspector.get_columns(tablename)]

                if "human_readable_ist" not in columns:
                    logger.info(
                        "Adding human_readable_ist column to existing scheduler database"
                    )
                    with self.engine.connect() as conn:
                        alter_query = text(
                            f"ALTER TABLE {tablename} ADD COLUMN human_readable_ist VARCHAR(50)"
                        )
                        conn.execute(alter_query)
                        conn.commit()
                    logger.info("Successfully added human_readable_ist column")
            except Exception as e:
                logger.warning(f"Could not check/add human_readable_ist column: {e}")
        except Exception as e:
            logger.warning(f"Could not modify database schema: {e}")
            # If it fails, try to create the table normally
            metadata.create_all(self.engine)

    def _format_ist_time(self, next_run_time):
        """Convert unix timestamp to human-readable IST format"""
        if next_run_time is None:
            return None

        ist_tz = pytz.timezone("Asia/Kolkata")
        dt = datetime.fromtimestamp(next_run_time, tz=ist_tz)
        return dt.strftime("%d-%m-%Y %I:%M %p")

    def add_job(self, job):
        """Override to add human-readable IST time"""
        human_readable = self._format_ist_time(
            job.next_run_time.timestamp() if job.next_run_time else None
        )

        insert = self.jobs_t.insert().values(
            id=job.id,
            next_run_time=job.next_run_time.timestamp() if job.next_run_time else None,
            job_state=pickle.dumps(job.__getstate__(), self.pickle_protocol),
            human_readable_ist=human_readable,
        )

        try:
            with self.engine.connect() as conn:
                conn.execute(insert)
                conn.commit()
        except Exception as e:
            if "UNIQUE constraint failed" in str(e) or "already exists" in str(e):
                raise ConflictingIdError(job.id)
            else:
                logger.error(f"Failed to add job {job.id}: {e}")
                raise

    def update_job(self, job):
        """Override to update human-readable IST time"""
        human_readable = self._format_ist_time(
            job.next_run_time.timestamp() if job.next_run_time else None
        )

        update = (
            self.jobs_t.update()
            .values(
                next_run_time=job.next_run_time.timestamp()
                if job.next_run_time
                else None,
                job_state=pickle.dumps(job.__getstate__(), self.pickle_protocol),
                human_readable_ist=human_readable,
            )
            .where(self.jobs_t.c.id == job.id)
        )

        try:
            with self.engine.connect() as conn:
                result = conn.execute(update)
                conn.commit()
                if result.rowcount == 0:
                    raise JobLookupError(job.id)
        except JobLookupError:
            raise
        except Exception as e:
            logger.error(f"Failed to update job {job.id}: {e}")
            raise


class SchedulerCore:
    def __init__(self):
        # Setup database directory
        self.db_dir = Path(r"C:\Users\Sivasai\Documents\GitHub\CaseFarm\database\db")
        self.db_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.db_dir / "scheduler.db"

        logger.info(f"Initializing SchedulerCore with database at: {self.db_path}")

        # Use Extended SQLAlchemyJobStore for persistence with human-readable timestamps
        logger.info(
            "Using Extended SQLAlchemyJobStore for job persistence with IST timestamps"
        )
        try:
            self.jobstores = {
                "default": ExtendedSQLAlchemyJobStore(
                    url=f"sqlite:///{self.db_path}", tablename="apscheduler_jobs"
                )
            }
            logger.info(
                "Extended SQLAlchemyJobStore initialized successfully with human-readable IST support"
            )
        except Exception as e:
            logger.error(f"Failed to initialize Extended SQLAlchemyJobStore: {e}")
            raise

        self.executors = {"default": AsyncIOExecutor()}
        logger.info("AsyncIO executor configured")

        self.job_defaults = {
            "coalesce": False,
            "max_instances": 1,
            "misfire_grace_time": 300,  # 5 minutes
        }
        logger.info(f"Job defaults configured: {self.job_defaults}")

        try:
            self.scheduler = AsyncIOScheduler(
                jobstores=self.jobstores,
                executors=self.executors,
                job_defaults=self.job_defaults,
            )
            logger.info(
                "AsyncIOScheduler instance created successfully with persistent storage"
            )
        except Exception as e:
            logger.error(f"Failed to create scheduler: {e}")
            raise

        # Add event listeners
        self.scheduler.add_listener(
            self._job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR | EVENT_JOB_MISSED
        )
        logger.info("Job event listeners added")

        self.running = False

    def _job_listener(self, event):
        """Event listener for job monitoring with detailed logging"""
        job_id = getattr(event, "job_id", "unknown")

        if hasattr(event, "exception") and event.exception:
            logger.error(f"Job '{job_id}' failed with exception: {event.exception}")
            logger.error(f"Job failure details - Code: {getattr(event, 'code', 'N/A')}")
        elif hasattr(event, "retval"):
            logger.info(f"Job '{job_id}' executed successfully")
            logger.debug(f"Job return value: {event.retval}")
        else:
            logger.warning(f"Job '{job_id}' was missed")
            logger.warning(
                f"Job miss details - Scheduled time: {getattr(event, 'scheduled_run_time', 'N/A')}"
            )

    def start(self):
        """Start the scheduler with comprehensive logging"""
        if not self.running:
            logger.info("Starting CaseFarm scheduler...")
            logger.info(
                f"Using job store type: {type(self.jobstores['default']).__name__}"
            )

            try:
                # Update existing jobs with human-readable timestamps
                self._update_existing_jobs_with_human_readable()

                # Add standalone job functions (no class methods!)
                self._add_standalone_jobs()

                # Start the scheduler
                logger.info("Attempting to start scheduler...")
                self.scheduler.start()
                self.running = True
                logger.info("CaseFarm scheduler started successfully")

                # Log final job status
                all_jobs = self.scheduler.get_jobs()
                logger.info(f"Scheduler running with {len(all_jobs)} total jobs")

                # Setup graceful shutdown
                atexit.register(self.shutdown)
                logger.info("Graceful shutdown handler registered")

            except Exception as e:
                logger.error(f"Failed to start scheduler: {e}")
                self.running = False
                raise
        else:
            logger.warning("Scheduler is already running")

    def _update_existing_jobs_with_human_readable(self):
        """Update existing jobs in database to include human-readable IST timestamps"""
        try:
            from sqlalchemy import text

            engine = self.jobstores["default"].engine

            with engine.connect() as conn:
                # Get all jobs without human_readable_ist
                query = text(
                    "SELECT id, next_run_time FROM apscheduler_jobs WHERE human_readable_ist IS NULL"
                )
                result = conn.execute(query)
                jobs_to_update = result.fetchall()

                if jobs_to_update:
                    logger.info(
                        f"Updating {len(jobs_to_update)} existing jobs with human-readable timestamps"
                    )

                    for job_row in jobs_to_update:
                        job_id, next_run_time = job_row
                        human_readable = self.jobstores["default"]._format_ist_time(
                            next_run_time
                        )

                        update_query = text(
                            "UPDATE apscheduler_jobs SET human_readable_ist = :human_time WHERE id = :job_id"
                        )
                        conn.execute(
                            update_query,
                            {"human_time": human_readable, "job_id": job_id},
                        )

                    conn.commit()
                    logger.info(
                        "Successfully updated existing jobs with human-readable timestamps"
                    )
                else:
                    logger.info("All jobs already have human-readable timestamps")

        except Exception as e:
            logger.warning(
                f"Could not update existing jobs with human-readable timestamps: {e}"
            )

    def _add_standalone_jobs(self):
        """Add standalone jobs that don't depend on user sessions"""

        # Define IST timezone and time window
        ist_tz = pytz.timezone("Asia/Kolkata")
        current_time = datetime.now(ist_tz)
        current_time_only = current_time.time()

        # Define the active window: 7:30 PM to 10:30 AM next day
        window_start = dt_time(15, 30)  # 3:30 PM for now will change in prod
        window_end = dt_time(10, 30)  # 10:30 AM

        # Check if current time is within the active window
        def is_in_active_window(current_time_only, start_time, end_time):
            # Handle overnight window (7:30 PM to 10:30 AM next day)
            if start_time > end_time:  # Overnight window
                return current_time_only >= start_time or current_time_only <= end_time
            else:  # Same day window
                return start_time <= current_time_only <= end_time

        in_window = is_in_active_window(current_time_only, window_start, window_end)

        # Schedule generation job
        schedule_job_id = "schedule_generation"

        if in_window:
            # If we're in the active window, run immediately and then schedule for next 7:30 PM
            logger.info(
                f"Current time {current_time_only} is within active window (19:30-10:30). Running schedule generator immediately."
            )

            # Add immediate job
            self.scheduler.add_job(
                standalone_schedule_generation_task,
                trigger="date",  # Run once immediately
                id=f"{schedule_job_id}_immediate",
                replace_existing=True,
            )

            # Also schedule the recurring daily job at 7:30 PM
            self.scheduler.add_job(
                standalone_schedule_generation_task,
                trigger=CronTrigger(
                    hour=19, minute=30, timezone=ist_tz
                ),  # Daily at 7:30 PM IST
                id=schedule_job_id,
                replace_existing=True,
            )

            logger.info(
                "Successfully added immediate schedule generation job and daily job at 19:30 IST"
            )

        else:
            # If we're outside the window, wait for next 7:30 PM
            logger.info(
                f"Current time {current_time_only} is outside active window (19:30-10:30). Waiting for next 19:30 IST."
            )

            self.scheduler.add_job(
                standalone_schedule_generation_task,
                trigger=CronTrigger(
                    hour=19, minute=30, timezone=ist_tz
                ),  # Daily at 7:30 PM IST
                id=schedule_job_id,
                replace_existing=True,
            )

            logger.info("Successfully added daily schedule generation job at 19:30 IST")

        # Health check job - more frequent for better monitoring
        health_job_id = "health_check"
        try:
            self.scheduler.add_job(
                health_check_task,
                trigger=IntervalTrigger(mins=10),  # Every 10 minutes
                id=health_job_id,
                replace_existing=True,
            )
            logger.info(f"Successfully added job: {health_job_id} (every 10 minutes)")
        except Exception as e:
            logger.error(f"Failed to add job {health_job_id}: {e}")

    def shutdown(self):
        """Gracefully shutdown the scheduler with detailed logging"""
        if self.running:
            logger.info("Initiating CaseFarm scheduler shutdown...")

            try:
                # Log current jobs before shutdown
                jobs = self.scheduler.get_jobs()
                logger.info(f"Shutting down scheduler with {len(jobs)} active jobs")

                for job in jobs:
                    logger.debug(f"Active job at shutdown: {job.id}")

                self.scheduler.shutdown(wait=True)
                self.running = False
                logger.info("CaseFarm scheduler shut down successfully")

            except Exception as e:
                logger.error(f"Error during scheduler shutdown: {e}")
                self.running = False
        else:
            logger.info("Scheduler is not running, no shutdown needed")

    def get_job_status(self):
        """Get detailed status of all jobs"""
        logger.debug("Retrieving job status information")

        try:
            jobs = self.scheduler.get_jobs()
            status = []

            for job in jobs:
                job_info = {
                    "id": job.id,
                    "next_run": job.next_run_time.isoformat()
                    if job.next_run_time
                    else None,
                    "func": job.func.__name__,
                    "trigger": str(job.trigger),
                    "misfire_grace_time": job.misfire_grace_time,
                    "max_instances": job.max_instances,
                }
                status.append(job_info)
                logger.debug(f"Job status: {job_info}")

            logger.info(f"Retrieved status for {len(status)} jobs")
            return status

        except Exception as e:
            logger.error(f"Error retrieving job status: {e}")
            return []


class CaseFarmScheduler(SchedulerCore):
    def __init__(self):
        logger.info("Initializing CaseFarmScheduler")
        super().__init__()
        logger.info("CaseFarmScheduler initialization completed")


# Global scheduler instance
logger.info("Creating global CaseFarmScheduler instance")
casefarm_scheduler = CaseFarmScheduler()


async def main():
    """Main function with comprehensive logging and error handling"""
    logger.info("=== CaseFarm Automation System Starting ===")

    try:
        # Start the scheduler
        logger.info("Initializing scheduler...")
        casefarm_scheduler.start()

        logger.info("🚀 CaseFarm automation system running successfully")
        logger.info(
            f"🏪 Job store type: {type(casefarm_scheduler.jobstores['default']).__name__}"
        )

        # Log initial system status
        job_status = casefarm_scheduler.get_job_status()
        logger.info(f"📊 System started with {len(job_status)} scheduled jobs")

        # Keep the event loop running with periodic status updates
        loop_count = 0
        while True:
            await asyncio.sleep(60)  # Check every minute
            loop_count += 1

            # Log status every 10 minutes
            if loop_count % 10 == 0:
                logger.debug(f"System running normally - {loop_count} minutes elapsed")

                # Periodic job status check every hour
                if loop_count % 60 == 0:
                    current_jobs = casefarm_scheduler.get_job_status()
                    logger.info(f"Hourly status: {len(current_jobs)} jobs active")

    except KeyboardInterrupt:
        logger.info("🛑 Received shutdown signal (Ctrl+C)")
        print("\n🛑 Shutting down CaseFarm automation system...")

    except Exception as e:
        logger.error(f"💥 Unexpected error in main: {e}")
        logger.exception("Full main() traceback:")

    finally:
        logger.info("🔄 Initiating system shutdown...")
        casefarm_scheduler.shutdown()
        logger.info("✅ CaseFarm automation system shutdown complete")


if __name__ == "__main__":
    logger.info("Starting CaseFarm automation from command line")
    asyncio.run(main())
