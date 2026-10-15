
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"

RF_FILE = RESULTS / "forecast_test_predictions.csv"
LSTM_FILE = RESULTS / "lstm_test_predictions.csv"
GRU_FILE = RESULTS / "gru_test_predictions.csv"


def load_rf_predictions():
    df = pd.read_csv(RF_FILE, parse_dates=["measured_on"])

    required = {
        "measured_on",
        "actual_power_w",
        "persistence_prediction_w",
        "random_forest_prediction_w",
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns in RF file: {missing}")

    df = df[
        [
            "measured_on",
            "actual_power_w",
            "persistence_prediction_w",
            "random_forest_prediction_w",
        ]
    ].copy()

    if df["measured_on"].duplicated().any():
        raise ValueError("Duplicate timestamps in RF predictions.")

    return df


def load_sequence_predictions(path, model_name, prediction_column):
    df = pd.read_csv(path, parse_dates=["measured_on"])

    required = {"measured_on", "actual_power_w", "predicted_power_w"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns in {path.name}: {missing}")

    df = df[["measured_on", "actual_power_w", "predicted_power_w"]].copy()
    df = df.rename(columns={
        "actual_power_w": f"actual_{model_name}",
        "predicted_power_w": prediction_column,
    })

    if df["measured_on"].duplicated().any():
        raise ValueError(f"Duplicate timestamps in {path.name}")

    return df


def calculate_metrics(actual, predicted):
    nonzero = actual != 0

    return {
        "rows_evaluated": int(len(actual)),
        "MAE_W": float(mean_absolute_error(actual, predicted)),
        "RMSE_W": float(np.sqrt(mean_squared_error(actual, predicted))),
        "MAPE_percent_nonzero_actuals": (
            float(
                np.mean(
                    np.abs(
                        (actual[nonzero] - predicted[nonzero])
                        / actual[nonzero]
                    )
                ) * 100
            )
            if nonzero.any()
            else np.nan
        ),
        "R2": float(r2_score(actual, predicted)),
    }


def main():
    rf = load_rf_predictions()

    lstm = load_sequence_predictions(
        LSTM_FILE, "lstm", "lstm_prediction_w"
    )
    gru = load_sequence_predictions(
        GRU_FILE, "gru", "gru_prediction_w"
    )

    # Inner joins retain only timestamps evaluated by all three files.
    common = rf.merge(lstm, on="measured_on", how="inner")
    common = common.merge(gru, on="measured_on", how="inner")

    if common.empty:
        raise ValueError("No common timestamps across prediction files.")

    actual_rf = common["actual_power_w"].to_numpy(dtype=float)
    actual_lstm = common["actual_lstm"].to_numpy(dtype=float)
    actual_gru = common["actual_gru"].to_numpy(dtype=float)

    if not (
        np.allclose(actual_rf, actual_lstm, equal_nan=True)
        and np.allclose(actual_rf, actual_gru, equal_nan=True)
    ):
        raise ValueError("Actual power differs across prediction files.")

    actual = actual_rf

    model_predictions = {
        "Persistence": common["persistence_prediction_w"].to_numpy(dtype=float),
        "Random Forest": common["random_forest_prediction_w"].to_numpy(dtype=float),
        "LSTM": common["lstm_prediction_w"].to_numpy(dtype=float),
        "GRU": common["gru_prediction_w"].to_numpy(dtype=float),
    }

    # Evaluate every model on the same rows with finite actuals and predictions.
    valid = np.isfinite(actual)
    for predicted in model_predictions.values():
        valid &= np.isfinite(predicted)

    common = common.loc[valid].reset_index(drop=True)
    actual = actual[valid]
    model_predictions = {
        name: predicted[valid]
        for name, predicted in model_predictions.items()
    }

    if len(actual) == 0:
        raise ValueError("No common valid predictions across all models.")

    rows = []
    for model, predicted in model_predictions.items():
        row = {"model": model}
        row.update(calculate_metrics(actual, predicted))
        rows.append(row)

    comparison = pd.DataFrame(rows)
    comparison.to_csv(
        RESULTS / "fair_model_comparison.csv", index=False
    )

    output = pd.DataFrame({
        "measured_on": common["measured_on"],
        "actual_power_w": actual,
        "persistence_prediction_w": model_predictions["Persistence"],
        "random_forest_prediction_w": model_predictions["Random Forest"],
        "lstm_prediction_w": model_predictions["LSTM"],
        "gru_prediction_w": model_predictions["GRU"],
    })
    output.to_csv(
        RESULTS / "common_timestamp_predictions.csv", index=False
    )

    print(f"Common valid test timestamps: {len(common)}")
    print("\nFair model comparison:")
    print(
        comparison.to_string(
            index=False,
            float_format=lambda x: f"{x:.3f}"
        )
    )
    print("\nSaved:", RESULTS / "fair_model_comparison.csv")
    print("Saved:", RESULTS / "common_timestamp_predictions.csv")


if __name__ == "__main__":
    main()
