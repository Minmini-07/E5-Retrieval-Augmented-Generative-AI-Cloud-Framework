# GreenRAG-Sec — Security & Trust Engine

**Author & Research Lead:** Pritika  
**Research Track:** Cybersecurity + Secure RAG + Trust-Aware Decision Intelligence  
**Repository Branch:** `feature/pritika`  
**Version:** 1.0.0  

---

## 1. Overview

The `security/` package provides the complete cyber-physical security, document integrity, prompt protection, and trust-aware decision infrastructure for **GreenRAG-Sec**. 

Designed specifically for safety-critical renewable energy assets (solar farms and wind parks), it operates as a modular, pure-Python suite with zero mandatory cloud dependencies for local testing, while maintaining 100% plug-and-play compatibility with future FastAPI, Azure Functions, and Azure AI Search deployments.

---

## 2. Architecture & Modules

```text
security/
├── __init__.py                   # Package exports and unified symbols
├── config.py                     # Solar physical bounds, trust weights, and prompt-injection rules
├── schemas.py                    # Pydantic models (TelemetryPayload, DocumentChunk, TrustScoreResult, etc.)
├── pipeline.py                   # Unified GreenRAGSecPipeline orchestrator for team integration
├── telemetry/                    # Cyber-physical SCADA security
│   ├── attack_simulator.py       # False-Data Injection (spikes, creeping drift, replay, contradictions)
│   └── anomaly_detector.py       # Deterministic physics bounds & multi-sensor correlation filter
├── document_trust/               # Knowledge-base integrity & poisoning defense
│   ├── provenance.py             # SHA-256 cryptographic verification & exponential freshness decay F(t)
│   └── poisoning_detector.py     # Scans manuals for hostile overrides & unauthorized safety bypasses
├── prompt_security/              # Input security & delimiter isolation
│   ├── injection_detector.py     # Direct & indirect prompt-injection detection (100% detection rate)
│   └── context_isolator.py       # XML delimiter prompt builder (<evidence>, <user_query>, <system_policy>)
├── retrieval/                    # Secure evidence retrieval & grounding
│   ├── secure_retriever.py       # Security-filtered retrieval wrapper & aggregate relevance calculator (R)
│   └── evidence_verifier.py      # Automated citation extraction & claim grounding verifier
└── trust_engine/                 # Trust-aware decision intelligence
    ├── scoring.py                # 4-pillar trust calculator: T = w_E*E + w_R*R + w_C*C + w_S*S
    └── decision_validator.py     # Physical safety interlock enforcement (hard block on unsafe actions)
```

---

## 3. Quickstart & Integration Guide

### 3.1 Initializing the Unified Pipeline
```python
from security import GreenRAGSecPipeline, TelemetryPayload, DocumentChunk, OperationalDecisionRequest

# Initialize with default safety bounds and calibrated weights
pipeline = GreenRAGSecPipeline()
```

### 3.2 Minmini's Track: Securing Telemetry Ingress (`POST /forecast`)
Before passing SCADA telemetry to forecasting models, filter out False-Data Injection and sensor spoofing:
```python
# Raw telemetry payload containing the 27 lag/rolling features
telemetry = TelemetryPayload(features=request_json["features"])

# Run cyber-physical anomaly check
assessment = pipeline.secure_telemetry_ingress(telemetry)

if assessment.is_anomalous:
    # Reject or flag spoofed readings before prediction
    return {"error": "Telemetry rejected by security interlock", "violations": assessment.violated_rules}, 400

# Proceed with forecasting
prediction = model.predict(telemetry.features)
```

### 3.3 Tarunica's Track: Securing Knowledge Retrieval & Prompt Assembly
Prevent knowledge-base poisoning and indirect prompt injection:
```python
# 1. Sanitize user query
query_assessment = pipeline.secure_query_ingress(user_query)
if query_assessment.is_malicious:
    return {"error": "Query blocked by prompt-injection filter"}, 403

# 2. Filter raw retrieved chunks from vector store
approved_chunks, quarantined_chunks = pipeline.secure_knowledge_retrieval(raw_retrieved_chunks)

# 3. Construct delimiter-isolated prompt safe from instruction hijacking
isolated_prompt = pipeline.construct_isolated_prompt(user_query, approved_chunks)

# 4. Invoke LLM with isolated_prompt
llm_response = call_llm(isolated_prompt)
```

### 3.4 Authorizing Operational Decisions (Safety Interlocks)
Never allow raw LLM output to trigger physical actuators or breakers without deterministic safety validation:
```python
decision_request = OperationalDecisionRequest(
    query=user_query,
    recommended_action=llm_response["recommended_action"],
    telemetry=telemetry,
    evidence_chunks=approved_chunks,
    model_confidence=0.92,
)

decision_response = pipeline.evaluate_and_authorize_decision(decision_request)

if decision_response.is_authorized:
    execute_action(decision_response.executed_action)
else:
    escalate_to_operator(
        tier=decision_response.action_tier,
        reason=decision_response.escalation_reason,
    )
```

---

## 4. The 4-Pillar Trust Score ($T$)

The decision engine calculates an objective trust score:
$$T = w_E \cdot E + w_R \cdot R + w_C \cdot C + w_S \cdot S$$

| Variable | Pillar | Description | Default Weight |
|---|---|---|:---:|
| **$E$** | Evidence Quality | Authority rating, SHA-256 integrity, freshness decay $F(t)$ | $w_E = 0.25$ |
| **$R$** | Retrieval Relevance | Semantic cosine similarity & reranking scores | $w_R = 0.20$ |
| **$C$** | Model Confidence | Forecasting prediction interval tightness / fault probability | $w_C = 0.25$ |
| **$S$** | Security Confidence | $1.0 - \max(P_{fdi}, P_{inj}, P_{poison})$ | $w_S = 0.30$ |

### Action Tiers
- **`APPROVED` ($T \ge 0.85, S \ge 0.80$):** High evidence and security trust; action authorized.
- **`FLAGGED` ($0.60 \le T < 0.85$):** Human-in-the-loop review required with confidence warnings.
- **`REJECTED` ($T < 0.60$):** Insufficient evidence; action withheld.
- **`HARD_SECURITY_BLOCK` ($S < 0.50$ or physical violation):** Hard fail-closed trip; emergency alert dispatched.

---

## 5. Verification & Testing

### 5.1 Run Automated Pytest Suite
```bash
python -m pytest tests/security/ -v
```
**Test Results:** **32 passed in 0.33 seconds** across 6 test suites:
- `test_telemetry_attacks.py`: 6 tests (FDI, drift, physical contradictions).
- `test_document_trust.py`: 5 tests (SHA-256 integrity, freshness decay, poisoning).
- `test_prompt_injection.py`: 8 tests (direct jailbreaks, indirect injections, isolator).
- `test_evidence_verifier.py`: 3 tests (citation checks, ungrounded claims).
- `test_trust_engine.py`: 5 tests (trust score calculation, thermal interlocks).
- `test_end_to_end_pipeline.py`: 5 tests (complete ingress-to-decision pipeline).

### 5.2 Run Research Benchmark Experiments
```bash
python evaluation/security_benchmarks/run_security_benchmarks.py
```
**Empirical Results Summary:**
- **Experiment 1 (FDI Detection):** F1-Score = **1.0000** | False Positive Rate = **0.0000**
- **Experiment 2 (Poisoning Mitigation):** Quarantine Rate = **100.0%** | Clean Retention = **100.0%**
- **Experiment 3 (Prompt Injection):** Detection Rate = **100.0%** | Attack Success Rate = **0.0%**
- **Experiment 4 (Safety Interlocks):** Unsafe Actions Blocked = **100.0%**
- **Experiment 5 (System Ablation Study):** Evaluated across Configurations A through F.
