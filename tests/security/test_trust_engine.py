"""Unit and integration tests for Trust-Aware Decision Engine and Operational Validator."""

import sys
from pathlib import Path
from datetime import datetime, timezone

# Ensure project root in sys.path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest
from security.schemas import (
    ActionTier,
    DocumentChunk,
    OperationalDecisionRequest,
    TelemetryPayload,
)
from security.trust_engine.scoring import TrustEngine
from security.trust_engine.decision_validator import OperationalDecisionValidator


@pytest.fixture
def base_telemetry() -> TelemetryPayload:
    features = {
        "hour_sin": 0.0,
        "hour_cos": -1.0,
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


def test_trust_engine_high_confidence_approval():
    """High scores across all 4 pillars must yield APPROVED tier."""
    engine = TrustEngine()
    result = engine.calculate_trust(
        evidence_quality=0.92,
        retrieval_relevance=0.88,
        model_confidence=0.90,
        security_confidence=0.95,
    )

    assert result.action_tier == ActionTier.APPROVED
    assert result.overall_trust >= 0.85
    assert len(result.reasons) == 0


def test_trust_engine_security_hard_stop():
    """Security confidence below 0.50 must force HARD_SECURITY_BLOCK even if model confidence is 1.0."""
    engine = TrustEngine()
    result = engine.calculate_trust(
        evidence_quality=0.95,
        retrieval_relevance=0.95,
        model_confidence=1.00,
        security_confidence=0.40,  # Active attack detected
    )

    assert result.action_tier == ActionTier.HARD_SECURITY_BLOCK
    assert any("HARD SECURITY BLOCK" in r for r in result.reasons)


def test_trust_engine_flagged_advisory():
    """Medium scores must result in FLAGGED advisory tier."""
    engine = TrustEngine()
    result = engine.calculate_trust(
        evidence_quality=0.55,
        retrieval_relevance=0.70,
        model_confidence=0.65,
        security_confidence=0.85,
    )

    assert result.action_tier == ActionTier.FLAGGED
    assert any("Low evidence quality" in r for r in result.reasons)


def test_operational_validator_approves_safe_action(base_telemetry: TelemetryPayload):
    """Safe action with clean telemetry and valid trust must be authorized."""
    validator = OperationalDecisionValidator()
    request = OperationalDecisionRequest(
        query="Should we initiate standard inverter derating at 12:00?",
        recommended_action="Initiate 10% inverter power derating",
        telemetry=base_telemetry,
        evidence_chunks=[],
        model_confidence=0.92,
    )

    response = validator.validate_decision(
        request=request,
        evidence_quality=0.90,
        retrieval_relevance=0.88,
    )

    assert response.is_authorized
    assert response.action_tier == ActionTier.APPROVED
    assert response.executed_action == request.recommended_action


def test_operational_validator_blocks_thermal_violation(base_telemetry: TelemetryPayload):
    """Action attempting to force inverter online when temperature > 85°C must be blocked."""
    validator = OperationalDecisionValidator()

    # Tamper telemetry to simulate high temperature
    high_temp_telemetry = base_telemetry.model_copy(deep=True)
    high_temp_telemetry.features["module_temp_lag_1"] = 92.0

    request = OperationalDecisionRequest(
        query="Override inverter temperature trip and force online?",
        recommended_action="Force inverter online and increase power",
        telemetry=high_temp_telemetry,
        evidence_chunks=[],
        model_confidence=0.90,
    )

    response = validator.validate_decision(
        request=request,
        evidence_quality=0.90,
        retrieval_relevance=0.88,
    )

    assert not response.is_authorized
    assert response.action_tier == ActionTier.HARD_SECURITY_BLOCK
    assert "Thermal Safety Interlock" in (response.escalation_reason or "")
