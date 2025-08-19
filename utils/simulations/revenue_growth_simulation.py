import json
import math
import os
import sys
import time
from datetime import date, datetime, timedelta

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import requests
from ipywidgets import interact, widgets
from tqdm import tqdm

pio.renderers.default = "browser"

# Add the requested import statements
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


# Note: All calculations are done in rupees with any foreign currency prices being converted into inr

ACCOUNT_COST_STEAM_IDR_INITIAL: float = (
    81257.36  # 'ACCOUNT_COST_REAL' is how much inr is needed to buy giftcards for this
)
ACCOUNT_COST_STEAM_IDR_TOTAL: float = 236574.46
UPGRADE_COST_STEAM_IDR: float = 261000

csfloat_tax: float = 1.0585  # After u obtain csfloat prices, this is how much u divide it by to get real balance to bank (also multiply with the current usd to inr obviously)


def convert_idr_to_real(idr_amount: float) -> float | None:
    """
    Convert Indonesian Rupiah (IDR) to Indian Rupees (INR).

    Args:
        idr_amount (float): Amount in IDR

    Returns:
        float: Equivalent amount in INR
    """

    # Define cache file path
    cache_dir: str = (
        r"C:\Users\Sivasai\Documents\GitHub\CaseFarm\utils\cache\miscellaneous"
    )
    cache_file: str = os.path.join(cache_dir, "idr_to_inr_rate.json")

    # Ensure cache directory exists
    os.makedirs(cache_dir, exist_ok=True)

    # Check if we have a valid cached rate
    should_fetch_new_data: bool = True
    if os.path.exists(cache_file):
        # Check file age
        file_age_seconds: float = time.time() - os.path.getmtime(cache_file)
        one_hour_in_seconds: int = 3600

        # If file is less than 1 hour old, use cached data
        if file_age_seconds < one_hour_in_seconds:
            try:
                with open(cache_file, "r") as f:
                    cached_data: dict = json.load(f)
                    idr_to_inr_rate: float = cached_data.get("idr", {}).get("inr")

                    if idr_to_inr_rate is not None:
                        should_fetch_new_data = False
            except Exception as e:
                logger.error(f"Error reading cache: {e}")

    # Fetch new data if needed
    if should_fetch_new_data:
        try:
            # Fetch the latest exchange rates
            response = requests.get(
                "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/idr.json"
            )
            data: dict = response.json()

            # Cache the data
            with open(cache_file, "w") as f:
                json.dump(data, f)

            # Extract rate
            idr_to_inr_rate: float = data["idr"]["inr"]
            logger.debug(f"Fetched new IDR to INR rate: {idr_to_inr_rate}")
        except Exception as e:
            logger.error(f"Error fetching currency data: {e}")

            # If we have a cache file but it's old, use it as fallback
            if os.path.exists(cache_file):
                try:
                    with open(cache_file, "r") as f:
                        cached_data: dict = json.load(f)
                        idr_to_inr_rate: float = cached_data.get("idr", {}).get("inr")
                        logger.warning("Using outdated cache as fallback")
                except Exception as cache_e:
                    logger.error(f"Error reading fallback cache: {cache_e}")
                    return None
            else:
                return None

    # Convert IDR to INR
    inr_amount: float = idr_amount * idr_to_inr_rate
    logger.trace(f"Converted {idr_amount} IDR to {inr_amount} INR")

    return inr_amount


# Constants for business simulation
CONSTANTS: dict[str, float] = {
    "ACCOUNT_COST_REAL": 474.59,
    "ACCOUNT_COST_STEAM": convert_idr_to_real(
        ACCOUNT_COST_STEAM_IDR_TOTAL - ACCOUNT_COST_STEAM_IDR_INITIAL
    ),
    "UPGRADE_COST": convert_idr_to_real(UPGRADE_COST_STEAM_IDR),
    "REAL_TO_STEAM_CONVERSION_RATE": 0.9421,
}

# Shared Constants
BASE_REVENUE_WEEK: float = 57.3
BASE_REVENUE_DAILY: float = 0
MONTHLY_INVESTMENT: float = 9000
FIXED_COST: float = 1663.7
STEAM_TO_REAL_EFFICIENCY: float = 0.72
REAL_TO_STEAM_CONVERSION_RATE: float = 0.9421
HOME_COMPUTER_CAPACITY: int = 4
STEAM_RESERVE_PERCENTAGE: float = 50

# Local computer constants
LOCAL_COMPUTER_COST: float = 10000
LOCAL_COMPUTER_THRESHOLD: int = 26
LOCAL_COMPUTER_CONTRACT_MONTHS: int = 36  # 36-month contract
CUTTING_EDGE_CAPACITY: int = 40  # Capacity for cutting edge solution after completion
DERISKING_THRESHOLD: int = LOCAL_COMPUTER_THRESHOLD

# Revenue calculation constants
redeemed_item_price: float = 89
redeemed_item_stars: int = 2
steam_tax_rate: float = 1.15
total_num_stars_per_pass: int = 40
revenue_increase_on_upgrade: float = (
    redeemed_item_price
    * (total_num_stars_per_pass / redeemed_item_stars)
    / steam_tax_rate
)
OLD_MAX_UPGRADES: int = 60
NEW_MAX_UPGRADES: int = 105

SIMULATION_DAYS: int = 365


def convert_real_to_steam(real_amount: float) -> float:
    return real_amount * REAL_TO_STEAM_CONVERSION_RATE


def convert_steam_to_real(steam_amount: float) -> float:
    return steam_amount * STEAM_TO_REAL_EFFICIENCY


class Account:
    def __init__(self, constants: dict[str, float]):
        self.upgrades: int = 0
        self.pending_upgrades: int = 0
        self.constants: dict[str, float] = constants
        self.activation_date: date | None = None

    def weekly_revenue_base(self) -> float:
        return BASE_REVENUE_WEEK

    def weekly_armoury_pass_revenue_without_costs(self) -> float:
        return self.upgrades * revenue_increase_on_upgrade

    def daily_revenue(self) -> float:
        return BASE_REVENUE_DAILY

    def can_upgrade(self, current_date: date, completion_date: date) -> bool:
        # Determine max upgrades based on whether new software is available
        max_upgrades = (
            NEW_MAX_UPGRADES if current_date >= completion_date else OLD_MAX_UPGRADES
        )
        return (self.upgrades + self.pending_upgrades) < max_upgrades

    def get_max_upgrades(self, current_date: date, completion_date: date) -> int:
        return NEW_MAX_UPGRADES if current_date >= completion_date else OLD_MAX_UPGRADES

    def upgrade(self) -> bool:
        self.pending_upgrades += 1
        return True

    def activate_upgrade(self) -> bool:
        if self.pending_upgrades > 0:
            self.upgrades += 1
            self.pending_upgrades -= 1
            return True
        return False


def simulate_business(
    simulation_days: int, constants: dict[str, float], completion_days_from_now: int
) -> pd.DataFrame:
    start_date: date = date.today()
    end_date: date = start_date + timedelta(days=simulation_days)
    casual_farm_completion_date: date = start_date + timedelta(
        days=completion_days_from_now
    )

    logger.info(f"Starting simulation from {start_date} to {end_date}")
    logger.info(f"Casual farm completion date set to {casual_farm_completion_date}")

    accounts: list[Account] = []
    steam_balance: float = 0.0
    steam_reserve: float = 0.0
    real_balance: float = 0.0
    daily_stats: list[dict] = []

    # Track local computer contracts: (purchase_date, remaining_months)
    local_computer_contracts: list[tuple[date, int]] = []

    # Dictionaries for scheduling:
    weekly_rev_schedule: dict[date, float] = {}
    daily_rev_schedule: dict[date, float] = {}
    upgrade_schedule: dict[date, list[tuple[Account, int]]] = {}

    # Calculate total days for the progress bar
    total_days: int = (end_date - start_date).days + 1

    # Use tqdm to wrap the date iteration
    current_date: date = start_date
    for _ in tqdm(range(total_days - 1), desc="Simulating business"):
        # Weekly revenue scheduling
        if current_date.weekday() == 2:
            base_weekly_rev = sum(
                acc.weekly_revenue_base()
                for acc in accounts
                if getattr(acc, "activation_date", current_date) <= current_date
            )
            scheduled_date_base: date = current_date
            weekly_rev_schedule[scheduled_date_base] = (
                weekly_rev_schedule.get(scheduled_date_base, 0) + base_weekly_rev
            )

            armoury_rev: float = sum(
                (
                    acc.weekly_armoury_pass_revenue_without_costs()
                    - acc.upgrades * constants["UPGRADE_COST"]
                )
                for acc in accounts
                if getattr(acc, "activation_date", current_date) <= current_date
            )
            scheduled_date_armoury: date = current_date + timedelta(days=7)
            weekly_rev_schedule[scheduled_date_armoury] = (
                weekly_rev_schedule.get(scheduled_date_armoury, 0) + armoury_rev
            )

            logger.trace(
                f"Scheduled weekly revenue: {base_weekly_rev} for {scheduled_date_base}, {armoury_rev} for {scheduled_date_armoury}"
            )

        # Process scheduled events
        if current_date in upgrade_schedule:
            for candidate, num_upgrades in upgrade_schedule[current_date]:
                for _ in range(num_upgrades):
                    candidate.activate_upgrade()
            logger.debug(
                f"Processed {len(upgrade_schedule[current_date])} scheduled upgrades for {current_date}"
            )
            del upgrade_schedule[current_date]

        if current_date in weekly_rev_schedule:
            revenue_amount = weekly_rev_schedule[current_date]
            steam_balance += revenue_amount
            logger.debug(
                f"Added scheduled weekly revenue: {revenue_amount} to steam balance, now at {steam_balance}"
            )
            del weekly_rev_schedule[current_date]

        if current_date in daily_rev_schedule:
            revenue_amount = daily_rev_schedule[current_date]
            steam_balance += revenue_amount
            logger.debug(
                f"Added scheduled daily revenue: {revenue_amount} to steam balance, now at {steam_balance}"
            )
            del daily_rev_schedule[current_date]

        # Calculate daily revenue
        daily_rev: float = sum(
            acc.daily_revenue()
            for acc in accounts
            if getattr(acc, "activation_date", current_date) <= current_date
        )

        # Schedule revenue deposits
        if current_date.weekday() == 2:  # Wednesday
            steam_balance += daily_rev
            logger.trace(
                f"Added {daily_rev} daily revenue directly to steam balance on Wednesday"
            )
        else:
            days_to_wednesday: int = (2 - current_date.weekday()) % 7
            next_wednesday: date = current_date + timedelta(days=days_to_wednesday)
            daily_rev_schedule[next_wednesday] = (
                daily_rev_schedule.get(next_wednesday, 0) + daily_rev
            )
            logger.trace(
                f"Scheduled {daily_rev} daily revenue for next Wednesday ({next_wednesday})"
            )

        # Determine computer capacity based on whether we've reached completion date
        home_capacity: int = HOME_COMPUTER_CAPACITY
        # If completion date has passed, use cutting edge capacity for new computers
        account_threshold: int = (
            CUTTING_EDGE_CAPACITY
            if current_date >= casual_farm_completion_date
            else LOCAL_COMPUTER_THRESHOLD
        )

        # Monthly expenses and computer management
        if current_date.day == 1:
            real_balance += MONTHLY_INVESTMENT
            logger.info(
                f"Added monthly investment of {MONTHLY_INVESTMENT}, real balance now: {real_balance}"
            )

            # Calculate license costs
            num_accounts: int = len(accounts)
            num_licenses: int = (
                math.ceil(num_accounts / account_threshold) if num_accounts > 0 else 0
            )
            license_cost: float = num_licenses * FIXED_COST

            # Calculate how many local computers we need
            extra_accounts: int = max(0, num_accounts - home_capacity)
            required_local_computers: int = (
                math.ceil(extra_accounts / account_threshold)
                if extra_accounts > 0
                else 0
            )

            # Purchase new local computers if needed
            if required_local_computers > len(local_computer_contracts):
                new_computers_needed: int = required_local_computers - len(
                    local_computer_contracts
                )
                for _ in range(new_computers_needed):
                    local_computer_contracts.append(
                        (current_date, LOCAL_COMPUTER_CONTRACT_MONTHS)
                    )
                logger.info(f"Purchased {new_computers_needed} new local computers")

            # Pay for existing local computer contracts
            local_computer_cost: float = 0
            updated_contracts: list[tuple[date, int]] = []
            for purchase_date, remaining_months in local_computer_contracts:
                if remaining_months > 0:
                    local_computer_cost += LOCAL_COMPUTER_COST
                    updated_contracts.append((purchase_date, remaining_months - 1))
            local_computer_contracts = updated_contracts

            total_expenses: float = license_cost + local_computer_cost
            logger.info(
                f"Monthly expenses: license cost {license_cost}, computer cost {local_computer_cost}, total {total_expenses}"
            )

            # Handle fund shortages
            if real_balance < total_expenses:
                needed: float = total_expenses - real_balance
                required_steam: float = needed / STEAM_TO_REAL_EFFICIENCY
                if steam_balance >= required_steam:
                    steam_balance -= required_steam
                    real_balance += needed
                    logger.debug(
                        f"Converted {required_steam} steam to cover expenses shortage"
                    )
                else:
                    available_steam: float = steam_balance
                    steam_balance = 0
                    converted_amount: float = available_steam * STEAM_TO_REAL_EFFICIENCY
                    real_balance += converted_amount
                    logger.warning(
                        f"Insufficient funds: converted all steam ({available_steam}) but still short on expenses"
                    )

            real_balance -= total_expenses
            logger.debug(
                f"Paid {total_expenses} in expenses, remaining real balance: {real_balance}"
            )

        # Investment logic
        fully_invested: bool = False
        while not fully_invested:
            candidate: Account | None = None
            for acc in accounts:
                if acc.can_upgrade(current_date, casual_farm_completion_date):
                    candidate = acc
                    break

            # EXISTING DERISKING LOGIC
            derisk_threshold: int = (
                CUTTING_EDGE_CAPACITY * 2
                if current_date >= casual_farm_completion_date
                else DERISKING_THRESHOLD
            )
            if (
                candidate is None
                and len(accounts) > home_capacity
                and ((len(accounts) - home_capacity) >= derisk_threshold)
            ):
                account_value: float = (
                    constants["ACCOUNT_COST_REAL"] / STEAM_TO_REAL_EFFICIENCY
                    + constants["ACCOUNT_COST_STEAM"]
                    + 5 * constants["UPGRADE_COST"]
                )
                target_steam: float = (
                    (STEAM_RESERVE_PERCENTAGE / 100) * len(accounts) * account_value
                )

                if steam_reserve < target_steam:
                    logger.info(
                        f"Derisking needed: steam reserve {steam_reserve} < target {target_steam}"
                    )
                    if steam_balance + steam_reserve < target_steam:
                        needed_steam: float = target_steam - (
                            steam_balance + steam_reserve
                        )
                        required_real: float = (
                            needed_steam / REAL_TO_STEAM_CONVERSION_RATE
                        )
                        if real_balance >= required_real:
                            real_balance -= required_real
                            steam_balance += convert_real_to_steam(required_real)
                            logger.debug(
                                f"Converted {required_real} real to steam for derisking"
                            )
                            fully_invested = True
                            continue
                        else:
                            steam_balance += convert_real_to_steam(real_balance)
                            logger.warning(
                                f"Insufficient real balance for derisking, converting all {real_balance}"
                            )
                            real_balance = 0
                            fully_invested = True
                            continue
                    else:
                        to_transfer: float = target_steam - steam_reserve
                        steam_balance -= to_transfer
                        steam_reserve += to_transfer
                        logger.debug(
                            f"Transferred {to_transfer} from steam balance to reserve"
                        )
                        continue

            # Purchasing new accounts
            if candidate is None:
                if (
                    real_balance >= constants["ACCOUNT_COST_REAL"]
                    and steam_balance >= constants["ACCOUNT_COST_STEAM"]
                ):
                    real_balance -= constants["ACCOUNT_COST_REAL"]
                    steam_balance -= constants["ACCOUNT_COST_STEAM"]
                    candidate = Account(constants)
                    candidate.activation_date = current_date + timedelta(days=7)
                    accounts.append(candidate)
                    logger.success(
                        f"Created new account with activation date {candidate.activation_date}"
                    )
                else:
                    if real_balance < constants["ACCOUNT_COST_REAL"]:
                        needed: float = constants["ACCOUNT_COST_REAL"] - real_balance
                        required_steam: float = needed / STEAM_TO_REAL_EFFICIENCY
                        if (
                            steam_balance
                            >= required_steam + constants["ACCOUNT_COST_STEAM"]
                        ):
                            steam_balance -= required_steam
                            real_balance += needed
                            real_balance -= constants["ACCOUNT_COST_REAL"]
                            steam_balance -= constants["ACCOUNT_COST_STEAM"]
                            candidate = Account(constants)
                            candidate.activation_date = current_date + timedelta(days=7)
                            accounts.append(candidate)
                            logger.success(
                                f"Created new account by converting {required_steam} steam to real"
                            )
                            continue
                        else:
                            fully_invested = True
                            continue
                    elif steam_balance < constants["ACCOUNT_COST_STEAM"]:
                        needed: float = constants["ACCOUNT_COST_STEAM"] - steam_balance
                        required_real: float = needed / REAL_TO_STEAM_CONVERSION_RATE
                        if (
                            real_balance
                            >= required_real + constants["ACCOUNT_COST_REAL"]
                        ):
                            real_balance -= required_real
                            steam_balance += convert_real_to_steam(required_real)
                            real_balance -= constants["ACCOUNT_COST_REAL"]
                            steam_balance -= constants["ACCOUNT_COST_STEAM"]
                            candidate = Account(constants)
                            candidate.activation_date = current_date + timedelta(days=7)
                            accounts.append(candidate)
                            logger.success(
                                f"Created new account by converting {required_real} real to steam"
                            )
                        else:
                            fully_invested = True
                            continue

            # Scheduling upgrades
            if candidate is not None and candidate.can_upgrade(
                current_date, casual_farm_completion_date
            ):
                max_possible_upgrades: int = candidate.get_max_upgrades(
                    current_date, casual_farm_completion_date
                ) - (candidate.upgrades + candidate.pending_upgrades)
                max_affordable_upgrades: int = math.floor(
                    steam_balance / constants["UPGRADE_COST"]
                )

                if max_affordable_upgrades == 0:
                    needed_steam: float = constants["UPGRADE_COST"] - steam_balance
                    required_real: float = needed_steam / REAL_TO_STEAM_CONVERSION_RATE
                    if real_balance >= required_real:
                        real_balance -= required_real
                        steam_balance += convert_real_to_steam(required_real)
                        max_affordable_upgrades = math.floor(
                            steam_balance / constants["UPGRADE_COST"]
                        )
                        logger.debug(
                            f"Converted {required_real} real to steam for upgrades"
                        )
                    else:
                        fully_invested = True
                        continue

                if max_affordable_upgrades > 0:
                    num_upgrades: int = min(
                        max_possible_upgrades, max_affordable_upgrades
                    )
                    total_cost: float = num_upgrades * constants["UPGRADE_COST"]
                    steam_balance -= total_cost

                    scheduled_date_upgrade: date = current_date + timedelta(days=7)
                    if scheduled_date_upgrade not in upgrade_schedule:
                        upgrade_schedule[scheduled_date_upgrade] = []

                    for _ in range(num_upgrades):
                        candidate.upgrade()

                    upgrade_schedule[scheduled_date_upgrade].append(
                        (candidate, num_upgrades)
                    )
                    logger.debug(
                        f"Scheduled {num_upgrades} upgrades for {scheduled_date_upgrade}"
                    )
                else:
                    fully_invested = True
                    break
            else:
                fully_invested = True

        # Collect daily stats
        weekly_rev_stat: float = sum(
            (
                acc.weekly_revenue_base()
                + (
                    acc.weekly_armoury_pass_revenue_without_costs()
                    - acc.upgrades * constants["UPGRADE_COST"]
                )
            )
            for acc in accounts
            if getattr(acc, "activation_date", current_date) <= current_date
        )

        # Calculate expenses for reporting
        num_licenses: int = (
            math.ceil(len(accounts) / account_threshold) if len(accounts) > 0 else 0
        )
        license_cost: float = num_licenses * FIXED_COST
        local_computer_cost: float = (
            len([c for c in local_computer_contracts if c[1] > 0]) * LOCAL_COMPUTER_COST
        )
        total_expenses: float = license_cost + local_computer_cost

        monthly_revenue: float = (
            (365 / 12) * daily_rev + (365 / (12 * 7)) * weekly_rev_stat - total_expenses
        )

        # Store days from start for easier plotting
        days_from_start: int = (current_date - start_date).days
        daily_stats.append(
            {
                "date": current_date.strftime("%Y-%m-%d"),
                "days_from_start": days_from_start,
                "accounts": len(accounts),
                "monthly_revenue": monthly_revenue,
                "steam_balance": steam_balance,
                "steam_reserve": steam_reserve,
                "real_balance": real_balance,
                "max_upgrades": NEW_MAX_UPGRADES
                if current_date >= casual_farm_completion_date
                else OLD_MAX_UPGRADES,
                "account_capacity": account_threshold,
                "is_completion_date": current_date == casual_farm_completion_date,
            }
        )

        current_date += timedelta(days=1)

    logger.success(
        f"Simulation completed. Total accounts: {len(accounts)}, Final monthly revenue: {monthly_revenue:.2f}"
    )
    # Convert to DataFrame for easier manipulation
    return pd.DataFrame(daily_stats)


def plot_simulation(
    completion_days: int = 180, simulation_days: int = 365
) -> go.Figure:
    """Run simulation and plot results with completion date marker"""
    # Run simulation
    logger.info(
        f"Running simulation with completion_days={completion_days}, simulation_days={simulation_days}"
    )
    df = simulate_business(simulation_days, CONSTANTS, completion_days)

    # Create figure
    fig = go.Figure()
    logger.debug("Creating figure for simulation results")

    # Add traces for each metric
    fig.add_trace(
        go.Scatter(
            x=df["days_from_start"],
            y=df["monthly_revenue"],
            name="Monthly Revenue",
            line=dict(color="blue", width=2),
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df["days_from_start"],
            y=df["accounts"],
            name="Accounts",
            line=dict(color="red", width=2),
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df["days_from_start"],
            y=df["steam_balance"],
            name="Steam Balance",
            line=dict(color="green", width=2),
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df["days_from_start"],
            y=df["real_balance"],
            name="Real Balance",
            line=dict(color="purple", width=2),
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df["days_from_start"],
            y=df["steam_reserve"],
            name="Steam Reserve",
            line=dict(color="orange", width=2),
        )
    )
    logger.trace("Added 5 trace lines to figure")

    # Find the completion date in the dataframe
    completion_row = df[df["is_completion_date"]]
    if not completion_row.empty:
        completion_day = completion_row.iloc[0]["days_from_start"]
        logger.debug(f"Found completion date at day {completion_day}")

        # Add shape for vertical line at completion date
        fig.add_shape(
            type="line",
            x0=completion_day,
            x1=completion_day,
            y0=0,
            y1=1,
            yref="paper",
            line=dict(color="red", width=2, dash="dash"),
        )

        # Add annotation for completion date
        fig.add_annotation(
            x=completion_day,
            y=1,
            yref="paper",
            text=f"Software Completion (Day {completion_day})",
            showarrow=True,
            arrowhead=1,
            ax=0,
            ay=-40,
        )
        logger.trace("Added vertical line and annotation for completion date")

    # Update layout
    fig.update_layout(
        xaxis_title="Days from Start",
        yaxis_title="Value",
        height=600,
        legend_title="Metrics",
        hovermode="x unified",
    )
    logger.debug("Figure layout updated")

    return fig


def interactive_plot() -> None:
    """Create an interactive widget to adjust completion date"""
    # Define the widget
    logger.info("Creating interactive widget for completion date adjustment")
    completion_slider = widgets.IntSlider(
        min=30,
        max=365,
        step=30,
        description="Completion Day:",
        continuous_update=False,
    )

    # Create the interactive plot
    interact(
        plot_simulation,
        completion_days=completion_slider,
        simulation_days=widgets.fixed(365),
    )
    logger.success("Interactive plot created successfully")


def main() -> None:
    """
    Main function to run the simulation with an interactive slider
    for software completion date
    """
    logger.info("Starting main simulation function")

    # Define current date and date range for simulation
    current_date = datetime.now().date()
    logger.debug(f"Using current date: {current_date}")

    # Define range of completion days to simulate (from day 30 to day 345)
    min_completion_day: int = 30
    max_completion_day: int = 365
    step: int = 30
    completion_days_range: list[int] = list(
        range(min_completion_day, max_completion_day + 1, step)
    )
    logger.debug(
        f"Created completion days range with {len(completion_days_range)} values"
    )

    # Calculate days to January 1, 2026
    jan_1_2026 = datetime(2026, 1, 1).date()
    days_to_jan_1_2026 = (jan_1_2026 - current_date).days
    logger.info(f"Days to January 1, 2026: {days_to_jan_1_2026}")

    # Find the closest value in completion_days_range
    default_step_index = min(
        range(len(completion_days_range)),
        key=lambda i: abs(completion_days_range[i] - days_to_jan_1_2026),
    )
    logger.debug(f"Selected default step index: {default_step_index}")

    # Create corresponding date objects for display
    completion_dates: list[str] = [
        (current_date + timedelta(days=day)).strftime("%Y-%m-%d")
        for day in completion_days_range
    ]

    # Create empty figure that will be populated based on slider position
    fig = go.Figure()
    logger.debug("Created empty figure for slider-based visualization")

    # Add initial traces for the first simulation with Jan 2026 completion
    initial_completion_day = completion_days_range[default_step_index]
    logger.info(
        f"Running initial simulation with completion day: {initial_completion_day}"
    )
    initial_df = simulate_business(365, CONSTANTS, initial_completion_day)

    # Convert day numbers to actual dates for x-axis
    date_x_values: list[str] = [
        (current_date + timedelta(days=int(day))).strftime("%Y-%m-%d")
        for day in initial_df["days_from_start"]
    ]
    logger.trace(f"Generated {len(date_x_values)} date values for x-axis")

    # Add traces for each metric - set only Monthly Revenue visible by default
    fig.add_trace(
        go.Scatter(
            x=date_x_values,
            y=initial_df["monthly_revenue"],
            name="Monthly Revenue",
            line=dict(color="blue", width=2),
            visible=True,  # This one stays visible
        )
    )

    fig.add_trace(
        go.Scatter(
            x=date_x_values,
            y=initial_df["accounts"],
            name="Accounts",
            line=dict(color="red", width=2),
            visible="legendonly",  # Hidden by default
        )
    )

    fig.add_trace(
        go.Scatter(
            x=date_x_values,
            y=initial_df["steam_balance"],
            name="Steam Balance",
            line=dict(color="green", width=2),
            visible="legendonly",  # Hidden by default
        )
    )

    fig.add_trace(
        go.Scatter(
            x=date_x_values,
            y=initial_df["real_balance"],
            name="Real Balance",
            line=dict(color="purple", width=2),
            visible="legendonly",  # Hidden by default
        )
    )

    fig.add_trace(
        go.Scatter(
            x=date_x_values,
            y=initial_df["steam_reserve"],
            name="Steam Reserve",
            line=dict(color="orange", width=2),
            visible="legendonly",  # Hidden by default
        )
    )
    logger.debug("Added 5 default traces to figure")

    # Initial completion date is now set to Jan 2026
    initial_completion_date = (
        current_date + timedelta(days=initial_completion_day)
    ).strftime("%Y-%m-%d")
    logger.info(f"Initial completion date set to {initial_completion_date}")

    # Add shape for vertical line at completion date
    fig.add_shape(
        type="line",
        x0=initial_completion_date,
        x1=initial_completion_date,
        y0=0,
        y1=1,
        yref="paper",
        line=dict(color="red", width=2, dash="dash"),
    )

    # Add annotation for completion date
    fig.add_annotation(
        x=initial_completion_date,
        y=1,
        yref="paper",
        text=f"Software Completion ({initial_completion_date})",
        showarrow=True,
        arrowhead=1,
        ax=0,
        ay=-40,
    )

    # Create steps for slider
    logger.info("Creating slider steps for different completion dates")
    steps: list[dict] = []
    for i, (completion_day, completion_date) in enumerate(
        zip(completion_days_range, completion_dates)
    ):
        # Create a step for each completion date
        step: dict = {
            "method": "update",
            "args": [
                # Update the data
                {"x": [], "y": []},
                # Update the layout
                {
                    "shapes": [
                        {
                            "type": "line",
                            "x0": completion_date,
                            "x1": completion_date,
                            "y0": 0,
                            "y1": 1,
                            "yref": "paper",
                            "line": {"color": "red", "width": 2, "dash": "dash"},
                        }
                    ],
                    "annotations": [
                        {
                            "x": completion_date,
                            "y": 1,
                            "yref": "paper",
                            "text": f"Software Completion ({completion_date})",
                            "showarrow": True,
                            "arrowhead": 1,
                            "ax": 0,
                            "ay": -40,
                        }
                    ],
                },
            ],
            "label": f"{completion_date}",
        }

        # Pre-calculate the data for this step
        logger.debug(f"Pre-calculating data for completion day {completion_day}")
        df = simulate_business(365, CONSTANTS, completion_day)

        # Convert days to dates for x-axis
        date_values: list[str] = [
            (current_date + timedelta(days=int(day))).strftime("%Y-%m-%d")
            for day in df["days_from_start"]
        ]

        # Update the x and y data for each trace
        step["args"][0]["x"] = [
            date_values,  # Monthly Revenue
            date_values,  # Accounts
            date_values,  # Steam Balance
            date_values,  # Real Balance
            date_values,  # Steam Reserve
        ]

        step["args"][0]["y"] = [
            df["monthly_revenue"].tolist(),  # Monthly Revenue
            df["accounts"].tolist(),  # Accounts
            df["steam_balance"].tolist(),  # Steam Balance
            df["real_balance"].tolist(),  # Real Balance
            df["steam_reserve"].tolist(),  # Steam Reserve
        ]

        steps.append(step)
    logger.debug(f"Created {len(steps)} slider steps")

    # Set explicit range for x-axis to ensure full width is used
    start_date = current_date.strftime("%Y-%m-%d")
    end_date = (current_date + timedelta(days=365)).strftime("%Y-%m-%d")

    # Add slider to layout with Jan 2026 as default
    sliders: list[dict] = [
        {
            "active": default_step_index,  # Set default to January 2026
            "steps": steps,
            "currentvalue": {
                "prefix": "Software Completion Date: ",
                "visible": True,
                "xanchor": "left",
            },
            "transition": {"duration": 300, "easing": "cubic-in-out"},
            "pad": {"b": 10, "t": 50},
            "len": 0.9,
            "x": 0.1,
            "y": 0,
            "yanchor": "top",
        }
    ]

    # Update layout with slider and other settings
    logger.info("Updating figure layout with slider and buttons")
    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Value",
        autosize=True,
        height=800,
        legend_title="Metrics",
        hovermode="x unified",
        sliders=sliders,
        margin=dict(
            l=50, r=50, t=150, b=150
        ),  # Increased margins for slider and buttons
        updatemenus=[
            {
                "buttons": [
                    {
                        "label": "Monthly Revenue",
                        "method": "update",
                        "args": [{"visible": [True, False, False, False, False]}],
                    },
                    {
                        "label": "Accounts",
                        "method": "update",
                        "args": [{"visible": [False, True, False, False, False]}],
                    },
                    {
                        "label": "Steam Balance",
                        "method": "update",
                        "args": [{"visible": [False, False, True, False, False]}],
                    },
                    {
                        "label": "Real Balance",
                        "method": "update",
                        "args": [{"visible": [False, False, False, True, False]}],
                    },
                    {
                        "label": "Steam Reserve",
                        "method": "update",
                        "args": [{"visible": [False, False, False, False, True]}],
                    },
                    {
                        "label": "All Metrics",
                        "method": "update",
                        "args": [{"visible": [True, True, True, True, True]}],
                    },
                ],
                "direction": "down",
                "showactive": True,
                "x": 0.1,
                "y": 1.15,
            }
        ],
    )

    # Explicitly set x-axis range to ensure lines span the entire graph
    fig.update_xaxes(range=[start_date, end_date])
    logger.debug(f"Set x-axis range from {start_date} to {end_date}")

    # Preserve visibility state when slider changes
    for step in steps:
        visible_states: list[bool | str] = [
            True,
            "legendonly",
            "legendonly",
            "legendonly",
            "legendonly",
        ]
        step["args"][0]["visible"] = visible_states

    # Show the figure with configuration options
    config: dict = {
        "responsive": True,
        "displayModeBar": True,
        "modeBarButtonsToAdd": ["toggleFullScreen"],
        "scrollZoom": True,
    }

    logger.success("Figure fully configured, displaying visualization")
    fig.show(config=config)


if __name__ == "__main__":
    main()
