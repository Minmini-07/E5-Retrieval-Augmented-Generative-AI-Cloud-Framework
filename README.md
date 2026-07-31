# GreenRAG — Secure Retrieval-Augmented Generative AI Cloud Framework for Intelligent Renewable Energy Assistants

## Project Title
A Secure Retrieval-Augmented Generative AI Cloud Framework for Intelligent Renewable Energy Assistants with Generation Forecasting, Fault Diagnosis, and Predictive Decision Intelligence

## Team Members
| Name | Register No. | Role |
|------|-------------|------|
| Minmini K | 23BIT0198 | Literature Survey (Papers 1-5), Frontend, Database |
| Tarunica Senthil | 23BIT0185 | Literature Survey (Papers 6-10), Backend, Architecture |
| TBD | TBD | Literature Survey (Papers 11-15), AI Models, Azure Infra |

## Problem Statement
Renewable energy operators managing solar farms and wind parks rely on manual lookups through scattered equipment manuals, spreadsheets and SCADA exports to diagnose faults, forecast generation and plan maintenance. Large language models can automate this, but without grounding in actual technical documents they produce unreliable answers. Existing RAG implementations are single-domain, single-deployment systems with static corpora and no shared infrastructure — every new energy sub-domain is a separate engineering project.

## Objectives
1. Design a multi-tenant RAG framework on Azure where onboarding a new energy sub-domain (solar, wind, fault diagnosis, maintenance) requires only a configuration manifest.
2. Build an event-driven ingestion pipeline processing SCADA sensor data, weather forecasts (ERA5, NASA POWER), equipment manuals and IEC standards — indexing only changed content with freshness metadata.
3. Implement confidence-routed tiered serving — generation forecasts served cheaply when grounded, fault diagnoses escalated when uncertain.
4. Integrate a cyber-physical security layer monitoring SCADA anomalies alongside identity-based document filtering via Entra ID.
5. Report grounding score, forecast accuracy (MAE/RMSE), latency and cost per query as unified telemetry through Power BI energy operations dashboards.
6. Validate on solar forecasting (PVDAQ + NSRDB) and wind turbine fault diagnosis (SCADA + IEC standards) domains.

## Proposed Architecture / Framework
GreenRAG uses a modular cloud-native architecture on Azure:

**Ingestion Layer:** Azure IoT Hub (SCADA sensors) + Azure Functions (event-driven chunking/embedding) + Azure Blob Storage (raw corpora per tenant)

**Retrieval Layer:** Azure AI Search (hybrid vector + BM25 index with timestamp, equipment tag, tenant metadata) with identity-based filtering via Microsoft Entra ID

**Generation Layer:** Azure OpenAI Service (GPT-4o / GPT-4o-mini) with grounding-confidence scoring and tiered serving policy

**Security Layer:** Azure Stream Analytics (real-time SCADA anomaly detection) + Azure WAF + Azure VNet

**Telemetry Layer:** Azure Monitor + Power BI (unified grounding + forecast accuracy + cost dashboards)

**Adaptation Layer:** Azure Machine Learning (scheduled adapter refresh from production failures, gated by regression evaluation)

> Architecture diagrams are in the `architecture/` folder.

## Technology Stack
| Layer | Technology |
|-------|-----------|
| Cloud Platform | Microsoft Azure |
| LLM Inference | Azure OpenAI Service (GPT-4o, GPT-4o-mini, ada-002 embeddings) |
| Vector Search | Azure AI Search (hybrid vector + keyword) |
| Serverless Compute | Azure Functions (Python) |
| IoT Ingestion | Azure IoT Hub |
| Stream Processing | Azure Stream Analytics |
| ML Training | Azure Machine Learning |
| Authentication | Microsoft Entra ID (Azure AD) |
| Monitoring | Azure Monitor + Power BI |
| Database | Azure Cosmos DB |
| Storage | Azure Blob Storage |
| Security | Azure WAF, Azure VNet, Azure Key Vault |
| Frontend | React.js (hosted on Azure App Service) |
| Backend | FastAPI (Python, hosted on Azure App Service) |

## Dataset Details
| Dataset | Source | Purpose |
|---------|--------|---------|
| PVDAQ + NSRDB + NASA POWER | NREL, NASA | Solar generation forecasting |
| NREL WIND Toolkit + GEFCom 2014 | NREL, IEEE | Wind power forecasting |
| Wind Turbine SCADA + PVDAQ Faults | Open research repos, NREL | Fault diagnosis |
| IEC Standards + NREL Reports + OEM Manuals | IEC, NREL, Manufacturers | RAG knowledge corpus |
| ERA5 + NASA POWER | ECMWF, NASA | Weather context for forecasts |

> Full dataset details (size, features, preprocessing) are in the `dataset/` folder.
