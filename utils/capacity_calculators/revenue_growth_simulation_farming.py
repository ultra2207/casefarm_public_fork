import datetime
import math
import sys

import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots
from tqdm import tqdm

pio.renderers.default = "browser"
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


SIMULATION_DAYS = 500


def handle_derisking(
    accounts_spent: int,
    balance_steam: float,
    balance_real: float,
    steam_reserve: float,
    PRIME_CONSTANTS: dict[str, float],
    STEAM_TO_REAL_EFFICIENCY: float,
    REAL_TO_STEAM_CONVERSION_RATE: float,
) -> tuple[float, float, float, bool]:
    """Handle derisking logic when account threshold is reached based on spent accounts"""
    steam_reserves_full = True
    target_steam_reserve = (
        0.2
        * accounts_spent
        * (
            (PRIME_CONSTANTS["ACCOUNT_COST_REAL"] / STEAM_TO_REAL_EFFICIENCY)
            + PRIME_CONSTANTS["ACCOUNT_COST_STEAM"]
        )
    )
    required_steam_reserve = target_steam_reserve - steam_reserve

    if steam_reserve < target_steam_reserve:
        steam_reserves_full = False
        if balance_steam >= required_steam_reserve:
            balance_steam -= required_steam_reserve
            steam_reserve += required_steam_reserve
            steam_reserves_full = True
            logger.debug(
                f"Added {required_steam_reserve:.2f} to steam reserve, now at {steam_reserve:.2f}"
            )
        else:
            # Convert all real to steam and add to reserve
            balance_steam += balance_real * REAL_TO_STEAM_CONVERSION_RATE
            steam_reserve += balance_steam
            logger.debug(
                f"Converted all real balance and added {balance_steam:.2f} to steam reserve, now at {steam_reserve:.2f}"
            )
            balance_steam = 0
            balance_real = 0

    return balance_steam, balance_real, steam_reserve, steam_reserves_full


def try_create_account(
    balance_steam: float,
    balance_real: float,
    PRIME_CONSTANTS: dict[str, float],
    STEAM_TO_REAL_EFFICIENCY: float,
    REAL_TO_STEAM_CONVERSION_RATE: float,
) -> tuple[float, float, bool]:
    """Attempt to create a new account using available funds"""

    # Direct creation if enough in both currencies
    if (
        balance_steam >= PRIME_CONSTANTS["ACCOUNT_COST_STEAM"]
        and balance_real >= PRIME_CONSTANTS["ACCOUNT_COST_REAL"]
    ):
        balance_steam -= PRIME_CONSTANTS["ACCOUNT_COST_STEAM"]
        balance_real -= PRIME_CONSTANTS["ACCOUNT_COST_REAL"]
        logger.debug(
            f"Created account using direct funds: steam -{PRIME_CONSTANTS['ACCOUNT_COST_STEAM']}, real -{PRIME_CONSTANTS['ACCOUNT_COST_REAL']}"
        )
        return balance_steam, balance_real, True

    # Try converting steam to real
    elif balance_steam >= PRIME_CONSTANTS["ACCOUNT_COST_STEAM"]:
        missing_real = PRIME_CONSTANTS["ACCOUNT_COST_REAL"] - balance_real
        required_steam = missing_real / STEAM_TO_REAL_EFFICIENCY
        if balance_steam >= PRIME_CONSTANTS["ACCOUNT_COST_STEAM"] + required_steam:
            balance_steam -= required_steam
            balance_real += required_steam * STEAM_TO_REAL_EFFICIENCY
            balance_steam -= PRIME_CONSTANTS["ACCOUNT_COST_STEAM"]
            balance_real -= PRIME_CONSTANTS["ACCOUNT_COST_REAL"]
            logger.debug(
                f"Created account by converting {required_steam:.2f} steam to real"
            )
            return balance_steam, balance_real, True

    # Try converting real to steam
    elif balance_real >= PRIME_CONSTANTS["ACCOUNT_COST_REAL"]:
        missing_steam = PRIME_CONSTANTS["ACCOUNT_COST_STEAM"] - balance_steam
        required_real = missing_steam / REAL_TO_STEAM_CONVERSION_RATE
        if balance_real >= PRIME_CONSTANTS["ACCOUNT_COST_REAL"] + required_real:
            balance_real -= required_real
            balance_steam += required_real * REAL_TO_STEAM_CONVERSION_RATE
            balance_steam -= PRIME_CONSTANTS["ACCOUNT_COST_STEAM"]
            balance_real -= PRIME_CONSTANTS["ACCOUNT_COST_REAL"]
            logger.debug(
                f"Created account by converting {required_real:.2f} real to steam"
            )
            return balance_steam, balance_real, True

    logger.trace("Insufficient funds to create a new account")
    return balance_steam, balance_real, False


def calculate_monthly_revenue(
    active_prime_accounts: int,
    PRIME_CONSTANTS: dict[str, float],
    STEAM_TO_REAL_EFFICIENCY: float,
) -> float:
    """Calculate monthly revenue based on active accounts"""
    total_accounts = active_prime_accounts
    return STEAM_TO_REAL_EFFICIENCY * (
        total_accounts
        * (
            PRIME_CONSTANTS["BASE_REVENUE_WEEK"] * (365 / (7 * 12))
            + PRIME_CONSTANTS["BASE_REVENUE_DAILY"] * (365 / 12)
        )
    )


def main() -> None:
    # Initialize simulation parameters
    start_date = datetime.date.today()
    logger.info(f"Starting simulation from {start_date} for {SIMULATION_DAYS} days")

    # Instead of one prime account counter, we separate spending from activation:
    active_prime_accounts: int = (
        0  # Prime accounts that are active and generate revenue
    )
    pending_prime_accounts: list[
        datetime.date
    ] = []  # List of activation dates for accounts created but not active yet

    PRIME_CONSTANTS: dict[str, float] = {
        "ACCOUNT_COST_STEAM": 820,
        "ACCOUNT_COST_REAL": 420.42,
        "BASE_REVENUE_WEEK": 57.3,
        "BASE_REVENUE_DAILY": 0,
    }

    # Infrastructure constants
    SINGLE_LICENSE_FEE: float = 1663.7
    SHADOW_TECH_PROVIDER_PRICE: float = 4338
    # The initial free cloud computers are now set to 38
    HOME_COMPUTER_CAPACITY: int = 38
    CLOUD_COMPUTER_THRESHOLD: int = 200
    CLOUD_MACHINES_IN_PROVIDER_PRICE: float = 2379
    CLOUD_MACHINES_IN_QUANTITY: int = 6

    # Conversion rates
    STEAM_TO_REAL_EFFICIENCY: float = 0.7753
    REAL_TO_STEAM_CONVERSION_RATE: float = 1.02

    # Initialize balances
    balance_steam: float = 0.0
    balance_real: float = 0.0
    steam_reserve: float = 0.0
    # cloud_computers variable is not used outside monthly cost calculation

    # Lists to hold delayed revenue events.
    # Each entry is a tuple: (release_date, amount)
    pending_prime_revenue: list[
        tuple[datetime.date, float]
    ] = []  # For weekly prime revenue (available after 7 days)

    # Recording lists for plotting
    dates: list[datetime.date] = []
    prime_account_history: list[int] = []
    monthly_revenue_history: list[float] = []
    steam_reserve_history: list[float] = []

    logger.info("Starting day-by-day simulation")
    for day in tqdm(range(SIMULATION_DAYS)):
        current_date = start_date + datetime.timedelta(days=day)

        # ===== Process matured delayed revenue events =====
        matured_prime = [
            event for event in pending_prime_revenue if event[0] <= current_date
        ]
        pending_prime_revenue = [
            event for event in pending_prime_revenue if event[0] > current_date
        ]
        for _, amount in matured_prime:
            balance_steam += amount

        if matured_prime:
            logger.trace(
                f"Day {day}: Processed {len(matured_prime)} matured revenue events"
            )

        # ===== Activate pending prime accounts =====
        activated = [d for d in pending_prime_accounts if d <= current_date]
        if activated:
            active_prime_accounts += len(activated)
            logger.debug(
                f"Day {day}: Activated {len(activated)} new prime accounts, total active: {active_prime_accounts}"
            )
            pending_prime_accounts = [
                d for d in pending_prime_accounts if d > current_date
            ]

        # ===== Daily revenue (only active accounts produce revenue) =====
        daily_prime_revenue = (
            active_prime_accounts * PRIME_CONSTANTS["BASE_REVENUE_DAILY"]
        )
        balance_steam += daily_prime_revenue

        # ===== Monthly cloud computer costs and monthly real rupee addition =====
        if current_date.day == 1:
            # Add 9000 real rupees every month on the first
            balance_real += 9000
            logger.info(
                f"Day {day}: Monthly addition of 9000 to real balance, new balance: {balance_real:.2f}"
            )

            # Calculate additional cloud computers needed based on risk exposure
            num_licenses = (
                math.ceil(active_prime_accounts / CLOUD_COMPUTER_THRESHOLD)
                if active_prime_accounts > 0
                else 0
            )
            license_cost = num_licenses * SINGLE_LICENSE_FEE

            extra_accounts = max(0, active_prime_accounts - HOME_COMPUTER_CAPACITY)
            num_cloud_computers = (
                math.ceil(extra_accounts / CLOUD_COMPUTER_THRESHOLD)
                if extra_accounts > 0
                else 0
            )

            if num_cloud_computers <= CLOUD_MACHINES_IN_QUANTITY:
                cloud_cost = num_cloud_computers * CLOUD_MACHINES_IN_PROVIDER_PRICE
            else:
                cloud_cost = (
                    CLOUD_MACHINES_IN_QUANTITY * CLOUD_MACHINES_IN_PROVIDER_PRICE
                    + (num_cloud_computers - CLOUD_MACHINES_IN_QUANTITY)
                    * SHADOW_TECH_PROVIDER_PRICE
                )
            total_expenses = license_cost + cloud_cost
            logger.info(
                f"Day {day}: Monthly expenses - licenses: {license_cost:.2f}, cloud: {cloud_cost:.2f}"
            )

            if balance_real < total_expenses:
                needed_to_convert = (
                    total_expenses - balance_real
                ) / STEAM_TO_REAL_EFFICIENCY
                if balance_steam >= needed_to_convert:
                    balance_steam -= needed_to_convert
                    balance_real = 0
                    logger.debug(
                        f"Day {day}: Converted {needed_to_convert:.2f} steam to cover expenses"
                    )
                else:
                    balance_real += balance_steam * STEAM_TO_REAL_EFFICIENCY
                    logger.warning(
                        f"Day {day}: Converted all steam balance but still insufficient for expenses"
                    )
                    balance_steam = 0

            balance_real -= total_expenses
            logger.debug(
                f"Day {day}: Paid {total_expenses:.2f} in expenses, remaining real balance: {balance_real:.2f}"
            )

        # ===== Wednesday processing: schedule weekly revenue and account creation =====
        if current_date.weekday() == 2:  # Wednesday
            steam_reserves_full = True
            # Calculate weekly revenue amounts
            weekly_prime_revenue = (
                active_prime_accounts * PRIME_CONSTANTS["BASE_REVENUE_WEEK"]
            )
            # Instead of instantly adding, schedule the prime revenue to be available after 7 days
            pending_prime_revenue.append(
                (current_date + datetime.timedelta(days=7), weekly_prime_revenue)
            )
            logger.trace(
                f"Day {day}: Scheduled {weekly_prime_revenue:.2f} prime revenue for {current_date + datetime.timedelta(days=7)}"
            )

            # Attempt to create new accounts as long as funds allow
            accounts_created = 0
            while steam_reserves_full:
                if active_prime_accounts >= 3 * CLOUD_COMPUTER_THRESHOLD:
                    balance_steam, balance_real, steam_reserve, steam_reserves_full = (
                        handle_derisking(
                            active_prime_accounts,
                            balance_steam,
                            balance_real,
                            steam_reserve,
                            PRIME_CONSTANTS,
                            STEAM_TO_REAL_EFFICIENCY,
                            REAL_TO_STEAM_CONVERSION_RATE,
                        )
                    )

                balance_steam, balance_real, success = try_create_account(
                    balance_steam,
                    balance_real,
                    PRIME_CONSTANTS,
                    STEAM_TO_REAL_EFFICIENCY,
                    REAL_TO_STEAM_CONVERSION_RATE,
                )

                if not success:
                    break

                pending_prime_accounts.append(
                    current_date + datetime.timedelta(days=9.9)
                )
                accounts_created += 1

            if accounts_created > 0:
                logger.success(
                    f"Day {day}: Created {accounts_created} new pending prime accounts"
                )

        # ===== Record metrics for plotting =====
        monthly_revenue = calculate_monthly_revenue(
            active_prime_accounts, PRIME_CONSTANTS, STEAM_TO_REAL_EFFICIENCY
        )

        dates.append(current_date)
        # For plotting, show total revenue-producing accounts (active plus armoury)
        prime_account_history.append(active_prime_accounts)
        monthly_revenue_history.append(monthly_revenue)
        steam_reserve_history.append(steam_reserve)

    logger.info(
        f"Simulation completed. Final active prime accounts: {active_prime_accounts}"
    )
    logger.info(f"Final monthly revenue: {monthly_revenue_history[-1]:.2f}")
    logger.info(f"Final steam reserve: {steam_reserve:.2f}")

    # Create and show plots
    fig = make_subplots(
        rows=3,
        cols=1,
        subplot_titles=[
            "Active Prime Accounts Over Time",
            "Monthly Revenue Over Time",
            "Steam Reserves Over Time",
        ],
    )

    fig.add_trace(
        go.Scatter(
            x=dates, y=prime_account_history, mode="lines", name="Active Prime Accounts"
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=dates, y=monthly_revenue_history, mode="lines", name="Monthly Revenue"
        ),
        row=2,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=dates, y=steam_reserve_history, mode="lines", name="Steam Reserves"
        ),
        row=3,
        col=1,
    )

    fig.update_layout(
        height=900,
        title_text="Simulation Results",
        xaxis_title="Date",
        hovermode="x unified",
    )

    fig.update_yaxes(title_text="Active Prime Accounts", row=1, col=1)
    fig.update_yaxes(title_text="Monthly Revenue", row=2, col=1)
    fig.update_yaxes(title_text="Steam Reserves", row=3, col=1)

    fig.show()


if __name__ == "__main__":
    main()
