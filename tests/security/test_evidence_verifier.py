"""Unit tests for Evidence Verifier and Claim Grounding."""

import sys
from pathlib import Path

# Ensure project root in sys.path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest
from security.schemas import DocumentChunk
from security.retrieval.evidence_verifier import EvidenceVerifier


@pytest.fixture
def evidence_chunks() -> list[DocumentChunk]:
    return [
        DocumentChunk(
            chunk_id="chunk-1",
            source_id="manual-inverter",
            authority_type="oem_manual_verified",
            text="Inverter thermal threshold is 85°C. Power derating is required above 85°C to avoid shutdown.",
            hash_sha256="abc",
            trust_score=0.90,
        ),
        DocumentChunk(
            chunk_id="chunk-2",
            source_id="iec-std",
            authority_type="iec_standard",
            text="IEC 62109: Emergency trip must occur if internal ambient exceeds 60°C.",
            hash_sha256="def",
            trust_score=1.0,
        ),
    ]


def test_evidence_quality_calculation(evidence_chunks: list[DocumentChunk]):
    verifier = EvidenceVerifier()
    quality = verifier.compute_evidence_quality(evidence_chunks)
    assert 0.90 <= quality <= 1.0


def test_grounded_response_with_citations(evidence_chunks: list[DocumentChunk]):
    verifier = EvidenceVerifier()
    grounded_text = (
        "Based on [Evidence 1] and [IEC-62109], the inverter thermal limit is 85°C. "
        "We recommend initiating power derating immediately to avoid trip."
    )
    score, issues = verifier.verify_claim_grounding(grounded_text, evidence_chunks)
    assert score >= 0.80
    assert len(issues) == 0


def test_ungrounded_response_without_citations(evidence_chunks: list[DocumentChunk]):
    verifier = EvidenceVerifier()
    hallucinated_text = "The voltage is too high, replace the cooling fluid."
    score, issues = verifier.verify_claim_grounding(hallucinated_text, evidence_chunks)
    assert score < 0.70
    assert any("No explicit evidence citations" in issue for issue in issues)
