
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = PROJECT_ROOT / "data" / "raw"
OUTPUT_ROOT = PROJECT_ROOT / "data" / "processed"
OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

SCALE_FACTOR = 2000.0
REQUIRED_COLUMNS = [
    "measured_on",
    "ac_power__5074",
    "poa_irradiance__5041",
    "ambient_temp__5042",
    "module_temp__5043",
]

year_frames = []

for year in [2014, 2015, 2016]:
    folder = RAW_ROOT / f"system_1430_{year}"
    files = sorted(folder.glob("*.csv"))

    if not files:
        raise FileNotFoundError(f"No CSV files found in {folder}")

    daily_frames = []
    failed_files = []

    for file in files:
        try:
            daily_frames.append(pd.read_csv(file))
        except Exception as exc:
            failed_files.append((file.name, str(exc)))

    if failed_files:
        raise RuntimeError(
            f"{year}: {len(failed_files)} files could not be read. "
            f"First failure: {failed_files[0]}"
        )

    year_df = pd.concat(daily_frames, ignore_index=True)

    missing_columns = [
        column for column in REQUIRED_COLUMNS
        if column not in year_df.columns
    ]
    if missing_columns:
        raise ValueError(
            f"{year} is missing required columns: {missing_columns}"
        )

    year_df = year_df[REQUIRED_COLUMNS].copy()
    year_df["measured_on"] = pd.to_datetime(
        year_df["measured_on"], errors="coerce", utc=True
    )

    year_df = year_df.dropna(subset=["measured_on"])
    year_df = year_df.sort_values("measured_on")

    if year_df["measured_on"].duplicated().any():
        raise ValueError(f"Duplicate timestamps found in {year}")

    year_df["year"] = year
    year_frames.append(year_df)

    print(f"{year}: {len(year_df):,} rows loaded")

data = pd.concat(year_frames, ignore_index=True)
data = data.sort_values("measured_on").reset_index(drop=True)

if data["measured_on"].duplicated().any():
    raise ValueError("Duplicate timestamps found across years")

# Convert raw AC power to watts using the confirmed metadata.
data["power_w"] = (
    pd.to_numeric(data["ac_power__5074"], errors="coerce")
    * SCALE_FACTOR
)

# Convert sensor columns to numeric values.
for column in [
    "poa_irradiance__5041",
    "ambient_temp__5042",
    "module_temp__5043",
]:
    data[column] = pd.to_numeric(data[column], errors="coerce")

# Correct tiny negative readings only at night.
night = data["poa_irradiance__5041"].fillna(0) < 20
tiny_negative = data["power_w"].between(-100, 0, inclusive="left")
data.loc[night & tiny_negative, "power_w"] = 0.0

# Keep missing target readings as missing; do not invent measurements.
# Retain timestamps and source sensor columns for traceability.
output_file = OUTPUT_ROOT / "solar_system1430_2014_2016.csv"
data.to_csv(output_file, index=False)

print("\nDataset created successfully!")
print(f"Saved to: {output_file}")
print(f"Total rows: {len(data):,}")
print(f"Date range: {data['measured_on'].min()} to "
      f"{data['measured_on'].max()}")
print(f"Missing power readings: {data['power_w'].isna().sum():,}")
print(f"Maximum power: {data['power_w'].max():,.1f} W")
print(f"Duplicate timestamps: {data['measured_on'].duplicated().sum()}")
print("\nRows by year:")
print(data.groupby("year").size())
