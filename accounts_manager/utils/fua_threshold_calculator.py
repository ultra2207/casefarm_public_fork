import sys
from datetime import datetime, timedelta

import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots

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


def load_config() -> dict:
    config_path = r"C:\Users\Sivasai\Documents\GitHub\CaseFarm\config.yaml"
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    return config


_config = load_config()
# Load configuration
setup_cost: int = _config.get("threshold_calculator_setup_cost")
batch_passes_cost: int = _config.get("threshold_calculator_batch_passes_cost")
profit_scenario1: int = _config.get("threshold_calculator_profit_scenario1")
profit_scenario2: int = _config.get("threshold_calculator_profit_scenario2")
weekly_bonus: int = _config.get("threshold_calculator_weekly_bonus")
farming_hours: int = _config.get("threshold_calculator_farming_hours")
simulation_days: int = 365 * _config.get("threshold_calculator_simulation_years")

# Timezone offset (5h30m)
tz_offset: timedelta = timedelta(hours=5, minutes=30)


# Helper: get next time at a specific hour:minute after a given datetime
def next_time(dt: datetime, hour: int, minute: int) -> datetime:
    dt = dt.replace(second=0, microsecond=0)
    candidate = dt.replace(hour=hour, minute=minute)
    if candidate <= dt:
        candidate += timedelta(days=1)
    return candidate


def simulate_scenario1(initial_balance: int) -> tuple[float, float, float]:
    # Immediate selling at unlock (12:30 PM local time)
    balance: float = initial_balance - setup_cost
    if balance < 0:
        return 0, 0, 0

    # Buy as many passes as possible
    num_pass_batches: int = int(balance // batch_passes_cost)
    balance -= num_pass_batches * batch_passes_cost

    # Start time in local time zone
    current_time: datetime = datetime(2025, 4, 27, 1, 50, 0) + tz_offset
    end_time: datetime = current_time + timedelta(days=simulation_days)
    pending_drops: list[datetime] = []
    waiting_time: timedelta = timedelta(0)
    total_drops: int = 0

    # Weekly bonus: every Wednesday at 12:30 PM
    last_bonus_time: datetime = current_time.replace(
        hour=12, minute=30, second=0, microsecond=0
    )
    while last_bonus_time.weekday() != 2:  # 2 is Wednesday
        last_bonus_time -= timedelta(days=1)
    if last_bonus_time > current_time:
        last_bonus_time -= timedelta(days=7)

    bank_balance: float = 0  # Separate bank balance for profits

    while current_time < end_time:
        # Weekly bonus
        while last_bonus_time + timedelta(days=7) <= current_time:
            last_bonus_time += timedelta(days=7)
            bank_balance += weekly_bonus

        if num_pass_batches > 0:
            # Farm for 15 hours
            farm_end_time: datetime = min(
                current_time + timedelta(hours=farming_hours), end_time
            )
            current_time = farm_end_time
            total_drops += 1

            # Drop unlocks in 7 days at 12:30 PM
            unlock_time: datetime = current_time + timedelta(days=7)
            clear_time: datetime = unlock_time.replace(
                hour=12, minute=30, second=0, microsecond=0
            )
            if clear_time < unlock_time:
                clear_time += timedelta(days=1)
            pending_drops.append(clear_time)
            num_pass_batches -= 1

        else:
            # Check for drops to clear
            drops_to_clear: list[int] = [
                i for i, t in enumerate(pending_drops) if t <= current_time
            ]
            total_cleared: int = len(drops_to_clear)
            for i in sorted(drops_to_clear, reverse=True):
                pending_drops.pop(i)
            # Add profit and auto-buy passes
            for _ in range(total_cleared):
                bank_balance += profit_scenario1
                num_pass_batches += 1
            # End simulation if nothing left
            if num_pass_batches == 0 and not pending_drops:
                break
            # Wait to next clear time if needed
            if num_pass_batches == 0 and pending_drops:
                next_clear: datetime = min(pending_drops)
                waiting_time += next_clear - current_time
                current_time = next_clear

    final_balance: float = bank_balance + balance + num_pass_batches * batch_passes_cost
    roi: float = bank_balance / initial_balance if initial_balance > 0 else 0
    total_waiting_hours: float = waiting_time.total_seconds() / 3600
    return roi, final_balance, total_waiting_hours


def simulate_scenario2(initial_balance: int) -> tuple[float, float, float]:
    # Delayed selling: unlock at 12:30 PM, sell at next 6:00 AM (after at least 17.5h)
    balance: float = initial_balance - setup_cost
    if balance < 0:
        return 0, 0, 0

    # Buy as many passes as possible
    num_pass_batches: int = int(balance // batch_passes_cost)
    balance -= num_pass_batches * batch_passes_cost

    # Start time in local time zone
    current_time: datetime = datetime(2025, 4, 27, 1, 50, 0) + tz_offset
    end_time: datetime = current_time + timedelta(days=simulation_days)
    pending_drops: list[datetime] = []
    waiting_time: timedelta = timedelta(0)
    total_drops: int = 0

    # Weekly bonus: every Wednesday at 12:30 PM
    last_bonus_time: datetime = current_time.replace(
        hour=12, minute=30, second=0, microsecond=0
    )
    while last_bonus_time.weekday() != 2:
        last_bonus_time -= timedelta(days=1)
    if last_bonus_time > current_time:
        last_bonus_time -= timedelta(days=7)

    bank_balance: float = 0  # Separate bank balance for profits

    while current_time < end_time:
        # Weekly bonus
        while last_bonus_time + timedelta(days=7) <= current_time:
            last_bonus_time += timedelta(days=7)
            bank_balance += weekly_bonus

        if num_pass_batches > 0:
            # Farm for 15 hours
            farm_end_time: datetime = min(
                current_time + timedelta(hours=farming_hours), end_time
            )
            current_time = farm_end_time
            total_drops += 1

            # Drop unlocks in 7 days at 12:30 PM
            unlock_time: datetime = current_time + timedelta(days=7)
            unlock_time = unlock_time.replace(
                hour=12, minute=30, second=0, microsecond=0
            )
            if unlock_time < current_time + timedelta(days=7):
                unlock_time += timedelta(days=1)
            # Sell at next 6:00 AM after unlock (at least 17.5h after unlock)
            sell_time: datetime = unlock_time + timedelta(days=1)  # Next day
            sell_time = sell_time.replace(hour=6, minute=0, second=0, microsecond=0)
            pending_drops.append(sell_time)
            num_pass_batches -= 1

        else:
            drops_to_clear: list[int] = [
                i for i, t in enumerate(pending_drops) if t <= current_time
            ]
            total_cleared: int = len(drops_to_clear)
            for i in sorted(drops_to_clear, reverse=True):
                pending_drops.pop(i)
            for _ in range(total_cleared):
                bank_balance += profit_scenario2
                num_pass_batches += 1
            if num_pass_batches == 0 and not pending_drops:
                break
            if num_pass_batches == 0 and pending_drops:
                next_clear: datetime = min(pending_drops)
                waiting_time += next_clear - current_time
                current_time = next_clear

    final_balance: float = bank_balance + balance + num_pass_batches * batch_passes_cost
    roi: float = bank_balance / initial_balance if initial_balance > 0 else 0
    total_waiting_hours: float = waiting_time.total_seconds() / 3600
    return roi, final_balance, total_waiting_hours


def refined_search() -> None:
    # First pass - search in 500 increments
    results_combined: list[tuple[int, str, float, float, float]] = []
    balances = range(7550, 120001, 500)
    for bal in balances:
        roi1, final1, wait1 = simulate_scenario1(bal)
        roi2, final2, wait2 = simulate_scenario2(bal)
        results_combined.append((bal, "Scenario 1", roi1, final1, wait1))
        results_combined.append((bal, "Scenario 2", roi2, final2, wait2))

    # Sort by ROI descending and get the best result
    results_sorted = sorted(results_combined, key=lambda x: x[2], reverse=True)
    best_balance = results_sorted[0][0]
    best_scenario = results_sorted[0][1]

    logger.info(
        f"Best initial balance from broad search: {best_balance}, Scenario: {best_scenario}"
    )

    # Second pass - refine search around best balance in 10 increments
    refined_results: list[tuple[int, str, float, float, float]] = []
    start: int = max(7550, best_balance - 500)  # Don't go below minimum
    end: int = min(120000, best_balance + 500)  # Don't go above maximum

    for bal in range(start, end + 1, 10):
        if best_scenario == "Scenario 1":
            roi, final, wait = simulate_scenario1(bal)
        else:
            roi, final, wait = simulate_scenario2(bal)

        refined_results.append((bal, best_scenario, roi, final, wait))

    # Sort refined results by ROI descending
    refined_sorted = sorted(refined_results, key=lambda x: x[2], reverse=True)

    # Print top 10 refined results
    logger.info("Top 10 Refined Results (by ROI):")
    logger.info(f"{'Balance':>8} | {'ROI':>7} | {'Final':>10} | {'Wait (h)':>8}")
    for entry in refined_sorted[:10]:
        logger.info(
            f"{entry[0]:8} | {entry[2]:7.3f} | {entry[3]:10,.0f} | {entry[4]:8.1f}"
        )

    # Get the best balance from refined search
    best_refined = refined_sorted[0]
    logger.info(
        f"Best refined result: Balance {best_refined[0]}, {best_refined[1]}, ROI: {best_refined[2]:.3f}"
    )

    final_num_pass_batches = (best_refined[0] - setup_cost) / batch_passes_cost
    logger.info(
        f"An optimal fully upgraded account will have {final_num_pass_batches:.2f} batches of passes and a total theoretical value of {best_refined[0]}."
    )

    # Extract data for plotting
    balances1 = [r[0] for r in results_combined if r[1] == "Scenario 1"]
    rois1 = [r[2] for r in results_combined if r[1] == "Scenario 1"]
    waits1 = [r[4] for r in results_combined if r[1] == "Scenario 1"]

    balances2 = [r[0] for r in results_combined if r[1] == "Scenario 2"]
    rois2 = [r[2] for r in results_combined if r[1] == "Scenario 2"]
    waits2 = [r[4] for r in results_combined if r[1] == "Scenario 2"]

    # Create subplots with 2 rows and 1 column
    fig = make_subplots(
        rows=2,
        cols=1,
        subplot_titles=("ROI vs Initial Balance", "Wait Time vs Initial Balance"),
        vertical_spacing=0.15,
    )

    # Add traces for ROI vs Initial Balance to the first row
    fig.add_trace(
        go.Scatter(
            x=balances1,
            y=rois1,
            mode="lines+markers",
            name="Scenario 1 (Immediate Sell)",
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=balances2, y=rois2, mode="lines+markers", name="Scenario 2 (Delayed Sell)"
        ),
        row=1,
        col=1,
    )

    # Add traces for Wait Time vs Initial Balance to the second row
    fig.add_trace(
        go.Scatter(
            x=balances1,
            y=waits1,
            mode="lines+markers",
            name="Scenario 1 (Immediate Sell)",
        ),
        row=2,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=balances2,
            y=waits2,
            mode="lines+markers",
            name="Scenario 2 (Delayed Sell)",
        ),
        row=2,
        col=1,
    )

    # Update layout
    fig.update_layout(
        height=800,  # Increased height for two graphs
        title_text="Simulation Results Analysis",
        template="plotly_white",
    )

    # Update y-axis labels
    fig.update_yaxes(title_text="ROI (Bank Balance / Initial Balance)", row=1, col=1)  # type: ignore
    fig.update_yaxes(title_text="Wait Time (Hours)", row=2, col=1)  # type: ignore

    # Update x-axis labels
    fig.update_xaxes(title_text="Initial Balance", row=2, col=1)  # type: ignore

    # fig.show() commented out to avoid opening a browser window, just printing number of batches is enough for use in production
    logger.success("Simulation completed successfully")


if __name__ == "__main__":
    refined_search()
