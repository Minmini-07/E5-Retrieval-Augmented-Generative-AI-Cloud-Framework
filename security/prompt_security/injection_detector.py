"""Prompt-injection detector for user queries and retrieved context."""

import re
from typing import List, Tuple
from security.config import PromptSecurityConfig
from security.schemas import AttackType, DocumentChunk, SecurityAssessment


class PromptInjectionDetector:
    """Detects direct and indirect adversarial prompt injection."""

    def __init__(self, config: PromptSecurityConfig = PromptSecurityConfig()):
        self.config = config
        self.forbidden_patterns = [
            re.compile(re.escape(phrase), re.IGNORECASE) for phrase in self.config.forbidden_phrases
        ]
        self.jailbreak_patterns = [
            re.compile(r"(?:dan|jailbreak|unrestricted)\s+mode", re.IGNORECASE),
            re.compile(r"you\s+must\s+now\s+(?:act|ignore|obey)", re.IGNORECASE),
            re.compile(r"(?:<\|im_start\|>|<\|im_end\|>|\[INST\]|\[\/INST\])", re.IGNORECASE),
            re.compile(r"system\s*:\s*(?:you\s+are|override)", re.IGNORECASE),
            re.compile(r"repeat\s+(?:the\s+)?system\s+prompt", re.IGNORECASE),
        ]

    def scan_query(self, query: str) -> SecurityAssessment:
        """Scan a user query for direct prompt-injection signatures."""
        violations = []

        if len(query) > self.config.max_query_length:
            violations.append(f"Query exceeds maximum character limit ({len(query)} > {self.config.max_query_length})")

        for pattern in self.forbidden_patterns:
            match = pattern.search(query)
            if match:
                violations.append(f"Forbidden phrase detected: '{match.group(0)}'")

        for pattern in self.jailbreak_patterns:
            match = pattern.search(query)
            if match:
                violations.append(f"Jailbreak signature detected: '{match.group(0)}'")

        if violations:
            return SecurityAssessment(
                is_anomalous=True,
                is_malicious=True,
                attack_type=AttackType.PROMPT_INJECTION_DIRECT,
                anomaly_score=1.0,
                security_confidence=0.0,
                violated_rules=violations,
                details={"query_length": len(query), "violations": violations},
            )

        return SecurityAssessment(
            is_anomalous=False,
            is_malicious=False,
            attack_type=AttackType.CLEAN,
            anomaly_score=0.0,
            security_confidence=1.0,
            violated_rules=[],
            details={"status": "CLEAN_QUERY"},
        )

    def scan_context(
        self, chunks: List[DocumentChunk]
    ) -> Tuple[List[DocumentChunk], List[DocumentChunk]]:
        """Scan retrieved chunks for indirect prompt injection and split into (safe, suspicious)."""
        safe_chunks = []
        suspicious_chunks = []

        for chunk in chunks:
            is_suspicious = False
            for pattern in self.forbidden_patterns + self.jailbreak_patterns:
                if pattern.search(chunk.text):
                    is_suspicious = True
                    break

            if is_suspicious:
                suspicious_chunks.append(chunk)
            else:
                safe_chunks.append(chunk)

        return safe_chunks, suspicious_chunks
