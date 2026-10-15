
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent

folders = {
    2014: ROOT / "data/raw/system_1430_2014",
    2015: ROOT / "data/raw/system_1430_2015",
    2016: ROOT / "data/raw/system_1430_2016",
}

for year, folder in folders.items():
    frames = []
    files = sorted(folder.glob("*.csv"))

    for file in files:
        try:
            df = pd.read_csv(file)
            if "measured_on" in df.columns:
                frames.append(df)
        except Exception as exc:
            print(f"Could not read {file.name}: {exc}")

    if not frames:
        print(f"\n{year}: No readable data found.")
        continue

    data = pd.concat(frames, ignore_index=True)

    print(f"\n===== {year} =====")
    print("Files read:", len(frames))
    print("Available columns:", data.columns.tolist())

    if "ac_power__5074" not in data.columns:
        print("Cannot verify: AC power column is missing.")
        continue

    ac = pd.to_numeric(data["ac_power__5074"], errors="coerce")
    ac_scaled = ac * 2000

    print("Missing AC readings:", int(ac.isna().sum()))
    print("Raw AC maximum:", round(ac.max(), 3))
    print("Scaled AC maximum (W):", round(ac_scaled.max(), 1))

    if "dc_power__5077" not in data.columns:
        print("DC power column unavailable; skipping AC/DC check.")
        continue

    if "poa_irradiance__5041" not in data.columns:
        print("Irradiance column unavailable; skipping AC/DC check.")
        continue

    dc = pd.to_numeric(data["dc_power__5077"], errors="coerce")
    irradiance = pd.to_numeric(
        data["poa_irradiance__5041"], errors="coerce"
    )

    valid = (
        (irradiance >= 200)
        & ac_scaled.notna()
        & dc.notna()
        & (dc > 0)
    )

    ratio = ac_scaled[valid] / dc[valid]

    print("DC maximum (W):", round(dc.max(), 1))
    print("Valid daytime AC/DC comparisons:", int(valid.sum()))

    if len(ratio):
        print("AC/DC ratio median:", round(ratio.median(), 4))
        print(
            "AC/DC ratio 5th percentile:",
            round(ratio.quantile(0.05), 4),
        )
        print(
            "AC/DC ratio 95th percentile:",
            round(ratio.quantile(0.95), 4),
        )
    else:
        print("No valid rows for AC/DC comparison.")
