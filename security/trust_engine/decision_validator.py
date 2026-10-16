"""Operational decision validator and physical safety interlock enforcement."""

import re
from typing import Tuple
from security.config import TelemetryPhysicalBounds
from security.schemas import (
    ActionTier,
    OperationalDecisionRequest,
    OperationalDecisionResponse,
    TrustScoreResult,
)
from security.telemetry.anomaly_detector import TelemetryAnomalyDetector
from security.trust_engine.scoring import TrustEngine


class OperationalDecisionValidator:
    """Enforces deterministic physical safety envelopes before authorizing LLM operational actions."""

    def __init__(
        self,
        bounds: TelemetryPhysicalBounds = TelemetryPhysicalBounds(),
        trust_engine: TrustEngine = None,
        anomaly_detector: TelemetryAnomalyDetector = None,
    ):
        self.bounds = bounds
        self.trust_engine = trust_engine or TrustEngine()
        self.anomaly_detector = anomaly_detector or TelemetryAnomalyDetector(bounds=bounds)

    def check_physical_safety_interlock(
        self,
        recommended_action: str,
        current_telemetry: dict[str, float],
    ) -> Tuple[bool, str]:
        """Verify that recommended action does not conflict with physical state or safety limits."""
        action_lower = recommended_action.lower()

        # Inverter thermal safety interlock
        module_temp = current_telemetry.get("module_temp_lag_1", 25.0)
        if module_temp > 85.0:
            if "force" in action_lower or "increase power" in action_lower or "online" in action_lower:
                return False, f"Thermal Safety Interlock: Module temp is {module_temp}°C (>85°C limit); cannot increase generation."

        # Midnight generation interlock
        hour_cos = current_telemetry.get("hour_cos", 0.0)
        if hour_cos > 0.85:  # Night hours
            if "maximum dispatch" in action_lower or "increase solar" in action_lower:
                return False, "Nocturnal Interlock: Cannot dispatch solar generation during night hours."

        # Safety trip bypass check
        if "disable trip" in action_lower or "bypass breaker" in action_lower:
            return False, "Interlock Violation: Bypassing protective breakers is strictly prohibited."

        return True, "Physical constraints satisfied."

    def validate_decision(
        self,
        request: OperationalDecisionRequest,
        evidence_quality: float,
        retrieval_relevance: float,
    ) -> OperationalDecisionResponse:
        """Run complete end-to-end operational validation: security + telemetry + trust + safety interlocks."""
        # 1. Telemetry security evaluation
        telemetry_assessment = self.anomaly_detector.evaluate(request.telemetry)
        security_conf = telemetry_assessment.security_confidence

        # 2. Trust score evaluation
        trust_result = self.trust_engine.calculate_trust(
            evidence_quality=evidence_quality,
            retrieval_relevance=retrieval_relevance,
            model_confidence=request.model_confidence,
            security_confidence=security_conf,
        )

        # 3. Physical safety interlock check
        is_safe, interlock_msg = self.check_physical_safety_interlock(
            recommended_action=request.recommended_action,
            current_telemetry=request.telemetry.features,
        )

        # 4. Gating authorization
        if not is_safe:
            return OperationalDecisionResponse(
                is_authorized=False,
                action_tier=ActionTier.HARD_SECURITY_BLOCK,
                trust_score=trust_result,
                executed_action=None,
                escalation_reason=f"PHYSICAL SAFETY INTERLOCK TRIPPED: {interlock_msg}",
            )

        if trust_result.action_tier == ActionTier.APPROVED:
            return OperationalDecisionResponse(
                is_authorized=True,
                action_tier=ActionTier.APPROVED,
                trust_score=trust_result,
                executed_action=request.recommended_action,
                escalation_reason=None,
            )

        # If FLAGGED or REJECTED or HARD_SECURITY_BLOCK
        return OperationalDecisionResponse(
            is_authorized=False,
            action_tier=trust_result.action_tier,
            trust_score=trust_result,
            executed_action=None,
            escalation_reason=f"Action withheld [{trust_result.action_tier.value}]: {trust_result.decision_summary}",
        )
