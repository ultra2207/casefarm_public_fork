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

import datetime
import math

import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots
from tqdm import tqdm

pio.renderers.default = "browser"

# End date is June 7, 2030

SIMULATION_DAYS = 1200


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
        0.5
        * accounts_spent
        * (
            (PRIME_CONSTANTS["ACCOUNT_COST_REAL"] / STEAM_TO_REAL_EFFICIENCY)
            + PRIME_CONSTANTS["ACCOUNT_COST_STEAM"]
        )
    )
    required_steam_reserve = target_steam_reserve - steam_reserve

    logger.trace(
        f"Derisking check: target reserve {target_steam_reserve:.2f}, required {required_steam_reserve:.2f}"
    )

    if steam_reserve < target_steam_reserve:
        steam_reserves_full = False
        if balance_steam >= required_steam_reserve:
            balance_steam -= required_steam_reserve
            steam_reserve += required_steam_reserve
            steam_reserves_full = True
            logger.debug(f"Steam reserves replenished: {steam_reserve:.2f}")
        else:
            # Convert all real to steam and add to reserve
            balance_steam += balance_real * REAL_TO_STEAM_CONVERSION_RATE
            steam_reserve += balance_steam
            balance_steam = 0
            balance_real = 0
            logger.info(
                f"Converting all real to steam for reserves: {steam_reserve:.2f}"
            )

    return balance_steam, balance_real, steam_reserve, steam_reserves_full


def try_create_account(
    balance_steam: float,
    balance_real: float,
    PRIME_CONSTANTS: dict[str, float],
    STEAM_TO_REAL_EFFICIENCY: float,
    REAL_TO_STEAM_CONVERSION_RATE: float,
) -> tuple[float, float, bool]:
    """Attempt to create a new account using available funds"""

    logger.trace(
        f"Attempting account creation - Steam: {balance_steam:.2f}, Real: {balance_real:.2f}"
    )

    # Direct creation if enough in both currencies
    if (
        balance_steam >= PRIME_CONSTANTS["ACCOUNT_COST_STEAM"]
        and balance_real >= PRIME_CONSTANTS["ACCOUNT_COST_REAL"]
    ):
        balance_steam -= PRIME_CONSTANTS["ACCOUNT_COST_STEAM"]
        balance_real -= PRIME_CONSTANTS["ACCOUNT_COST_REAL"]
        logger.debug("Account created with direct funds")
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
            logger.debug("Account created via steam-to-real conversion")
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
            logger.debug("Account created via real-to-steam conversion")
            return balance_steam, balance_real, True

    logger.debug("Insufficient funds for account creation")
    return balance_steam, balance_real, False


def calculate_monthly_revenue(
    active_prime_accounts: int,
    armoury_accounts: int,
    armoury_profit_weekly: float,
    PRIME_CONSTANTS: dict[str, float],
    STEAM_TO_REAL_EFFICIENCY: float,
) -> float:
    """Calculate monthly revenue based on active accounts"""
    total_accounts = active_prime_accounts + armoury_accounts
    return STEAM_TO_REAL_EFFICIENCY * (
        total_accounts
        * (
            PRIME_CONSTANTS["BASE_REVENUE_WEEK"] * (365 / (7 * 12))
            + PRIME_CONSTANTS["BASE_REVENUE_DAILY"] * (365 / 12)
        )
        + (armoury_profit_weekly * (365 / (7 * 12)))
    )


def main() -> None:
    # Initialize simulation parameters
    start_date = datetime.date(
        2027, 5, 5
    )  # May 5 2027 marks the end of stage 1 and the start of stage 2

    logger.info(f"Starting simulation from {start_date} for {SIMULATION_DAYS} days")

    # Armoury data
    armoury_accounts = 600
    armoury_crate_price = 83
    armoury_profit_weekly = (
        armoury_accounts * 55 * (((armoury_crate_price * 20) / 1.15) - 1350)
    )

    logger.debug(
        f"Initialized with {armoury_accounts} armoury accounts, weekly profit: {armoury_profit_weekly:.2f}"
    )

    # Instead of one prime account counter, we separate spending from activation:
    active_prime_accounts = 0  # Prime accounts that are active and generate revenue
    pending_prime_accounts: list[
        datetime.date
    ] = []  # List of activation dates for accounts created but not active yet

    PRIME_CONSTANTS = {
        "ACCOUNT_COST_STEAM": 820,
        "ACCOUNT_COST_REAL": 424.71,
        "BASE_REVENUE_WEEK": 57.3,
        "BASE_REVENUE_DAILY": 0,
    }

    # Infrastructure constants
    SINGLE_LICENSE_FEE = 1663.7
    SHADOW_TECH_PROVIDER_PRICE = 4338
    INITIAL_CLOUD_COMPUTERS = 125
    CLOUD_COMPUTER_THRESHOLD = 200

    # Conversion rates
    STEAM_TO_REAL_EFFICIENCY = 0.73
    REAL_TO_STEAM_CONVERSION_RATE = 1.06

    # Initialize balances
    balance_steam = 0.0
    balance_real = 0.0
    # armoury_steam_reserve = 16.75 * 10**6  # not touched, here for reference
    steam_reserve = 0.0
    cloud_computers = INITIAL_CLOUD_COMPUTERS

    # Lists to hold delayed revenue events.
    # Each entry is a tuple: (release_date, amount)
    pending_prime_revenue: list[
        tuple[datetime.date, float]
    ] = []  # For weekly prime revenue (available after 7 days)
    pending_armoury_revenue: list[
        tuple[datetime.date, float]
    ] = []  # For armoury profit (available after 14 days)

    # Recording lists for plotting
    dates: list[datetime.date] = []
    prime_account_history: list[int] = []
    monthly_revenue_history: list[float] = []
    steam_reserve_history: list[float] = []

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
            logger.trace(
                f"Received prime revenue: {amount:.2f}, new steam balance: {balance_steam:.2f}"
            )

        matured_armoury = [
            event for event in pending_armoury_revenue if event[0] <= current_date
        ]
        pending_armoury_revenue = [
            event for event in pending_armoury_revenue if event[0] > current_date
        ]
        for _, amount in matured_armoury:
            balance_steam += amount
            logger.trace(
                f"Received armoury revenue: {amount:.2f}, new steam balance: {balance_steam:.2f}"
            )

        # ===== Activate pending prime accounts =====
        activated = [d for d in pending_prime_accounts if d <= current_date]
        if activated:
            active_prime_accounts += len(activated)
            pending_prime_accounts = [
                d for d in pending_prime_accounts if d > current_date
            ]
            logger.debug(
                f"Activated {len(activated)} accounts, total active: {active_prime_accounts}"
            )

        # ===== Daily revenue (only active accounts produce revenue) =====
        daily_prime_revenue = (
            active_prime_accounts + armoury_accounts
        ) * PRIME_CONSTANTS["BASE_REVENUE_DAILY"]
        balance_steam += daily_prime_revenue

        # ===== Monthly cloud computer costs =====
        if current_date.day == 1:
            cloud_computers = (
                math.ceil(active_prime_accounts / CLOUD_COMPUTER_THRESHOLD)
                + INITIAL_CLOUD_COMPUTERS
            )
            real_cost = cloud_computers * (
                SHADOW_TECH_PROVIDER_PRICE + SINGLE_LICENSE_FEE
            )

            logger.info(
                f"Monthly costs: {cloud_computers} computers at {real_cost:.2f}"
            )

            if balance_real < real_cost:
                needed_to_convert = (
                    real_cost - balance_real
                ) / STEAM_TO_REAL_EFFICIENCY
                if balance_steam >= needed_to_convert:
                    balance_steam -= needed_to_convert
                    balance_real = 0
                    logger.debug(
                        f"Converting {needed_to_convert:.2f} steam to cover costs"
                    )
                else:
                    balance_real += balance_steam * STEAM_TO_REAL_EFFICIENCY
                    balance_steam = 0
                    logger.warning(
                        "Insufficient steam to cover costs, converted all available"
                    )
            balance_real -= real_cost

        # ===== Wednesday processing: schedule weekly revenue and account creation =====
        if current_date.weekday() == 2:  # Wednesday
            steam_reserves_full = True
            # Calculate weekly revenue amounts
            weekly_prime_revenue = (
                active_prime_accounts + armoury_accounts
            ) * PRIME_CONSTANTS["BASE_REVENUE_WEEK"]
            # Instead of instantly adding, schedule the prime revenue to be available after 7 days
            pending_prime_revenue.append(
                (current_date + datetime.timedelta(days=7), weekly_prime_revenue)
            )
            # Schedule armoury profit revenue to be available after 14 days
            pending_armoury_revenue.append(
                (current_date + datetime.timedelta(days=14), armoury_profit_weekly)
            )

            logger.trace(
                f"Scheduled weekly revenue: Prime {weekly_prime_revenue:.2f}, Armoury {armoury_profit_weekly:.2f}"
            )

            # Attempt to create new accounts as long as funds allow
            accounts_created = 0
            while steam_reserves_full:
                balance_steam, balance_real, success = try_create_account(
                    balance_steam,
                    balance_real,
                    PRIME_CONSTANTS,
                    STEAM_TO_REAL_EFFICIENCY,
                    REAL_TO_STEAM_CONVERSION_RATE,
                )

                if not success:
                    break
                # Schedule the account to become active 7 days later
                pending_prime_accounts.append(current_date + datetime.timedelta(days=7))
                accounts_created += 1

                # Trigger derisking if the threshold is reached (using spent accounts)
                if active_prime_accounts >= CLOUD_COMPUTER_THRESHOLD:
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

            if accounts_created > 0:
                logger.info(
                    f"Created {accounts_created} new accounts on {current_date}"
                )

        # ===== Record metrics for plotting =====
        monthly_revenue = calculate_monthly_revenue(
            active_prime_accounts,
            armoury_accounts,
            armoury_profit_weekly,
            PRIME_CONSTANTS,
            STEAM_TO_REAL_EFFICIENCY,
        )

        dates.append(current_date)
        # For plotting, show total revenue-producing accounts (active plus armoury)
        prime_account_history.append(active_prime_accounts + armoury_accounts)
        monthly_revenue_history.append(monthly_revenue)
        steam_reserve_history.append(steam_reserve)

    logger.success(
        f"Simulation complete: {active_prime_accounts} active accounts, {monthly_revenue_history[-1]:.2f} monthly revenue"
    )

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

# Final state: 1.816M with 44.6 cr/month theoretical and >300 cr/annum realisitc on June 7, 2030
# This date assumes that pessimistc scenario is taken to account for all potential losses
