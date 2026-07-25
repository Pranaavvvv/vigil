"""
Vigil -- Fusion Model
======================
Implements FR-3.3 and FR-3.4: fuses sequence_score, graph_score,
and profile_deviation_score into a single 0-100 risk score.

Uses a gradient-boosted classifier (sklearn) with class-imbalance
handling via class weights.

Usage:
    python -m detection.fusion --data-dir data
"""

import argparse
import json
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import (
    precision_recall_curve,
    average_precision_score,
    classification_report,
    confusion_matrix,
)
from sklearn.model_selection import train_test_split


def prepare_features(data_dir: str = "data") -> tuple:
    """Load and merge all score components."""
    data_path = Path(data_dir)

    # Load all score sources
    deviations = pd.read_parquet(data_path / "deviations.parquet")
    seq_scores = pd.read_parquet(data_path / "sequence_scores.parquet")
    graph_scores = pd.read_parquet(data_path / "graph_scores.parquet")
    
    # Try to load GCN scores if they exist
    try:
        gcn_scores = pd.read_parquet(data_path / "gcn_scores.parquet")
    except FileNotFoundError:
        gcn_scores = pd.DataFrame(columns=["session_id", "gcn_score"])

    labels = pd.read_parquet(data_path / "labels.parquet")
    sessions = pd.read_parquet(data_path / "sessions.parquet")

    # Merge on session_id
    merged = deviations[["session_id", "entity_id", "profile_deviation_score",
                          "hour_deviation", "geo_deviation", "resource_novelty",
                          "duration_deviation", "device_novelty", "baseline_status"]].copy()

    merged = merged.merge(
        seq_scores[["session_id", "sequence_score"]],
        on="session_id", how="left"
    )
    merged = merged.merge(
        graph_scores[["session_id", "graph_score", "degree_change",
                       "new_edge_ratio", "neighborhood_overlap",
                       "suspicion_propagation"]],
        on="session_id", how="left"
    )
    merged = merged.merge(
        labels[["session_id", "label", "pattern_name"]],
        on="session_id", how="left"
    )

    # Merge GCN scores
    merged = merged.merge(
        gcn_scores[["session_id", "gcn_score"]],
        on="session_id", how="left"
    )

    # Add session-level features from raw data
    merged = merged.merge(
        sessions[["session_id", "session_duration", "timestamp"]],
        on="session_id", how="left"
    )

    # Fill NaN scores with 0
    score_cols = ["sequence_score", "graph_score", "profile_deviation_score",
                  "degree_change", "new_edge_ratio", "neighborhood_overlap",
                  "suspicion_propagation", "hour_deviation", "geo_deviation",
                  "resource_novelty", "duration_deviation", "device_novelty", "gcn_score"]
    merged[score_cols] = merged[score_cols].fillna(0.0)

    # Binary label
    merged["label"] = merged["label"].fillna(0).astype(int)

    return merged, score_cols


def train_fusion(data_dir: str = "data"):
    """Train the fusion classifier and produce risk scores."""
    data_path = Path(data_dir)

    print("=" * 60)
    print("  Vigil -- Fusion Model Training")
    print("=" * 60)

    merged, feature_cols = prepare_features(data_dir)
    print(f"  Total samples: {len(merged):,}")
    print(f"  Anomalous:     {merged['label'].sum():,} ({merged['label'].mean()*100:.2f}%)")
    print(f"  Features:      {len(feature_cols)}")

    X = merged[feature_cols].values
    y = merged["label"].values

    # Train/test split (stratified)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # Class weights to handle imbalance (FR-3.4)
    n_neg = (y_train == 0).sum()
    n_pos = (y_train == 1).sum()
    scale_pos_weight = n_neg / max(n_pos, 1)
    sample_weights = np.where(y_train == 1, scale_pos_weight, 1.0)

    print(f"  Class weight (pos): {scale_pos_weight:.2f}")
    print(f"  Training ({len(X_train):,} samples)...")

    # Gradient Boosted Classifier
    clf = GradientBoostingClassifier(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.1,
        subsample=0.8,
        random_state=42,
    )
    clf.fit(X_train, y_train, sample_weight=sample_weights)

    # Save model
    model_path = data_path / "fusion_model.pkl"
    with open(model_path, "wb") as f:
        pickle.dump(clf, f)
    print(f"  Model saved to {model_path}")

    # Predict probabilities on ALL data
    probs = clf.predict_proba(X)[:, 1]
    risk_scores = (probs * 100).clip(0, 100).round(1)

    merged["risk_score"] = risk_scores
    merged["sequence_score_pct"] = merged["sequence_score"] * 100
    merged["graph_score_pct"] = merged["graph_score"] * 100
    merged["profile_score_pct"] = merged["profile_deviation_score"] * 100

    # Feature importances
    importances = dict(zip(feature_cols, clf.feature_importances_))
    sorted_imp = sorted(importances.items(), key=lambda x: -x[1])

    # Evaluation on test set
    y_pred_test = clf.predict(X_test)
    y_prob_test = clf.predict_proba(X_test)[:, 1]
    pr_auc = average_precision_score(y_test, y_prob_test)

    # Alert budget: top 1% of events
    n_alert_budget = max(1, int(len(merged) * 0.01))
    top_indices = np.argsort(-risk_scores)[:n_alert_budget]
    alert_budget_labels = merged.iloc[top_indices]["label"].values
    precision_at_budget = alert_budget_labels.sum() / len(alert_budget_labels)
    fpr_at_budget = (1 - alert_budget_labels).sum() / max((y == 0).sum(), 1)

    # Precision/recall curve
    precision_vals, recall_vals, thresholds = precision_recall_curve(y, probs)

    # Save alerts (sessions above alert budget threshold)
    risk_threshold = float(np.sort(risk_scores)[-n_alert_budget])
    alert_mask = risk_scores >= risk_threshold

    alerts_df = merged[alert_mask].copy()
    alerts_df["alert_id"] = [f"alert-{i:05d}" for i in range(len(alerts_df))]
    alerts_df["status"] = "new"

    # Save all outputs
    # Full scored dataset
    merged.to_parquet(data_path / "scored_sessions.parquet", index=False)

    # Alerts
    alerts_df.to_parquet(data_path / "alerts.parquet", index=False)

    # Metrics
    metrics = {
        "pr_auc": float(pr_auc),
        "precision_at_budget": float(precision_at_budget),
        "fpr_at_budget": float(fpr_at_budget),
        "alert_budget_size": int(n_alert_budget),
        "risk_threshold": float(risk_threshold),
        "n_alerts": int(len(alerts_df)),
        "feature_importances": {k: float(v) for k, v in sorted_imp},
        "classification_report": classification_report(y_test, y_pred_test, output_dict=True),
    }

    # Confusion matrix on all data (for anomaly types later)
    metrics["confusion_matrix"] = confusion_matrix(y, (risk_scores >= risk_threshold).astype(int)).tolist()

    with open(data_path / "metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

    # Summary
    print()
    print("-" * 60)
    print("  FUSION MODEL RESULTS")
    print("-" * 60)
    print(f"  PR-AUC:                 {pr_auc:.4f}")
    print(f"  Precision @ 1% budget:  {precision_at_budget:.4f}")
    print(f"  FPR @ budget:           {fpr_at_budget:.6f}")
    print(f"  Alert threshold:        {risk_threshold:.1f}")
    print(f"  Total alerts:           {len(alerts_df):,}")
    print()
    print(f"  Risk score distribution:")
    print(f"    Mean:  {risk_scores.mean():.1f}")
    print(f"    P50:   {np.percentile(risk_scores, 50):.1f}")
    print(f"    P95:   {np.percentile(risk_scores, 95):.1f}")
    print(f"    P99:   {np.percentile(risk_scores, 99):.1f}")
    print(f"    Max:   {risk_scores.max():.1f}")
    print()
    print(f"  Top feature importances:")
    for feat, imp in sorted_imp[:5]:
        print(f"    {feat:<30s} {imp:.4f}")
    print()
    print(f"  Test set classification report:")
    report = classification_report(y_test, y_pred_test)
    for line in report.strip().split("\n"):
        print(f"    {line}")
    print("-" * 60)

    return alerts_df, metrics


def main():
    parser = argparse.ArgumentParser(description="Vigil Fusion Model")
    parser.add_argument("--data-dir", type=str, default="data")
    args = parser.parse_args()
    train_fusion(data_dir=args.data_dir)


if __name__ == "__main__":
    main()
