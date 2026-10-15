
from pathlib import Path
import json

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = (
    ROOT / "data" / "processed"
    / "solar_forecasting_features_2014_2016.csv"
)
RESULTS_DIR = ROOT / "results"
MODELS_DIR = ROOT / "models"

RESULTS_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)

TARGET = "power_w"
TIME = "measured_on"


def calculate_metrics(actual, predicted, model_name):
    valid = (
        actual.notna()
        & predicted.notna()
        & np.isfinite(actual)
        & np.isfinite(predicted)
    )
    y_true = actual.loc[valid]
    y_pred = predicted.loc[valid]

    if len(y_true) == 0:
        raise ValueError(f"No valid predictions for {model_name}")

    nonzero = y_true.abs() > 1e-8
    mape = (
        float(
            (
                (y_true.loc[nonzero] - y_pred.loc[nonzero]).abs()
                / y_true.loc[nonzero].abs()
            ).mean() * 100
        )
        if nonzero.any()
        else None
    )

    return {
        "model": model_name,
        "rows_evaluated": int(len(y_true)),
        "MAE_W": float(mean_absolute_error(y_true, y_pred)),
        "RMSE_W": float(
            np.sqrt(mean_squared_error(y_true, y_pred))
        ),
        "MAPE_percent_nonzero_actuals": mape,
        "R2": float(r2_score(y_true, y_pred)),
    }


def main():
    df = pd.read_csv(DATA_FILE, parse_dates=[TIME])
    df[TIME] = pd.to_datetime(df[TIME], utc=True)
    df = df.sort_values(TIME).reset_index(drop=True)

    train_mask = df[TIME] < "2016-01-01"
    val_mask = (
        (df[TIME] >= "2016-01-01")
        & (df[TIME] < "2016-07-01")
    )
    test_mask = (
        (df[TIME] >= "2016-07-01")
        & (df[TIME] < "2017-01-01")
    )

    # Select intended features explicitly; exclude target and timestamp.
    feature_names = [
        "hour_sin", "hour_cos", "day_of_week",
        "month_sin", "month_cos",
        "day_of_year_sin", "day_of_year_cos",
        "power_lag_1", "power_lag_3",
        "power_lag_6", "power_lag_24",
        "irradiance_lag_1", "irradiance_lag_3",
        "irradiance_lag_6", "irradiance_lag_24",
        "ambient_temp_lag_1", "ambient_temp_lag_3",
        "ambient_temp_lag_6", "ambient_temp_lag_24",
        "module_temp_lag_1", "module_temp_lag_3",
        "module_temp_lag_6", "module_temp_lag_24",
        "power_rolling_mean_4", "power_rolling_std_4",
        "power_rolling_mean_24", "power_rolling_std_24",
    ]
    missing_features = [
        col for col in feature_names if col not in df.columns
    ]
    if missing_features:
        raise ValueError(f"Missing features: {missing_features}")

    train = df.loc[train_mask & df[TARGET].notna()].copy()
    val = df.loc[val_mask & df[TARGET].notna()].copy()
    test = df.loc[test_mask & df[TARGET].notna()].copy()

    X_train = train[feature_names]
    y_train = train[TARGET]
    X_val = val[feature_names]
    y_val = val[TARGET]
    X_test = test[feature_names]
    y_test = test[TARGET]

    print("Training rows:", len(train))
    print("Validation rows:", len(val))
    print("Test rows:", len(test))
    print("Number of features:", len(feature_names))

    model = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("forest", RandomForestRegressor(
            n_estimators=100,
            min_samples_leaf=2,
            max_features=0.8,
            random_state=42,
            n_jobs=-1,
        )),
    ])
    model.fit(X_train, y_train)

    # One-step-ahead persistence baseline using the previous reading.
    persistence = test["power_lag_1"].where(
        np.isfinite(test["power_lag_1"])
    )

    val_predictions = pd.Series(
        model.predict(X_val), index=val.index
    )
    test_predictions = pd.Series(
        model.predict(X_test), index=test.index
    )

    # Empirical residual intervals calibrated on validation data.
    val_residuals = y_val - val_predictions
    lower_error = float(val_residuals.quantile(0.05))
    upper_error = float(val_residuals.quantile(0.95))

    lower_bound = (test_predictions + lower_error).clip(lower=0)
    upper_bound = (test_predictions + upper_error).clip(lower=0)

    metrics = pd.DataFrame([
        calculate_metrics(y_test, persistence, "Persistence"),
        calculate_metrics(y_test, test_predictions, "Random Forest"),
    ])
    metrics.to_csv(RESULTS_DIR / "forecast_metrics.csv", index=False)

    predictions = pd.DataFrame({
        TIME: test[TIME].to_numpy(),
        "actual_power_w": y_test.to_numpy(),
        "persistence_prediction_w": persistence.to_numpy(),
        "random_forest_prediction_w": test_predictions.to_numpy(),
        "lower_bound_90_w": lower_bound.to_numpy(),
        "upper_bound_90_w": upper_bound.to_numpy(),
    })
    predictions.to_csv(
        RESULTS_DIR / "forecast_test_predictions.csv",
        index=False,
    )

    valid_interval = (
        y_test.notna()
        & np.isfinite(lower_bound)
        & np.isfinite(upper_bound)
    )
    covered = (
        (y_test[valid_interval] >= lower_bound[valid_interval])
        & (y_test[valid_interval] <= upper_bound[valid_interval])
    )

    uncertainty = {
        "nominal_coverage": 0.90,
        "test_coverage": float(covered.mean()),
        "interval_rows_evaluated": int(valid_interval.sum()),
        "mean_interval_width_w": float(
            (upper_bound[valid_interval]
             - lower_bound[valid_interval]).mean()
        ),
        "validation_lower_residual_quantile_w": lower_error,
        "validation_upper_residual_quantile_w": upper_error,
        "method": "Empirical validation residual quantiles",
        "interpretation": (
            "Nominal 90% interval; actual test coverage is measured, "
            "not guaranteed."
        ),
    }
    with open(
        RESULTS_DIR / "uncertainty_metrics.json",
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(uncertainty, file, indent=2)

    joblib.dump(
        model, MODELS_DIR / "solar_random_forest.joblib"
    )

    print("\nTest metrics:")
    print(metrics.to_string(index=False))
    print("\nUncertainty evaluation:")
    print(json.dumps(uncertainty, indent=2))
    print("\nResults saved in:", RESULTS_DIR)
    print("Model saved in:", MODELS_DIR)


if __name__ == "__main__":
    main()
