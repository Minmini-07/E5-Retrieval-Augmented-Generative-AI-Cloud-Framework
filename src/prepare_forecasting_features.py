
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

INPUT_FILE = (
    ROOT / "data" / "processed"
    / "solar_system1430_2014_2016_final.csv"
)
OUTPUT_FILE = (
    ROOT / "data" / "processed"
    / "solar_forecasting_features_2014_2016.csv"
)

df = pd.read_csv(INPUT_FILE, parse_dates=["measured_on"])
df = df.sort_values("measured_on").reset_index(drop=True)

df["measured_on"] = pd.to_datetime(df["measured_on"], utc=True)
df = df.set_index("measured_on")

# Cyclical time features preserve the natural daily/yearly cycles.
hour = df.index.hour + df.index.minute / 60
day_of_year = df.index.dayofyear

df["hour_sin"] = np.sin(2 * np.pi * hour / 24)
df["hour_cos"] = np.cos(2 * np.pi * hour / 24)
df["day_of_week"] = df.index.dayofweek
df["month_sin"] = np.sin(2 * np.pi * (df.index.month - 1) / 12)
df["month_cos"] = np.cos(2 * np.pi * (df.index.month - 1) / 12)
df["day_of_year_sin"] = np.sin(2 * np.pi * day_of_year / 365.25)
df["day_of_year_cos"] = np.cos(2 * np.pi * day_of_year / 365.25)

# Use only past measurements as predictors.
lag_steps = [1, 3, 6, 24]

for lag in lag_steps:
    df[f"power_lag_{lag}"] = df["power_w"].shift(lag)
    df[f"irradiance_lag_{lag}"] = (
        df["poa_irradiance__5041"].shift(lag)
    )
    df[f"ambient_temp_lag_{lag}"] = (
        df["ambient_temp__5042"].shift(lag)
    )
    df[f"module_temp_lag_{lag}"] = (
        df["module_temp__5043"].shift(lag)
    )

# Shift first, then roll: current/future targets are never included.
past_power = df["power_w"].shift(1)

df["power_rolling_mean_4"] = past_power.rolling(
    window=4, min_periods=4
).mean()
df["power_rolling_std_4"] = past_power.rolling(
    window=4, min_periods=4
).std()

df["power_rolling_mean_24"] = past_power.rolling(
    window=24, min_periods=24
).mean()
df["power_rolling_std_24"] = past_power.rolling(
    window=24, min_periods=24
).std()

df = df.replace([np.inf, -np.inf], np.nan)
df = df.reset_index()

df.to_csv(OUTPUT_FILE, index=False)

print("Feature dataset saved:", OUTPUT_FILE)
print("Total rows:", len(df))
print("Total columns:", len(df.columns))
print("Target missing:", df["power_w"].isna().sum())
print("First timestamp:", df["measured_on"].min())
print("Last timestamp:", df["measured_on"].max())

print("\nNew forecasting features:")
print([
    c for c in df.columns
    if "_lag_" in c or "_rolling_" in c
    or c.endswith("_sin") or c.endswith("_cos")
    or c == "day_of_week"
])
