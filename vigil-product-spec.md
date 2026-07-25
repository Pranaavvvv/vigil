# Vigil — Behavioral Risk Intelligence Platform
### Product spec: pages, features, user flow, use cases

Companion to `behavioral-anomaly-detection-build-spec.md`. That doc covers the ML pipeline; this one covers the product wrapped around it — what a judge or a SOC analyst actually clicks through.

---

## 1. Product shape

Six pages. Each maps to one or more of the seven required deliverables, so the product doubles as your demo script.

| # | Page | Deliverable it demonstrates |
|---|---|---|
| 1 | Command center | Overview / system health |
| 2 | Alert queue | Detection + risk scoring |
| 3 | Investigation view | Explainability + anomaly classification |
| 4 | Entity profile | Baseline profiling + cold-start/drift |
| 5 | Relationship graph | Lateral movement / graph detection |
| 6 | Model health | Metrics, imbalance handling, drift monitoring |

A seventh, **Simulation studio**, is optional — a control panel to fire synthetic attack scenarios live during the demo. High payoff for a judged presentation, low cost since it just calls the generator from deliverable 1.

---

## 2. Page-by-page breakdown

### Page 1 — Command center (home)
The first thing anyone sees. Answers "is anything on fire right now."

Features:
- **Risk pulse** — a single number/badge summarizing overall system risk posture (rolling average of top-N alert scores)
- **Stat cards** — active alerts, entities monitored, average risk score, active drift flags (see the mockup above)
- **Ranked alert queue preview** — top 5 alerts by risk score, click-through to full queue
- **Entity type breakdown** — users / service accounts / edge devices, count and flagged-rate per type
- **Recent model activity feed** — "baseline refreshed for finance cohort," "12 new entities cold-started," etc.

### Page 2 — Alert queue
The analyst's main workspace. Full ranked list from the preview above.

Features:
- **Sortable/filterable table**: risk score, entity, anomaly type, ATT&CK tag, first-seen time, status (new / investigating / resolved)
- **Alert budget indicator** — shows how many alerts fall inside the "top 1%" analyst budget the spec's evaluation criteria call out, vs. how many are below threshold
- **Bulk actions** — acknowledge, escalate, mark benign (feeds the feedback loop back into the model)
- **Filter by anomaly type** — brute force, impossible travel, credential stuffing, lateral movement, device spoofing, low-and-slow exfiltration, insider drift
- **Saved views** — e.g. "OT devices only," "cold-start entities only"

### Page 3 — Investigation view
Opens when an analyst clicks an alert. This is the explainability deliverable made visible.

Features:
- **Risk score breakdown** — the fused score decomposed into its three inputs: sequence-branch score, graph-branch score, profile-deviation score
- **"Why flagged" panel** — plain-language reason string (e.g. "flagged due to geo-velocity + new device fingerprint") plus the MITRE ATT&CK technique tag
- **Session timeline** — the specific access events that triggered the alert, laid out chronologically
- **Baseline comparison strip** — this session's values vs. the entity's normal range (or cohort range, if cold-start) for each key feature
- **Mini relationship graph** — just this entity's local neighborhood, so an analyst can see lateral-movement context without leaving the page
- **Analyst verdict controls** — true positive / false positive / needs escalation, with an optional note; this is the human-feedback loop that feeds concept-drift handling

### Page 4 — Entity profile
Deep-dive on one user, service account, or device — independent of any specific alert.

Features:
- **Identity header** — entity ID, type, role/cohort, device fingerprint history
- **Baseline status badge** — "established" (per-entity baseline active) vs. "cold-start" (running on cohort prior), with session count toward graduation threshold
- **Behavioral timeline** — login-hour heatmap, geo history, resource-access history over time
- **Risk history chart** — this entity's risk score over time, with past alerts marked
- **Cohort comparison** — how this entity compares to its peer group, useful for both cold-start entities and insider-drift review
- **Drift indicator** — flags if this entity's baseline has shifted enough to trigger a refresh

### Page 5 — Relationship graph explorer
The visual proof of the graph-based differentiator.

Features:
- **Interactive entity-resource graph** — nodes for entities and resources, edges for access; new/anomalous edges highlighted
- **Lateral-movement path highlighting** — traces the shortest path a compromised entity took through resources it doesn't normally touch
- **Neighborhood suspicion propagation view** — shows how risk score climbs for entities co-accessing resources with an already-flagged entity
- **Time-scrubber** — replay how the graph changed around an incident window

### Page 6 — Model health
For the ML-engineer persona and for judges evaluating "system design & scalability."

Features:
- **Detection metrics** — precision/recall/PR-AUC at the fixed alert budget, plus false-positive rate, matching the evaluation criteria directly
- **Anomaly-type confusion matrix** — how well classification distinguishes the 7 attack types
- **Drift monitor** — population-stability-index chart per cohort, flags when a baseline refresh fired
- **Retraining log** — when the fusion classifier was last retrained and on what feedback volume
- **Streaming feasibility note** — a short architecture callout (stateless profiling stage, low-latency scoring service) answering the scalability criterion without needing live infra

### Page 7 (optional) — Simulation studio
Not for production; for your demo. Lets you narrate the story live in front of judges instead of relying on pre-baked screenshots.

Features:
- **Scenario picker** — buttons for each of the 8 injected patterns (brute force, impossible travel, etc.)
- **Fire scenario** — injects a synthetic event and shows it propagate: appears in the alert queue within seconds, fully explained
- **Cold-start toggle** — spin up a brand-new entity with zero history and show it still gets scored sensibly against its cohort

---

## 3. User flow

**Primary flow — SOC analyst daily triage:**

1. Analyst opens **Command center**, sees risk pulse and today's stat cards
2. Notices the alert count is elevated, clicks through to **Alert queue**
3. Sorts by risk score, sees `svc-acct-finance-07` at the top (score 92, lateral movement)
4. Opens **Investigation view** — reads the "why flagged" panel, sees the ATT&CK tag, checks the session timeline
5. Clicks the mini relationship graph, jumps to full **Relationship graph explorer** to trace the lateral-movement path
6. Confirms it's a true positive, escalates from the investigation view
7. Curious about the account's normal behavior, opens **Entity profile** to see its baseline and risk history
8. Marks the verdict — this feedback flows back into the model's training signal

**Secondary flow — new device onboarding (cold-start):**

1. A new edge device joins the network, entity profile shows "cold-start" badge, scored against `device_class: POS-terminal` cohort from session one
2. Analyst spot-checks it in **Entity profile**, confirms the cohort comparison looks reasonable, no action needed

**Tertiary flow — judge/demo walkthrough:**

1. Open **Simulation studio**, fire an "impossible travel" scenario
2. Switch to **Alert queue** live, show the alert appear
3. Open **Investigation view**, walk through the explainability panel and ATT&CK tag
4. Close with **Model health** to show metrics against the evaluation criteria

---

## 4. Use cases

| Use case | Primary persona | Pages involved |
|---|---|---|
| Daily alert triage | SOC analyst | Command center → Alert queue → Investigation view |
| Lateral-movement incident response | Incident responder | Investigation view → Relationship graph explorer |
| False-positive budget tuning | Security engineer | Alert queue → Model health |
| Model drift monitoring | ML engineer | Model health |
| New device/user onboarding review | SOC analyst | Entity profile (cold-start) |
| OT/IoT fleet monitoring | OT security team | Command center (entity-type breakdown) → Entity profile |
| Insider-drift audit | Compliance/audit | Entity profile → Risk history + cohort comparison |
| Live capability demo | Presenter/judge | Simulation studio → Alert queue → Investigation view → Model health |

---

## 5. Build notes

- Frontend: React, keep it to one framework, no heavier state management than context/hooks needed for a 6-page app
- Charts: a lightweight lib (Recharts or Chart.js) for the risk history, PSI drift chart, and confusion matrix — don't hand-roll SVG charts under time pressure
- Graph explorer: `d3-force` or `react-force-graph` for the entity-resource visualization — this is the one page worth spending real UI time on, since it's your visual differentiator
- Keep the other five pages functional and clean rather than pushing for polish everywhere — judges weight explainability and detection accuracy over visual design per the evaluation criteria; the graph explorer is the exception because it *is* the differentiator made visible
- Backend: a thin FastAPI layer serving the model outputs from the pipeline in the build spec — no need for a separate microservice architecture at this scale
