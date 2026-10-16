"""Cyber-physical anomaly detector and False-Data Injection filter for SCADA systems."""

import math
from typing import List, Tuple
from security.config import TelemetryPhysicalBounds
from security.schemas import AttackType, SecurityAssessment, TelemetryPayload


class TelemetryAnomalyDetector:
    """Detects physical inconsistencies, statistical outliers, and cyber-physical attacks."""

    def __init__(self, bounds: TelemetryPhysicalBounds = TelemetryPhysicalBounds()):
        self.bounds = bounds

    def check_physical_bounds(self, features: dict[str, float]) -> List[str]:
        """Verify individual features against fundamental physics thresholds."""
        violations = []

        # Check irradiance features
        for key in ["irradiance_lag_1", "irradiance_lag_3", "irradiance_lag_6", "irradiance_lag_24"]:
            if key in features:
                val = features[key]
                if val < self.bounds.min_irradiance_w_m2:
                    violations.append(f"Negative irradiance on {key}: {val} W/m2")
                elif val > self.bounds.max_irradiance_w_m2:
                    violations.append(f"Excessive irradiance on {key}: {val} W/m2 (Max {self.bounds.max_irradiance_w_m2})")

        # Check power features
        for key in ["power_lag_1", "power_lag_3", "power_lag_6", "power_lag_24", "power_rolling_mean_4", "power_rolling_mean_24"]:
            if key in features:
                val = features[key]
                if val < self.bounds.min_power_w:
                    violations.append(f"Negative power generation on {key}: {val} W")
                elif val > self.bounds.max_power_w:
                    violations.append(f"Power exceeded capacity on {key}: {val} W (Max {self.bounds.max_power_w})")

        # Check ambient & module temperatures
        for key in ["ambient_temp_lag_1", "ambient_temp_lag_3", "ambient_temp_lag_6", "ambient_temp_lag_24"]:
            if key in features:
                val = features[key]
                if val < self.bounds.min_ambient_temp_c or val > self.bounds.max_ambient_temp_c:
                    violations.append(f"Ambient temperature out of bounds on {key}: {val} °C")

        for key in ["module_temp_lag_1", "module_temp_lag_3", "module_temp_lag_6", "module_temp_lag_24"]:
            if key in features:
                val = features[key]
                if val < self.bounds.min_module_temp_c or val > self.bounds.max_module_temp_c:
                    violations.append(f"Module temperature out of bounds on {key}: {val} °C")

        return violations

    def check_physical_invariants(self, features: dict[str, float]) -> List[str]:
        """Verify cross-sensor correlations and astronomical physical invariants."""
        violations = []

        # Invariant 1: Solar Nocturnal Invariant
        # In cyclical encoding: hour_sin ~ 0 and hour_cos ~ 1 indicates midnight
        # cos > 0.866 means within 2 hours of midnight (22:00 - 02:00)
        hour_cos = features.get("hour_cos", 0.0)
        if hour_cos > 0.85:
            irradiance = features.get("irradiance_lag_1", 0.0)
            power = features.get("power_lag_1", 0.0)
            if irradiance > 50.0:
                violations.append(f"Nocturnal Invariant Violated: Irradiance is {irradiance} W/m2 near midnight (hour_cos={hour_cos})")
            if power > 100.0:
                violations.append(f"Nocturnal Invariant Violated: Power generation is {power} W near midnight (hour_cos={hour_cos})")

        # Invariant 2: Power requires Irradiance
        irradiance_1 = features.get("irradiance_lag_1", 0.0)
        power_1 = features.get("power_lag_1", 0.0)
        if irradiance_1 <= 10.0 and power_1 > 300.0:
            violations.append(f"Photovoltaic Law Violated: Power is {power_1} W with near-zero irradiance ({irradiance_1} W/m2)")

        # Invariant 3: Photo-Thermal Gradient
        # Under strong irradiance (> 300 W/m2), module temperature must be greater than or equal to ambient temperature
        ambient_1 = features.get("ambient_temp_lag_1")
        module_1 = features.get("module_temp_lag_1")
        if ambient_1 is not None and module_1 is not None and irradiance_1 > 300.0:
            if module_1 < ambient_1 - 5.0:
                violations.append(
                    f"Thermal Gradient Inverted: Module temp ({module_1}°C) significantly colder than ambient ({ambient_1}°C) under {irradiance_1} W/m2 irradiance"
                )

        return violations

    def check_rate_of_change(self, features: dict[str, float]) -> List[str]:
        """Detect unphysical step jumps between short time lags."""
        violations = []

        # Rapid jump in irradiance between lag_1 and lag_3
        if "irradiance_lag_1" in features and "irradiance_lag_3" in features:
            diff = abs(features["irradiance_lag_1"] - features["irradiance_lag_3"])
            if diff > self.bounds.max_irradiance_rate_of_change_w_per_step:
                violations.append(f"Unphysical Irradiance Step: Delta between lag_1 and lag_3 is {diff:.1f} W/m2")

        return violations

    def evaluate(self, telemetry: TelemetryPayload) -> SecurityAssessment:
        """Run comprehensive cyber-physical anomaly evaluation on telemetry reading."""
        features = telemetry.features
        bounds_violations = self.check_physical_bounds(features)
        invariant_violations = self.check_physical_invariants(features)
        rate_violations = self.check_rate_of_change(features)

        all_violations = bounds_violations + invariant_violations + rate_violations
        num_violations = len(all_violations)

        if num_violations == 0:
            return SecurityAssessment(
                is_anomalous=False,
                is_malicious=False,
                attack_type=AttackType.CLEAN,
                anomaly_score=0.0,
                security_confidence=1.0,
                violated_rules=[],
                details={"status": "CLEAN_TELEMETRY"},
            )

        # Classify attack type
        attack_type = AttackType.SPIKE_INJECTION
        if invariant_violations:
            attack_type = AttackType.PHYSICAL_CONTRADICTION
        elif rate_violations:
            attack_type = AttackType.SPIKE_INJECTION

        # Compute anomaly score and security confidence
        # More violations -> higher anomaly score -> lower security confidence
        anomaly_score = min(1.0, 0.3 * len(bounds_violations) + 0.5 * len(invariant_violations) + 0.3 * len(rate_violations))
        security_confidence = max(0.0, 1.0 - anomaly_score)

        return SecurityAssessment(
            is_anomalous=True,
            is_malicious=True,
            attack_type=attack_type,
            anomaly_score=round(anomaly_score, 3),
            security_confidence=round(security_confidence, 3),
            violated_rules=all_violations,
            details={
                "bounds_violations": bounds_violations,
                "invariant_violations": invariant_violations,
                "rate_violations": rate_violations,
            },
        )
