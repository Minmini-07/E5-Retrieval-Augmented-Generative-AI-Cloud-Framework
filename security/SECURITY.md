# GreenRAG-Sec — Security Architecture & Threat Model

**Author:** Pritika (Cybersecurity & Secure RAG Lead)  
**Status:** Active  
**Scope:** Cyber-physical telemetry, document integrity, prompt defense, evidence grounding, trust scoring.  

---

## 1. Threat Model Overview (STRIDE / MITRE ATLAS for Energy RAG)

| Threat Category | System Asset | Attack Vector | Mitigation Control | Fail-Safe Policy |
|---|---|---|---|---|
| **Spoofing** | SCADA / IoT Sensors | Sensor tampering, false identity | Telemetry rate-of-change & correlation detector | Reject readings outside physical envelope |
| **Tampering** | Weather / Telemetry | False-Data Injection (FDI), drift | Physical consistency checks ($P_{pv} \propto G_{poa}$) | Suppress power dispatch update |
| **Repudiation** | Operator Actions | Unaudited manual override | Immutable SHA-256 audit logger | Require cryptographic operator signature |
| **Info Disclosure** | Knowledge Base | Proprietary OEM equipment manuals | Tenant-partitioned vector indexing | Access restricted by tenant identity |
| **Denial of Service** | Forecast / RAG API | Malformed payload flood | Pydantic strict schema validation, rate limits | Immediate 400 Bad Request drop |
| **Elevation of Privilege** | LLM Recommendation | Direct/indirect prompt injection | Delimiter-bounded context, strict system prompts | Strip instruction tokens from retrieved context |

---

## 2. Physical Consistency Envelopes (Solar PV Domain)

The telemetry security layer validates every incoming reading against deterministic physical laws:
1. **Solar Nocturnal Invariant:**  
   $$\text{If } \text{hour} \in [21, 4], \quad \text{Power} = 0 \text{ W}, \quad \text{Irradiance} = 0 \text{ W/m}^2$$
2. **Photo-Thermal Gradient Invariant:**  
   Under solar irradiance $G > 200 \text{ W/m}^2$:  
   $$T_{module} \ge T_{ambient}$$
3. **Power-to-Irradiance Ratio Bound:**  
   Power cannot exceed rated peak panel capacity times incident irradiance divided by standard test condition (STC = $1000 \text{ W/m}^2$):  
   $$P \le P_{max} \cdot \frac{G}{1000} \cdot 1.15$$

Any reading violating these physical invariants is flagged as an active FDI / sensor spoofing anomaly.

---

## 3. Trust Score ($T$) Formulation & Action Thresholds

$$T = w_E \cdot E + w_R \cdot R + w_C \cdot C + w_S \cdot S$$

- **$w_E = 0.25$:** Evidence quality (source authority, freshness decay, hash integrity).
- **$w_R = 0.20$:** Retrieval relevance (semantic cosine similarity, reranking score).
- **$w_C = 0.25$:** Model confidence (uncertainty interval tightness, classifier probability).
- **$w_S = 0.30$:** Security confidence ($1.0 - \max(P_{fdi}, P_{inj}, P_{poison})$).

### Decision Policy Table
| Overall Score $T$ | Security Score $S$ | Action Outcome | Description |
|---|---|---|---|
| $\ge 0.85$ | $\ge 0.80$ | **APPROVED** | Autonomous operational recommendation issued. |
| $0.60 \le T < 0.85$ | $\ge 0.70$ | **FLAGGED / ADVISORY** | Advisory presented with explicit confidence warnings. |
| $< 0.60$ | Any | **REJECTED / ABSTAIN** | Recommendation withheld; manual inspection required. |
| Any | $< 0.50$ | **HARD SECURITY BLOCK** | Operational action blocked; security alert dispatched. |
