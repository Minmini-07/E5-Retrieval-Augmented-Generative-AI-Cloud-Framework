"""Pydantic data schemas for telemetry, security assessments, and trust scoring."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class AttackType(str, Enum):
    """Types of simulated or detected attacks."""

    CLEAN = "clean"
    SPIKE_INJECTION = "spike_injection"
    GRADUAL_DRIFT = "gradual_drift"
    REPLAY_ATTACK = "replay_attack"
    PHYSICAL_CONTRADICTION = "physical_contradiction"
    PROMPT_INJECTION_DIRECT = "prompt_injection_direct"
    PROMPT_INJECTION_INDIRECT = "prompt_injection_indirect"
    KNOWLEDGE_POISONING = "knowledge_poisoning"


class ActionTier(str, Enum):
    """Action outcome from the Trust-Aware Decision Engine."""

    APPROVED = "APPROVED"
    FLAGGED = "FLAGGED"
    REJECTED = "REJECTED"
    HARD_SECURITY_BLOCK = "HARD_SECURITY_BLOCK"


class TelemetryPayload(BaseModel):
    """Raw or preprocessed solar/SCADA telemetry reading."""

    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    features: Dict[str, float] = Field(description="Dictionary of numerical telemetry features.")

    @field_validator("features")
    def validate_features_non_empty(cls, v: Dict[str, float]) -> Dict[str, float]:
        if not v:
            raise ValueError("Telemetry features cannot be empty.")
        return v


class SecurityAssessment(BaseModel):
    """Result of an automated cybersecurity analysis."""

    is_anomalous: bool = False
    is_malicious: bool = False
    attack_type: AttackType = AttackType.CLEAN
    anomaly_score: float = Field(default=0.0, ge=0.0, le=1.0)
    security_confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    violated_rules: List[str] = Field(default_factory=list)
    details: Dict[str, Any] = Field(default_factory=dict)


class DocumentChunk(BaseModel):
    """Text chunk for RAG knowledge base with cryptographic provenance."""

    chunk_id: str
    source_id: str
    author: str = "unknown"
    authority_type: str = "unverified_external"
    text: str
    hash_sha256: str
    verified_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict)
    trust_score: float = Field(default=0.5, ge=0.0, le=1.0)


class TrustScoreResult(BaseModel):
    """Calibrated four-pillar composite trust evaluation."""

    overall_trust: float = Field(ge=0.0, le=1.0)
    evidence_score: float = Field(ge=0.0, le=1.0)
    retrieval_score: float = Field(ge=0.0, le=1.0)
    confidence_score: float = Field(ge=0.0, le=1.0)
    security_confidence: float = Field(ge=0.0, le=1.0)
    action_tier: ActionTier
    decision_summary: str
    reasons: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class OperationalDecisionRequest(BaseModel):
    """Request to validate an LLM-recommended operational decision."""

    query: str
    recommended_action: str
    telemetry: TelemetryPayload
    evidence_chunks: List[DocumentChunk]
    model_prediction: Optional[float] = None
    model_confidence: float = Field(default=0.85, ge=0.0, le=1.0)


class OperationalDecisionResponse(BaseModel):
    """Safety-validated operational response."""

    is_authorized: bool
    action_tier: ActionTier
    trust_score: TrustScoreResult
    executed_action: Optional[str] = None
    escalation_reason: Optional[str] = None
