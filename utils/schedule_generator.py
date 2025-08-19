import torch

torch.set_float32_matmul_precision("medium")
import asyncio
import json
import os
import random
import subprocess
import sys
import time
import webbrowser
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pytz
import yaml
from aiosteampy import App
from aiosteampy.ext.user_agents import UserAgentsService
from darts import TimeSeries
from darts.metrics import mape
from darts.utils.statistics import check_seasonality
from darts.utils.utils import ModelMode, SeasonalityMode


def load_config():
    config_path = r"C:\Users\Sivasai\Documents\GitHub\CaseFarm\config.yaml"
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    return config


_config = load_config()
ROOT_DIR = _config["ROOT_DIR"]
sys.path.insert(0, ROOT_DIR)
from database import (
    get_all_steam_accounts,
    get_client,
    save_cookies_and_close_session,
    steam_api_call_with_retry,
)
from utils.logger import get_custom_logger

logger = get_custom_logger()


# -- Optimized Constants and Configurations--
# -- Runs for approximately 3 minutes and 30 seconds --
# -- Best model is printed for compatibility reasons, always choose the weighted ensemble when running with 5 splits --


def load_config() -> dict:
    config_path = r"C:\Users\Sivasai\Documents\GitHub\CaseFarm\config.yaml"
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    return config


_config = load_config()


N_EPOCHS = _config.get("N_EPOCHS")
MARKET_HASH_NAME_DEFAULT = _config.get("MARKET_HASH_NAME_DEFAULT")
MAX_SPLITS = _config.get("MAX_SPLITS")
OUTPUT_CHUNK_LENGTH_DEFAULT = _config.get("OUTPUT_CHUNK_LENGTH_DEFAULT")


class PriceHistoryEntry:
    def __init__(self, date, price, daily_volume) -> None:
        self.date = date
        self.price = price
        self.daily_volume = daily_volume


def convert_price_history(price_history_list, market_hash_name) -> str:
    # Filter for Fever Case if needed
    if market_hash_name == "Fever Case":
        cutoff_date = datetime(2025, 4, 22, 0, 0, tzinfo=timezone.utc)
        price_history_list = [
            entry for entry in price_history_list if entry.date >= cutoff_date
        ]

    # Find the point where the difference changes from 1 day to less than 24 hours
    i = 0
    while i < len(price_history_list) - 1:
        diff = price_history_list[i + 1].date - price_history_list[i].date
        if diff < timedelta(hours=OUTPUT_CHUNK_LENGTH_DEFAULT):
            break
        i += 1

    # Take data from that point onwards
    filtered_list = price_history_list[i:]

    # Group entries by date
    date_groups = defaultdict(list)
    for entry in filtered_list:
        date_groups[entry.date.date()].append(entry)

    # Format the output JSON
    prices = []
    for date, entries in date_groups.items():
        for idx, entry in enumerate(entries):
            adjusted_date = entry.date.replace(hour=idx % OUTPUT_CHUNK_LENGTH_DEFAULT)
            date_str = adjusted_date.strftime("%b %d %Y %H: +0")
            prices.append([date_str, entry.price, str(entry.daily_volume)])

    result = {
        "success": True,
        "price_prefix": "₹",
        "price_suffix": "",
        "prices": prices,
    }

    return json.dumps(result, indent=4, ensure_ascii=False)


async def get_price_history_json(market_hash_name=MARKET_HASH_NAME_DEFAULT) -> str:
    user_agents = UserAgentsService()
    await user_agents.load()
    all_accounts = get_all_steam_accounts()

    selected_accounts = [
        acc for acc in all_accounts if acc["prime"] and acc["currency"] == "INR"
    ]

    account = random.choice(selected_accounts)

    client = get_client(account)

    price_history_object = await steam_api_call_with_retry(
        client.fetch_price_history, obj=market_hash_name, app=App.CS2
    )

    try:
        await save_cookies_and_close_session(client)
    except Exception:
        pass

    price_history_json = convert_price_history(price_history_object, market_hash_name)

    return price_history_json


def parse_gmt_timestamp(ts_str) -> datetime:
    """Parse GMT timestamp string to datetime object"""
    try:
        # Try parsing format like "Apr 08 2025 08:00 GMT"
        ts_clean = ts_str.split(" GMT")[0]
        dt = datetime.strptime(ts_clean, "%b %d %Y %H:%M")
    except ValueError:
        # Fallback for format like "Apr 08 2025 08" (assuming :00)
        parts = ts_str.split(":")
        ts_clean = parts[0].strip()
        dt = datetime.strptime(ts_clean, "%b %d %Y %H")
    return pytz.timezone("GMT").localize(dt)


def load_and_process_data(json_data) -> pd.DataFrame:
    """Load data from JSON file and convert timestamps from GMT to IST"""
    data = json.loads(json_data)

    prices_list = data["prices"]
    df = pd.DataFrame(prices_list, columns=["timestamp", "price", "id"])
    df["price"] = pd.to_numeric(df["price"])

    # Parse GMT timestamps and convert to IST
    df["timestamp_gmt"] = df["timestamp"].apply(parse_gmt_timestamp)
    ist = pytz.timezone("Asia/Kolkata")
    df["timestamp_ist"] = df["timestamp_gmt"].apply(lambda x: x.astimezone(ist))
    df["timestamp_ist"] = df["timestamp_ist"].dt.tz_localize(
        None
    )  # Make tz-naive for darts

    df.set_index("timestamp_ist", inplace=True)
    df = df.drop(columns=["timestamp", "timestamp_gmt", "id"])
    df = df.sort_index()

    # Ensure hourly frequency, forward fill missing values if any (optional)
    df = df.asfreq("h", method="ffill")

    return df


def split_data_for_evaluation(df, test_hours=OUTPUT_CHUNK_LENGTH_DEFAULT) -> tuple:
    """Split data into training and test sets. Test set is the last `test_hours`."""
    if len(df) < test_hours:
        raise ValueError(
            f"Dataframe length ({len(df)}) is less than test_hours ({test_hours})"
        )

    split_point = len(df) - test_hours
    train_df = df.iloc[:split_point].copy()
    test_df = df.iloc[split_point:].copy()
    return train_df, test_df


# --- Weighted Average Model (Unchanged) ---
def weighted_average_model(df, half_life_days=7) -> Any:
    """Compute weighted average price by hour, giving more weight to recent data"""
    model_df = df.copy()
    last_date = model_df.index.max().date()
    model_df["days_from_end"] = [(last_date - d.date()).days for d in model_df.index]
    model_df["weight"] = np.exp(
        -np.log(2) * (model_df["days_from_end"] / half_life_days)
    )
    model_df["hour"] = model_df.index.hour

    weighted_avg = model_df.groupby("hour").apply(
        lambda x: np.average(x["price"], weights=x["weight"]),
        include_groups=False,  # Changed based on pandas update warning
    )
    return weighted_avg


# --- Darts Model Evaluation (Modified for new chunk lengths and variations) ---


def evaluate_darts_models(df, n_splits=None) -> tuple[dict, dict[Any, float]]:
    """Evaluation with aligned test windows but variable training windows using latest splits"""
    df = df.copy()
    df["date"] = df.index.date

    # Create model dictionary
    sample_train_ts = TimeSeries.from_dataframe(
        df.iloc[:48], value_cols=["price"], freq="h"
    )
    models = create_model_dictionary(sample_train_ts)

    # Get model-specific required training hours
    model_req_hours = {}
    for name, model in models.items():
        if hasattr(model, "input_chunk_length"):
            # Need input_chunk_length + output_chunk_length (24h)
            required_hours = model.input_chunk_length + OUTPUT_CHUNK_LENGTH_DEFAULT
            model_req_hours[name] = required_hours
        else:
            # Statistical models use predefined values
            base_name = name.split("_")[0]
            model_req_hours[name] = {
                "ExponentialSmoothing": 48,  # 2 days
                "TBATS": 48,
                "AutoTBATS": 48,
                "AutoARIMA": 72,  # 3 days
                "Croston": 48,
                "KalmanForecaster": 48,
                "AutoCES": 48,
            }.get(base_name, 48)

    # Determine longest required training window
    max_req_hours = max(model_req_hours.values())

    # Fixed test window size (24 hours)
    test_hours = OUTPUT_CHUNK_LENGTH_DEFAULT

    # Calculate maximum possible splits
    total_hours = len(df)
    max_splits = (total_hours - max_req_hours) // test_hours
    n_splits = min(n_splits or max_splits, MAX_SPLITS)

    logger.info(f"Running {n_splits} splits with aligned test windows (latest splits)")

    accumulated_results = defaultdict(lambda: {"mape": [], "smape": []})
    ensemble_weights_history = []

    # Calculate the starting split index to use the latest n_splits
    start_split_idx = max_splits - n_splits

    for split_idx in range(start_split_idx, start_split_idx + n_splits):
        print("\n")
        logger.info(f"=== Split {split_idx - start_split_idx + 1}/{n_splits} ===")
        split_results = {}
        forecasts = {}

        # Calculate test window for this split
        test_start = max_req_hours + (split_idx * test_hours)
        test_end = test_start + test_hours

        # Skip if test window exceeds data length
        if test_end > total_hours:
            logger.error(
                f"Skipping split {split_idx - start_split_idx + 1}: insufficient data"
            )
            continue

        test_df = df.iloc[test_start:test_end]
        test_ts = TimeSeries.from_dataframe(test_df, value_cols=["price"], freq="h")

        for name, model in models.items():
            # Calculate training window for this model and split
            train_hours = model_req_hours[name]
            train_start = test_start - train_hours
            train_end = test_start

            # Skip if training window goes before start of data
            if train_start < 0:
                logger.error(
                    f"{name} skipped: insufficient history (needs {train_hours}h)"
                )
                continue

            train_df = df.iloc[train_start:train_end]

            # Validate training data length
            if len(train_df) < train_hours:
                logger.error(
                    f"{name} skipped: Only {len(train_df)}h/{train_hours}h available"
                )
                continue

            # Training and forecasting
            try:
                train_ts = TimeSeries.from_dataframe(
                    train_df, value_cols=["price"], freq="h"
                )

                model.fit(train_ts)
                forecast = model.predict(len(test_ts))
                mape_score = mape(test_ts, forecast)

                split_results[name] = mape_score
                forecasts[name] = forecast
                accumulated_results[name]["mape"].append(mape_score)

                train_start_date = train_df.index[0].date()
                train_end_date = train_df.index[-1].date()
                logger.info(
                    f"{name:<18} | Train: {train_start_date}→{train_end_date} ({len(train_ts)}h) | MAPE: {mape_score:.1f}%"
                )
            except Exception as e:
                logger.error(f"{name:<18} | Error: {str(e)[:60]}")

        # Ensemble creation for this split
        valid_models = {k: v for k, v in split_results.items()}
        if len(valid_models) >= 2:
            weights = {k: 1 / (v + 1e-6) for k, v in valid_models.items()}
            total_weight = sum(weights.values())
            norm_weights = {k: w / total_weight for k, w in weights.items()}

            ensemble_values = sum(
                forecasts[name].values() * weight
                for name, weight in norm_weights.items()
            )
            ensemble_forecast = TimeSeries.from_times_and_values(
                test_ts.time_index, ensemble_values
            )

            ensemble_mape = mape(test_ts, ensemble_forecast)
            split_results["WeightedEnsemble"] = ensemble_mape
            logger.info(f"{'WeightedEnsemble':<18} | MAPE: {ensemble_mape:.1f}%")

            if "WeightedEnsemble" not in accumulated_results:
                accumulated_results["WeightedEnsemble"] = {"mape": []}
            accumulated_results["WeightedEnsemble"]["mape"].append(ensemble_mape)
            ensemble_weights_history.append(norm_weights)

    # Calculate average metrics
    avg_results = {}
    for name, metrics in accumulated_results.items():
        avg_results[name] = {
            "mape": np.mean(metrics["mape"]),
            "std_mape": np.std(metrics["mape"]),
            "n_splits": len(metrics["mape"]),
        }

    # Calculate average ensemble weights
    avg_weights = defaultdict(float)
    for weights in ensemble_weights_history:
        for name, weight in weights.items():
            avg_weights[name] += weight / len(ensemble_weights_history)

    return avg_results, dict(avg_weights)


def plot_combined_results(
    full_ts,
    forecasts,
    market_hash_name,
    best_times_ensemble=None,
    best_times_best_model=None,
    filename="combined_forecast.html",
) -> None:
    """Plot historical data and forecasts using Plotly with connected lines and proper naming"""

    # Set defaults for best times if not provided
    if best_times_ensemble is None:
        best_times_ensemble = []
    if best_times_best_model is None:
        best_times_best_model = []

    fig = go.Figure()

    # Use the last 100 points of full_ts for historical data display
    combined_dates = list(full_ts[-100:].time_index)
    combined_values = list(full_ts[-100:].values().flatten())

    # Get the last timestamp of historical data for connecting forecasts
    last_timestamp = combined_dates[-1]
    last_value = combined_values[-1]

    # Plot combined historical data with dull color
    fig.add_trace(
        go.Scatter(
            x=combined_dates,
            y=combined_values,
            mode="lines",
            name="Historical Data",
            line=dict(color="rgba(128,128,128,0.5)"),  # dull gray color
        )
    )

    # Plot forecasts with proper naming and ensure connection to historical data
    colors = [
        "rgba(147, 112, 219, 0.7)",
        "blue",
    ]  # Colors for different forecast models

    for i, (label, forecast) in enumerate(forecasts.items()):
        # Format name by replacing underscores with spaces
        display_name = label.replace("_", " ")

        color = colors[i % len(colors)]
        if len(forecasts) == 1:
            color = colors[1]

        # Create extended forecast data that includes the last point of historical data
        forecast_dates = [last_timestamp] + list(forecast.time_index)
        forecast_values = [last_value] + list(forecast.values().flatten())

        fig.add_trace(
            go.Scatter(
                x=forecast_dates,
                y=forecast_values,
                mode="lines",
                name=display_name,
                line=dict(color=color),
            )
        )

    if len(forecasts) > 1:
        title = f"Price Forecasts for {market_hash_name}"
    elif len(forecasts) == 1:
        title = f"Price Forecast for {market_hash_name}"
    else:
        raise Exception(f"Invalid number of forecasts: {len(forecasts)}")

    # Update layout
    fig.update_layout(
        title=title,
        xaxis_title="Date/Time (IST)",
        yaxis_title="Price (₹)",
        legend=dict(x=0.01, y=0.99),
        template="plotly_white",
        hovermode="x unified",
    )

    # Add grid
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor="rgba(0,0,0,0.1)")
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="rgba(0,0,0,0.1)")

    # Save a copy to the specified folder
    target_path = r"C:\Users\Sivasai\Documents\GitHub\CaseFarm\.venv"
    target_file = os.path.join(target_path, os.path.basename(filename))
    fig.write_html(target_file)
    print("\n")
    logger.info(f"Saved to {filename} in {target_path}")

    # Save raw data as JSON including recommended selling times in order
    json_filename = "combined_forecast_data.json"
    json_path = os.path.join(target_path, json_filename)

    # Helper function to convert recommended times list to dict
    def convert_recommended_times(times_list) -> list:
        current_time = datetime.fromtimestamp(time.time())
        formatted_times = []
        for i, t in enumerate(times_list):
            timestamp = None
            try:
                date_str = t["formatted_time"]
                dt = datetime.strptime(date_str, "%A, %B %d, %Y at %I:%M %p IST")
                timestamp = int(dt.timestamp())
            except Exception as e:
                logger.error(f"Could not parse time from string: {e}")

            time_dict = {
                "rank": i + 1,
                "formatted_time": t["formatted_time"],
                "price": t.get("price", None),
            }

            if timestamp is not None:
                time_dict["unix_timestamp"] = timestamp
                diff = dt - current_time
                total_seconds = int(diff.total_seconds())
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60

                if hours > 0 and minutes > 0:
                    time_from_now = f"{hours} hours {minutes} minutes from now"
                elif hours > 0:
                    time_from_now = f"{hours} hours from now"
                elif minutes > 0:
                    time_from_now = f"{minutes} minutes from now"
                else:
                    time_from_now = "less than a minute from now"

                time_dict["time_from_now"] = time_from_now

            formatted_times.append(time_dict)

        return formatted_times

    # Prepare data dictionary - use full_ts instead of train/test split
    data_dict = {}

    # Add recommended selling times in order
    data_dict["recommended_selling_times"] = {
        "ensemble": convert_recommended_times(best_times_ensemble),
        "best_model": convert_recommended_times(best_times_best_model),
    }

    for label, forecast in forecasts.items():
        data_dict[f"{label}_forecast"] = {
            "time": [t.isoformat() for t in forecast.time_index],
            "values": forecast.values().flatten().tolist(),
        }

    data_dict["historical_data"] = {
        "time": [t.isoformat() for t in full_ts[-100:].time_index],
        "values": full_ts[-100:].values().flatten().tolist(),
    }

    # Save to JSON
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data_dict, f, indent=4, ensure_ascii=False)

    logger.info(
        f"Raw data with recommended times saved to {json_filename} in {target_path}"
    )

    # Open the HTML file specifically in Chrome
    file_url = os.path.abspath(target_file)
    try:
        # For Windows
        chrome_path = "C:/Program Files/Google/Chrome/Application/chrome.exe %s"
        webbrowser.get(chrome_path).open_new_tab(file_url)
    except Exception as e:
        logger.error(f"Could not open Chrome: {e}")
        logger.info("Trying alternative method...")
        try:
            # Alternative method using subprocess
            subprocess.Popen(["start", "chrome", file_url], shell=True)
        except Exception as e:
            logger.error(f"Failed to open Chrome: {e}")
            logger.info("Opening in default browser instead.")
            webbrowser.open_new_tab(f"file://{file_url}")


# StatsForecast wrappers
# Regression-based models
# Deep learning models
# Model mode constants
from darts.models import (
    TBATS,
    AutoARIMA,
    AutoCES,
    AutoMFLES,
    AutoTBATS,
    Croston,
    DLinearModel,
    ExponentialSmoothing,
    KalmanForecaster,
    NBEATSModel,
    NLinearModel,
    XGBModel,
)
from darts.models.forecasting.baselines import NaiveMovingAverage


def create_model_dictionary(train_ts) -> dict:
    """Create and return dictionary of model instances with comprehensive options"""
    # Detect seasonality
    seasonal, period = check_seasonality(
        train_ts, m=OUTPUT_CHUNK_LENGTH_DEFAULT, max_lag=48
    )
    detected_period = period if seasonal else OUTPUT_CHUNK_LENGTH_DEFAULT

    # --- Define Chunk Lengths ---
    output_chunk_length_fixed = (
        OUTPUT_CHUNK_LENGTH_DEFAULT  # Target: predict next 24 hours directly
    )
    n_epochs_default = N_EPOCHS

    models = {}

    # == Classical & Statistical Models ==
    # These don't use input/output chunk lengths but might use seasonality period
    models.update(
        {
            "ExponentialSmoothing": ExponentialSmoothing(
                trend=ModelMode.ADDITIVE,
                seasonal=SeasonalityMode.MULTIPLICATIVE
                if seasonal
                else SeasonalityMode.NONE,
                seasonal_periods=detected_period,
            ),
            "AutoARIMA": AutoARIMA(),
            # TBATS requires season_length
            "TBATS": TBATS(season_length=detected_period),
            "Croston": Croston(),  # For intermittent data
            "KalmanForecaster": KalmanForecaster(),  # State-space model
            # StatsForecast wrappers
            "AutoCES": AutoCES(season_length=detected_period),
            "AutoTBATS": AutoTBATS(season_length=detected_period),
            # Simple baseline models
            "NaiveMovingAverage": NaiveMovingAverage(
                input_chunk_length=OUTPUT_CHUNK_LENGTH_DEFAULT
            ),
        }
    )

    # == Deep Learning Global Models ==

    models.update(
        {
            "AutoMFLES": AutoMFLES(
                season_length=detected_period, test_size=output_chunk_length_fixed
            )
        }
    )

    models["XGBoost_2x"] = XGBModel(
        lags=detected_period,
        output_chunk_length=output_chunk_length_fixed,
        n_estimators=100,
        max_depth=3,
    )

    for i in range(4, 8):
        icl = i * output_chunk_length_fixed
        models[f"N-BEATS_{i + 1}x"] = NBEATSModel(
            input_chunk_length=icl,
            output_chunk_length=output_chunk_length_fixed,
            n_epochs=n_epochs_default,
        )

        models[f"DLinear_{i + 1}x"] = DLinearModel(
            input_chunk_length=icl,
            output_chunk_length=output_chunk_length_fixed,
            n_epochs=n_epochs_default,
        )
        models[f"NLinear_{i + 1}x"] = NLinearModel(
            input_chunk_length=icl,
            output_chunk_length=output_chunk_length_fixed,
            n_epochs=n_epochs_default,
        )

    return models


def find_best_selling_times(forecast) -> list:
    """Find top N hours with highest forecasted price within the forecast period."""
    # Ensure forecast is a Darts TimeSeries
    if not isinstance(forecast, TimeSeries):
        logger.warning("Warning: forecast object is not a Darts TimeSeries.")
        return []

    # Try multiple approaches to get the DataFrame
    try:
        # Use the correct method for current Darts version
        df_forecast = forecast.to_dataframe()
    except (AttributeError, TypeError) as e:
        logger.error(f"Error accessing forecast data: {e}")
        logger.info(
            f"Available methods: {[m for m in dir(forecast) if not m.startswith('_')]}"
        )
        return []

    # Ensure the DataFrame has the expected column name 'price'
    if "price" not in df_forecast.columns:
        # If not 'price', try the first column (common for univariate)
        if len(df_forecast.columns) > 0:
            price_col = df_forecast.columns[0]
            logger.warn(f"Warning: 'price' column not found, using '{price_col}'.")
        else:
            logger.warm("Error: Forecast DataFrame has no columns.")
            return []
    else:
        price_col = "price"

    # Ensure index is DatetimeIndex
    if not isinstance(df_forecast.index, pd.DatetimeIndex):
        logger.warn("Warning: Forecast index is not DatetimeIndex.")
        # Attempt conversion if possible, otherwise return empty
        try:
            df_forecast.index = pd.to_datetime(df_forecast.index)
        except Exception as e:
            logger.error(f"Error converting forecast index to DatetimeIndex: {e}")
            return []

    top_times = df_forecast.sort_values(by=price_col, ascending=False)
    results = []
    ist = pytz.timezone("Asia/Kolkata")  # Define IST timezone

    for idx, row in top_times.iterrows():
        # Remove the localize - timestamps are already in IST
        # Just make timezone-aware by localizing directly to IST
        dt_aware = ist.localize(idx) if idx.tzinfo is None else idx.astimezone(ist)
        price = row[price_col]
        results.append(
            {
                "datetime_obj": dt_aware,
                "formatted_time": dt_aware.strftime("%A, %B %d, %Y at %I:%M %p %Z"),
                "price": f"₹{price:.2f}",
            }
        )
    return results


def create_weighted_ensemble_forecast(
    results, full_ts, forecast_horizon=OUTPUT_CHUNK_LENGTH_DEFAULT, preset_weights=None
) -> None | TimeSeries | Any:
    """
    Create weighted ensemble forecast using either preset weights or calculated weights.
    """
    print("\n")
    logger.info("--- Creating weighted ensemble forecast ---")

    # Filter successful models that exist in both results and preset_weights (if provided)
    successful_models = {}
    if preset_weights is not None:
        # Use only models present in both results and preset weights
        successful_models = {
            name: info
            for name, info in results.items()
            if "model" in info and name in preset_weights
        }
        logger.info(
            f"Using {len(successful_models)} preset weighted models for ensemble"
        )
    else:
        # Use all successful models with mape scores
        successful_models = {
            name: info
            for name, info in results.items()
            if "model" in info and "mape" in info
        }
        logger.info(
            f"Using {len(successful_models)} performance-weighted models for ensemble"
        )

    if not successful_models:
        logger.error("Error: No successful models to create ensemble.")
        return None

    # Initialize storage for forecasts and weights
    all_forecasts = []
    model_names = []
    weights = []

    # Generate forecasts and determine weights
    for name, info in successful_models.items():
        model = info["model"]
        try:
            # Generate forecast using already trained model
            forecast = model.predict(n=forecast_horizon)
            all_forecasts.append(forecast)
            model_names.append(name)

            # Determine weights
            if preset_weights is not None:
                weight = preset_weights[name]
            else:
                # Calculate weight from mape performance
                mape_score = info["mape"]
                weight = 1.0 / (mape_score + 0.001)  # Prevent division by zero

            weights.append(weight)
            logger.info(f"  ✓ {name} forecast generated (weight: {weight:.4f})")

        except Exception as e:
            logger.error(f"  ✗ {name} failed during forecasting: {str(e)[:80]}")

    if not all_forecasts:
        logger.critical("Error: No models were able to generate forecasts.")
        return None

    # Normalize weights to sum to 1
    total_weight = sum(weights)
    normalized_weights = [w / total_weight for w in weights]

    # Create weighted average forecast
    try:
        # Initialize with zeros array of correct shape
        ensemble_values = np.zeros_like(all_forecasts[0].values())

        # Sum weighted forecasts
        for i, forecast in enumerate(all_forecasts):
            ensemble_values += forecast.values() * normalized_weights[i]

        # Create final ensemble TimeSeries
        ensemble_forecast = TimeSeries.from_times_and_values(
            times=all_forecasts[0].time_index,
            values=ensemble_values,
            columns=full_ts.columns,
            freq=full_ts.freq,
        )
        print("\n")
        logger.info("Ensemble forecast created successfully")
        return ensemble_forecast

    except Exception as e:
        logger.error(f"Error creating ensemble: {str(e)[:150]}")
        # Fallback to best individual model if available
        if all_forecasts:
            best_idx = weights.index(max(weights))
            logger.info(f"Falling back to best model: {model_names[best_idx]}")
            return all_forecasts[best_idx]
        return None


def get_model_required_length(name, model) -> Any | int:
    """Get the minimum required training length for a model."""
    if hasattr(model, "input_chunk_length"):
        return model.input_chunk_length + OUTPUT_CHUNK_LENGTH_DEFAULT
    else:
        base_name = name.split("_")[0]
        return {
            "ExponentialSmoothing": 48,  # 2 days
            "TBATS": 48,
            "AutoTBATS": 48,
            "AutoARIMA": 72,  # 3 days
            "Croston": 48,
            "KalmanForecaster": 48,
            "AutoCES": 48,
            "NaiveMovingAverage": 48,
            "XGBoost": 48,
            "AutoMFLES": 48,
            "SF_MFLES": 48,
            "SF_DOT": 48,
        }.get(base_name, 48)


# --- Main Execution Logic ---
async def generate_schedule(market_hash_name=MARKET_HASH_NAME_DEFAULT) -> Literal[True]:
    """
    Generates the selling schedule for the market_hash_name that you're passing. It creates a plotly graph which is stored at .venv/combined_forecast.html
    and it also creates a json which contains the graph data along with the selling time recommendations which is at .venv/combined_forecast_data.json
    """
    start_time = time.time()
    print("\n")
    logger.info(f"=== Generating Schedule for {market_hash_name} ===")
    # --- Fetch Price History Object ---
    price_history_json = await get_price_history_json(market_hash_name=market_hash_name)
    # --- Data Loading ---
    df = load_and_process_data(price_history_json)
    print("\n")
    logger.info(
        f"Loaded {len(df)} hourly records from {df.index.min()} to {df.index.max()}"
    )
    # --- Data Validation ---
    min_days = 8  # 7 days training + 1 day testing
    if len(df) < OUTPUT_CHUNK_LENGTH_DEFAULT * min_days:
        raise ValueError(
            f"Insufficient data: Need at least {min_days} full days (got {len(df) / OUTPUT_CHUNK_LENGTH_DEFAULT:.1f} days)"
        )
    print("\n")
    logger.info("=== Running multiple split training and evaluation runs ===")
    cv_results, ensemble_weights = evaluate_darts_models(df)
    print("\n")
    logger.info("=== Training Final Models ===")
    full_ts = TimeSeries.from_dataframe(df, value_cols=["price"], freq="h")

    # Train best individual model
    best_model_name = min(cv_results.items(), key=lambda x: x[1]["mape"])[0]
    if best_model_name != "WeightedEnsemble":
        best_model_is_ensemble = False
        print("\n")
        logger.info(f"Training best individual model ({best_model_name})...")
        best_model = create_model_dictionary(full_ts)[best_model_name]

        # Check if we have enough data
        required_length = get_model_required_length(best_model_name, best_model)
        if len(full_ts) >= required_length:
            # Create appropriate slice of the time series
            train_ts = full_ts[-required_length:]
            logger.info(f"Data given to {best_model_name} for training:")
            logger.info(
                f"Using {len(train_ts)} data points from {train_ts.start_time()} to {train_ts.end_time()}"
            )

            # Train on the appropriate slice
            best_model.fit(train_ts)
            best_forecast = best_model.predict(OUTPUT_CHUNK_LENGTH_DEFAULT)
        else:
            logger.error(
                f"Cannot train {best_model_name}: requires {required_length} data points, but only have {len(full_ts)}"
            )
            best_model_is_ensemble = True  # Fall back to ensemble
    else:
        best_model_is_ensemble = True

    # Train all ensemble candidate models on full data
    final_models = {}
    model_definitions = create_model_dictionary(full_ts)
    for name in ensemble_weights.keys():
        try:
            # Check if we have enough data for this model
            model = model_definitions[name]
            required_length = get_model_required_length(name, model)

            if len(full_ts) < required_length:
                print("\n")
                logger.info(
                    f"Skipping {name}: requires {required_length} data points, but only have {len(full_ts)}"
                )
                continue

            # Create appropriate slice of the time series
            train_ts = full_ts[-required_length:]
            logger.info(
                f"Data given to {name} for training: {len(train_ts)} data points from {train_ts.start_time()} to {train_ts.end_time()}"
            )
            print("\n")
            # Train on the appropriate slice
            model.fit(train_ts)
            final_models[name] = {
                "model": model,
                "mape": cv_results[name]["mape"],  # Use CV performance for weighting
            }
        except Exception as e:
            logger.critical(f"Failed to train {name}: {str(e)[:50]}")

    # Create weighted ensemble
    print("\n")
    logger.info("Creating weighted ensemble...")
    ensemble_forecast = create_weighted_ensemble_forecast(
        results=final_models,  # Pass trained models with CV metrics
        full_ts=full_ts,
        forecast_horizon=OUTPUT_CHUNK_LENGTH_DEFAULT,
        preset_weights=ensemble_weights,
    )

    # --- Display CV Results ---
    print("\n")
    logger.info("=== Model Accuracies ===")
    logger.info(f"{'Model':<25} {'Avg MAPE':>10} {'Std MAPE':>10}")
    for name, metrics in sorted(cv_results.items(), key=lambda x: x[1]["mape"]):
        logger.info(
            f"{name:<25} {metrics['mape']:>10.2f}% {metrics['std_mape']:>10.2f}"
        )

    # --- Generate Predictions ---

    best_times_ensemble = find_best_selling_times(ensemble_forecast)

    if not best_model_is_ensemble:
        best_times_best_model = find_best_selling_times(best_forecast)
    else:
        best_times_best_model = None

    # --- Visualization ---

    # Create forecasts dictionary for visualization

    if best_model_is_ensemble:
        forecasts = {"Weighted_Ensemble": ensemble_forecast}
    else:
        forecasts = {
            "Best_Model": best_forecast,
            "Weighted_Ensemble": ensemble_forecast,
        }

    # Keep existing combined plot
    plot_combined_results(
        full_ts,
        forecasts,
        market_hash_name,
        best_times_ensemble=best_times_ensemble,
        best_times_best_model=best_times_best_model,
        filename="combined_forecast.html",
    )

    end_time = time.time()
    elapsed_time = end_time - start_time

    # Convert to hours, minutes, seconds
    hours = int(elapsed_time // 3600)
    minutes = int((elapsed_time % 3600) // 60)
    seconds = elapsed_time % 60

    # Print conditionally based on whether hours exist
    if hours > 0:
        print("\n")
        logger.info(
            f"Total time taken: {hours} hours {minutes} minutes {seconds:.2f} seconds"
        )
    else:
        print("\n")
        logger.info(f"Total time taken: {minutes} minutes {seconds:.2f} seconds")

    # --- Output Results ---
    print("\n")
    logger.info("=== Final Recommendation ===")
    print("\n")
    logger.info("Recommended Selling Times in order (ensemble):")
    for i, t in enumerate(best_times_ensemble[:5], 1):
        logger.info(f"{i}. {t['formatted_time']} - {t['price']}")

    return True


# Example Usage
if __name__ == "__main__":
    predicted_times = asyncio.run(
        generate_schedule(market_hash_name=MARKET_HASH_NAME_DEFAULT)
    )
