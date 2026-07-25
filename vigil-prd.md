# Vigil — Product Requirements Document (PRD)

References: `vigil-srs.md` (what, precisely), `vigil-system-design.md` (how), `behavioral-anomaly-detection-build-spec.md` (ML approach), `vigil-product-spec.md` (UI/pages).

---

## 1. Problem statement

Traditional signature-based security fails against novel or slow intrusions. Honeywell's challenge asks for a system that learns "normal" access behavior for users, service accounts, and devices, and flags deviations in near real time — across IT, OT, and IoT contexts alike — with an explainable risk score, not just a bare anomaly flag.

## 2. Vision and positioning

**Vigil** is a behavioral risk intelligence platform: it watches how entities normally behave, catches the moment they don't, tells an analyst why in plain language, and does it even for an entity it has never seen before. Positioned against likely competing submissions as the entry that treats explainability, cold-start, and lateral-movement detection as first-class requirements rather than afterthoughts — because the assessment's own evaluation criteria weight exactly those.

## 3. Target users (personas)

| Persona | Need |
|---|---|
| SOC analyst | Triage alerts fast, trust the "why," act with one click |
| Incident responder | Trace how a compromised entity moved through the network |
| Security engineer | Tune the false-positive budget against real workload |
| ML engineer | Monitor detection metrics and drift over time |
| OT security team | Same tool must work for edge devices, not just user logins |
| Judge/evaluator | See the differentiator demonstrated live, not just claimed |

## 4. Goals and success metrics

- Detection: strong precision/recall/PR-AUC at the top-1% alert budget (the assessment's stated operating point)
- Classification: correct anomaly-type assignment for injected attacks, visible via confusion matrix
- Explainability: every single alert carries a human-readable reason and an ATT&CK tag — zero unexplained alerts
- Cold-start: a zero-history entity gets a sane score on session one, not a null/default score
- Demo quality: the differentiator (cohort cold-start + graph lateral-movement + ATT&CK mapping) must be *visible on screen*, not just described in the report

## 5. Differentiators (why this wins, not just works)

1. **Cohort-relative cold start** — structural, not a fallback hack.
2. **Graph-based lateral-movement detection** without a full GNN — cheap to build, directly answers a requirement most teams will skip.
3. **MITRE ATT&CK mapping on every alert** — signals domain fluency to a cybersecurity/OT company.

## 6. Scope

**In scope (MVP, must ship):**
- Synthetic data generator with documented assumptions
- Baseline profiling (per-entity + cohort)
- Sequence detector + graph detector + fusion risk score
- Anomaly-type classification + explainability strings + ATT&CK tags
- Command center, Alert queue, Investigation view, Entity profile pages
- Model health page with the metrics the evaluation criteria name

**In scope (stretch, ship if time allows):**
- Relationship graph explorer (interactive)
- Simulation studio for live demo

**Out of scope:** see `vigil-srs.md` §6 — no auth, no real streaming infra, no cloud deployment, no automated retraining scheduler.

## 7. Feature summary

Full feature-by-page breakdown lives in `vigil-product-spec.md`. Summary:

- Command center — risk pulse, stat cards, alert preview, entity-type breakdown
- Alert queue — sortable/filterable table, alert-budget indicator, bulk actions
- Investigation view — risk breakdown, why-flagged panel, session timeline, baseline comparison, mini graph, verdict controls
- Entity profile — baseline status, behavioral timeline, risk history, cohort comparison
- Relationship graph explorer — interactive graph, lateral-movement path highlighting
- Model health — detection metrics, confusion matrix, drift monitor
- Simulation studio (stretch) — fire scenarios live for demo

## 8. Milestones

Aligned to the build window in `behavioral-anomaly-detection-build-spec.md` §10:
1. Data generator + labels (day 1 morning)
2. Baseline profiling (day 1 midday)
3. Sequence + graph detectors, fusion (day 1 afternoon–evening)
4. Explainability + ATT&CK mapping (day 1 evening)
5. API + dashboard core pages (day 2 morning)
6. Model health + polish (day 2 midday)
7. Report + slides (day 2 afternoon)
8. Buffer (remaining time)

## 9. Risks

| Risk | Mitigation |
|---|---|
| Sequence model underperforms on synthetic data | Keep it simple (GRU, not Transformer) — leaves time to tune the fusion layer instead |
| Graph module scope creep into a full GNN | Explicitly capped to `networkx` degree/neighborhood features per system design |
| Dashboard eats the whole timeline | Build API + Alert queue + Investigation view first — those two pages carry most of the demo |
| Judges don't see the differentiator | Simulation studio exists specifically so it's demonstrated live, not just claimed in the report |
