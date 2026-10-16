"""Document provenance, cryptographic integrity, and source authority evaluation."""

import hashlib
import math
from datetime import datetime, timezone
from typing import Dict, Optional
from security.config import TrustEngineConfig
from security.schemas import DocumentChunk


class DocumentProvenanceVerifier:
    """Verifies cryptographic hashes and evaluates source trustworthiness."""

    def __init__(self, config: TrustEngineConfig = TrustEngineConfig()):
        self.config = config

    @staticmethod
    def compute_sha256(text: str) -> str:
        """Calculate SHA-256 hash of document text."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def verify_chunk_integrity(self, chunk: DocumentChunk) -> bool:
        """Check whether the chunk's text matches its recorded SHA-256 hash."""
        calculated = self.compute_sha256(chunk.text)
        return calculated == chunk.hash_sha256

    def compute_freshness_factor(
        self,
        verified_at: datetime,
        current_time: Optional[datetime] = None,
        half_life_days: float = 365.0,
    ) -> float:
        """Calculate exponential time-decay freshness factor F(t) in range (0.0, 1.0]."""
        if current_time is None:
            current_time = datetime.now(timezone.utc)

        # Ensure both datetimes are timezone-aware
        if verified_at.tzinfo is None:
            verified_at = verified_at.replace(tzinfo=timezone.utc)
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=timezone.utc)

        elapsed_days = max(0.0, (current_time - verified_at).total_seconds() / 86400.0)
        decay_constant = math.log(2.0) / half_life_days
        return round(math.exp(-decay_constant * elapsed_days), 4)

    def evaluate_document_trust(
        self,
        chunk: DocumentChunk,
        current_time: Optional[datetime] = None,
    ) -> float:
        """Compute composite document trust score based on authority, integrity, and freshness."""
        # 1. Integrity check: if corrupted, trust drops to 0.0 immediately
        if not self.verify_chunk_integrity(chunk):
            return 0.0

        # 2. Authority rating
        authority = self.config.authority_ratings.get(
            chunk.authority_type,
            self.config.authority_ratings["unverified_external"],
        )

        # 3. Freshness decay
        freshness = self.compute_freshness_factor(chunk.verified_at, current_time)

        # Composite score
        trust = authority * (0.8 + 0.2 * freshness)
        return round(min(1.0, max(0.0, trust)), 4)
