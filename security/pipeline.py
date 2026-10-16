"""Unified GreenRAG-Sec Security Pipeline & Orchestrator for Team Integration."""

from typing import List, Optional, Tuple
from security.config import TrustEngineConfig, TelemetryPhysicalBounds
from security.schemas import (
    ActionTier,
    DocumentChunk,
    OperationalDecisionRequest,
    OperationalDecisionResponse,
    SecurityAssessment,
    TelemetryPayload,
    TrustScoreResult,
)
from security.telemetry.anomaly_detector import TelemetryAnomalyDetector
from security.document_trust.poisoning_detector import KnowledgePoisoningDetector
from security.document_trust.provenance import DocumentProvenanceVerifier
from security.prompt_security.injection_detector import PromptInjectionDetector
from security.prompt_security.context_isolator import SecureContextIsolator
from security.retrieval.secure_retriever import SecureRetriever
from security.retrieval.evidence_verifier import EvidenceVerifier
from security.trust_engine.scoring import TrustEngine
from security.trust_engine.decision_validator import OperationalDecisionValidator


class GreenRAGSecPipeline:
    """Unified entrypoint for GreenRAG-Sec cybersecurity and trust services.

    Designed for clean, plug-and-play integration with:
    - Minmini's forecasting microservice (`/forecast`)
    - Tarunica's RAG knowledge retrieval and fault diagnosis orchestrator
    """

    def __init__(
        self,
        trust_config: TrustEngineConfig = TrustEngineConfig(),
        physical_bounds: TelemetryPhysicalBounds = TelemetryPhysicalBounds(),
    ):
        self.trust_config = trust_config
        self.physical_bounds = physical_bounds

        # Subsystems
        self.anomaly_detector = TelemetryAnomalyDetector(bounds=physical_bounds)
        self.poisoning_detector = KnowledgePoisoningDetector()
        self.provenance_verifier = DocumentProvenanceVerifier(config=trust_config)
        self.injection_detector = PromptInjectionDetector()
        self.context_isolator = SecureContextIsolator()
        self.secure_retriever = SecureRetriever(
            min_trust_threshold=0.50,
            poisoning_detector=self.poisoning_detector,
            provenance_verifier=self.provenance_verifier,
            injection_detector=self.injection_detector,
        )
        self.evidence_verifier = EvidenceVerifier()
        self.trust_engine = TrustEngine(config=trust_config)
        self.decision_validator = OperationalDecisionValidator(
            bounds=physical_bounds,
            trust_engine=self.trust_engine,
            anomaly_detector=self.anomaly_detector,
        )

    def secure_telemetry_ingress(self, telemetry: TelemetryPayload) -> SecurityAssessment:
        """Filter incoming SCADA telemetry before consumption by forecasting models."""
        return self.anomaly_detector.evaluate(telemetry)

    def secure_query_ingress(self, query: str) -> SecurityAssessment:
        """Filter user query for prompt injection attacks."""
        return self.injection_detector.scan_query(query)

    def secure_knowledge_retrieval(
        self, raw_chunks: List[DocumentChunk]
    ) -> Tuple[List[DocumentChunk], List[DocumentChunk]]:
        """Verify provenance and filter out poisoned or untrusted document chunks."""
        return self.secure_retriever.filter_and_rank_chunks(raw_chunks)

    def construct_isolated_prompt(
        self, user_query: str, approved_chunks: List[DocumentChunk]
    ) -> str:
        """Assemble delimiter-bounded prompt payload safe from prompt injection."""
        return self.context_isolator.assemble_secure_prompt(user_query, approved_chunks)

    def evaluate_and_authorize_decision(
        self,
        request: OperationalDecisionRequest,
        retrieval_relevance: float = 0.85,
    ) -> OperationalDecisionResponse:
        """Perform end-to-end trust scoring and physical safety interlock verification."""
        # 1. Evidence quality calculation
        evidence_quality = self.evidence_verifier.compute_evidence_quality(request.evidence_chunks)

        # 2. Complete decision validation
        return self.decision_validator.validate_decision(
            request=request,
            evidence_quality=evidence_quality,
            retrieval_relevance=retrieval_relevance,
        )
