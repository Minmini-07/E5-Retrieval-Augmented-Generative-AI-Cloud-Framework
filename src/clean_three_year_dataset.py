
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

input_file = ROOT / "data" / "processed" / "solar_system1430_2014_2016.csv"
output_file = ROOT / "data" / "processed" / "solar_system1430_2014_2016_clean.csv"

df = pd.read_csv(input_file)

weather_columns = [
    "poa_irradiance__5041",
    "ambient_temp__5042",
    "module_temp__5043",
]

# Keep the original dataset unchanged.
# Mark negative irradiance as invalid rather than treating it as zero.
negative_irradiance = df["poa_irradiance__5041"] < 0
print("Negative irradiance readings:", int(negative_irradiance.sum()))

df.loc[negative_irradiance, "poa_irradiance__5041"] = float("nan")

# Do not invent missing sensor readings or target values.
# Keep rows and timestamps for chronological forecasting.
df.to_csv(output_file, index=False)

print("\nCleaned dataset saved:", output_file)
print("Rows retained:", len(df))
print("\nMissing values after cleaning:")
print(df[["power_w"] + weather_columns].isna().sum().to_string())

print("\nNegative irradiance remaining:",
      int((df["poa_irradiance__5041"] < 0).sum()))
print("Negative power readings:", int((df["power_w"] < 0).sum()))
print("Zero-power readings:", int((df["power_w"] == 0).sum()))
