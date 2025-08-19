import json
import math
import os
import sys
import time
from datetime import date, timedelta

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import requests
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

# Note: current regions being compared is Indonesia and Vietnam, if u wish to compare new regions,
# then give copilot new prices for ACCOUNT_COST_STEAM_VND_INITIAL (giftcard value in that currency) and
# ACCOUNT_COST_STEAM_VND_TOTAL (prime cost in that currency) and in regions dict "new_account_cost_real" which is the cost
# of the giftcard u bought in inr. give copilot these values and the new currency name so that it can update the file for the
# region switching comparison

# Note: All calculations are done in rupees with any foreign currency prices being converted into inr

# Original IDR prices (Indonesia region)
ACCOUNT_COST_STEAM_IDR_INITIAL: float = 84000
ACCOUNT_COST_STEAM_IDR_TOTAL: float = 245000
UPGRADE_COST_STEAM_IDR_ORIGINAL: float = 261000  # Original upgrade cost

# New upgrade cost after price increase
UPGRADE_COST_STEAM_IDR_INCREASED: float = 261000  # This is the increased price

# Vietnam region prices
ACCOUNT_COST_STEAM_VND_INITIAL: float = 150000  # Vietnam initial steam cost in VND
ACCOUNT_COST_STEAM_VND_TOTAL: float = 375000  # Vietnam total steam cost in VND
UPGRADE_COST_VND: float = 400000  # Vietnam upgrade cost in VND

csfloat_tax: float = 1.0585


def convert_idr_to_real(idr_amount: float) -> float | None:
    """Convert Indonesian Rupiah (IDR) to Indian Rupees (INR)."""
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


def convert_vnd_to_real(vnd_amount: float) -> float | None:
    """Convert Vietnamese Dong (VND) to Indian Rupees (INR)."""
    # Define cache file path
    cache_dir: str = (
        r"C:\Users\Sivasai\Documents\GitHub\CaseFarm\utils\cache\miscellaneous"
    )
    cache_file: str = os.path.join(cache_dir, "vnd_to_inr_rate.json")

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
                    vnd_to_inr_rate: float = cached_data.get("vnd", {}).get("inr")

                    if vnd_to_inr_rate is not None:
                        should_fetch_new_data = False
            except Exception as e:
                logger.error(f"Error reading cache: {e}")

    # Fetch new data if needed
    if should_fetch_new_data:
        try:
            # Fetch the latest exchange rates
            response = requests.get(
                "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/vnd.json"
            )
            data: dict = response.json()

            # Cache the data
            with open(cache_file, "w") as f:
                json.dump(data, f)

            # Extract rate
            vnd_to_inr_rate: float = data["vnd"]["inr"]
            logger.debug(f"Fetched new VND to INR rate: {vnd_to_inr_rate}")
        except Exception as e:
            logger.error(f"Error fetching currency data: {e}")

            # If we have a cache file but it's old, use it as fallback
            if os.path.exists(cache_file):
                try:
                    with open(cache_file, "r") as f:
                        cached_data: dict = json.load(f)
                        vnd_to_inr_rate: float = cached_data.get("vnd", {}).get("inr")
                        logger.warning("Using outdated cache as fallback")
                except Exception as cache_e:
                    logger.error(f"Error reading fallback cache: {cache_e}")
                    return None
            else:
                return None

    # Convert VND to INR
    inr_amount: float = vnd_amount * vnd_to_inr_rate
    logger.trace(f"Converted {vnd_amount} VND to {inr_amount} INR")

    return inr_amount


# Region configurations
REGIONS = {
    "INDONESIA": {
        "name": "Indonesia",
        "new_account_cost_real": 474.59,
        "new_account_cost_steam": convert_idr_to_real(
            ACCOUNT_COST_STEAM_IDR_TOTAL - ACCOUNT_COST_STEAM_IDR_INITIAL
        ),
        "upgrade_cost": convert_idr_to_real(UPGRADE_COST_STEAM_IDR_INCREASED),
        "switching_cost_real": 474.59,  # Same as new account cost for region switching
        "switching_cost_steam": convert_idr_to_real(
            ACCOUNT_COST_STEAM_IDR_TOTAL - ACCOUNT_COST_STEAM_IDR_INITIAL
        ),
    },
    "VIETNAM": {
        "name": "Vietnam",
        "new_account_cost_real": 520.27,  # Vietnam-specific real cost for new accounts
        "new_account_cost_steam": convert_vnd_to_real(
            ACCOUNT_COST_STEAM_VND_TOTAL - ACCOUNT_COST_STEAM_VND_INITIAL
        ),  # Vietnam-specific steam cost for new accounts
        "upgrade_cost": convert_vnd_to_real(UPGRADE_COST_VND),
        "switching_cost_real": 520.27,  # Cost to switch existing account to Vietnam
        "switching_cost_steam": convert_vnd_to_real(
            ACCOUNT_COST_STEAM_VND_TOTAL - ACCOUNT_COST_STEAM_VND_INITIAL
        ),  # Vietnam-specific switching cost
    },
}

# Shared Constants (same as original)
BASE_REVENUE_WEEK: float = 62.14
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
LOCAL_COMPUTER_CONTRACT_MONTHS: int = 36
CUTTING_EDGE_CAPACITY: int = 40
DERISKING_THRESHOLD: int = LOCAL_COMPUTER_THRESHOLD

# Revenue calculation constants
redeemed_item_price: float = 86
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
    def __init__(self, region: str):
        self.upgrades: int = 0
        self.pending_upgrades: int = 0
        self.region: str = region
        self.activation_date: date | None = None
        self.is_switching: bool = False
        self.switch_completion_date: date | None = None
        self.switch_target_region: str | None = None

    def weekly_revenue_base(self) -> float:
        # No revenue during switching period
        if self.is_switching:
            return 0.0
        return BASE_REVENUE_WEEK

    def weekly_armoury_pass_revenue_without_costs(self) -> float:
        # No revenue during switching period
        if self.is_switching:
            return 0.0
        return self.upgrades * revenue_increase_on_upgrade

    def daily_revenue(self) -> float:
        # No revenue during switching period
        if self.is_switching:
            return 0.0
        return BASE_REVENUE_DAILY

    def can_upgrade(self, current_date: date, completion_date: date) -> bool:
        # Can't upgrade during switching period
        if self.is_switching:
            return False

        max_upgrades = (
            NEW_MAX_UPGRADES if current_date >= completion_date else OLD_MAX_UPGRADES
        )
        return (self.upgrades + self.pending_upgrades) < max_upgrades

    def get_max_upgrades(self, current_date: date, completion_date: date) -> int:
        return NEW_MAX_UPGRADES if current_date >= completion_date else OLD_MAX_UPGRADES

    def upgrade(self) -> bool:
        if not self.is_switching:
            self.pending_upgrades += 1
            return True
        return False

    def activate_upgrade(self) -> bool:
        if self.pending_upgrades > 0 and not self.is_switching:
            self.upgrades += 1
            self.pending_upgrades -= 1
            return True
        return False

    def start_region_switch(self, target_region: str, completion_date: date) -> None:
        """Start the process of switching to a different region"""
        self.is_switching = True
        self.switch_target_region = target_region
        self.switch_completion_date = completion_date
        logger.debug(
            f"Account switching from {self.region} to {target_region}, completion: {completion_date}"
        )

    def complete_region_switch(self, current_date: date) -> bool:
        """Complete the region switch if the time has come"""
        if (
            self.is_switching
            and self.switch_completion_date
            and current_date >= self.switch_completion_date
        ):
            old_region = self.region
            self.region = self.switch_target_region
            self.is_switching = False
            self.switch_completion_date = None
            self.switch_target_region = None
            logger.info(f"Account completed switch from {old_region} to {self.region}")
            return True
        return False

    def get_upgrade_cost(self) -> float:
        """Get the upgrade cost for the current region"""
        return REGIONS[self.region]["upgrade_cost"]


def should_switch_region(
    accounts: list[Account], current_region: str, target_region: str
) -> bool:
    """
    Determine if it makes financial sense to switch regions based on upgrade cost difference
    """
    current_upgrade_cost = REGIONS[current_region]["upgrade_cost"]
    target_upgrade_cost = REGIONS[target_region]["upgrade_cost"]

    # Calculate potential savings per upgrade
    savings_per_upgrade = current_upgrade_cost - target_upgrade_cost

    # Calculate switching costs
    switching_cost_real = REGIONS[target_region]["switching_cost_real"]
    switching_cost_steam = REGIONS[target_region]["switching_cost_steam"]
    total_switching_cost = (
        switching_cost_real / STEAM_TO_REAL_EFFICIENCY + switching_cost_steam
    )

    # Estimate future upgrades for accounts in current region
    accounts_in_current_region = [
        acc for acc in accounts if acc.region == current_region and not acc.is_switching
    ]

    if not accounts_in_current_region:
        return False

    # Simple heuristic: if savings over next 10 upgrades per account > switching cost
    estimated_upgrades_per_account = 10
    total_estimated_savings = (
        len(accounts_in_current_region)
        * estimated_upgrades_per_account
        * savings_per_upgrade
    )
    total_switching_cost_all = len(accounts_in_current_region) * total_switching_cost

    should_switch = total_estimated_savings > total_switching_cost_all

    if should_switch:
        logger.info(f"Region switch recommended: {current_region} -> {target_region}")
        logger.info(
            f"Estimated savings: {total_estimated_savings:.2f}, Switching cost: {total_switching_cost_all:.2f}"
        )

    return should_switch


def simulate_business_scenario(
    simulation_days: int,
    completion_days_from_now: int,
    switch_trigger_day: int = 50,
    enable_switching: bool = True,
) -> pd.DataFrame:
    """
    Simulate business with optional region switching

    Args:
        simulation_days: Number of days to simulate
        completion_days_from_now: Days until software completion
        switch_trigger_day: Day to evaluate/execute region switch
        enable_switching: If True, execute region switch on trigger day. If False, continue with original region.
    """
    start_date: date = date.today()
    end_date: date = start_date + timedelta(days=simulation_days)
    casual_farm_completion_date: date = start_date + timedelta(
        days=completion_days_from_now
    )

    logger.info(f"Starting region switching simulation from {start_date} to {end_date}")
    logger.info(f"Switch evaluation will start on day {switch_trigger_day}")

    accounts: list[Account] = []
    steam_balance: float = 0.0
    steam_reserve: float = 0.0
    real_balance: float = 0.0
    daily_stats: list[dict] = []

    # Track region switching
    has_evaluated_switch: bool = False

    # Track local computer contracts
    local_computer_contracts: list[tuple[date, int]] = []

    # Dictionaries for scheduling
    weekly_rev_schedule: dict[date, float] = {}
    daily_rev_schedule: dict[date, float] = {}
    upgrade_schedule: dict[date, list[tuple[Account, int]]] = {}

    total_days: int = (end_date - start_date).days + 1
    current_date: date = start_date

    for _ in tqdm(
        range(total_days - 1), desc="Simulating business with region switching"
    ):
        # Complete any region switches that are due
        for account in accounts:
            account.complete_region_switch(current_date)

        # Evaluate region switching after the trigger day
        if (
            current_date - start_date
        ).days >= switch_trigger_day and not has_evaluated_switch:
            if enable_switching:
                indonesia_accounts = [
                    acc
                    for acc in accounts
                    if acc.region == "INDONESIA" and not acc.is_switching
                ]

                if indonesia_accounts:
                    # Force switch all Indonesia accounts to Vietnam regardless of profitability
                    switch_completion_date = current_date + timedelta(
                        days=7
                    )  # 1 week delay

                    # Calculate switching costs
                    total_switching_cost_real = (
                        len(indonesia_accounts)
                        * REGIONS["VIETNAM"]["switching_cost_real"]
                    )
                    total_switching_cost_steam = (
                        len(indonesia_accounts)
                        * REGIONS["VIETNAM"]["switching_cost_steam"]
                    )

                    # Deduct switching costs (even if it causes negative balance)
                    real_balance -= total_switching_cost_real
                    steam_balance -= total_switching_cost_steam

                    # Start the switch for all accounts
                    for account in indonesia_accounts:
                        account.start_region_switch("VIETNAM", switch_completion_date)

                    # Add new prime accounts equal to the number being migrated
                    num_migrated_accounts = len(indonesia_accounts)
                    for _ in range(num_migrated_accounts):
                        new_prime_account = Account("INDONESIA")
                        # These are actually the existing accounts which have been converted into prime accounts so they retain the current region
                        # as regions dont matter for base accounts
                        new_prime_account.activation_date = (
                            current_date  # Activate immediately
                        )
                        accounts.append(new_prime_account)

                    logger.success(
                        f"Started region switch for {len(indonesia_accounts)} accounts to Vietnam"
                    )
                    logger.info(
                        f"Added {num_migrated_accounts} new prime accounts during migration"
                    )
                    logger.info(
                        f"Switching costs: Real={total_switching_cost_real:.2f}, Steam={total_switching_cost_steam:.2f}"
                    )

            has_evaluated_switch = True

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
                    - acc.upgrades * acc.get_upgrade_cost()
                )
                for acc in accounts
                if getattr(acc, "activation_date", current_date) <= current_date
            )
            scheduled_date_armoury: date = current_date + timedelta(days=7)
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
            revenue_amount = weekly_rev_schedule[current_date]
            steam_balance += revenue_amount
            del weekly_rev_schedule[current_date]

        if current_date in daily_rev_schedule:
            revenue_amount = daily_rev_schedule[current_date]
            steam_balance += revenue_amount
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
        else:
            days_to_wednesday: int = (2 - current_date.weekday()) % 7
            next_wednesday: date = current_date + timedelta(days=days_to_wednesday)
            daily_rev_schedule[next_wednesday] = (
                daily_rev_schedule.get(next_wednesday, 0) + daily_rev
            )

        # Determine computer capacity
        home_capacity: int = HOME_COMPUTER_CAPACITY
        account_threshold: int = (
            CUTTING_EDGE_CAPACITY
            if current_date >= casual_farm_completion_date
            else LOCAL_COMPUTER_THRESHOLD
        )

        # Monthly expenses and computer management
        if current_date.day == 1:
            real_balance += MONTHLY_INVESTMENT

            # Calculate expenses
            num_accounts: int = len(accounts)
            num_licenses: int = (
                math.ceil(num_accounts / account_threshold) if num_accounts > 0 else 0
            )
            license_cost: float = num_licenses * FIXED_COST

            # Local computer management
            extra_accounts: int = max(0, num_accounts - home_capacity)
            required_local_computers: int = (
                math.ceil(extra_accounts / account_threshold)
                if extra_accounts > 0
                else 0
            )

            if required_local_computers > len(local_computer_contracts):
                new_computers_needed: int = required_local_computers - len(
                    local_computer_contracts
                )
                for _ in range(new_computers_needed):
                    local_computer_contracts.append(
                        (current_date, LOCAL_COMPUTER_CONTRACT_MONTHS)
                    )

            local_computer_cost: float = 0
            updated_contracts: list[tuple[date, int]] = []
            for purchase_date, remaining_months in local_computer_contracts:
                if remaining_months > 0:
                    local_computer_cost += LOCAL_COMPUTER_COST
                    updated_contracts.append((purchase_date, remaining_months - 1))
            local_computer_contracts = updated_contracts

            total_expenses: float = license_cost + local_computer_cost

            # Handle fund shortages
            if real_balance < total_expenses:
                needed: float = total_expenses - real_balance
                required_steam: float = needed / STEAM_TO_REAL_EFFICIENCY
                if steam_balance >= required_steam:
                    steam_balance -= required_steam
                    real_balance += needed
                else:
                    available_steam: float = steam_balance
                    steam_balance = 0
                    converted_amount: float = available_steam * STEAM_TO_REAL_EFFICIENCY
                    real_balance += converted_amount

            real_balance -= total_expenses

        # Investment logic
        fully_invested: bool = False
        while not fully_invested:
            candidate: Account | None = None
            for acc in accounts:
                if acc.can_upgrade(current_date, casual_farm_completion_date):
                    candidate = acc
                    break

            # Derisking logic
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
                # Use Vietnam region costs for new accounts (assuming we prefer Vietnam after evaluation)
                region_to_use = "VIETNAM" if has_evaluated_switch else "INDONESIA"
                account_cost_real = REGIONS[region_to_use]["new_account_cost_real"]
                account_cost_steam = REGIONS[region_to_use]["new_account_cost_steam"]
                upgrade_cost = REGIONS[region_to_use]["upgrade_cost"]

                account_value: float = (
                    account_cost_real / STEAM_TO_REAL_EFFICIENCY
                    + account_cost_steam
                    + 5 * upgrade_cost
                )
                target_steam: float = (
                    (STEAM_RESERVE_PERCENTAGE / 100) * len(accounts) * account_value
                )

                if steam_reserve < target_steam:
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
                            fully_invested = True
                            continue
                        else:
                            steam_balance += convert_real_to_steam(real_balance)
                            real_balance = 0
                            fully_invested = True
                            continue
                    else:
                        to_transfer: float = target_steam - steam_reserve
                        steam_balance -= to_transfer
                        steam_reserve += to_transfer
                        continue

            # Purchasing new accounts
            if candidate is None:
                # Always use Vietnam region for new accounts after switch evaluation (cheaper upgrades)
                region_for_new_account = (
                    "VIETNAM" if has_evaluated_switch else "INDONESIA"
                )
                account_cost_real = REGIONS[region_for_new_account][
                    "new_account_cost_real"
                ]
                account_cost_steam = REGIONS[region_for_new_account][
                    "new_account_cost_steam"
                ]

                if (
                    real_balance >= account_cost_real
                    and steam_balance >= account_cost_steam
                ):
                    real_balance -= account_cost_real
                    steam_balance -= account_cost_steam
                    candidate = Account(region_for_new_account)
                    candidate.activation_date = current_date + timedelta(days=7)
                    accounts.append(candidate)
                else:
                    if real_balance < account_cost_real:
                        needed: float = account_cost_real - real_balance
                        required_steam: float = needed / STEAM_TO_REAL_EFFICIENCY
                        if steam_balance >= required_steam + account_cost_steam:
                            steam_balance -= required_steam
                            real_balance += needed
                            real_balance -= account_cost_real
                            steam_balance -= account_cost_steam
                            candidate = Account(region_for_new_account)
                            candidate.activation_date = current_date + timedelta(days=7)
                            accounts.append(candidate)
                            continue
                        else:
                            fully_invested = True
                            continue
                    elif steam_balance < account_cost_steam:
                        needed: float = account_cost_steam - steam_balance
                        required_real: float = needed / REAL_TO_STEAM_CONVERSION_RATE
                        if real_balance >= required_real + account_cost_real:
                            real_balance -= required_real
                            steam_balance += convert_real_to_steam(required_real)
                            real_balance -= account_cost_real
                            steam_balance -= account_cost_steam
                            candidate = Account(region_for_new_account)
                            candidate.activation_date = current_date + timedelta(days=7)
                            accounts.append(candidate)
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

                upgrade_cost = candidate.get_upgrade_cost()
                max_affordable_upgrades: int = math.floor(steam_balance / upgrade_cost)

                if max_affordable_upgrades == 0:
                    needed_steam: float = upgrade_cost - steam_balance
                    required_real: float = needed_steam / REAL_TO_STEAM_CONVERSION_RATE
                    if real_balance >= required_real:
                        real_balance -= required_real
                        steam_balance += convert_real_to_steam(required_real)
                        max_affordable_upgrades = math.floor(
                            steam_balance / upgrade_cost
                        )
                    else:
                        fully_invested = True
                        continue

                if max_affordable_upgrades > 0:
                    num_upgrades: int = min(
                        max_possible_upgrades, max_affordable_upgrades
                    )
                    total_cost: float = num_upgrades * upgrade_cost
                    steam_balance -= total_cost

                    scheduled_date_upgrade: date = current_date + timedelta(days=7)
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
        weekly_rev_stat: float = sum(
            (
                acc.weekly_revenue_base()
                + (
                    acc.weekly_armoury_pass_revenue_without_costs()
                    - acc.upgrades * acc.get_upgrade_cost()
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

        # Count accounts by region
        indonesia_accounts = len([acc for acc in accounts if acc.region == "INDONESIA"])
        vietnam_accounts = len([acc for acc in accounts if acc.region == "VIETNAM"])
        switching_accounts = len([acc for acc in accounts if acc.is_switching])

        days_from_start: int = (current_date - start_date).days
        daily_stats.append(
            {
                "date": current_date.strftime("%Y-%m-%d"),
                "days_from_start": days_from_start,
                "accounts": len(accounts),
                "indonesia_accounts": indonesia_accounts,
                "vietnam_accounts": vietnam_accounts,
                "switching_accounts": switching_accounts,
                "monthly_revenue": monthly_revenue,
                "steam_balance": steam_balance,
                "steam_reserve": steam_reserve,
                "real_balance": real_balance,
                "max_upgrades": NEW_MAX_UPGRADES
                if current_date >= casual_farm_completion_date
                else OLD_MAX_UPGRADES,
                "account_capacity": account_threshold,
                "is_completion_date": current_date == casual_farm_completion_date,
                "has_evaluated_switch": has_evaluated_switch,
                "switch_evaluation_day": switch_trigger_day,
                "scenario": "switch" if enable_switching else "no_switch",
            }
        )

        current_date += timedelta(days=1)

    logger.success(
        f"Region switching simulation completed. Total accounts: {len(accounts)}, "
        f"Indonesia: {indonesia_accounts}, Vietnam: {vietnam_accounts}"
    )
    return pd.DataFrame(daily_stats)


def plot_comparison_simulation(
    completion_days: int = 180, simulation_days: int = 365, switch_trigger_day: int = 50
) -> go.Figure:
    """Run both scenarios and plot comparison results"""
    logger.info(
        f"Running comparison simulation: completion_days={completion_days}, "
        f"switch_trigger_day={switch_trigger_day}"
    )

    # Run both scenarios
    logger.info("Running scenario 1: No region switching")
    df_no_switch = simulate_business_scenario(
        simulation_days, completion_days, switch_trigger_day, enable_switching=False
    )

    logger.info("Running scenario 2: With region switching")
    df_switch = simulate_business_scenario(
        simulation_days, completion_days, switch_trigger_day, enable_switching=True
    )

    # Create figure
    fig = go.Figure()

    # Add traces for no-switch scenario
    fig.add_trace(
        go.Scatter(
            x=df_no_switch["days_from_start"],
            y=df_no_switch["monthly_revenue"],
            name="Monthly Revenue (No Switch)",
            line=dict(color="blue", width=2),
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df_no_switch["days_from_start"],
            y=df_no_switch["accounts"],
            name="Total Accounts (No Switch)",
            line=dict(color="red", width=2),
            visible="legendonly",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df_no_switch["days_from_start"],
            y=df_no_switch["steam_balance"],
            name="Steam Balance (No Switch)",
            line=dict(color="green", width=2),
            visible="legendonly",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df_no_switch["days_from_start"],
            y=df_no_switch["real_balance"],
            name="Real Balance (No Switch)",
            line=dict(color="purple", width=2),
            visible="legendonly",
        )
    )

    # Add traces for switch scenario
    fig.add_trace(
        go.Scatter(
            x=df_switch["days_from_start"],
            y=df_switch["monthly_revenue"],
            name="Monthly Revenue (With Switch)",
            line=dict(color="blue", width=2, dash="dash"),
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df_switch["days_from_start"],
            y=df_switch["accounts"],
            name="Total Accounts (With Switch)",
            line=dict(color="red", width=2, dash="dash"),
            visible="legendonly",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df_switch["days_from_start"],
            y=df_switch["steam_balance"],
            name="Steam Balance (With Switch)",
            line=dict(color="green", width=2, dash="dash"),
            visible="legendonly",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df_switch["days_from_start"],
            y=df_switch["real_balance"],
            name="Real Balance (With Switch)",
            line=dict(color="purple", width=2, dash="dash"),
            visible="legendonly",
        )
    )

    # Add region-specific traces for switch scenario
    fig.add_trace(
        go.Scatter(
            x=df_switch["days_from_start"],
            y=df_switch["indonesia_accounts"],
            name="Indonesia Accounts (Switch Scenario)",
            line=dict(color="orange", width=2),
            visible="legendonly",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df_switch["days_from_start"],
            y=df_switch["vietnam_accounts"],
            name="Vietnam Accounts (Switch Scenario)",
            line=dict(color="cyan", width=2),
            visible="legendonly",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df_switch["days_from_start"],
            y=df_switch["switching_accounts"],
            name="Switching Accounts",
            line=dict(color="magenta", width=2, dash="dot"),
            visible="legendonly",
        )
    )

    # Add vertical line for switch evaluation day
    fig.add_shape(
        type="line",
        x0=switch_trigger_day,
        x1=switch_trigger_day,
        y0=0,
        y1=1,
        yref="paper",
        line=dict(color="orange", width=2, dash="dash"),
    )

    fig.add_annotation(
        x=switch_trigger_day,
        y=0.9,
        yref="paper",
        text=f"Switch Day {switch_trigger_day}",
        showarrow=True,
        arrowhead=1,
        ax=0,
        ay=-40,
    )

    # Find the completion date in the dataframe
    completion_row = df_no_switch[df_no_switch["is_completion_date"]]
    if not completion_row.empty:
        completion_day = completion_row.iloc[0]["days_from_start"]

        fig.add_shape(
            type="line",
            x0=completion_day,
            x1=completion_day,
            y0=0,
            y1=1,
            yref="paper",
            line=dict(color="red", width=2, dash="dash"),
        )

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
        title="Business Simulation: Region Switch vs No Switch Comparison",
        xaxis_title="Days from Start",
        yaxis_title="Value",
        height=800,
        legend_title="Metrics",
        hovermode="x unified",
        updatemenus=[
            {
                "buttons": [
                    {
                        "label": "Monthly Revenue",
                        "method": "update",
                        "args": [
                            {
                                "visible": [
                                    True,
                                    False,
                                    False,
                                    False,
                                    True,
                                    False,
                                    False,
                                    False,
                                    False,
                                    False,
                                    False,
                                ]
                            }
                        ],
                    },
                    {
                        "label": "Total Accounts",
                        "method": "update",
                        "args": [
                            {
                                "visible": [
                                    False,
                                    True,
                                    False,
                                    False,
                                    False,
                                    True,
                                    False,
                                    False,
                                    False,
                                    False,
                                    False,
                                ]
                            }
                        ],
                    },
                    {
                        "label": "Steam Balance",
                        "method": "update",
                        "args": [
                            {
                                "visible": [
                                    False,
                                    False,
                                    True,
                                    False,
                                    False,
                                    False,
                                    True,
                                    False,
                                    False,
                                    False,
                                    False,
                                ]
                            }
                        ],
                    },
                    {
                        "label": "Real Balance",
                        "method": "update",
                        "args": [
                            {
                                "visible": [
                                    False,
                                    False,
                                    False,
                                    True,
                                    False,
                                    False,
                                    False,
                                    True,
                                    False,
                                    False,
                                    False,
                                ]
                            }
                        ],
                    },
                    {
                        "label": "Regional Breakdown",
                        "method": "update",
                        "args": [
                            {
                                "visible": [
                                    False,
                                    False,
                                    False,
                                    False,
                                    False,
                                    False,
                                    False,
                                    False,
                                    True,
                                    True,
                                    True,
                                ]
                            }
                        ],
                    },
                    {
                        "label": "All Metrics",
                        "method": "update",
                        "args": [
                            {
                                "visible": [
                                    True,
                                    True,
                                    True,
                                    True,
                                    True,
                                    True,
                                    True,
                                    True,
                                    True,
                                    True,
                                    True,
                                ]
                            }
                        ],
                    },
                ],
                "direction": "down",
                "showactive": True,
                "x": 0.1,
                "y": 1.15,
            }
        ],
    )

    return fig


def main() -> None:
    """Main function to run the region switching comparison simulation"""
    logger.info("Starting region switching comparison simulation")

    # Show upgrade costs for comparison
    indonesia_upgrade_cost = REGIONS["INDONESIA"]["upgrade_cost"]
    vietnam_upgrade_cost = REGIONS["VIETNAM"]["upgrade_cost"]

    logger.info(f"Indonesia upgrade cost: {indonesia_upgrade_cost:.2f} INR")
    logger.info(f"Vietnam upgrade cost: {vietnam_upgrade_cost:.2f} INR")
    logger.info(
        f"Potential savings per upgrade: {indonesia_upgrade_cost - vietnam_upgrade_cost:.2f} INR"
    )

    # Show account costs for comparison
    indonesia_account_cost_real = REGIONS["INDONESIA"]["new_account_cost_real"]
    indonesia_account_cost_steam = REGIONS["INDONESIA"]["new_account_cost_steam"]
    vietnam_account_cost_real = REGIONS["VIETNAM"]["new_account_cost_real"]
    vietnam_account_cost_steam = REGIONS["VIETNAM"]["new_account_cost_steam"]

    logger.info(
        f"Indonesia new account cost: Real={indonesia_account_cost_real:.2f}, Steam={indonesia_account_cost_steam:.2f}"
    )
    logger.info(
        f"Vietnam new account cost: Real={vietnam_account_cost_real:.2f}, Steam={vietnam_account_cost_steam:.2f}"
    )

    # Calculate switching costs
    switching_cost_real = REGIONS["VIETNAM"]["switching_cost_real"]
    switching_cost_steam = REGIONS["VIETNAM"]["switching_cost_steam"]
    logger.info(
        f"Switching cost per account: Real={switching_cost_real:.2f}, Steam={switching_cost_steam:.2f}"
    )

    # Create and show the comparison plot
    fig = plot_comparison_simulation(
        completion_days=180, simulation_days=365, switch_trigger_day=50
    )

    config = {
        "responsive": True,
        "displayModeBar": True,
        "modeBarButtonsToAdd": ["toggleFullScreen"],
        "scrollZoom": True,
    }

    fig.show(config=config)


if __name__ == "__main__":
    main()
