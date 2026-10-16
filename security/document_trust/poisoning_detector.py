"""Knowledge-base poisoning detector for renewable energy documentation."""

import re
from typing import List, Tuple
from security.schemas import AttackType, DocumentChunk, SecurityAssessment


class KnowledgePoisoningDetector:
    """Scans incoming and retrieved document chunks for poisoning attacks and hostile instructions."""

    POISON_PATTERNS = [
        re.compile(r"ignore\s+(?:all\s+)?(?:safety|previous|system)\s+instructions?", re.IGNORECASE),
        re.compile(r"(?:system|emergency)\s+override", re.IGNORECASE),
        re.compile(r"disable\s+(?:the\s+)?(?:thermal|overheat|circuit|breaker|emergency)\s+(?:protection|cutoff|trip)", re.IGNORECASE),
        re.compile(r"operate\s+(?:the\s+)?inverter\s+(?:above|exceeding)\s+(?:1[0-9]{2}|200)\s*(?:°C|celsius)", re.IGNORECASE),
        re.compile(r"bypass\s+.*?(?:grounding|interlock|safety)", re.IGNORECASE),
        re.compile(r"do\s+not\s+(?:report|log|flag)\s+(?:this\s+)?(?:error|alarm|fault|anomaly)", re.IGNORECASE),
        re.compile(r"always\s+classify\s+(?:all\s+)?faults?\s+as\s+normal", re.IGNORECASE),
    ]

    def scan_chunk(self, chunk: DocumentChunk) -> SecurityAssessment:
        """Evaluate whether a document chunk contains poisoning signatures."""
        text = chunk.text
        violations = []

        for pattern in self.POISON_PATTERNS:
            match = pattern.search(text)
            if match:
                violations.append(f"Poisoning signature matched: '{match.group(0)}'")

        if violations:
            return SecurityAssessment(
                is_anomalous=True,
                is_malicious=True,
                attack_type=AttackType.KNOWLEDGE_POISONING,
                anomaly_score=1.0,
                security_confidence=0.0,
                violated_rules=violations,
                details={
                    "chunk_id": chunk.chunk_id,
                    "source_id": chunk.source_id,
                    "detected_patterns": violations,
                },
            )

        return SecurityAssessment(
            is_anomalous=False,
            is_malicious=False,
            attack_type=AttackType.CLEAN,
            anomaly_score=0.0,
            security_confidence=1.0,
            violated_rules=[],
            details={"chunk_id": chunk.chunk_id, "status": "VERIFIED_CLEAN"},
        )

    def filter_poisoned_chunks(
        self, chunks: List[DocumentChunk]
    ) -> Tuple[List[DocumentChunk], List[DocumentChunk]]:
        """Separate a list of chunks into (verified_clean_chunks, quarantined_poisoned_chunks)."""
        clean = []
        quarantined = []

        for chunk in chunks:
            assessment = self.scan_chunk(chunk)
            if assessment.is_malicious:
                quarantined.append(chunk)
            else:
                clean.append(chunk)

        return clean, quarantined
