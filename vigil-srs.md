# Vigil — Software Requirements Specification (SRS)

References: `vigil-prd.md` (why), `vigil-system-design.md` (how), `behavioral-anomaly-detection-build-spec.md` (ML approach), `vigil-product-spec.md` (UI/pages).

---

## 1. Purpose and scope

Defines what Vigil must *do*, precisely enough that "done" is checkable. Scoped to a hackathon/project build — not a production security product. No real customer data, no compliance certification, no production SLAs.

## 2. Definitions

- **Entity** — a user, service account, or edge device being monitored.
- **Cohort** — a peer group of entities sharing role/device_class, used to score entities with insufficient history.
- **Cold-start entity** — an entity with fewer than the graduation threshold (default: 20) sessions.
- **Risk score** — 0–100 fused output combining sequence, graph, and profile-deviation signals.
- **Alert budget** — the top 1% of scored events, the fixed operating point used for false-positive-rate evaluation.

## 3. Functional requirements

### FR-1 — Synthetic data generation
- FR-1.1: System shall generate synthetic entities with fields: `entity_id`, `entity_type` (user/service_account/edge_device), `role`/`device_class` (cohort key).
- FR-1.2: System shall generate session records matching the schema: `entity_id`, `entity_type`, `timestamp`, `source_ip`/`geo_location`, `resource_accessed`, `auth_method`, `session_duration`, `command_sequence`, `device_fingerprint`, `label`.
- FR-1.3: System shall generate a per-entity habitual baseline (login-hour distribution, home geo, resource set, device fingerprint) and sample "normal" sessions from it with noise.
- FR-1.4: System shall inject the 8 named patterns (normal baseline, brute force, impossible travel, credential stuffing, lateral movement, device spoofing, low-and-slow exfiltration, insider drift) at a configurable rate, default 0.5–3% of sessions.
- FR-1.5: Ground-truth labels shall be stored separately from the feature set used for training/inference.

### FR-2 — Behavioral profiling
- FR-2.1: System shall maintain a per-entity statistical baseline (rolling mean/variance of login hour, geo-centroid + radius, resource-set membership, session-duration distribution) once an entity reaches the graduation threshold.
- FR-2.2: System shall maintain a cohort-level baseline for entities below the graduation threshold and score them against it.
- FR-2.3: Baselines shall update online using an exponentially-weighted scheme (no full retrain required per new session).

### FR-3 — Detection
- FR-3.1: System shall score each session with a sequence-based anomaly score (prediction/reconstruction error from a GRU or comparable sequence model over the entity's own session history).
- FR-3.2: System shall score each session with a graph-based anomaly score derived from an entity-resource access graph (degree change, new-edge ratio, neighborhood overlap with baseline, one-hop suspicion propagation from already-flagged entities).
- FR-3.3: System shall fuse sequence score, graph score, and profile-deviation score into a single 0–100 risk score.
- FR-3.4: Fusion model training shall account for class imbalance (class weighting or focal loss at minimum).

### FR-4 — Classification and explainability
- FR-4.1: Every alert above the alert-budget threshold shall be classified into one of the 8 named anomaly types (or "unclassified" if none match confidently).
- FR-4.2: Every alert shall carry a plain-language reason string naming its top 2–3 contributing features.
- FR-4.3: Every alert shall carry a MITRE ATT&CK technique tag from a static lookup table keyed by anomaly type.

### FR-5 — API
- FR-5.1: System shall expose endpoints to list alerts (filterable/sortable), fetch alert detail, fetch entity profile, fetch graph neighborhood, fetch model metrics, and trigger a simulation scenario (see `vigil-system-design.md` §5 for the endpoint list).

### FR-6 — Dashboard (pages per `vigil-product-spec.md`)
- FR-6.1: Command center shall display live stat cards and a top-5 alert preview.
- FR-6.2: Alert queue shall be sortable/filterable by risk score, entity, anomaly type, and status, and shall display the alert-budget line.
- FR-6.3: Investigation view shall display the risk-score breakdown, reason string, ATT&CK tag, session timeline, baseline comparison, and a mini relationship graph; shall accept an analyst verdict (true positive / false positive / escalate).
- FR-6.4: Entity profile shall display baseline status (established/cold-start), behavioral timeline, risk history, and cohort comparison.
- FR-6.5: Relationship graph explorer shall render the entity-resource graph with lateral-movement path highlighting and a time-scrubber.
- FR-6.6: Model health shall display precision/recall/PR-AUC at the alert budget, false-positive rate, a confusion matrix over the 8 anomaly types, and a drift indicator per cohort.
- FR-6.7 (optional): Simulation studio shall let an operator fire any of the 8 scenarios on demand and observe it propagate to the alert queue.

### FR-7 — Feedback loop
- FR-7.1: Analyst verdicts recorded in FR-6.3 shall be persisted and usable as additional training signal (does not require automatic retraining to be implemented — logging the signal satisfies this requirement at project scale).

## 4. Non-functional requirements

- **NFR-1 Explainability**: every alert must be explainable without opening model internals — this is graded explicitly by the assessment.
- **NFR-2 Cold-start correctness**: an entity with zero prior sessions must still receive a non-degenerate risk score on its first session.
- **NFR-3 Usability**: an analyst unfamiliar with the system should be able to triage a top alert within two clicks of landing on the command center.
- **NFR-4 Reproducibility**: the synthetic generator must accept a random seed and reproduce identical datasets given the same seed.
- **NFR-5 Performance (project scale, not production)**: scoring a batch of ~1,000 sessions should complete in well under a minute on a laptop CPU; there is no requirement to handle live streaming throughput — the report should describe streaming feasibility, not implement it.

## 5. Data requirements

Default generation volume: ~300–500 entities, ~90 days of session history, 0.5–3% injected anomaly rate, ground truth withheld from the feature set at inference time. Full field list in FR-1.2 and `behavioral-anomaly-detection-build-spec.md` §3.

## 6. Constraints and explicit non-goals

This is a project build, not production software. The following are explicitly **out of scope**:
- Authentication/authorization, multi-tenant access control
- Real-time streaming ingestion (Kafka, etc.) — described in the report, not built
- Horizontal scaling, containerized orchestration, cloud deployment
- Automated retraining pipelines — the feedback signal is captured (FR-7.1), retraining is manual/documented, not scheduled
- Real intrusion data or any production security integration

## 7. Acceptance criteria (mapped to the assessment's evaluation criteria)

| Evaluation criterion | Satisfied by |
|---|---|
| Detection accuracy on imbalanced labels | FR-3.4, Model health page metrics |
| Correct anomaly-type classification | FR-4.1, confusion matrix |
| False-positive rate at alert budget | FR-3.3 fused score + Alert queue budget indicator |
| Explainability / analyst usability | FR-4.2, FR-4.3, Investigation view |
| Cold-start and concept drift handling | FR-2.2, FR-2.3, Entity profile baseline-status badge |
| System design & scalability | System design doc §7 streaming-feasibility note |
| Report clarity | Deliverable, not code — see PRD §8 |
