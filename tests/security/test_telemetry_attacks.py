import sys
from pathlib import Path

# Add project root to sys.path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest
from datetime import datetime, timezone
from security.schemas import AttackType, TelemetryPayload
from security.telemetry.attack_simulator import TelemetryAttackSimulator
from security.telemetry.anomaly_detector import TelemetryAnomalyDetector


@pytest.fixture
def clean_telemetry() -> TelemetryPayload:
    """Fixture providing a realistic, physically consistent midday solar telemetry reading."""
    features = {
        "hour_sin": 0.0,
        "hour_cos": -1.0,  # Midday (12:00)
        "day_of_week": 3.0,
        "month_sin": 0.5,
        "month_cos": 0.866,
        "day_of_year_sin": 0.2,
        "day_of_year_cos": 0.98,
        "power_lag_1": 4200.0,
        "power_lag_3": 4150.0,
        "power_lag_6": 3900.0,
        "power_lag_24": 4050.0,
        "irradiance_lag_1": 780.0,
        "irradiance_lag_3": 770.0,
        "irradiance_lag_6": 720.0,
        "irradiance_lag_24": 750.0,
        "ambient_temp_lag_1": 28.0,
        "ambient_temp_lag_3": 27.5,
        "ambient_temp_lag_6": 26.0,
        "ambient_temp_lag_24": 27.0,
        "module_temp_lag_1": 46.0,
        "module_temp_lag_3": 45.0,
        "module_temp_lag_6": 42.0,
        "module_temp_lag_24": 44.0,
        "power_rolling_mean_4": 4100.0,
        "power_rolling_std_4": 50.0,
        "power_rolling_mean_24": 2200.0,
        "power_rolling_std_24": 1800.0,
    }
    return TelemetryPayload(timestamp=datetime.now(timezone.utc), features=features)


def test_clean_telemetry_evaluation(clean_telemetry: TelemetryPayload):
    """Clean telemetry must have no violations and maximum security confidence."""
    detector = TelemetryAnomalyDetector()
    assessment = detector.evaluate(clean_telemetry)

    assert not assessment.is_anomalous
    assert not assessment.is_malicious
    assert assessment.attack_type == AttackType.CLEAN
    assert assessment.security_confidence == 1.0
    assert assessment.anomaly_score == 0.0
    assert len(assessment.violated_rules) == 0


def test_spike_injection_detection(clean_telemetry: TelemetryPayload):
    """Spike injection exceeding maximum irradiance must be flagged."""
    simulator = TelemetryAttackSimulator()
    detector = TelemetryAnomalyDetector()

    # Inject +1000 W/m2 spike on irradiance (total 1780 W/m2 > 1400 W/m2 bound)
    attacked = simulator.inject_spike(clean_telemetry, ["irradiance_lag_1"], magnitude=1000.0)
    assessment = detector.evaluate(attacked)

    assert assessment.is_anomalous
    assert assessment.is_malicious
    assert assessment.security_confidence < 1.0
    assert any("Excessive irradiance" in rule for rule in assessment.violated_rules)


def test_nocturnal_solar_contradiction(clean_telemetry: TelemetryPayload):
    """Injecting solar power at midnight must trigger the nocturnal invariant violation."""
    simulator = TelemetryAttackSimulator()
    detector = TelemetryAnomalyDetector()

    attacked = simulator.inject_physical_contradiction(clean_telemetry, contradiction_mode="nocturnal_solar")
    assessment = detector.evaluate(attacked)

    assert assessment.is_anomalous
    assert assessment.is_malicious
    assert assessment.attack_type == AttackType.PHYSICAL_CONTRADICTION
    assert any("Nocturnal Invariant Violated" in rule for rule in assessment.violated_rules)


def test_thermal_inversion_contradiction(clean_telemetry: TelemetryPayload):
    """Module temperature significantly colder than ambient under intense sun must be caught."""
    simulator = TelemetryAttackSimulator()
    detector = TelemetryAnomalyDetector()

    attacked = simulator.inject_physical_contradiction(clean_telemetry, contradiction_mode="thermal_inversion")
    assessment = detector.evaluate(attacked)

    assert assessment.is_anomalous
    assert any("Thermal Gradient Inverted" in rule for rule in assessment.violated_rules)


def test_power_without_sun_contradiction(clean_telemetry: TelemetryPayload):
    """High power generation with near-zero irradiance violates basic photovoltaic physics."""
    simulator = TelemetryAttackSimulator()
    detector = TelemetryAnomalyDetector()

    attacked = simulator.inject_physical_contradiction(clean_telemetry, contradiction_mode="power_without_sun")
    assessment = detector.evaluate(attacked)

    assert assessment.is_anomalous
    assert any("Photovoltaic Law Violated" in rule for rule in assessment.violated_rules)


def test_drift_injection_over_stream(clean_telemetry: TelemetryPayload):
    """Creeping drift must eventually exceed physical limits."""
    import copy
    simulator = TelemetryAttackSimulator()
    detector = TelemetryAnomalyDetector()

    stream = [copy.deepcopy(clean_telemetry) for _ in range(20)]
    # Drift ambient temp by +2.5°C per step (starts at 28°C, by step 15 is > 60°C max bound)
    drifted_stream = simulator.inject_drift(stream, "ambient_temp_lag_1", drift_rate_per_step=2.5)

    # First step (28 + 2.5 = 30.5°C) should be clean
    assert not detector.evaluate(drifted_stream[0]).is_anomalous
    # Final step (28 + 20 * 2.5 = 78°C) should be anomalous (> 60°C max bound)
    final_assessment = detector.evaluate(drifted_stream[-1])
    assert final_assessment.is_anomalous
    assert any("Ambient temperature out of bounds" in rule for rule in final_assessment.violated_rules)
