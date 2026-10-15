
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
from tensorflow.keras.layers import Input, LSTM, Dense, Dropout
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
SEQUENCE_LENGTH = 24  # 24 intervals = 6 hours at 15-minute resolution

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


def metrics(y_true, y_pred):
    nonzero = y_true != 0
    return {
        "rows_evaluated": int(len(y_true)),
        "MAE_W": float(mean_absolute_error(y_true, y_pred)),
        "RMSE_W": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "MAPE_percent_nonzero_actuals": (
            float(np.mean(np.abs(
                (y_true[nonzero] - y_pred[nonzero]) / y_true[nonzero]
            )) * 100) if nonzero.any() else None
        ),
        "R2": float(r2_score(y_true, y_pred)),
    }


def make_sequences(x, y, sequence_length):
    xs, ys, positions = [], [], []

    for end in range(sequence_length - 1, len(x)):
        # A sequence ends at the timestamp being predicted.
        # All input columns are calendar features or historical lag/rolling features.
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
        raise FileNotFoundError(f"Feature dataset not found: {DATA_PATH}")

    df = pd.read_csv(DATA_PATH, parse_dates=[TIMESTAMP])
    df = df.sort_values(TIMESTAMP).reset_index(drop=True)

    required = [TIMESTAMP, TARGET] + FEATURES
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # Keep the same chronological split as the Random Forest experiment.
    train_mask = df[TIMESTAMP] < "2016-01-01"
    val_mask = (
        (df[TIMESTAMP] >= "2016-01-01")
        & (df[TIMESTAMP] < "2016-07-01")
    )
    test_mask = df[TIMESTAMP] >= "2016-07-01"

    train_indices = np.flatnonzero(train_mask.to_numpy())
    val_indices = np.flatnonzero(val_mask.to_numpy())
    test_indices = np.flatnonzero(test_mask.to_numpy())

    print("Rows:", len(df))
    print("Training period:", df.loc[train_mask, TIMESTAMP].min(),
          "to", df.loc[train_mask, TIMESTAMP].max())
    print("Validation period:", df.loc[val_mask, TIMESTAMP].min(),
          "to", df.loc[val_mask, TIMESTAMP].max())
    print("Test period:", df.loc[test_mask, TIMESTAMP].min(),
          "to", df.loc[test_mask, TIMESTAMP].max())

    # Fit preprocessing only on training data.
    imputer = SimpleImputer(strategy="median")
    scaler = StandardScaler()

    x_train_rows = imputer.fit_transform(df.loc[train_mask, FEATURES])
    scaler.fit(x_train_rows)

    # Transform the complete timeline with training-fitted preprocessing.
    # This allows validation/test sequences to use earlier historical context.
    x_all = scaler.transform(imputer.transform(df[FEATURES]))
    y_all = pd.to_numeric(df[TARGET], errors="coerce").to_numpy(
        dtype=np.float64
    )

    # Create sequences independently inside each split. This prevents
    # training sequences from crossing into validation or test periods.
    # Validation/test predictions can still use earlier rows as history.
    x_train, y_train, train_pos = make_sequences(
        x_all[train_indices], y_all[train_indices], SEQUENCE_LENGTH
    )
    x_val, y_val, val_pos = make_sequences(
        x_all[val_indices], y_all[val_indices], SEQUENCE_LENGTH
    )
    x_test, y_test, test_pos = make_sequences(
        x_all[test_indices], y_all[test_indices], SEQUENCE_LENGTH
    )

    # Convert split-local positions back to positions in the full dataset.
    train_pos = train_indices[train_pos]
    val_pos = val_indices[val_pos]
    test_pos = test_indices[test_pos]

    print("\nSequence shapes:")
    print("Train:", x_train.shape, y_train.shape)
    print("Validation:", x_val.shape, y_val.shape)
    print("Test:", x_test.shape, y_test.shape)

    if not len(x_train) or not len(x_val) or not len(x_test):
        raise ValueError("A split has no usable LSTM sequences.")

    # Scale target using training targets only; predictions are converted
    # back to watts for evaluation and API integration.
    target_median = float(np.nanmedian(y_train))
    target_std = float(np.nanstd(y_train))
    if not np.isfinite(target_std) or target_std == 0:
        raise ValueError("Invalid target scale.")

    y_train_scaled = (y_train - target_median) / target_std
    y_val_scaled = (y_val - target_median) / target_std

    model = Sequential([
        Input(shape=(SEQUENCE_LENGTH, len(FEATURES))),
        LSTM(32, return_sequences=True),
        Dropout(0.2),
        LSTM(16),
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

    print("\nStarting LSTM training...")
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

    val_metrics = metrics(y_val, val_pred_w)
    test_metrics = metrics(y_test, test_pred_w)

    results = {
        "model": "LSTM",
        "sequence_length_intervals": SEQUENCE_LENGTH,
        "sequence_length_hours": SEQUENCE_LENGTH * 15 / 60,
        "features": FEATURES,
        "epochs_completed": len(history.history["loss"]),
        "best_validation_loss_scaled": float(min(history.history["val_loss"])),
        "validation_metrics": val_metrics,
        "test_metrics": test_metrics,
        "evaluation_note": (
            "Rolling one-step-ahead evaluation using historical measured "
            "lag features. This is not a multi-day forecast."
        ),
    }

    model.save(MODEL_DIR / "solar_lstm.keras")
    joblib.dump(imputer, MODEL_DIR / "solar_lstm_imputer.joblib")
    joblib.dump(scaler, MODEL_DIR / "solar_lstm_feature_scaler.joblib")
    joblib.dump(
        {"target_median": target_median, "target_std": target_std,
         "features": FEATURES, "sequence_length": SEQUENCE_LENGTH},
        MODEL_DIR / "solar_lstm_config.joblib",
    )

    pd.DataFrame([{
        "model": "LSTM",
        **test_metrics,
    }]).to_csv(RESULTS_DIR / "lstm_test_metrics.csv", index=False)

    pd.DataFrame({
        "measured_on": df.loc[test_pos, TIMESTAMP].to_numpy(),
        "actual_power_w": y_test,
        "predicted_power_w": test_pred_w,
        "error_w": test_pred_w - y_test,
    }).to_csv(RESULTS_DIR / "lstm_test_predictions.csv", index=False)

    with open(RESULTS_DIR / "lstm_training_results.json", "w",
              encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("\nLSTM test metrics:")
    print(json.dumps(test_metrics, indent=2))
    print("\nSaved model:", MODEL_DIR / "solar_lstm.keras")
    print("Saved metrics:", RESULTS_DIR / "lstm_test_metrics.csv")
    print("Saved predictions:", RESULTS_DIR / "lstm_test_predictions.csv")


if __name__ == "__main__":
    main()
