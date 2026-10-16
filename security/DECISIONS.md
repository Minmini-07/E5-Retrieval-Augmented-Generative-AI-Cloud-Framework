# GreenRAG-Sec — Architectural & Security Decisions Log

**Project Track:** Pritika — Cybersecurity + Secure RAG + Trust-Aware Decision Intelligence  
**Repository Branch:** `feature/pritika`  

---

## Decision ID: DEC-001
- **Date:** 2026-10-16
- **Problem:** How to structure cybersecurity components without hard dependencies on unavailable Azure cloud services during Phase-II development.
- **Alternatives Considered:**
  1. Rely exclusively on Azure Stream Analytics, Azure AI Search, and Entra ID (requires active Azure subscription, provisioning, credentials).
  2. Implement local pure-Python modular engines with pluggable interfaces that emulate the cloud contracts and run locally via pytest.
- **Chosen Approach:** Alternative 2 (Modular pure-Python implementation under `security/` with zero mandatory cloud credentials).
- **Reason:** Enables immediate, offline, verifiable unit and integration testing, reproducible research benchmarks, and straightforward migration to Azure Functions/FastAPI in Phase-III.
- **Trade-offs and Risks:** Cloud-specific latency and scale factors must be verified in late-stage integration.
- **Affected Components:** All modules in `security/`.
- **Verification Method:** Local `pytest` suite execution without network/API key requirements.
- **Status:** Final.

---

## Decision ID: DEC-002
- **Date:** 2026-10-16
- **Problem:** Telemetry attack schema compatibility with Minmini's forecasting pipeline.
- **Alternatives Considered:**
  1. Define a generic, arbitrary SCADA telemetry schema.
  2. Align exactly with the 27 cyclical, lag, and rolling features defined in Minmini's `src/app.py`.
- **Chosen Approach:** Alternative 2.
- **Reason:** Ensures direct plug-and-play integration with the existing solar forecasting service without schema translation overhead.
- **Trade-offs and Risks:** Solar-specific features; will require schema extension when Tarunica adds wind turbine SCADA.
- **Affected Components:** `security/schemas.py`, `security/telemetry/`.
- **Verification Method:** Interception tests passing raw and attacked payloads through `TelemetryPayload`.
- **Status:** Final.

---

## Decision ID: DEC-003
- **Date:** 2026-10-16
- **Problem:** Formulation and gating policy of the Trust-Aware Decision Engine ($T$).
- **Alternatives Considered:**
  1. Single heuristic score based solely on retrieval cosine similarity.
  2. 4-pillar weighted composite ($T = w_E E + w_R R + w_C C + w_S S$) with soft warnings only.
  3. 4-pillar weighted composite with hard physical/security cutoff gates (fail-closed security).
- **Chosen Approach:** Alternative 3.
- **Reason:** Renewable energy control systems are safety-critical cyber-physical assets. High linguistic confidence or high similarity must never override an active security alert or physical temperature/voltage threshold.
- **Trade-offs and Risks:** Slightly higher abstention rate under noisy conditions; avoids catastrophic actuator/switch failures.
- **Affected Components:** `security/trust_engine/`.
- **Verification Method:** Boundary testing where $S < 0.5$ forces status `REJECTED` / `ESCALATE` regardless of $E, R, C$.
- **Status:** Final.

---

## Decision ID: DEC-004
- **Date:** 2026-10-16
- **Problem:** Mitigation strategy for prompt-injection attacks.
- **Alternatives Considered:**
  1. Relying exclusively on an external LLM safety classifier.
  2. Using regex pattern filtering alone.
  3. Defense-in-depth: Regex heuristic scanner + strict XML delimiter tagging + post-generation output constraint validation.
- **Chosen Approach:** Alternative 3.
- **Reason:** Single-layer prompt guards are notoriously vulnerable to obfuscation, markdown nesting, and indirect context leakage.
- **Trade-offs and Risks:** Minor CPU processing latency during prompt construction.
- **Affected Components:** `security/prompt_security/`.
- **Verification Method:** 50-attack benchmark suite measuring Attack Success Rate (ASR) before and after defense.
- **Status:** Final.
