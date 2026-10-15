
from pathlib import Path
import json
import warnings

import joblib
import numpy as np
import pandas as pd
import tensorflow as tf

from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from tensorflow.keras import Sequential
from tensorflow.keras.layers import Input, GRU, Dense, Dropout
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau

warnings.filterwarnings("ignore", category=FutureWarning)

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "processed" / "solar_forecasting_features_2014_2016.csv"
MODEL_DIR = ROOT / "models"
RESULTS_DIR = ROOT / "results"

MODEL_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

TARGET = "power_w"
TIMESTAMP = "measured_on"
SEQUENCE_LENGTH = 24

FEATURES = [
    "hour_sin", "hour_cos", "day_of_week",
    "month_sin", "month_cos",
    "day_of_year_sin", "day_of_year_cos",
    "power_lag_1", "irradiance_lag_1",
    "ambient_temp_lag_1", "module_temp_lag_1",
    "power_lag_3", "irradiance_lag_3",
    "ambient_temp_lag_3", "module_temp_lag_3",
    "power_lag_6", "irradiance_lag_6",
    "ambient_temp_lag_6", "module_temp_lag_6",
    "power_lag_24", "irradiance_lag_24",
    "ambient_temp_lag_24", "module_temp_lag_24",
    "power_rolling_mean_4", "power_rolling_std_4",
    "power_rolling_mean_24", "power_rolling_std_24",
]


def calculate_metrics(actual, predicted):
    nonzero = actual != 0
    return {
        "rows_evaluated": int(len(actual)),
        "MAE_W": float(mean_absolute_error(actual, predicted)),
        "RMSE_W": float(np.sqrt(mean_squared_error(actual, predicted))),
        "MAPE_percent_nonzero_actuals": (
            float(np.mean(np.abs(
                (actual[nonzero] - predicted[nonzero])
                / actual[nonzero]
            )) * 100) if nonzero.any() else None
        ),
        "R2": float(r2_score(actual, predicted)),
    }


def make_sequences(x, y, sequence_length):
    xs, ys, positions = [], [], []
    for end in range(sequence_length - 1, len(x)):
        if np.isfinite(y[end]):
            xs.append(x[end - sequence_length + 1:end + 1])
            ys.append(y[end])
            positions.append(end)

    return (
        np.asarray(xs, dtype=np.float32),
        np.asarray(ys, dtype=np.float32),
        np.asarray(positions, dtype=int),
    )


def main():
    tf.keras.utils.set_random_seed(42)

    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Dataset not found: {DATA_PATH}")

    df = pd.read_csv(DATA_PATH, parse_dates=[TIMESTAMP])
    df = df.sort_values(TIMESTAMP).reset_index(drop=True)

    missing = [c for c in [TIMESTAMP, TARGET] + FEATURES if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    train_mask = df[TIMESTAMP] < "2016-01-01"
    val_mask = (
        (df[TIMESTAMP] >= "2016-01-01")
        & (df[TIMESTAMP] < "2016-07-01")
    )
    test_mask = df[TIMESTAMP] >= "2016-07-01"

    train_idx = np.flatnonzero(train_mask.to_numpy())
    val_idx = np.flatnonzero(val_mask.to_numpy())
    test_idx = np.flatnonzero(test_mask.to_numpy())

    # Fit preprocessing only on the training period.
    imputer = SimpleImputer(strategy="median")
    scaler = StandardScaler()

    x_train_rows = imputer.fit_transform(df.loc[train_mask, FEATURES])
    scaler.fit(x_train_rows)

    x_all = scaler.transform(imputer.transform(df[FEATURES]))
    y_all = pd.to_numeric(df[TARGET], errors="coerce").to_numpy(
        dtype=np.float64
    )

    # Sequences are constructed independently within each chronological split.
    x_train, y_train, _ = make_sequences(
        x_all[train_idx], y_all[train_idx], SEQUENCE_LENGTH
    )
    x_val, y_val, _ = make_sequences(
        x_all[val_idx], y_all[val_idx], SEQUENCE_LENGTH
    )
    x_test, y_test, test_pos_local = make_sequences(
        x_all[test_idx], y_all[test_idx], SEQUENCE_LENGTH
    )
    test_positions = test_idx[test_pos_local]

    if min(len(x_train), len(x_val), len(x_test)) == 0:
        raise ValueError("A data split has no valid sequences.")

    target_median = float(np.nanmedian(y_train))
    target_std = float(np.nanstd(y_train))
    if not np.isfinite(target_std) or target_std == 0:
        raise ValueError("Invalid target scaling.")

    y_train_scaled = (y_train - target_median) / target_std
    y_val_scaled = (y_val - target_median) / target_std

    model = Sequential([
        Input(shape=(SEQUENCE_LENGTH, len(FEATURES))),
        GRU(32, return_sequences=True),
        Dropout(0.2),
        GRU(16),
        Dense(16, activation="relu"),
        Dense(1),
    ])

    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
        loss="mse",
        metrics=["mae"],
    )

    callbacks = [
        EarlyStopping(
            monitor="val_loss",
            patience=4,
            restore_best_weights=True,
        ),
        ReduceLROnPlateau(
            monitor="val_loss",
            patience=2,
            factor=0.5,
            min_lr=0.00001,
        ),
    ]

    print("Training sequences:", len(x_train))
    print("Validation sequences:", len(x_val))
    print("Test sequences:", len(x_test))
    print("Starting GRU training...")

    history = model.fit(
        x_train,
        y_train_scaled,
        validation_data=(x_val, y_val_scaled),
        epochs=20,
        batch_size=256,
        callbacks=callbacks,
        shuffle=False,
        verbose=1,
    )

    val_pred = model.predict(x_val, verbose=0).reshape(-1)
    test_pred = model.predict(x_test, verbose=0).reshape(-1)

    val_pred_w = np.maximum(val_pred * target_std + target_median, 0)
    test_pred_w = np.maximum(test_pred * target_std + target_median, 0)

    results = {
        "model": "GRU",
        "sequence_length_intervals": SEQUENCE_LENGTH,
        "sequence_length_hours": SEQUENCE_LENGTH * 15 / 60,
        "features": FEATURES,
        "epochs_completed": len(history.history["loss"]),
        "best_validation_loss_scaled": float(min(history.history["val_loss"])),
        "validation_metrics": calculate_metrics(y_val, val_pred_w),
        "test_metrics": calculate_metrics(y_test, test_pred_w),
        "evaluation_note": (
            "Rolling one-step-ahead evaluation with historical lag features; "
            "not a multi-day forecast."
        ),
    }

    model.save(MODEL_DIR / "solar_gru.keras")
    joblib.dump(imputer, MODEL_DIR / "solar_gru_imputer.joblib")
    joblib.dump(scaler, MODEL_DIR / "solar_gru_feature_scaler.joblib")
    joblib.dump(
        {
            "target_median": target_median,
            "target_std": target_std,
            "features": FEATURES,
            "sequence_length": SEQUENCE_LENGTH,
        },
        MODEL_DIR / "solar_gru_config.joblib",
    )

    pd.DataFrame([{
        "model": "GRU",
        **results["test_metrics"],
    }]).to_csv(RESULTS_DIR / "gru_test_metrics.csv", index=False)

    pd.DataFrame({
        "measured_on": df.loc[test_positions, TIMESTAMP].to_numpy(),
        "actual_power_w": y_test,
        "predicted_power_w": test_pred_w,
        "error_w": test_pred_w - y_test,
    }).to_csv(RESULTS_DIR / "gru_test_predictions.csv", index=False)

    with open(
        RESULTS_DIR / "gru_training_results.json", "w", encoding="utf-8"
    ) as f:
        json.dump(results, f, indent=2)

    print("\nGRU test metrics:")
    print(json.dumps(results["test_metrics"], indent=2))
    print("\nSaved model:", MODEL_DIR / "solar_gru.keras")
    print("Saved metrics:", RESULTS_DIR / "gru_test_metrics.csv")
    print("Saved predictions:", RESULTS_DIR / "gru_test_predictions.csv")


if __name__ == "__main__":
    main()
