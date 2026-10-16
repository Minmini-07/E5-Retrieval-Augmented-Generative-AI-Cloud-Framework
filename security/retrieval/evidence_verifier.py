"""Evidence verifier for claim grounding, citation checking, and hallucination reduction."""

import re
from typing import List, Tuple
from security.schemas import DocumentChunk


class EvidenceVerifier:
    """Verifies that generated responses and operational claims are grounded in evidence."""

    @staticmethod
    def compute_evidence_quality(chunks: List[DocumentChunk]) -> float:
        """Compute aggregate evidence quality score E in range [0.0, 1.0]."""
        if not chunks:
            return 0.0

        total_trust = sum(chunk.trust_score for chunk in chunks)
        mean_trust = total_trust / len(chunks)
        # Small boost if multiple independent sources corroborate
        corroboration_factor = min(1.0, 0.9 + 0.05 * len(set(c.source_id for c in chunks)))
        return round(min(1.0, mean_trust * corroboration_factor), 4)

    @staticmethod
    def extract_citations(response_text: str) -> List[str]:
        """Extract evidence citations formatted as [Evidence N], (Manual-X), [IEC-XXXX], etc."""
        citations = []
        patterns = [
            re.compile(r"\[(?:Evidence|Chunk)\s*(\d+)\]", re.IGNORECASE),
            re.compile(r"\[(IEC[ -]\d+[^\]]*)\]", re.IGNORECASE),
            re.compile(r"\((?:Manual|Standard|Record)[ -][^)]+\)", re.IGNORECASE),
        ]
        for pattern in patterns:
            for match in pattern.finditer(response_text):
                citations.append(match.group(0))
        return citations

    def verify_claim_grounding(
        self,
        response_text: str,
        evidence_chunks: List[DocumentChunk],
    ) -> Tuple[float, List[str]]:
        """Evaluate evidence grounding and detect unsupported high-risk claims.

        Returns:
            Tuple[float, List[str]]: (grounding_score [0.0 - 1.0], list of ungrounded issues)
        """
        if not evidence_chunks:
            return 0.0, ["Response generated without any supporting evidence chunks."]

        issues = []
        citations = self.extract_citations(response_text)

        # Check for citation presence
        if not citations:
            issues.append("No explicit evidence citations found in technical recommendation.")

        # Check keyword grounding (entity overlap)
        evidence_corpus = " ".join(c.text.lower() for c in evidence_chunks)
        # Check high-consequence operational claims
        high_risk_terms = ["shutdown", "replace", "derate", "trip", "overheat", "voltage", "current"]
        ungrounded_risks = []
        for term in high_risk_terms:
            if term in response_text.lower() and term not in evidence_corpus:
                ungrounded_risks.append(term)

        if ungrounded_risks:
            issues.append(f"High-consequence operational terms not supported by evidence: {ungrounded_risks}")

        # Compute grounding score
        score = 1.0
        if not citations:
            score -= 0.4
        if ungrounded_risks:
            score -= 0.2 * len(ungrounded_risks)

        grounding_score = max(0.0, round(score, 3))
        return grounding_score, issues
