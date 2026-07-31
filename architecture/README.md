# Architecture Diagrams — GreenRAG

## Diagram 1: Azure Cloud Architecture
Shows how Azure services interact within the GreenRAG energy framework.

### Components
- **Input Sources:** IoT sensors (SCADA) via Azure IoT Hub; Weather APIs (ERA5, NASA POWER) via Azure Functions; Operator queries via Azure API Management
- **Ingestion:** Azure Functions (event-driven chunking/embedding) writing to Azure AI Search (hybrid index with timestamp + equipment tag + tenant metadata)
- **Storage:** Azure Blob Storage (SCADA logs, weather data, OEM manuals, IEC standards per tenant), Azure Cosmos DB (telemetry, configs)
- **Generation:** Azure OpenAI Service (GPT-4o / GPT-4o-mini with confidence scoring)
- **Security:** Azure Stream Analytics (SCADA anomaly detection), Microsoft Entra ID (identity-based retrieval filtering), Azure WAF, Azure VNet
- **Monitoring:** Azure Monitor (grounding score, forecast MAE, latency, cost) to Power BI energy dashboards

> Diagram file: Azure_Cloud_Architecture.png

## Diagram 2: Complete System Architecture
End-to-end GreenRAG workflow in 7 stages:

1. **Domain Onboarding** — Config manifest specifying corpus sources (PVDAQ/NSRDB/SCADA/IEC), chunking rules, prompt template, access policy
2. **Ingestion** — SCADA readings + weather data + manual updates via Azure Functions — chunk, embed, upsert with dual-TTL caching (long for manuals, short for sensor data)
3. **Query** — Operator authenticates via Entra ID, hybrid retrieval (vector + BM25) with identity + equipment filter, Azure OpenAI generates answer with grounding confidence
4. **Tiered Serving** — Confident forecasts served from GPT-4o-mini; uncertain fault diagnoses escalated to GPT-4o or field engineer queue
5. **Security** — Azure Stream Analytics monitors SCADA for cyber-physical anomalies, alerts via Service Bus
6. **Telemetry** — Grounding score + forecast MAE/RMSE + tier + latency + cost emitted to Azure Monitor and Power BI
7. **Adaptation** — Scheduled job: low-confidence logs + new maintenance docs train adapter, regression gate before deployment

> Diagram file: Complete_System_Architecture.png
