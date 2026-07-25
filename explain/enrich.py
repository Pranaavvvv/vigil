"""
Vigil -- Explainability & Classification Pipeline
===================================================
Implements FR-4.1 through FR-4.3:
  - Anomaly-type classification into the 8 named types
  - Plain-language reason strings from top contributing features
  - MITRE ATT&CK technique tag from static lookup

Usage:
    python -m explain.enrich --data-dir data
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


# ── Feature -> human-readable name mapping ───────────────────────────

FEATURE_NAMES = {
    "hour_deviation":        "unusual login time",
    "geo_deviation":         "geo-location anomaly",
    "resource_novelty":      "novel resource access",
    "duration_deviation":    "unusual session duration",
    "device_novelty":        "unknown device fingerprint",
    "sequence_score":        "abnormal session sequence",
    "graph_score":           "abnormal access graph pattern",
    "degree_change":         "resource access breadth expansion",
    "new_edge_ratio":        "new resource connections",
    "neighborhood_overlap":  "access pattern divergence from baseline",
    "suspicion_propagation": "co-access with flagged entities",
    "profile_deviation_score": "overall profile deviation",
}


# ── Anomaly type classification (FR-4.1) ─────────────────────────────

def classify_anomaly_type(row: dict) -> str:
    """
    Rule-based classifier that maps feature signatures to one of
    the 8 named anomaly types. Falls back to "unclassified" if
    no pattern matches confidently.
    """
    scores = {
        "brute_force": 0.0,
        "impossible_travel": 0.0,
        "credential_stuffing": 0.0,
        "lateral_movement": 0.0,
        "device_spoofing": 0.0,
        "low_and_slow": 0.0,
        "insider_drift": 0.0,
    }

    # Brute force: short duration + rapid sessions
    dur_dev = row.get("duration_deviation", 0)
    hour_dev = row.get("hour_deviation", 0)
    if dur_dev > 0.3 and row.get("session_duration", 30) < 2:
        scores["brute_force"] += 0.6
    if dur_dev > 0.5:
        scores["brute_force"] += 0.2

    # Impossible travel: high geo deviation
    geo_dev = row.get("geo_deviation", 0)
    if geo_dev > 0.5:
        scores["impossible_travel"] += 0.7
    if geo_dev > 0.3 and row.get("device_novelty", 0) > 0.5:
        scores["impossible_travel"] += 0.3

    # Credential stuffing: new device + low duration
    dev_novelty = row.get("device_novelty", 0)
    if dev_novelty > 0.5 and dur_dev > 0.2 and row.get("session_duration", 30) < 5:
        scores["credential_stuffing"] += 0.5
    if row.get("suspicion_propagation", 0) > 0.3:
        scores["credential_stuffing"] += 0.3

    # Lateral movement: graph features dominate
    new_edge = row.get("new_edge_ratio", 0)
    degree_chg = row.get("degree_change", 0)
    res_novelty = row.get("resource_novelty", 0)
    if new_edge > 0.3 or degree_chg > 0.3:
        scores["lateral_movement"] += 0.5
    if res_novelty > 0.5 and new_edge > 0.2:
        scores["lateral_movement"] += 0.3
    if row.get("neighborhood_overlap", 0) > 0.3:
        scores["lateral_movement"] += 0.2

    # Device spoofing: unknown device fingerprint is the primary signal
    if dev_novelty > 0.5 and geo_dev < 0.3:
        scores["device_spoofing"] += 0.7
    if dev_novelty > 0.5:
        scores["device_spoofing"] += 0.2

    # Low-and-slow exfiltration: gradually increasing duration + novel resources
    if dur_dev > 0.3 and res_novelty > 0.3 and row.get("session_duration", 0) > 50:
        scores["low_and_slow"] += 0.6
    if dur_dev > 0.4 and row.get("session_duration", 0) > 100:
        scores["low_and_slow"] += 0.3

    # Insider drift: moderate across multiple features (not extreme in any one)
    profile_dev = row.get("profile_deviation_score", 0)
    if hour_dev > 0.3 and profile_dev > 0.15:
        scores["insider_drift"] += 0.4
    if hour_dev > 0.2 and res_novelty > 0.2 and dur_dev > 0.2:
        scores["insider_drift"] += 0.3
    if profile_dev > 0.2 and max(geo_dev, dev_novelty) < 0.3:
        scores["insider_drift"] += 0.2

    # Pick the highest-scoring type
    best_type = max(scores, key=scores.get)
    best_score = scores[best_type]

    if best_score < 0.3:
        return "unclassified"
    return best_type


# ── Reason string generation (FR-4.2) ────────────────────────────────

def generate_reason_string(row: dict) -> str:
    """
    Build a plain-language reason string naming the top 2-3
    contributing features.
    """
    # Rank features by their deviation score
    feature_scores = []
    for feat_key, human_name in FEATURE_NAMES.items():
        val = row.get(feat_key, 0)
        if val and val > 0.1:
            feature_scores.append((human_name, val))

    # Sort by score descending
    feature_scores.sort(key=lambda x: -x[1])

    # Take top 2-3
    top_features = feature_scores[:3]

    if not top_features:
        return "Flagged due to elevated overall risk score"

    feature_parts = [f[0] for f in top_features]
    if len(feature_parts) == 1:
        return f"Flagged due to {feature_parts[0]}"
    elif len(feature_parts) == 2:
        return f"Flagged due to {feature_parts[0]} + {feature_parts[1]}"
    else:
        return f"Flagged due to {feature_parts[0]}, {feature_parts[1]}, + {feature_parts[2]}"


# ── Main enrichment pipeline ─────────────────────────────────────────

def enrich_alerts(data_dir: str = "data"):
    """
    Enrich alerts with anomaly type classification, reason strings,
    and ATT&CK tags.
    """
    data_path = Path(data_dir)
    explain_path = Path(__file__).parent

    print("=" * 60)
    print("  Vigil -- Explainability & Classification")
    print("=" * 60)

    # Load alerts
    alerts_df = pd.read_parquet(data_path / "alerts.parquet")
    print(f"  Alerts to enrich: {len(alerts_df):,}")

    # Load ATT&CK mapping
    with open(explain_path / "attack_mapping.json") as f:
        attack_map = json.load(f)

    # Classify and generate reasons for each alert
    anomaly_types = []
    reason_strings = []
    attck_ids = []
    attck_names = []
    attck_tactics = []

    for _, row in alerts_df.iterrows():
        row_dict = row.to_dict()

        # Classify anomaly type
        anom_type = classify_anomaly_type(row_dict)
        anomaly_types.append(anom_type)

        # Generate reason string
        reason = generate_reason_string(row_dict)
        reason_strings.append(reason)

        # ATT&CK lookup
        mapping = attack_map.get(anom_type, attack_map.get("normal", {}))
        attck_ids.append(mapping.get("technique_id"))
        attck_names.append(mapping.get("technique_name"))
        attck_tactics.append(mapping.get("tactic"))

    alerts_df["anomaly_type"] = anomaly_types
    alerts_df["reason_string"] = reason_strings
    alerts_df["attck_id"] = attck_ids
    alerts_df["attck_name"] = attck_names
    alerts_df["attck_tactic"] = attck_tactics

    # Save enriched alerts
    alerts_df.to_parquet(data_path / "alerts_enriched.parquet", index=False)

    # Summary
    type_counts = pd.Series(anomaly_types).value_counts()
    print()
    print("-" * 60)
    print("  ENRICHMENT SUMMARY")
    print("-" * 60)
    print(f"  Total alerts enriched: {len(alerts_df):,}")
    print()
    print("  Anomaly type distribution:")
    for atype, count in type_counts.items():
        atk = attack_map.get(atype, {})
        tid = atk.get("technique_id", "N/A")
        print(f"    {atype:<25s} {count:>5}  ({tid})")
    print()
    print("  Sample reason strings:")
    for _, row in alerts_df.head(5).iterrows():
        print(f"    [{row['anomaly_type']}] {row['reason_string']}")
    print("-" * 60)

    return alerts_df


def main():
    parser = argparse.ArgumentParser(description="Vigil Explainability Pipeline")
    parser.add_argument("--data-dir", type=str, default="data")
    args = parser.parse_args()
    enrich_alerts(data_dir=args.data_dir)


if __name__ == "__main__":
    main()
