import datetime
import json
import math
import os
import sys
import time

import pandas as pd
import plotly.graph_objects as go
import requests
import yaml
from ipywidgets import interact, widgets
from tqdm import tqdm


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

import plotly.io as pio

pio.renderers.default = "browser"

# Note: All calculations are done in rupees with any foreign currency prices being converted into inr

ACCOUNT_COST_STEAM_IDR_INITIAL = (
    84000  # 'ACCOUNT_COST_REAL' is how much inr is needed to buy giftcards for this
)
ACCOUNT_COST_STEAM_IDR_TOTAL = 229000
UPGRADE_COST_STEAM_IDR = 244999


def convert_idr_to_real(idr_amount):
    """
    Convert Indonesian Rupiah (IDR) to Indian Rupees (INR).

    Args:
        idr_amount (float): Amount in IDR

    Returns:
        float: Equivalent amount in INR
    """

    # Define cache file path
    cache_dir = r"C:\Users\Sivasai\Documents\GitHub\CaseFarm\utils\cache\miscellaneous"
    cache_file = os.path.join(cache_dir, "idr_to_inr_rate.json")

    # Ensure cache directory exists
    os.makedirs(cache_dir, exist_ok=True)

    # Check if we have a valid cached rate
    should_fetch_new_data = True
    if os.path.exists(cache_file):
        # Check file age
        file_age_seconds = time.time() - os.path.getmtime(cache_file)
        one_hour_in_seconds = 3600

        # If file is less than 1 hour old, use cached data
        if file_age_seconds < one_hour_in_seconds:
            try:
                with open(cache_file, "r") as f:
                    cached_data = json.load(f)
                    idr_to_inr_rate = cached_data.get("idr", {}).get("inr")

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
            data = response.json()

            # Cache the data
            with open(cache_file, "w") as f:
                json.dump(data, f)

            # Extract rate
            idr_to_inr_rate = data["idr"]["inr"]
        except Exception as e:
            logger.error(f"Error fetching currency data: {e}")

            # If we have a cache file but it's old, use it as fallback
            if os.path.exists(cache_file):
                try:
                    with open(cache_file, "r") as f:
                        cached_data = json.load(f)
                        idr_to_inr_rate = cached_data.get("idr", {}).get("inr")
                        logger.warning("Using outdated cache as fallback")
                except Exception as cache_e:
                    logger.error(f"Error reading fallback cache: {cache_e}")
                    return None
            else:
                return None

    # Convert IDR to INR
    inr_amount = idr_amount * idr_to_inr_rate

    return inr_amount


# Constants for business simulation
CONSTANTS = {
    "ACCOUNT_COST_REAL": 474.59,
    "ACCOUNT_COST_STEAM": convert_idr_to_real(
        ACCOUNT_COST_STEAM_IDR_TOTAL - ACCOUNT_COST_STEAM_IDR_INITIAL
    ),
    "UPGRADE_COST": convert_idr_to_real(UPGRADE_COST_STEAM_IDR),
    "REAL_TO_STEAM_CONVERSION_RATE": 0.9421,
}

# Shared Constants
BASE_REVENUE_WEEK = 57.3
BASE_REVENUE_DAILY = 0
MONTHLY_INVESTMENT = 9000
FIXED_COST = 1663.7
STEAM_TO_REAL_EFFICIENCY = 0.73
REAL_TO_STEAM_CONVERSION_RATE = 0.9421
HOME_COMPUTER_CAPACITY = 4
STEAM_RESERVE_PERCENTAGE = 50

# Local computer constants
LOCAL_COMPUTER_COST = 8000  # Monthly cost for a local computer
LOCAL_COMPUTER_THRESHOLD = 20  # Each local computer can support 5 accounts
LOCAL_COMPUTER_CONTRACT_MONTHS = 36  # 36-month contract
CUTTING_EDGE_CAPACITY = 40  # Capacity for cutting edge solution after completion
DERISKING_THRESHOLD = LOCAL_COMPUTER_THRESHOLD * 2

# Revenue calculation constants
redeemed_item_price = 110
redeemed_item_stars = 2
steam_tax_rate = 1.15
total_num_stars_per_pass = 40
revenue_increase_on_upgrade = (
    redeemed_item_price
    * (total_num_stars_per_pass / redeemed_item_stars)
    / steam_tax_rate
)
OLD_MAX_UPGRADES = 60
NEW_MAX_UPGRADES = 105

SIMULATION_DAYS = 500


def convert_real_to_steam(real_amount):
    return real_amount * REAL_TO_STEAM_CONVERSION_RATE


def convert_steam_to_real(steam_amount):
    return steam_amount * STEAM_TO_REAL_EFFICIENCY


class Account:
    def __init__(self, constants):
        self.upgrades = 0
        self.pending_upgrades = 0
        self.constants = constants

    def weekly_revenue_base(self):
        return BASE_REVENUE_WEEK

    def weekly_armoury_pass_revenue_without_costs(self):
        return self.upgrades * revenue_increase_on_upgrade

    def daily_revenue(self):
        return BASE_REVENUE_DAILY

    def can_upgrade(self, current_date, completion_date):
        # Determine max upgrades based on whether new software is available
        max_upgrades = (
            NEW_MAX_UPGRADES if current_date >= completion_date else OLD_MAX_UPGRADES
        )
        return (self.upgrades + self.pending_upgrades) < max_upgrades

    def get_max_upgrades(self, current_date, completion_date):
        return NEW_MAX_UPGRADES if current_date >= completion_date else OLD_MAX_UPGRADES

    def upgrade(self):
        self.pending_upgrades += 1
        return True

    def activate_upgrade(self):
        if self.pending_upgrades > 0:
            self.upgrades += 1
            self.pending_upgrades -= 1
            return True
        return False


def simulate_business(simulation_days, constants, completion_days_from_now):
    start_date = datetime.date.today()
    end_date = start_date + datetime.timedelta(days=simulation_days)
    casual_farm_completion_date = start_date + datetime.timedelta(
        days=completion_days_from_now
    )

    accounts = []
    steam_balance = 0.0
    steam_reserve = 0.0
    real_balance = 0.0
    daily_stats = []

    # Track local computer contracts: (purchase_date, remaining_months)
    local_computer_contracts = []

    # Dictionaries for scheduling:
    weekly_rev_schedule = {}
    daily_rev_schedule = {}
    upgrade_schedule = {}

    # Calculate total days for the progress bar
    total_days = (end_date - start_date).days + 1

    # Use tqdm to wrap the date iteration
    current_date = start_date
    for _ in tqdm(range(total_days - 1), desc="Simulating business"):
        # Weekly revenue scheduling
        if current_date.weekday() == 2:
            base_weekly_rev = sum(
                acc.weekly_revenue_base()
                for acc in accounts
                if getattr(acc, "activation_date", current_date) <= current_date
            )
            scheduled_date_base = current_date
            weekly_rev_schedule[scheduled_date_base] = (
                weekly_rev_schedule.get(scheduled_date_base, 0) + base_weekly_rev
            )

            armoury_rev = sum(
                (
                    acc.weekly_armoury_pass_revenue_without_costs()
                    - acc.upgrades * constants["UPGRADE_COST"]
                )
                for acc in accounts
                if getattr(acc, "activation_date", current_date) <= current_date
            )
            scheduled_date_armoury = current_date + datetime.timedelta(days=7)
            weekly_rev_schedule[scheduled_date_armoury] = (
                weekly_rev_schedule.get(scheduled_date_armoury, 0) + armoury_rev
            )

        # Process scheduled events
        if current_date in upgrade_schedule:
            for candidate, num_upgrades in upgrade_schedule[current_date]:
                for _ in range(num_upgrades):
                    candidate.activate_upgrade()
            del upgrade_schedule[current_date]

        if current_date in weekly_rev_schedule:
            steam_balance += weekly_rev_schedule[current_date]
            del weekly_rev_schedule[current_date]

        if current_date in daily_rev_schedule:
            steam_balance += daily_rev_schedule[current_date]
            del daily_rev_schedule[current_date]

        # Calculate daily revenue
        daily_rev = sum(
            acc.daily_revenue()
            for acc in accounts
            if getattr(acc, "activation_date", current_date) <= current_date
        )

        # Weekly revenue scheduling
        if current_date.weekday() == 2:
            base_weekly_rev = sum(
                acc.weekly_revenue_base()
                for acc in accounts
                if getattr(acc, "activation_date", current_date) <= current_date
            )
            scheduled_date_base = current_date + datetime.timedelta(days=7)
            weekly_rev_schedule[scheduled_date_base] = (
                weekly_rev_schedule.get(scheduled_date_base, 0) + base_weekly_rev
            )

            armoury_rev = sum(
                (
                    acc.weekly_armoury_pass_revenue_without_costs()
                    - acc.upgrades * constants["UPGRADE_COST"]
                )
                for acc in accounts
                if getattr(acc, "activation_date", current_date) <= current_date
            )
            scheduled_date_armoury = current_date + datetime.timedelta(days=14)
            weekly_rev_schedule[scheduled_date_armoury] = (
                weekly_rev_schedule.get(scheduled_date_armoury, 0) + armoury_rev
            )

        # Determine computer capacity based on whether we've reached completion date
        home_capacity = HOME_COMPUTER_CAPACITY
        # If completion date has passed, use cutting edge capacity for new computers
        account_threshold = (
            CUTTING_EDGE_CAPACITY
            if current_date >= casual_farm_completion_date
            else LOCAL_COMPUTER_THRESHOLD
        )

        # Monthly expenses and computer management
        if current_date.day == 1:
            real_balance += MONTHLY_INVESTMENT

            # Calculate license costs
            num_accounts = len(accounts)
            num_licenses = (
                math.ceil(num_accounts / account_threshold) if num_accounts > 0 else 0
            )
            license_cost = num_licenses * FIXED_COST

            # Calculate how many local computers we need
            extra_accounts = max(0, num_accounts - home_capacity)
            required_local_computers = (
                math.ceil(extra_accounts / account_threshold)
                if extra_accounts > 0
                else 0
            )

            # Purchase new local computers if needed
            if required_local_computers > len(local_computer_contracts):
                new_computers_needed = required_local_computers - len(
                    local_computer_contracts
                )
                for _ in range(new_computers_needed):
                    local_computer_contracts.append(
                        (current_date, LOCAL_COMPUTER_CONTRACT_MONTHS)
                    )

            # Pay for existing local computer contracts
            local_computer_cost = 0
            updated_contracts = []
            for purchase_date, remaining_months in local_computer_contracts:
                if remaining_months > 0:
                    local_computer_cost += LOCAL_COMPUTER_COST
                    updated_contracts.append((purchase_date, remaining_months - 1))
            local_computer_contracts = updated_contracts

            total_expenses = license_cost + local_computer_cost

            # Handle fund shortages
            if real_balance < total_expenses:
                needed = total_expenses - real_balance
                required_steam = needed / STEAM_TO_REAL_EFFICIENCY
                if steam_balance >= required_steam:
                    steam_balance -= required_steam
                    real_balance += needed
                else:
                    available_steam = steam_balance
                    steam_balance = 0
                    converted_amount = available_steam * STEAM_TO_REAL_EFFICIENCY
                    real_balance += converted_amount

            real_balance -= total_expenses

        # Investment logic
        fully_invested = False
        while not fully_invested:
            candidate = None
            for acc in accounts:
                if acc.can_upgrade(current_date, casual_farm_completion_date):
                    candidate = acc
                    break

            # EXISTING DERISKING LOGIC
            derisk_threshold = (
                CUTTING_EDGE_CAPACITY * 2
                if current_date >= casual_farm_completion_date
                else DERISKING_THRESHOLD
            )
            if (
                candidate is None
                and len(accounts) > home_capacity
                and ((len(accounts) - home_capacity) >= derisk_threshold)
            ):
                account_value = (
                    constants["ACCOUNT_COST_REAL"] / STEAM_TO_REAL_EFFICIENCY
                    + constants["ACCOUNT_COST_STEAM"]
                    + 5 * constants["UPGRADE_COST"]
                )
                target_steam = (
                    (STEAM_RESERVE_PERCENTAGE / 100) * len(accounts) * account_value
                )

                if steam_reserve < target_steam:
                    if steam_balance + steam_reserve < target_steam:
                        needed_steam = target_steam - (steam_balance + steam_reserve)
                        required_real = needed_steam / REAL_TO_STEAM_CONVERSION_RATE
                        if real_balance >= required_real:
                            real_balance -= required_real
                            steam_balance += convert_real_to_steam(required_real)
                            fully_invested = True
                            continue
                        else:
                            steam_balance += convert_real_to_steam(real_balance)
                            real_balance = 0
                            fully_invested = True
                            continue
                    else:
                        to_transfer = target_steam - steam_reserve
                        steam_balance -= to_transfer
                        steam_reserve += to_transfer
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
                    candidate.activation_date = current_date + datetime.timedelta(
                        days=7
                    )
                    accounts.append(candidate)
                else:
                    if real_balance < constants["ACCOUNT_COST_REAL"]:
                        needed = constants["ACCOUNT_COST_REAL"] - real_balance
                        required_steam = needed / STEAM_TO_REAL_EFFICIENCY
                        if (
                            steam_balance
                            >= required_steam + constants["ACCOUNT_COST_STEAM"]
                        ):
                            steam_balance -= required_steam
                            real_balance += needed
                            real_balance -= constants["ACCOUNT_COST_REAL"]
                            steam_balance -= constants["ACCOUNT_COST_STEAM"]
                            candidate = Account(constants)
                            candidate.activation_date = (
                                current_date + datetime.timedelta(days=7)
                            )
                            accounts.append(candidate)
                            continue
                        else:
                            fully_invested = True
                            continue
                    elif steam_balance < constants["ACCOUNT_COST_STEAM"]:
                        needed = constants["ACCOUNT_COST_STEAM"] - steam_balance
                        required_real = needed / REAL_TO_STEAM_CONVERSION_RATE
                        if (
                            real_balance
                            >= required_real + constants["ACCOUNT_COST_REAL"]
                        ):
                            real_balance -= required_real
                            steam_balance += convert_real_to_steam(required_real)
                            real_balance -= constants["ACCOUNT_COST_REAL"]
                            steam_balance -= constants["ACCOUNT_COST_STEAM"]
                            candidate = Account(constants)
                            candidate.activation_date = (
                                current_date + datetime.timedelta(days=7)
                            )
                            accounts.append(candidate)
                        else:
                            fully_invested = True
                            continue

            # Scheduling upgrades
            if candidate is not None and candidate.can_upgrade(
                current_date, casual_farm_completion_date
            ):
                max_possible_upgrades = candidate.get_max_upgrades(
                    current_date, casual_farm_completion_date
                ) - (candidate.upgrades + candidate.pending_upgrades)
                max_affordable_upgrades = math.floor(
                    steam_balance / constants["UPGRADE_COST"]
                )

                if max_affordable_upgrades == 0:
                    needed_steam = constants["UPGRADE_COST"] - steam_balance
                    required_real = needed_steam / REAL_TO_STEAM_CONVERSION_RATE
                    if real_balance >= required_real:
                        real_balance -= required_real
                        steam_balance += convert_real_to_steam(required_real)
                        max_affordable_upgrades = math.floor(
                            steam_balance / constants["UPGRADE_COST"]
                        )
                    else:
                        fully_invested = True
                        continue

                if max_affordable_upgrades > 0:
                    num_upgrades = min(max_possible_upgrades, max_affordable_upgrades)
                    total_cost = num_upgrades * constants["UPGRADE_COST"]
                    steam_balance -= total_cost

                    scheduled_date_upgrade = current_date + datetime.timedelta(days=7)
                    if scheduled_date_upgrade not in upgrade_schedule:
                        upgrade_schedule[scheduled_date_upgrade] = []

                    for _ in range(num_upgrades):
                        candidate.upgrade()

                    upgrade_schedule[scheduled_date_upgrade].append(
                        (candidate, num_upgrades)
                    )
                else:
                    fully_invested = True
                    break
            else:
                fully_invested = True

        # Collect daily stats
        weekly_rev_stat = sum(
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
        num_licenses = (
            math.ceil(len(accounts) / account_threshold) if len(accounts) > 0 else 0
        )
        license_cost = num_licenses * FIXED_COST
        local_computer_cost = (
            len([c for c in local_computer_contracts if c[1] > 0]) * LOCAL_COMPUTER_COST
        )
        total_expenses = license_cost + local_computer_cost

        monthly_revenue = (
            (365 / 12) * daily_rev + (365 / (12 * 7)) * weekly_rev_stat - total_expenses
        )

        # Store days from start for easier plotting
        days_from_start = (current_date - start_date).days

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

        current_date += datetime.timedelta(days=1)

    # Convert to DataFrame for easier manipulation
    return pd.DataFrame(daily_stats)


def plot_simulation(completion_days=180, simulation_days=SIMULATION_DAYS):
    """Run simulation and plot results with completion date marker"""
    # Run simulation
    df = simulate_business(simulation_days, CONSTANTS, completion_days)

    # Create figure
    fig = go.Figure()

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

    # Find the completion date in the dataframe
    completion_row = df[df["is_completion_date"]]
    if not completion_row.empty:
        completion_day = completion_row.iloc[0]["days_from_start"]

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

    # Update layout
    fig.update_layout(
        xaxis_title="Days from Start",
        yaxis_title="Value",
        height=600,
        legend_title="Metrics",
        hovermode="x unified",
    )

    return fig


def interactive_plot():
    """Create an interactive widget to adjust completion date"""
    # Define the widget
    completion_slider = widgets.IntSlider(
        min=30,
        max=SIMULATION_DAYS,
        step=30,
        description="Completion Day:",
        continuous_update=False,
    )

    # Create the interactive plot
    interact(
        plot_simulation,
        completion_days=completion_slider,
        simulation_days=widgets.fixed(),
    )


def main():
    """
    Main function to run the simulation with an interactive slider
    for software completion date
    """
    # Import required libraries
    from datetime import datetime, timedelta

    import plotly.graph_objects as go

    # Define current date and date range for simulation
    current_date = datetime(2025, 3, 18)

    # Define range of completion days to simulate (from day 30 to day 345)
    min_completion_day = 30
    max_completion_day = SIMULATION_DAYS
    step = 30
    completion_days_range = list(
        range(min_completion_day, max_completion_day + 1, step)
    )

    # Calculate days to January 1, 2026
    jan_1_2026 = datetime(2026, 1, 1)
    days_to_jan_1_2026 = (jan_1_2026 - current_date).days

    # Find the closest value in completion_days_range
    default_step_index = min(
        range(len(completion_days_range)),
        key=lambda i: abs(completion_days_range[i] - days_to_jan_1_2026),
    )

    # Create corresponding date objects for display
    completion_dates = [
        (current_date + timedelta(days=day)).strftime("%Y-%m-%d")
        for day in completion_days_range
    ]

    # Create empty figure that will be populated based on slider position
    fig = go.Figure()

    # Add initial traces for the first simulation with Jan 2026 completion
    initial_completion_day = completion_days_range[default_step_index]
    initial_df = simulate_business(SIMULATION_DAYS, CONSTANTS, initial_completion_day)

    # Convert day numbers to actual dates for x-axis
    date_x_values = [
        (current_date + timedelta(days=int(day))).strftime("%Y-%m-%d")
        for day in initial_df["days_from_start"]
    ]

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

    # Initial completion date is now set to Jan 2026
    initial_completion_date = (
        current_date + timedelta(days=initial_completion_day)
    ).strftime("%Y-%m-%d")

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
    steps = []
    for i, (completion_day, completion_date) in enumerate(
        zip(completion_days_range, completion_dates)
    ):
        # Create a step for each completion date
        step = {
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
        df = simulate_business(SIMULATION_DAYS, CONSTANTS, completion_day)

        # Convert days to dates for x-axis
        date_values = [
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

    # Set explicit range for x-axis to ensure full width is used
    start_date = current_date.strftime("%Y-%m-%d")
    end_date = (current_date + timedelta(days=SIMULATION_DAYS)).strftime("%Y-%m-%d")

    # Add slider to layout with Jan 2026 as default
    sliders = [
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

    # Preserve visibility state when slider changes
    for step in steps:
        visible_states = [True, "legendonly", "legendonly", "legendonly", "legendonly"]
        step["args"][0]["visible"] = visible_states

    # Show the figure with configuration options
    config = {
        "responsive": True,
        "displayModeBar": True,
        "modeBarButtonsToAdd": ["toggleFullScreen"],
        "scrollZoom": True,
    }

    fig.show(config=config)


if __name__ == "__main__":
    main()
