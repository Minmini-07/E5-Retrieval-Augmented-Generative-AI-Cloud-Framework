"""Security-aware retriever wrapper with document trust filtering and poisoning isolation."""

from typing import List, Tuple
from security.document_trust.poisoning_detector import KnowledgePoisoningDetector
from security.document_trust.provenance import DocumentProvenanceVerifier
from security.prompt_security.injection_detector import PromptInjectionDetector
from security.schemas import DocumentChunk


class SecureRetriever:
    """Wraps retrieval operations with integrity, poisoning, and indirect prompt checks."""

    def __init__(
        self,
        min_trust_threshold: float = 0.50,
        poisoning_detector: KnowledgePoisoningDetector = None,
        provenance_verifier: DocumentProvenanceVerifier = None,
        injection_detector: PromptInjectionDetector = None,
    ):
        self.min_trust_threshold = min_trust_threshold
        self.poisoning_detector = poisoning_detector or KnowledgePoisoningDetector()
        self.provenance_verifier = provenance_verifier or DocumentProvenanceVerifier()
        self.injection_detector = injection_detector or PromptInjectionDetector()

    def filter_and_rank_chunks(
        self,
        raw_chunks: List[DocumentChunk],
    ) -> Tuple[List[DocumentChunk], List[DocumentChunk]]:
        """Filter unverified, poisoned, or hostile chunks and assign verified trust scores.

        Returns:
            Tuple[List[DocumentChunk], List[DocumentChunk]]: (approved_chunks, rejected_chunks)
        """
        approved = []
        rejected = []

        for chunk in raw_chunks:
            # 1. Cryptographic integrity check
            if not self.provenance_verifier.verify_chunk_integrity(chunk):
                rejected.append(chunk)
                continue

            # 2. Poisoning signature check
            poison_assessment = self.poisoning_detector.scan_chunk(chunk)
            if poison_assessment.is_malicious:
                rejected.append(chunk)
                continue

            # 3. Calculate provenance trust score
            trust = self.provenance_verifier.evaluate_document_trust(chunk)
            chunk.trust_score = trust

            # 4. Check minimum threshold
            if trust < self.min_trust_threshold:
                rejected.append(chunk)
            else:
                approved.append(chunk)

        # Sort approved chunks by trust score descending
        approved.sort(key=lambda x: x.trust_score, reverse=True)
        return approved, rejected

    def compute_retrieval_relevance(
        self,
        approved_chunks: List[DocumentChunk],
        default_relevance: float = 0.85,
    ) -> float:
        """Calculate aggregate retrieval relevance metric R from chunk metadata or similarities."""
        if not approved_chunks:
            return 0.0

        scores = [
            chunk.metadata.get("similarity_score", default_relevance)
            for chunk in approved_chunks
        ]
        return round(sum(scores) / len(scores), 4)
