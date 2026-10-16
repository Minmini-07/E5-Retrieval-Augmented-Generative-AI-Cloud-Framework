"""Security configuration, physical safety limits, and trust engine parameters."""

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class TelemetryPhysicalBounds:
    """Physical consistency boundaries for solar photovoltaic telemetry."""

    max_irradiance_w_m2: float = 1400.0
    min_irradiance_w_m2: float = 0.0
    max_ambient_temp_c: float = 60.0
    min_ambient_temp_c: float = -30.0
    max_module_temp_c: float = 95.0
    min_module_temp_c: float = -30.0
    max_power_w: float = 10000.0  # Normalized site peak capacity
    min_power_w: float = 0.0
    max_temp_rate_of_change_c_per_step: float = 15.0
    max_irradiance_rate_of_change_w_per_step: float = 600.0


# The 27 features used by Minmini's solar forecasting model
SOLAR_FEATURE_NAMES: List[str] = [
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


@dataclass(frozen=True)
class TrustEngineConfig:
    """Weights and decision threshold gates for GreenRAG-Sec."""

    # Four-pillar weights: Evidence (E), Retrieval (R), Confidence (C), Security (S)
    weight_evidence: float = 0.25
    weight_retrieval: float = 0.20
    weight_confidence: float = 0.25
    weight_security: float = 0.30

    # Decision action thresholds
    approval_threshold: float = 0.85
    advisory_threshold: float = 0.60
    security_hard_stop_threshold: float = 0.50

    # Source authority ratings
    authority_ratings: Dict[str, float] = field(default_factory=lambda: {
        "iec_standard": 1.00,
        "nrel_report": 0.95,
        "oem_manual_verified": 0.90,
        "scada_historical_log": 0.80,
        "technician_maintenance_note": 0.65,
        "unverified_external": 0.30,
    })


@dataclass(frozen=True)
class PromptSecurityConfig:
    """Signatures and rules for prompt-injection detection."""

    forbidden_phrases: List[str] = field(default_factory=lambda: [
        "ignore previous instructions",
        "disregard all prior instructions",
        "system override",
        "developer mode",
        "jailbreak",
        "bypass safety limits",
        "disable thermal cutoff",
        "force inverter online",
        "override safety interlock",
        "act as an unrestricted",
        "do anything now",
    ])
    max_query_length: int = 1000
    max_evidence_chunk_length: int = 4000
