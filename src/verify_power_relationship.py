
from pathlib import Path
import pandas as pd

project = Path(__file__).resolve().parent.parent
folder = project / "data" / "raw" / "system_1430_sample"

df = pd.concat(
    [pd.read_csv(f) for f in sorted(folder.glob("*.csv"))],
    ignore_index=True,
)

for col in ["ac_power__5074", "dc_power__5077", "poa_irradiance__5041"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

day = df[df["poa_irradiance__5041"] >= 200].copy()

day["ac_power_scaled_w"] = day["ac_power__5074"] * 2000

valid = day[
    (day["ac_power_scaled_w"] > 0)
    & (day["dc_power__5077"] > 0)
]

print("Valid daytime pairs:", len(valid))

print(
    "\nCorrelation between scaled AC and DC power:",
    round(valid["ac_power_scaled_w"].corr(valid["dc_power__5077"]), 4),
)

valid["ac_dc_ratio"] = (
    valid["ac_power_scaled_w"] / valid["dc_power__5077"]
)

print("\nAC/DC ratio summary:")
print(valid["ac_dc_ratio"].describe().round(4).to_string())

print("\nSample comparison:")
print(
    valid[[
        "measured_on",
        "ac_power_scaled_w",
        "dc_power__5077",
        "ac_dc_ratio",
    ]].head(10).round(2).to_string(index=False)
)
