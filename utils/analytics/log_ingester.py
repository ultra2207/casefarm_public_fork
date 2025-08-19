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

import os
import re
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional

import requests

from utils.logger import get_custom_logger

logger = get_custom_logger()


class LogIngester:
    def __init__(
        self,
        db_path: str = r"C:\Users\Sivasai\Documents\GitHub\CaseFarm\database\db\ingester.db",
    ):
        self.db_path = db_path
        self.ensure_db_directory()
        self.init_database()

        # Updated default external costs
        self.default_costs = {
            "farmlabs_cost_eur": 17.5,
            "vm_cost_usd": 17.0,
            "standard_panel_cost_usd": 15.0,
        }

        logger.info(f"LogIngester initialized with database path: {self.db_path}")

    def ensure_db_directory(self):
        """Create database directory if it doesn't exist"""
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            logger.info(f"Database directory ensured: {os.path.dirname(self.db_path)}")
        except Exception as e:
            logger.error(f"Failed to create database directory: {e}")
            raise

    def init_database(self):
        """Initialize SQLite database with required tables"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Events table for parsed log data
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME,
                    date DATE,
                    event_type TEXT,
                    trade_volume_inr REAL,
                    gross_profit_inr REAL,
                    net_theoretical_profit_inr REAL,
                    successful_trades INTEGER,
                    failed_trades INTEGER,
                    completed_acceptances INTEGER,
                    success_rate REAL,
                    processed_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # External costs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS external_costs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE,
                    farmlabs_cost_eur REAL,
                    vm_cost_usd REAL,
                    panel_cost_usd REAL,
                    farmlabs_cost_inr REAL,
                    vm_cost_inr REAL,
                    panel_cost_inr REAL,
                    eur_to_inr_rate REAL,
                    usd_to_inr_rate REAL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Daily aggregates table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS daily_metrics (
                    date DATE PRIMARY KEY,
                    total_trades INTEGER,
                    total_trade_volume REAL,
                    total_gross_profit REAL,
                    total_net_theoretical_profit REAL,
                    avg_success_rate REAL,
                    farmlabs_cost_inr REAL,
                    vm_cost_inr REAL,
                    panel_cost_inr REAL,
                    total_external_costs_inr REAL,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Processing state table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS processing_state (
                    id INTEGER PRIMARY KEY,
                    last_processed_position INTEGER,
                    last_processed_timestamp DATETIME,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.commit()
            conn.close()
            logger.info("Database initialized successfully with all required tables")

        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    def get_exchange_rates(self) -> Dict[str, float]:
        """Get current exchange rates using free API"""
        try:
            logger.info("Fetching current exchange rates from free API...")
            response = requests.get(
                "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/inr.json",
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()

            # The API gives how much of other currencies you can get for 1 INR
            # To convert EUR to INR: 1 EUR = 1 / data["inr"]["eur"] INR
            # To convert USD to INR: 1 USD = 1 / data["inr"]["usd"] INR
            eur_to_inr = 1 / data["inr"]["eur"]
            usd_to_inr = 1 / data["inr"]["usd"]

            logger.info(
                f"Exchange rates fetched - EUR to INR: {eur_to_inr:.2f}, USD to INR: {usd_to_inr:.2f}"
            )

            return {"eur_to_inr": eur_to_inr, "usd_to_inr": usd_to_inr}
        except Exception as e:
            logger.warning(
                f"Failed to fetch exchange rates from API: {e}. Using fallback rates."
            )
            return {"eur_to_inr": 90.0, "usd_to_inr": 83.0}

    def update_external_costs(
        self, farmlabs_eur: float, vm_usd: float, standard_panel_usd: float
    ):
        """Update external costs with current exchange rates"""
        try:
            rates = self.get_exchange_rates()

            farmlabs_inr = farmlabs_eur * rates["eur_to_inr"]
            vm_inr = vm_usd * rates["usd_to_inr"]
            standard_panel_inr = standard_panel_usd * rates["usd_to_inr"]

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO external_costs 
                (date, farmlabs_cost_eur, vm_cost_usd, panel_cost_usd, 
                 farmlabs_cost_inr, vm_cost_inr, panel_cost_inr, 
                 eur_to_inr_rate, usd_to_inr_rate)
                VALUES (DATE('now'), ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    farmlabs_eur,
                    vm_usd,
                    standard_panel_usd,
                    farmlabs_inr,
                    vm_inr,
                    standard_panel_inr,
                    rates["eur_to_inr"],
                    rates["usd_to_inr"],
                ),
            )

            conn.commit()
            conn.close()

            logger.info(
                f"External costs updated - Farmlabs: €{farmlabs_eur} (₹{farmlabs_inr:.2f}), "
                f"VM: ${vm_usd} (₹{vm_inr:.2f}), Standard Panel: ${standard_panel_usd} (₹{standard_panel_inr:.2f})"
            )

        except Exception as e:
            logger.error(f"Failed to update external costs: {e}")
            raise

    def get_last_processed_position(self) -> int:
        """Get the last processed file position"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                "SELECT last_processed_position FROM processing_state WHERE id = 1"
            )
            result = cursor.fetchone()

            conn.close()
            position = result[0] if result else 0
            logger.info(f"Last processed position: {position}")
            return position

        except Exception as e:
            logger.error(f"Failed to get last processed position: {e}")
            return 0

    def update_processed_position(self, position: int):
        """Update the last processed file position"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT OR REPLACE INTO processing_state (id, last_processed_position, last_processed_timestamp)
                VALUES (1, ?, CURRENT_TIMESTAMP)
            """,
                (position,),
            )

            conn.commit()
            conn.close()
            logger.info(f"Updated processed position to: {position}")

        except Exception as e:
            logger.error(f"Failed to update processed position: {e}")

    def get_daily_external_costs(self) -> float:
        """Get daily external costs in INR"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT farmlabs_cost_inr, vm_cost_inr, panel_cost_inr
                FROM external_costs
                ORDER BY date DESC
                LIMIT 1
            """)

            cost_data = cursor.fetchone()
            conn.close()

            if cost_data:
                farmlabs_cost, vm_cost, standard_panel_cost = cost_data
                daily_external_cost = (
                    farmlabs_cost + vm_cost + standard_panel_cost
                ) / 30  # Monthly cost divided by 30 days
                logger.info(
                    f"Daily external costs: ₹{daily_external_cost:.2f} (Farmlabs: ₹{farmlabs_cost:.2f}, VM: ₹{vm_cost:.2f}, Standard Panel: ₹{standard_panel_cost:.2f})"
                )
                return daily_external_cost
            else:
                logger.warning("No external costs found in database, using zero costs")
                return 0.0

        except Exception as e:
            logger.error(f"Failed to get daily external costs: {e}")
            return 0.0

    def parse_log_file(self, log_file_path: str) -> List[Dict]:
        """Parse the log file and extract trading events"""
        if not os.path.exists(log_file_path):
            logger.error(f"Log file not found: {log_file_path}")
            return []

        try:
            events = []
            last_position = self.get_last_processed_position()

            with open(log_file_path, "r", encoding="utf-8") as f:
                # Skip to last processed position
                f.seek(last_position)
                content = f.read()

            if not content.strip():
                logger.info("No new content to process in log file")
                return []

            # Split content into lines
            lines = content.split("\n")
            logger.info(
                f"Processing {len(lines)} lines from log file, starting from position {last_position}"
            )

            i = 0
            while i < len(lines):
                line = lines[i]

                # Look for inventory summary start
                if "--- Inventory Summary ---" in line:
                    event = self.parse_trading_session(lines, i)
                    if event:
                        events.append(event)
                        logger.info(
                            f"Parsed trading session: {event['timestamp']} - Trade Volume: ₹{event['trade_volume_inr']:.2f}, "
                            f"Gross Profit: ₹{event['gross_profit_inr']:.2f}, Net Theoretical Profit: ₹{event['net_theoretical_profit_inr']:.2f}"
                        )
                        # Skip to avoid processing the same session again
                        i += 50  # Skip ahead to avoid re-processing
                    else:
                        i += 1
                else:
                    i += 1

            # Update processed position
            self.update_processed_position(last_position + len(content.encode("utf-8")))

            logger.info(
                f"Successfully parsed {len(events)} trading events from log file"
            )
            return events

        except Exception as e:
            logger.error(f"Failed to parse log file: {e}")
            return []

    def parse_trading_session(
        self, lines: List[str], start_index: int
    ) -> Optional[Dict]:
        """Parse a single trading session"""
        try:
            session_data = {
                "timestamp": None,
                "trade_volume": 0.0,
                "successful_trades": 0,
                "failed_trades": 0,
                "completed_acceptances": 0,
            }

            # Extract timestamp from the inventory summary line
            if start_index < len(lines):
                timestamp_match = re.match(
                    r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", lines[start_index]
                )
                if timestamp_match:
                    session_data["timestamp"] = datetime.strptime(
                        timestamp_match.group(1), "%Y-%m-%d %H:%M:%S"
                    )

            # Look for the next inventory summary or end of file
            end_index = len(lines)
            for j in range(start_index + 1, len(lines)):
                if "--- Inventory Summary ---" in lines[j]:
                    end_index = j
                    break

            # Parse session content
            session_lines = lines[start_index:end_index]

            for line in session_lines:
                # Extract tradable inventory value (this is our trade volume)
                if "Total tradable inventory value:" in line:
                    value_match = re.search(r"₹([\d,]+\.?\d*)", line)
                    if value_match:
                        value_str = value_match.group(1).replace(",", "")
                        session_data["trade_volume"] = float(value_str)

                # Extract successful and failed trades
                elif "Successful trades:" in line:
                    success_match = re.search(r"Successful trades: (\d+)", line)
                    if success_match:
                        session_data["successful_trades"] = int(success_match.group(1))

                elif "Failed trades:" in line:
                    fail_match = re.search(r"Failed trades: (\d+)", line)
                    if fail_match:
                        session_data["failed_trades"] = int(fail_match.group(1))

                # Count completed trade acceptances
                elif "Completed trade acceptance" in line:
                    session_data["completed_acceptances"] += 1

            # Only return event if there was tradable value > 0
            if session_data["trade_volume"] > 0 and session_data["timestamp"]:
                # Calculate success rate
                total_trades = (
                    session_data["successful_trades"] + session_data["failed_trades"]
                )
                if total_trades > 0:
                    success_rate = (
                        session_data["completed_acceptances"]
                        / session_data["successful_trades"]
                    )
                    success_rate = min(success_rate, 1.0)  # Cap at 100%
                else:
                    success_rate = 0.0

                # Calculate profits
                trade_volume = session_data["trade_volume"]
                gross_profit = trade_volume / 1.15  # Remove Steam tax

                # Get daily external costs
                daily_external_costs = self.get_daily_external_costs()

                # Net theoretical profit = tradable_value * 0.7 - total_expenses
                net_theoretical_profit = trade_volume * 0.7 - daily_external_costs

                return {
                    "timestamp": session_data["timestamp"],
                    "date": session_data["timestamp"].date(),
                    "event_type": "items_trade",
                    "trade_volume_inr": trade_volume,
                    "gross_profit_inr": gross_profit,
                    "net_theoretical_profit_inr": net_theoretical_profit,
                    "successful_trades": session_data["successful_trades"],
                    "failed_trades": session_data["failed_trades"],
                    "completed_acceptances": session_data["completed_acceptances"],
                    "success_rate": success_rate,
                }

            return None

        except Exception as e:
            logger.error(f"Failed to parse trading session at line {start_index}: {e}")
            return None

    def save_events(self, events: List[Dict]):
        """Save parsed events to database"""
        if not events:
            logger.info("No events to save")
            return

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            for event in events:
                cursor.execute(
                    """
                    INSERT INTO events 
                    (timestamp, date, event_type, trade_volume_inr, gross_profit_inr, net_theoretical_profit_inr,
                     successful_trades, failed_trades, completed_acceptances, success_rate)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        event["timestamp"],
                        event["date"],
                        event["event_type"],
                        event["trade_volume_inr"],
                        event["gross_profit_inr"],
                        event["net_theoretical_profit_inr"],
                        event["successful_trades"],
                        event["failed_trades"],
                        event["completed_acceptances"],
                        event["success_rate"],
                    ),
                )

            conn.commit()
            conn.close()

            logger.info(f"Successfully saved {len(events)} events to database")

        except Exception as e:
            logger.error(f"Failed to save events to database: {e}")
            raise

    def calculate_daily_metrics(self):
        """Calculate and store daily aggregated metrics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Get daily aggregates
            cursor.execute("""
                SELECT 
                    date,
                    COUNT(*) as total_trades,
                    SUM(trade_volume_inr) as total_trade_volume,
                    SUM(gross_profit_inr) as total_gross_profit,
                    SUM(net_theoretical_profit_inr) as total_net_theoretical_profit,
                    AVG(success_rate) as avg_success_rate
                FROM events
                GROUP BY date
            """)

            daily_data = cursor.fetchall()

            # Get latest external costs
            cursor.execute("""
                SELECT farmlabs_cost_inr, vm_cost_inr, panel_cost_inr
                FROM external_costs
                ORDER BY date DESC
                LIMIT 1
            """)

            cost_data = cursor.fetchone()
            if cost_data:
                farmlabs_cost, vm_cost, standard_panel_cost = cost_data
                daily_external_cost = (
                    farmlabs_cost + vm_cost + standard_panel_cost
                ) / 30  # Daily cost
                logger.info(
                    f"Using external costs - Farmlabs: ₹{farmlabs_cost:.2f}, VM: ₹{vm_cost:.2f}, Standard Panel: ₹{standard_panel_cost:.2f}"
                )
            else:
                daily_external_cost = 0
                farmlabs_cost = vm_cost = standard_panel_cost = 0
                logger.warning("No external costs found in database, using zero costs")

            # Update daily metrics
            updated_count = 0
            for row in daily_data:
                (
                    date,
                    total_trades,
                    total_trade_volume,
                    total_gross_profit,
                    total_net_theoretical_profit,
                    avg_success_rate,
                ) = row

                cursor.execute(
                    """
                    INSERT OR REPLACE INTO daily_metrics
                    (date, total_trades, total_trade_volume, total_gross_profit, total_net_theoretical_profit, avg_success_rate,
                     farmlabs_cost_inr, vm_cost_inr, panel_cost_inr, total_external_costs_inr)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        date,
                        total_trades,
                        total_trade_volume,
                        total_gross_profit,
                        total_net_theoretical_profit,
                        avg_success_rate,
                        farmlabs_cost,
                        vm_cost,
                        standard_panel_cost,
                        daily_external_cost,
                    ),
                )

                updated_count += 1

            conn.commit()
            conn.close()

            logger.info(
                f"Successfully calculated and updated daily metrics for {updated_count} days"
            )

        except Exception as e:
            logger.error(f"Failed to calculate daily metrics: {e}")
            raise

    def run_ingestion(
        self,
        log_file_path: str = r"C:\Users\Sivasai\Documents\GitHub\CaseFarm\utils\cache\logs\stage_1.log",
    ):
        """Run the complete ingestion process"""
        logger.info("Starting log ingestion process...")

        try:
            # Update external costs with defaults if not exist
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM external_costs")
            costs_exist = cursor.fetchone()[0] > 0
            conn.close()

            if not costs_exist:
                logger.info("No external costs found, initializing with default values")
                self.update_external_costs(
                    self.default_costs["farmlabs_cost_eur"],
                    self.default_costs["vm_cost_usd"],
                    self.default_costs["standard_panel_cost_usd"],
                )

            # Parse and save events
            events = self.parse_log_file(log_file_path)
            self.save_events(events)

            # Calculate metrics
            self.calculate_daily_metrics()

            logger.info(
                f"Log ingestion completed successfully! Processed {len(events)} events."
            )
            return len(events)

        except Exception as e:
            logger.error(f"Log ingestion failed: {e}")
            raise


if __name__ == "__main__":
    try:
        ingester = LogIngester()
        ingester.run_ingestion()
    except Exception as e:
        logger.error(f"Failed to run log ingestion: {e}")
        raise
