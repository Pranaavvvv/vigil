# AI-Powered Behavioral Anomaly Detection — Build Spec
### Honeywell campus challenge — differentiated solution design

---

## 1. The differentiator ("secret sauce")

Every team at this challenge will build *some* version of "sequence model + anomaly score." The judges will see five near-identical LSTM-autoencoder submissions. To win, pick a wedge that's hard to fake in 40 hours but cheap to build if you scope it right:

**Pick this angle: "Explainable risk graphs mapped to MITRE ATT&CK — domain-agnostic across IT/OT/IoT."**

Three things make this defensible:
1. **Cohort-relative cold start** instead of raw per-entity stats — new users/devices get scored against a peer-group prior (role, device type, subnet) from minute one, not after N days of history. Most teams will hand-wave the cold-start requirement; you solve it structurally.
2. **Graph-aware lateral-movement detection** — a lightweight entity-resource bipartite graph (not a full GNN — you don't have time) that flags resource-access breadth expansion. This directly answers "lateral movement" and "device spoofing" in the spec, which a pure sequence model can't see.
3. **MITRE ATT&CK mapping on every alert** — "flagged: credential misuse → T1078 Valid Accounts" reads as security-analyst-native and immediately signals domain fluency to Honeywell judges (this is a cybersecurity/OT company — ATT&CK fluency is a strong signal).

None of this requires exotic infra. It's a data design decision + a small graph feature layer + a lookup table. High leverage, low build cost — matches your instinct for lean, proportional infrastructure over-engineering.

---

## 2. System architecture

See the diagram above. Five stages, each independently testable:

| Stage | Purpose |
|---|---|
| Synthetic data generator | Produces the access-log schema + injects the 8 behavior patterns from the spec |
| Behavioral profiling | Builds per-entity baseline; falls back to cohort baseline for cold-start entities |
| Sequence + graph detector | Two parallel scorers: temporal (sequence model) + relational (entity-resource graph) |
| Explainability + risk scoring | Combines both scorers into one risk score with a feature-attribution reason string + ATT&CK tag |
| Analyst dashboard | Ranked queue, entity drill-down, "why flagged" panel |

---

## 3. Synthetic data generator

Use the schema exactly as given in the problem statement (`entity_id`, `entity_type`, `timestamp`, `source_ip`/`geo_location`, `resource_accessed`, `auth_method`, `session_duration`, `command_sequence`, `device_fingerprint`, `label`).

Build approach:
- **Python + NumPy/pandas + Faker**, per the spec's own suggestion — don't reach for anything heavier.
- Generate ~200–500 synthetic entities (mix of `user`, `service_account`, `edge_device`) each with a habitual profile: typical login-hour distribution (sampled from a per-entity Gaussian/von Mises for time-of-day), a home geo, a fixed resource set, a device fingerprint.
- Sample "normal" sessions from that profile with realistic noise (occasional late login, occasional new-but-nearby resource).
- Inject the 8 patterns from the spec's table at a **controlled, documented rate (0.5–3% of sessions)**, keep ground-truth labels in a separate file — never leak them into features.
- Explicitly generate a **cohort/role field** (e.g. `role: finance-analyst`, `device_class: POS-terminal`) — this is what powers cold-start scoring later. The spec's schema doesn't include this; adding it and documenting *why* is itself a small differentiator worth calling out in your report.

Deliverable 1 (generator + documented assumptions + attack taxonomy) is satisfied directly by this stage's code + a short `DATA_ASSUMPTIONS.md`.

---

## 4. Baseline profiling model (deliverable 2)

Two-tier baseline, not one:

1. **Per-entity statistical profile** once an entity has ≥ N (e.g. 20) sessions: rolling mean/variance of login hour, geo-centroid + radius, resource-set membership, session-duration distribution, device fingerprint history. Cheap, interpretable, updates online (exponentially-weighted moving stats — this is also your concept-drift handling, see §7).
2. **Cohort prior** for entities below N sessions: aggregate stats over all entities sharing `role`/`device_class`. This is the direct answer to the cold-start requirement — score new entities against "what's normal for a finance analyst" instead of nothing.

An autoencoder or one-class SVM over the tabular feature set is a reasonable "baseline profiling model" per the spec's own suggested list — use it as the statistical/unsupervised anchor, reconstruction error becomes one input feature into the final risk score (§6).

---

## 5. Detection model — sequence + graph (deliverable 3)

**Sequence branch:** a small GRU or lightweight Transformer encoder over each entity's session sequence (resource accessed, auth method, geo-delta, time-delta as tokens). Output: a per-session anomaly score from reconstruction/prediction error against the entity's own history. GRU is the pragmatic pick over a full Transformer given the build window — cheaper to train, easier to explain, still sequence-aware.

**Graph branch (the differentiator):** build a simple bipartite entity↔resource access graph per time window. Track, per entity: resource-set breadth vs. historical breadth, shortest-path novelty (is this resource reachable from the entity's normal footprint or a jump?), and co-access with recently-flagged entities (propagates suspicion one hop — this is what catches lateral movement). You do **not** need a trained GNN — a handful of graph-derived features (degree change, new-edge ratio, neighborhood overlap with baseline) computed with `networkx` is enough signal and is far cheaper to build and explain than a GNN in a 40-hour window.

Fuse both branches into a single anomaly score (simple weighted combination or a shallow gradient-boosted classifier over `[sequence_score, graph_score, profile_deviation]` — this also gives you a natural place to handle class imbalance, see §7).

---

## 6. Anomaly classification + explainability (deliverables 4–5)

- Once flagged, route the event through a small rule/classifier layer that maps the *pattern of triggered features* to one of the spec's named anomaly types (brute force, impossible travel, credential stuffing, lateral movement, device spoofing, low-and-slow exfiltration, insider drift). This can be a lightweight decision layer on top of the same features already computed — no need for a second heavy model.
- Explainability: for every alert, emit the top 2–3 contributing features in plain language ("flagged due to geo-velocity + new device fingerprint"), exactly as the spec's example shows, plus:
- **ATT&CK tag** — a static lookup table mapping anomaly type → technique ID (e.g. brute force → T1110, lateral movement → T1021, device spoofing → T1200-adjacent). This single addition makes the output read like a real SOC tool.

---

## 7. Handling the five hard requirements explicitly

The spec calls these out by name — your report should answer each one directly, since "handling cold-start and concept drift" and "detection accuracy on imbalanced labels" are named evaluation criteria.

- **Sequential/behavioral data:** handled by the sequence branch (§5) operating on ordered sessions, not snapshots.
- **Extreme class imbalance:** train the fusion classifier with class weighting or focal loss; report metrics as precision/recall/PR-AUC at a fixed alert budget (top 1% of events, as the spec specifies) rather than raw accuracy — this is also what the evaluation criteria ask for.
- **Concept drift:** exponentially-weighted per-entity baselines (§4) age out old behavior automatically; add a simple population-stability-index check that flags when a cohort's aggregate behavior has shifted enough to warrant a baseline refresh.
- **Explainability:** §6, on every alert, not just headline metrics.
- **Cold start:** cohort priors (§4), the structural answer rather than a fallback hack.

---

## 8. Analyst dashboard (deliverable 6)

Keep this lean — a single-page app is enough, doesn't need to be a polished product:
- Ranked alert queue (risk score, entity, anomaly type, ATT&CK tag)
- Click-through entity view: recent session timeline + baseline comparison
- "Why flagged" panel: feature attribution + plain-language reason string
- A simple filter by anomaly type / risk band

Build in whatever your usual stack is (React + a lightweight charting lib is enough) — this is a demo surface, not the deliverable judges weight most heavily per the evaluation criteria (explainability and detection accuracy outrank UI polish).

---

## 9. Report + presentation (deliverable 7)

Report should explicitly walk the evaluation criteria in order (detection accuracy, anomaly-type classification, false-positive rate at alert budget, explainability, cold-start/drift handling, system design/streaming feasibility, clarity) — judges are grading against that list, so mirror its structure. Include one paragraph on real-time streaming feasibility even though you're not building it: e.g. "profiling stage is stateless per-window and can run on a Kafka-consumer/feature-store architecture; sequence + graph scoring is the latency-critical path and should run as a low-latency online service." This satisfies "system design & scalability" without needing to actually deploy streaming infra.

Fill in the provided presentation template with: problem framing → your differentiator (cold-start cohorts + graph lateral-movement + ATT&CK mapping) → architecture diagram → sample alert walkthrough → metrics → limitations.

---

## 10. Suggested build order (fits a ~40 hour window)

1. Data schema + generator with injected patterns, ground truth held out (3–4 hrs)
2. Per-entity + cohort baseline profiling (2–3 hrs)
3. Sequence branch (GRU) trained on normal-session prediction error (4–6 hrs)
4. Graph feature layer (`networkx`, no GNN) (3–4 hrs)
5. Fusion classifier + imbalance handling + metrics (3–4 hrs)
6. Explainability strings + ATT&CK lookup table (2 hrs)
7. Dashboard (4–6 hrs)
8. Report + slides (3–4 hrs)
9. Buffer / polish (4+ hrs)

---

## 11. Tech stack

`pandas`, `numpy`, `faker` (synthetic data) · `scikit-learn` (baseline models, fusion classifier, class-imbalance handling) · `PyTorch` (GRU sequence model) · `networkx` (graph features) · `matplotlib`/`plotly` (report visuals) · React + lightweight charts (dashboard). Nothing here needs orchestration infra (LangGraph/Airflow etc.) — this is a bounded batch pipeline, not a long-running agentic system, so keep it flat.
