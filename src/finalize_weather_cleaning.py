
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

INPUT_FILE = (
    ROOT / "data" / "processed"
    / "solar_system1430_2014_2016_clean.csv"
)
OUTPUT_FILE = (
    ROOT / "data" / "processed"
    / "solar_system1430_2014_2016_final.csv"
)

df = pd.read_csv(INPUT_FILE)

ambient = "ambient_temp__5042"

# Treat implausibly high ambient-temperature measurements as missing.
# Preserve all rows and leave the original cleaned file unchanged.
invalid_temp = df[ambient] > 60
print("Ambient-temperature values above 60 C:", int(invalid_temp.sum()))

df.loc[invalid_temp, ambient] = float("nan")

df.to_csv(OUTPUT_FILE, index=False)

print("\nFinal dataset saved:", OUTPUT_FILE)
print("Rows retained:", len(df))
print("Missing ambient temperature:", int(df[ambient].isna().sum()))
print("Ambient temperature maximum:", df[ambient].max())
print("Negative irradiance remaining:",
      int((df["poa_irradiance__5041"] < 0).sum()))
print("Missing power:", int(df["power_w"].isna().sum()))

