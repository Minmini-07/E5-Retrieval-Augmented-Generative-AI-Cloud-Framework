
from pathlib import Path
import json

import joblib
import numpy as np
import pandas as pd
from flask import Flask, jsonify, request

ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = ROOT / "models"
RESULTS_DIR = ROOT / "results"

MODEL_FILE = MODELS_DIR / "solar_random_forest.joblib"
UNCERTAINTY_FILE = RESULTS_DIR / "uncertainty_metrics.json"

FEATURE_NAMES = [
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

app = Flask(__name__)

if not MODEL_FILE.exists():
    raise FileNotFoundError(
        f"Trained model not found: {MODEL_FILE}. "
        "Run src/train_forecasting_model.py first."
    )

if not UNCERTAINTY_FILE.exists():
    raise FileNotFoundError(
        f"Uncertainty metrics not found: {UNCERTAINTY_FILE}. "
        "Run src/train_forecasting_model.py first."
    )

model = joblib.load(MODEL_FILE)

with open(UNCERTAINTY_FILE, "r", encoding="utf-8") as file:
    uncertainty = json.load(file)

lower_error = float(
    uncertainty["validation_lower_residual_quantile_w"]
)
upper_error = float(
    uncertainty["validation_upper_residual_quantile_w"]
)


@app.get("/health")
def health():
    return jsonify({
        "status": "ok",
        "model": "Random Forest",
        "features_required": len(FEATURE_NAMES),
    })


@app.post("/forecast")
def forecast():
    payload = request.get_json(silent=True)

    if not isinstance(payload, dict):
        return jsonify({
            "error": "Send a JSON object containing a 'features' object."
        }), 400

    features = payload.get("features")

    if not isinstance(features, dict):
        return jsonify({
            "error": "'features' must be a JSON object."
        }), 400

    missing = [
        name for name in FEATURE_NAMES if name not in features
    ]

    extra = [
        name for name in features if name not in FEATURE_NAMES
    ]

    if missing:
        return jsonify({
            "error": "Missing required features.",
            "missing_features": missing,
        }), 400

    if extra:
        return jsonify({
            "error": "Unexpected features supplied.",
            "unexpected_features": extra,
        }), 400

    try:
        values = {}

        for name in FEATURE_NAMES:
            value = features[name]

            if value is None:
                values[name] = np.nan
                continue

            if isinstance(value, bool):
                raise ValueError(
                    f"'{name}' must be a number or null, not a boolean."
                )

            numeric_value = float(value)

            if not np.isfinite(numeric_value):
                raise ValueError(
                    f"'{name}' must be finite or null."
                )

            values[name] = numeric_value

        input_frame = pd.DataFrame(
            [[values[name] for name in FEATURE_NAMES]],
            columns=FEATURE_NAMES,
        )

        prediction = float(model.predict(input_frame)[0])

        lower_bound = max(0.0, prediction + lower_error)
        upper_bound = max(0.0, prediction + upper_error)

        return jsonify({
            "prediction": round(prediction, 2),
            "unit": "W",
            "lower_bound": round(lower_bound, 2),
            "upper_bound": round(upper_bound, 2),
            "nominal_interval_coverage": 0.90,
            "confidence": 90,
            "interval_method": "Empirical validation residual quantiles",
            "note": (
                "90% is the nominal interval target, not a guarantee "
                "that this individual prediction is correct. "
                "Supply historically available features in the "
                "training feature format."
            ),
        })

    except (TypeError, ValueError) as error:
        return jsonify({"error": str(error)}), 400


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
