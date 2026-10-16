"""Four-pillar calibrated Trust-Aware Decision Engine for GreenRAG-Sec."""

from security.config import TrustEngineConfig
from security.schemas import ActionTier, TrustScoreResult


class TrustEngine:
    """Computes overall trust score T from Evidence (E), Retrieval (R), Confidence (C), and Security (S)."""

    def __init__(self, config: TrustEngineConfig = TrustEngineConfig()):
        self.config = config

    def calculate_trust(
        self,
        evidence_quality: float,
        retrieval_relevance: float,
        model_confidence: float,
        security_confidence: float,
    ) -> TrustScoreResult:
        """Calculate composite trust score and assign action tier.

        Equation: T = w_E * E + w_R * R + w_C * C + w_S * S
        """
        # Ensure all components bounded [0.0, 1.0]
        e = min(1.0, max(0.0, float(evidence_quality)))
        r = min(1.0, max(0.0, float(retrieval_relevance)))
        c = min(1.0, max(0.0, float(model_confidence)))
        s = min(1.0, max(0.0, float(security_confidence)))

        raw_trust = (
            self.config.weight_evidence * e
            + self.config.weight_retrieval * r
            + self.config.weight_confidence * c
            + self.config.weight_security * s
        )
        overall_trust = round(min(1.0, max(0.0, raw_trust)), 4)

        reasons = []

        # Hard Security Gate: If security confidence drops below hard stop threshold
        if s < self.config.security_hard_stop_threshold:
            action_tier = ActionTier.HARD_SECURITY_BLOCK
            reasons.append(
                f"HARD SECURITY BLOCK: Security confidence ({s:.2f}) below safe threshold ({self.config.security_hard_stop_threshold:.2f})."
            )
            summary = "Operation blocked due to active cyber-physical attack or injection."

        # Tier 1: Approved for autonomous or high-trust execution
        elif overall_trust >= self.config.approval_threshold and s >= 0.80:
            action_tier = ActionTier.APPROVED
            summary = "Recommendation validated with high evidence and security trust."

        # Tier 2: Flagged / Advisory (Requires human engineer review)
        elif overall_trust >= self.config.advisory_threshold:
            action_tier = ActionTier.FLAGGED
            if e < 0.60:
                reasons.append(f"Low evidence quality ({e:.2f}).")
            if c < 0.70:
                reasons.append(f"Model uncertainty elevated ({c:.2f}).")
            if s < 0.80:
                reasons.append(f"Elevated security risk ({s:.2f}).")
            summary = "Operational advisory issued; human-in-the-loop sign-off required."

        # Tier 3: Rejected / Abstention
        else:
            action_tier = ActionTier.REJECTED
            reasons.append(
                f"Overall trust score ({overall_trust:.2f}) is below minimum acceptable threshold ({self.config.advisory_threshold:.2f})."
            )
            summary = "Recommendation withheld due to insufficient evidence or trust."

        return TrustScoreResult(
            overall_trust=overall_trust,
            evidence_score=round(e, 4),
            retrieval_score=round(r, 4),
            confidence_score=round(c, 4),
            security_confidence=round(s, 4),
            action_tier=action_tier,
            decision_summary=summary,
            reasons=reasons,
        )
