
from pathlib import Path
import pandas as pd

path = Path("data/processed/solar_system1430_may_july_2017.csv")
df = pd.read_csv(path, parse_dates=["measured_on"])

power = pd.to_numeric(df["power_w"], errors="coerce")
irradiance = pd.to_numeric(
    df["poa_irradiance__5041"], errors="coerce"
)

print("===== POWER QUALITY CHECK =====")
print("Missing power:", int(power.isna().sum()))
print("Negative power readings:", int((power < 0).sum()))
print("Zero power readings:", int((power == 0).sum()))
print("Positive power readings:", int((power > 0).sum()))

print("\nNegative readings:")
print(
    df.loc[power < 0, ["measured_on", "power_w",
                       "poa_irradiance__5041"]]
    .head(15)
    .to_string(index=False)
)

print("\nMissing power by month:")
print(
    df.loc[power.isna()]
    .groupby(df.loc[power.isna(), "measured_on"].dt.to_period("M"))
    .size()
)

daytime = irradiance >= 200
print("\nMissing power during daytime:",
      int((power.isna() & daytime).sum()))

print("Negative power during daytime:",
      int(((power < 0) & daytime).sum()))

print("\nLargest negative reading (W):", power.min())
