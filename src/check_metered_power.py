
from pathlib import Path
import pandas as pd

project = Path(__file__).resolve().parent.parent
input_file = project / "data" / "processed" / "pvdaq_combined_2011.csv"

df = pd.read_csv(input_file, parse_dates=["measured_on"])
meter = "ac_power_metered_kw__2802"

# Apply the scale factor documented in the System 1202 metadata.
df["metered_power_w"] = pd.to_numeric(
    df[meter], errors="coerce"
) * 1000

df = df.set_index("measured_on").sort_index()

# Resample the target to 15-minute intervals.
power = df["metered_power_w"].resample("15min").mean()

print("--- METERED POWER AFTER UNIT CONVERSION ---")
print("Total intervals:", len(power))
print("Observed intervals:", power.notna().sum())
print("Missing intervals:", power.isna().sum())
print("\nSummary in watts:")
print(power.describe().round(2).to_string())

print("\n--- DAILY COVERAGE AND VARIATION ---")
daily = power.groupby(power.index.date).agg(
    valid_readings="count",
    unique_values="nunique",
    mean="mean",
    maximum="max",
)

print(daily.round(2).to_string())

print("\nNote: constant readings and anomalies still need investigation.")
