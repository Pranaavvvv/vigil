# Vigil — System Design

References: `vigil-prd.md` (why), `vigil-srs.md` (what), `behavioral-anomaly-detection-build-spec.md` (ML detail), `vigil-product-spec.md` (UI detail).

**Scoping note:** this is a hackathon/project build. Every design decision below optimizes for "runs end-to-end on a laptop and is easy to explain in a report," not for production concerns (auth, scaling, multi-region, uptime). Where a production system would need something heavier, this doc says so explicitly and moves on.

---

## 1. Architecture overview

Five sequential stages, run as a batch pipeline, served by one lightweight API, consumed by one React frontend:

```
Synthetic data generator
        ↓
Behavioral profiling (per-entity + cohort baselines)
        ↓
Sequence + graph detector (two scorers → fusion)
        ↓
Explainability + risk scoring (reason string + ATT&CK tag)
        ↓
API layer → Dashboard (6–7 pages)
```

No message queue, no orchestration framework, no microservices. One Python process generates and scores data into a local store (Parquet/SQLite is enough); one FastAPI process serves it; one React app renders it. This is deliberate — matches the project's actual scale and keeps the whole thing debuggable by one person under time pressure.

## 2. Component breakdown

### 2.1 Data generator (`/data_gen`)
- Inputs: entity count, cohort definitions, injection rate, random seed
- Outputs: `sessions.parquet` (features), `labels.parquet` (ground truth, kept separate)
- Responsibility: entity profile creation, normal-session sampling, attack-pattern injection per `behavioral-anomaly-detection-build-spec.md` §3

### 2.2 Profiling engine (`/profiling`)
- Inputs: `sessions.parquet`
- Outputs: per-entity baseline table, per-cohort baseline table, both updateable incrementally
- Responsibility: FR-2 in the SRS — statistical profile + cohort fallback + EWMA-based drift handling

### 2.3 Detector (`/detection`)
- `sequence_model.py` — GRU trained on normal-session prediction error, per entity
- `graph_features.py` — `networkx`-based entity-resource graph, degree/neighborhood features
- `fusion.py` — combines sequence score + graph score + profile-deviation into one risk score; handles class imbalance at training time
- Outputs: `alerts.parquet` (risk score, contributing features, timestamp)

### 2.4 Explainability layer (`/explain`)
- Inputs: `alerts.parquet` + feature attributions from fusion
- Outputs: reason string, anomaly-type classification, ATT&CK tag (static lookup table, `attack_mapping.json`)

### 2.5 API (`/api`, FastAPI)
See §5 for endpoints. Reads from the Parquet/SQLite store, no separate database service needed at this scale.

### 2.6 Frontend (`/frontend`, React)
Six to seven pages per `vigil-product-spec.md`. Talks to the API only — no direct file access from the browser.

## 3. Data flow

1. Generator writes `sessions.parquet` + `labels.parquet` (labels never touch the feature path)
2. Profiling reads sessions, writes baseline tables
3. Detector reads sessions + baselines, writes `alerts.parquet`
4. Explainability reads alerts, enriches with reason strings + ATT&CK tags, writes `alerts_enriched.parquet`
5. API reads the enriched store and serves it to the frontend
6. Analyst verdicts from the Investigation view write back to a `feedback.parquet` (FR-7.1) — read by nothing automatically at this scale, but present and documented as the retraining hook

## 4. Data model

- **entities**: `entity_id`, `entity_type`, `role`/`device_class` (cohort key), `first_seen`
- **sessions**: matches the schema in the SRS §3 (FR-1.2)
- **baselines**: `entity_id` or `cohort_id`, feature stats (mean/variance/set membership), `status` (established/cold-start), `last_updated`
- **alerts**: `alert_id`, `entity_id`, `timestamp`, `risk_score`, `sequence_score`, `graph_score`, `profile_score`, `anomaly_type`, `attck_tag`, `reason_string`, `status`
- **feedback**: `alert_id`, `verdict`, `analyst_note`, `timestamp`

## 5. API design

| Endpoint | Purpose |
|---|---|
| `GET /alerts` | List alerts, filter/sort by score, type, status |
| `GET /alerts/{id}` | Full alert detail — score breakdown, reason, timeline |
| `POST /alerts/{id}/verdict` | Record analyst verdict (FR-7.1) |
| `GET /entities/{id}` | Entity profile — baseline status, history, risk timeline |
| `GET /entities/{id}/graph` | Local relationship-graph neighborhood |
| `GET /metrics` | Precision/recall/PR-AUC, confusion matrix, drift status |
| `POST /simulate` | (stretch) fire a named scenario into the pipeline live |

## 6. Tech stack and folder structure

- **Data/ML**: Python, pandas, numpy, faker, scikit-learn, PyTorch (GRU only — no Transformer, per the build spec's time-budget call), networkx
- **API**: FastAPI, served locally, Parquet or SQLite as the store (no separate DB server)
- **Frontend**: React, Recharts or Chart.js for charts, `react-force-graph` or `d3-force` for the graph explorer
- **Repo layout**:
```
vigil/
  data_gen/
  profiling/
  detection/
  explain/
  api/
  frontend/
  reports/          # generated metrics, confusion matrix, PSI charts for the write-up
  notebooks/         # exploratory only, not part of the shipped pipeline
```

## 7. Non-goals and streaming-feasibility note

Explicitly not built (see SRS §6): authentication, horizontal scaling, containerized deployment, live streaming ingestion, automated retraining scheduling.

For the report's "system design & scalability" criterion, describe rather than build: the profiling stage is stateless per time-window and can run as a Kafka-consumer/feature-store job; the fused scorer is the latency-critical path and would run as a small online inference service reading from that feature store. This is a one-paragraph architecture note, not a deliverable.

## 8. Testing strategy

Covered in the QA prompt (`vigil-qa-prompt.md`) — this doc defines *what exists to test*, not the test plan itself.
