"""Adversarial Telemetry Attack Simulator for Renewable Energy SCADA systems.

Supports False-Data Injection (FDI), sensor spoofing, drift, replay, and physical contradictions.
"""

import copy
from typing import Dict, List, Optional
from security.schemas import AttackType, TelemetryPayload


class TelemetryAttackSimulator:
    """Generates controlled cyber-physical attack vectors on renewable telemetry."""

    def __init__(self, seed: Optional[int] = 42):
        self.seed = seed

    def inject_spike(
        self,
        telemetry: TelemetryPayload,
        target_keys: List[str],
        magnitude: float,
        additive: bool = True,
    ) -> TelemetryPayload:
        """Inject sudden step-function spike into specific sensor readings."""
        attacked = copy.deepcopy(telemetry)
        for key in target_keys:
            if key in attacked.features:
                if additive:
                    attacked.features[key] += magnitude
                else:
                    attacked.features[key] = magnitude
        return attacked

    def inject_drift(
        self,
        stream: List[TelemetryPayload],
        target_key: str,
        drift_rate_per_step: float,
    ) -> List[TelemetryPayload]:
        """Inject continuous creeping bias simulating sensor decalibration or stealthy FDI."""
        attacked_stream = [copy.deepcopy(item) for item in stream]
        accumulated_drift = 0.0
        for payload in attacked_stream:
            accumulated_drift += drift_rate_per_step
            if target_key in payload.features:
                payload.features[target_key] += accumulated_drift
        return attacked_stream

    def inject_replay(
        self,
        stream: List[TelemetryPayload],
        replay_source_indices: List[int],
    ) -> List[TelemetryPayload]:
        """Inject stale/frozen telemetry from previous timestamps to mask current events."""
        if not stream or not replay_source_indices:
            return stream

        attacked_stream = copy.deepcopy(stream)
        source_len = len(replay_source_indices)

        for i, payload in enumerate(attacked_stream):
            src_idx = replay_source_indices[i % source_len]
            if src_idx < len(stream):
                # Overwrite features with historical values, keeping current timestamp
                payload.features = copy.deepcopy(stream[src_idx].features)

        return attacked_stream

    def inject_physical_contradiction(
        self,
        telemetry: TelemetryPayload,
        contradiction_mode: str = "nocturnal_solar",
    ) -> TelemetryPayload:
        """Inject values that directly violate solar photovoltaic physics."""
        attacked = copy.deepcopy(telemetry)

        if contradiction_mode == "nocturnal_solar":
            # Simulate high solar power and irradiance at midnight
            # hour_sin ~ 0, hour_cos ~ 1 is midnight
            attacked.features["hour_sin"] = 0.0
            attacked.features["hour_cos"] = 1.0
            attacked.features["irradiance_lag_1"] = 950.0
            attacked.features["power_lag_1"] = 7500.0

        elif contradiction_mode == "thermal_inversion":
            # Under blazing sun (900 W/m2), module temp is spoofed to freezing (-10°C) while ambient is 35°C
            attacked.features["irradiance_lag_1"] = 900.0
            attacked.features["ambient_temp_lag_1"] = 35.0
            attacked.features["module_temp_lag_1"] = -10.0

        elif contradiction_mode == "power_without_sun":
            # Maximum power generation with zero irradiance
            attacked.features["irradiance_lag_1"] = 0.0
            attacked.features["power_lag_1"] = 9000.0
            attacked.features["power_rolling_mean_4"] = 8500.0

        return attacked
