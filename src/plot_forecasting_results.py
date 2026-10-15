
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
PREDICTIONS = RESULTS / "forecast_test_predictions.csv"

df = pd.read_csv(PREDICTIONS, parse_dates=["measured_on"])
df = df.sort_values("measured_on").reset_index(drop=True)

# Plot 1: actual versus predicted power for a 7-day sample.
sample = df.dropna(
    subset=["actual_power_w", "random_forest_prediction_w"]
).head(7 * 24 * 4)

plt.figure(figsize=(13, 5))
plt.plot(
    sample["measured_on"],
    sample["actual_power_w"] / 1000,
    label="Actual",
    linewidth=1.5,
)
plt.plot(
    sample["measured_on"],
    sample["random_forest_prediction_w"] / 1000,
    label="Random Forest",
    linewidth=1.2,
)
plt.xlabel("Timestamp")
plt.ylabel("Solar power (kW)")
plt.title("Solar Power: Actual vs Random Forest Prediction")
plt.legend()
plt.xticks(rotation=30)
plt.tight_layout()
plt.savefig(RESULTS / "actual_vs_predicted.png", dpi=160)
plt.close()

# Plot 2: prediction error over a 7-day sample.
sample["error_w"] = (
    sample["random_forest_prediction_w"] - sample["actual_power_w"]
)

plt.figure(figsize=(13, 5))
plt.plot(
    sample["measured_on"],
    sample["error_w"] / 1000,
    linewidth=1,
)
plt.axhline(0, linestyle="--")
plt.xlabel("Timestamp")
plt.ylabel("Prediction error (kW)")
plt.title("Random Forest Prediction Error")
plt.xticks(rotation=30)
plt.tight_layout()
plt.savefig(RESULTS / "prediction_error.png", dpi=160)
plt.close()

# Plot 3: actual power and empirical prediction interval.
interval_sample = df.dropna(
    subset=[
        "actual_power_w",
        "lower_bound_90_w",
        "upper_bound_90_w",
    ]
).head(7 * 24 * 4)

plt.figure(figsize=(13, 5))
plt.plot(
    interval_sample["measured_on"],
    interval_sample["actual_power_w"] / 1000,
    label="Actual",
    linewidth=1.4,
)
plt.plot(
    interval_sample["measured_on"],
    interval_sample["random_forest_prediction_w"] / 1000,
    label="Prediction",
    linewidth=1.1,
)
plt.fill_between(
    interval_sample["measured_on"],
    interval_sample["lower_bound_90_w"] / 1000,
    interval_sample["upper_bound_90_w"] / 1000,
    alpha=0.2,
    label="Nominal 90% interval",
)
plt.xlabel("Timestamp")
plt.ylabel("Solar power (kW)")
plt.title("Solar Forecast with Empirical Prediction Interval")
plt.legend()
plt.xticks(rotation=30)
plt.tight_layout()
plt.savefig(RESULTS / "prediction_intervals.png", dpi=160)
plt.close()

print("Plots saved:")
print(RESULTS / "actual_vs_predicted.png")
print(RESULTS / "prediction_error.png")
print(RESULTS / "prediction_intervals.png")

# Plot 4: compare persistence and Random Forest predictions.
comparison = df.dropna(
    subset=[
        "actual_power_w",
        "persistence_prediction_w",
        "random_forest_prediction_w",
    ]
).head(7 * 24 * 4)

plt.figure(figsize=(13, 5))
plt.plot(
    comparison["measured_on"],
    comparison["actual_power_w"] / 1000,
    label="Actual",
    linewidth=1.5,
)
plt.plot(
    comparison["measured_on"],
    comparison["persistence_prediction_w"] / 1000,
    label="Persistence",
    linewidth=1,
)
plt.plot(
    comparison["measured_on"],
    comparison["random_forest_prediction_w"] / 1000,
    label="Random Forest",
    linewidth=1,
)
plt.xlabel("Timestamp")
plt.ylabel("Solar power (kW)")
plt.title("Baseline Comparison: Persistence vs Random Forest")
plt.legend()
plt.xticks(rotation=30)
plt.tight_layout()
plt.savefig(RESULTS / "baseline_comparison.png", dpi=160)
plt.close()

print("Baseline comparison saved:", RESULTS / "baseline_comparison.png")
