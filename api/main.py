"""
Vigil -- FastAPI Backend
=========================
Implements FR-5.1: API endpoints per system design section 5.

Endpoints:
  GET  /alerts              - List alerts (filter/sort)
  GET  /alerts/{id}         - Alert detail
  POST /alerts/{id}/verdict - Record analyst verdict (FR-7.1)
  GET  /entities            - List entities
  GET  /entities/{id}       - Entity profile
  GET  /entities/{id}/graph - Local relationship graph
  GET  /metrics             - Model metrics
  GET  /dashboard           - Command center stats
  POST /simulate            - Fire scenario (stretch)

Usage:
    uvicorn api.main:app --reload --port 8000
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ── Data store ───────────────────────────────────────────────────────

DATA_DIR = Path(os.environ.get("VIGIL_DATA_DIR", "data"))


class DataStore:
    """Lazy-loading Parquet-backed data store."""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self._alerts = None
        self._entities = None
        self._sessions = None
        self._baselines = None
        self._cohort_baselines = None
        self._labels = None
        self._metrics = None
        self._scored = None
        self._feedback = []

    def _load(self, name: str, filename: str) -> pd.DataFrame:
        cache = getattr(self, f"_{name}", None)
        if cache is not None and not isinstance(cache, list):
            return cache
        path = self.data_dir / filename
        if not path.exists():
            return pd.DataFrame()
        df = pd.read_parquet(path)
        setattr(self, f"_{name}", df)
        return df

    @property
    def alerts(self) -> pd.DataFrame:
        return self._load("alerts", "alerts_enriched.parquet")

    @property
    def entities(self) -> pd.DataFrame:
        return self._load("entities", "entities.parquet")

    @property
    def sessions(self) -> pd.DataFrame:
        return self._load("sessions", "sessions.parquet")

    @property
    def baselines(self) -> pd.DataFrame:
        return self._load("baselines", "baselines.parquet")

    @property
    def cohort_baselines(self) -> pd.DataFrame:
        return self._load("cohort_baselines", "cohort_baselines.parquet")

    @property
    def labels(self) -> pd.DataFrame:
        return self._load("labels", "labels.parquet")

    @property
    def scored(self) -> pd.DataFrame:
        return self._load("scored", "scored_sessions.parquet")

    @property
    def metrics(self) -> dict:
        if self._metrics is None:
            path = self.data_dir / "metrics.json"
            if path.exists():
                with open(path) as f:
                    self._metrics = json.load(f)
            else:
                self._metrics = {}
        return self._metrics

    def save_feedback(self, alert_id: str, verdict: str, note: str = ""):
        self._feedback.append({
            "alert_id": alert_id,
            "verdict": verdict,
            "analyst_note": note,
            "timestamp": datetime.utcnow().isoformat(),
        })
        # Persist to parquet
        df = pd.DataFrame(self._feedback)
        df.to_parquet(self.data_dir / "feedback.parquet", index=False)

    def reload(self):
        """Force reload of all cached data."""
        self._alerts = None
        self._entities = None
        self._sessions = None
        self._baselines = None
        self._cohort_baselines = None
        self._labels = None
        self._metrics = None
        self._scored = None


store = DataStore(DATA_DIR)


# ── FastAPI app ──────────────────────────────────────────────────────

app = FastAPI(
    title="Vigil API",
    description="Behavioral Risk Intelligence Platform API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Pydantic models ─────────────────────────────────────────────────

class VerdictRequest(BaseModel):
    verdict: str  # true_positive | false_positive | escalate
    note: str = ""


class SimulateRequest(BaseModel):
    scenario: str  # one of the 8 pattern names
    entity_id: Optional[str] = None


# ── Helper: convert DataFrame rows to JSON-safe dicts ────────────────

def df_to_records(df: pd.DataFrame) -> list:
    """Convert DataFrame to list of dicts, handling NaN/None."""
    records = df.replace({np.nan: None}).to_dict(orient="records")
    return records


# ── Endpoints ────────────────────────────────────────────────────────

@app.get("/alerts")
def list_alerts(
    sort_by: str = Query("risk_score", description="Sort field"),
    order: str = Query("desc", description="asc or desc"),
    anomaly_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    entity_id: Optional[str] = Query(None),
    min_score: Optional[float] = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0),
):
    """List alerts with filtering and sorting (FR-5.1)."""
    df = store.alerts.copy()
    if df.empty:
        return {"alerts": [], "total": 0}

    if anomaly_type:
        df = df[df["anomaly_type"] == anomaly_type]
    if status:
        df = df[df["status"] == status]
    if entity_id:
        df = df[df["entity_id"] == entity_id]
    if min_score is not None:
        df = df[df["risk_score"] >= min_score]

    # Sort
    ascending = order == "asc"
    if sort_by in df.columns:
        df = df.sort_values(sort_by, ascending=ascending)

    total = len(df)
    df = df.iloc[offset:offset + limit]

    return {
        "alerts": df_to_records(df),
        "total": total,
        "offset": offset,
        "limit": limit,
    }


@app.get("/alerts/{alert_id}")
def get_alert(alert_id: str):
    """Get full alert detail (FR-5.1)."""
    df = store.alerts
    match = df[df["alert_id"] == alert_id]
    if match.empty:
        raise HTTPException(404, f"Alert {alert_id} not found")

    alert = match.iloc[0].replace({np.nan: None}).to_dict()

    # Get entity's session timeline around the alert
    eid = alert["entity_id"]
    sessions = store.sessions[store.sessions["entity_id"] == eid].copy()
    sessions = sessions.sort_values("timestamp")

    # Get baseline info
    baselines = store.baselines
    baseline = {}
    if not baselines.empty:
        bl_match = baselines[baselines["entity_id"] == eid]
        if not bl_match.empty:
            baseline = bl_match.iloc[0].replace({np.nan: None}).to_dict()

    return {
        "alert": alert,
        "session_timeline": df_to_records(sessions.tail(20)),
        "baseline": baseline,
    }


@app.post("/alerts/{alert_id}/verdict")
def record_verdict(alert_id: str, req: VerdictRequest):
    """Record analyst verdict on an alert (FR-7.1)."""
    df = store.alerts
    if not df[df["alert_id"] == alert_id].empty:
        # Update status in memory
        idx = df[df["alert_id"] == alert_id].index[0]
        store._alerts.at[idx, "status"] = "resolved"

    store.save_feedback(alert_id, req.verdict, req.note)
    return {"status": "ok", "alert_id": alert_id, "verdict": req.verdict}


@app.get("/entities")
def list_entities(
    entity_type: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0),
):
    """List all entities."""
    df = store.entities.copy()
    if entity_type:
        df = df[df["entity_type"] == entity_type]

    # Enrich with baseline status
    baselines = store.baselines
    if not baselines.empty:
        bl_info = baselines[["entity_id", "status", "session_count"]].copy()
        df = df.merge(bl_info, on="entity_id", how="left")

    total = len(df)
    df = df.iloc[offset:offset + limit]
    return {"entities": df_to_records(df), "total": total}


@app.get("/entities/{entity_id}")
def get_entity(entity_id: str):
    """Get entity profile (FR-5.1)."""
    entities = store.entities
    match = entities[entities["entity_id"] == entity_id]
    if match.empty:
        raise HTTPException(404, f"Entity {entity_id} not found")

    entity = match.iloc[0].replace({np.nan: None}).to_dict()

    # Baseline
    baselines = store.baselines
    baseline = {}
    if not baselines.empty:
        bl = baselines[baselines["entity_id"] == entity_id]
        if not bl.empty:
            baseline = bl.iloc[0].replace({np.nan: None}).to_dict()

    # Risk history from scored sessions
    scored = store.scored
    risk_history = []
    if not scored.empty:
        entity_scored = scored[scored["entity_id"] == entity_id][
            ["session_id", "timestamp", "risk_score"]
        ].sort_values("timestamp")
        risk_history = df_to_records(entity_scored)

    # Cohort comparison
    cohort_id = entity.get("role") or entity.get("device_class")
    cohort_info = {}
    cb = store.cohort_baselines
    if not cb.empty and cohort_id:
        cm = cb[cb["cohort_id"] == cohort_id]
        if not cm.empty:
            cohort_info = cm.iloc[0].replace({np.nan: None}).to_dict()

    # Alerts for this entity
    alerts = store.alerts
    entity_alerts = []
    if not alerts.empty:
        ea = alerts[alerts["entity_id"] == entity_id]
        entity_alerts = df_to_records(ea)

    return {
        "entity": entity,
        "baseline": baseline,
        "risk_history": risk_history,
        "cohort": cohort_info,
        "alerts": entity_alerts,
    }


@app.get("/entities/{entity_id}/graph")
def get_entity_graph(entity_id: str):
    """Get local relationship-graph neighborhood (FR-5.1)."""
    sessions = store.sessions
    entity_sessions = sessions[sessions["entity_id"] == entity_id]
    if entity_sessions.empty:
        raise HTTPException(404, f"Entity {entity_id} not found")

    # Build local graph: entity -> resources, co-accessing entities
    resources = entity_sessions["resource_accessed"].unique().tolist()

    nodes = [{"id": entity_id, "type": "entity", "is_primary": True}]
    edges = []
    seen_nodes = {entity_id}

    for res in resources:
        res_id = f"res:{res}"
        if res_id not in seen_nodes:
            nodes.append({"id": res_id, "type": "resource", "label": res})
            seen_nodes.add(res_id)
        edges.append({"source": entity_id, "target": res_id})

        # Find co-accessing entities (1-hop neighbors)
        co_accessors = sessions[sessions["resource_accessed"] == res]["entity_id"].unique()
        for co_eid in co_accessors[:10]:  # Limit to 10 per resource
            if co_eid != entity_id and co_eid not in seen_nodes:
                nodes.append({"id": co_eid, "type": "entity", "is_primary": False})
                seen_nodes.add(co_eid)
            if co_eid != entity_id:
                edges.append({"source": co_eid, "target": res_id})

    # Check which co-accessing entities are flagged
    alerts = store.alerts
    if not alerts.empty:
        flagged_ids = set(alerts["entity_id"].unique())
        for node in nodes:
            if node["type"] == "entity":
                node["is_flagged"] = node["id"] in flagged_ids

    return {"nodes": nodes, "edges": edges}


@app.get("/metrics")
def get_metrics():
    """Get model metrics (FR-5.1)."""
    metrics = store.metrics.copy()

    # Add anomaly type confusion matrix from enriched alerts
    # Force read from disk to bypass store cache and ensure latest data
    alerts_path = store.data_dir / "alerts_enriched.parquet"
    if alerts_path.exists():
        alerts = pd.read_parquet(alerts_path)
        enriched_with_truth = alerts
        if "pattern_name" in enriched_with_truth.columns and "anomaly_type" in enriched_with_truth.columns:
            # Build confusion matrix for anomaly types
            types = ["brute_force", "impossible_travel", "credential_stuffing",
                     "lateral_movement", "device_spoofing", "low_and_slow",
                     "insider_drift", "normal", "unclassified"]
            truth = enriched_with_truth["pattern_name"].fillna("normal")
            predicted = enriched_with_truth["anomaly_type"].fillna("unclassified")

            cm_data = []
            for t in types:
                row_data = {}
                for p in types:
                    row_data[p] = int(((truth == t) & (predicted == p)).sum())
                cm_data.append({"actual": t, **row_data})
            metrics["anomaly_type_confusion"] = cm_data

    # Cohort drift indicators
    cb = store.cohort_baselines
    if not cb.empty:
        metrics["cohort_drift"] = df_to_records(cb[["cohort_id", "session_count", "entity_count"]])

    return metrics


@app.get("/dashboard")
def get_dashboard():
    """Aggregated stats for command center (FR-6.1)."""
    alerts = store.alerts
    entities = store.entities
    scored = store.scored

    stats = {
        "total_entities": len(entities) if not entities.empty else 0,
        "total_alerts": len(alerts) if not alerts.empty else 0,
        "active_alerts": 0,
        "avg_risk_score": 0.0,
        "risk_pulse": 0.0,
        "entity_breakdown": {},
        "top_alerts": [],
        "recent_activity": [],
    }

    if not alerts.empty:
        stats["active_alerts"] = int((alerts["status"] == "new").sum())
        stats["avg_risk_score"] = round(float(alerts["risk_score"].mean()), 1)

        # Risk pulse: rolling average of top-N alert scores
        top_scores = alerts.nlargest(10, "risk_score")["risk_score"]
        stats["risk_pulse"] = round(float(top_scores.mean()), 1)

        # Top 5 alerts
        top5 = alerts.nlargest(5, "risk_score")
        stats["top_alerts"] = df_to_records(top5[[
            "alert_id", "entity_id", "risk_score", "anomaly_type",
            "attck_id", "reason_string", "status", "timestamp"
        ]])

        # Anomaly type distribution
        stats["anomaly_type_distribution"] = alerts["anomaly_type"].value_counts().to_dict()

    if not entities.empty:
        stats["entity_breakdown"] = entities["entity_type"].value_counts().to_dict()

        # Flagged rate per entity type
        if not alerts.empty:
            flagged_entities = set(alerts["entity_id"].unique())
            for etype in entities["entity_type"].unique():
                type_entities = set(entities[entities["entity_type"] == etype]["entity_id"])
                flagged = type_entities & flagged_entities
                stats[f"flagged_rate_{etype}"] = round(
                    len(flagged) / max(len(type_entities), 1), 4
                )

    # Cold-start count
    baselines = store.baselines
    if not baselines.empty:
        stats["cold_start_count"] = int((baselines["status"] == "cold-start").sum())
        stats["drift_flags"] = 0  # Placeholder

    # Recent model activity feed
    stats["recent_activity"] = [
        {"message": f"System monitoring {stats['total_entities']} entities", "type": "info"},
        {"message": f"{stats['active_alerts']} active alerts in queue", "type": "alert"},
    ]
    if not baselines.empty:
        cs = int((baselines["status"] == "cold-start").sum())
        if cs > 0:
            stats["recent_activity"].append(
                {"message": f"{cs} entities in cold-start mode (cohort scoring)", "type": "info"}
            )

    return stats


@app.post("/simulate")
def simulate_scenario(req: SimulateRequest):
    """Fire a named scenario (stretch, FR-6.7)."""
    # Placeholder: in a full implementation this would call the data
    # generator to inject a new event and re-score
    valid_scenarios = [
        "brute_force", "impossible_travel", "credential_stuffing",
        "lateral_movement", "device_spoofing", "low_and_slow",
        "insider_drift",
    ]
    if req.scenario not in valid_scenarios:
        raise HTTPException(400, f"Unknown scenario: {req.scenario}")

    return {
        "status": "simulated",
        "scenario": req.scenario,
        "message": f"Scenario '{req.scenario}' would be injected. "
                   "Full implementation requires pipeline re-run.",
    }


@app.get("/health")
def health():
    """Health check."""
    return {"status": "ok", "data_dir": str(DATA_DIR)}
