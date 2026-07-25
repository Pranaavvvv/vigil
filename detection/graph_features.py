"""
Vigil -- Graph-Based Anomaly Features
=======================================
Implements FR-3.2: entity-resource access graph features using networkx.
Computes per-session graph anomaly indicators:
  - Degree change vs baseline
  - New-edge ratio
  - Neighborhood overlap (Jaccard)
  - One-hop suspicion propagation

Usage:
    python -m detection.graph_features --data-dir data
"""

import argparse
from collections import defaultdict
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd


class AccessGraph:
    """
    Bipartite entity-resource access graph.
    Maintains a rolling baseline graph and computes per-session
    anomaly features by comparing current access against baseline.
    """

    def __init__(self, baseline_window_days: int = 30):
        self.baseline_window = baseline_window_days
        self.G_baseline = nx.Graph()  # Baseline graph (first N days)
        self.G_current = nx.Graph()   # Running graph
        self.entity_baseline_neighbors: dict[str, set] = {}  # entity -> {resources}
        self.entity_baseline_degree: dict[str, int] = {}
        self.flagged_entities: set = set()  # Already-flagged entities for suspicion propagation

    def build_baseline(self, sessions_df: pd.DataFrame, cutoff_date: str):
        """Build the baseline graph from sessions before cutoff_date."""
        baseline_sessions = sessions_df[sessions_df["timestamp"] < cutoff_date]

        for _, row in baseline_sessions.iterrows():
            eid = row["entity_id"]
            resource = row["resource_accessed"]
            self.G_baseline.add_edge(eid, f"res:{resource}")

        # Cache baseline neighborhoods
        for node in self.G_baseline.nodes():
            if not str(node).startswith("res:"):
                neighbors = set(self.G_baseline.neighbors(node))
                self.entity_baseline_neighbors[node] = neighbors
                self.entity_baseline_degree[node] = len(neighbors)

    def score_session(self, entity_id: str, resource: str,
                      session_entity_resources: dict) -> dict:
        """
        Compute graph-based anomaly features for a single session.
        """
        scores = {}
        res_node = f"res:{resource}"

        # Add edge to current graph
        self.G_current.add_edge(entity_id, res_node)

        baseline_neighbors = self.entity_baseline_neighbors.get(entity_id, set())
        baseline_degree = self.entity_baseline_degree.get(entity_id, 0)
        current_neighbors = set(self.G_current.neighbors(entity_id)) if entity_id in self.G_current else set()

        # 1. Degree change vs baseline
        current_degree = len(current_neighbors)
        if baseline_degree > 0:
            degree_change = (current_degree - baseline_degree) / baseline_degree
        else:
            degree_change = current_degree / max(current_degree, 1)
        scores["degree_change"] = min(max(degree_change, 0), 1.0)

        # 2. New-edge ratio: fraction of current edges not in baseline
        if current_neighbors:
            new_edges = current_neighbors - baseline_neighbors
            scores["new_edge_ratio"] = len(new_edges) / len(current_neighbors)
        else:
            scores["new_edge_ratio"] = 0.0

        # 3. Neighborhood overlap (Jaccard with baseline)
        if baseline_neighbors or current_neighbors:
            intersection = baseline_neighbors & current_neighbors
            union = baseline_neighbors | current_neighbors
            scores["neighborhood_overlap"] = 1.0 - (len(intersection) / len(union)) if union else 0.0
        else:
            scores["neighborhood_overlap"] = 0.0

        # 4. One-hop suspicion propagation
        # Check if any entities sharing this resource are flagged
        suspicion = 0.0
        if res_node in self.G_current:
            co_accessors = set(self.G_current.neighbors(res_node)) - {entity_id}
            flagged_co = co_accessors & self.flagged_entities
            if co_accessors:
                suspicion = len(flagged_co) / len(co_accessors)
        scores["suspicion_propagation"] = suspicion

        # Fused graph score
        weights = {
            "degree_change": 0.25,
            "new_edge_ratio": 0.30,
            "neighborhood_overlap": 0.25,
            "suspicion_propagation": 0.20,
        }
        fused = sum(scores[k] * weights[k] for k in weights)
        scores["graph_score"] = round(min(fused, 1.0), 4)

        return scores


def compute_graph_features(data_dir: str = "data"):
    """Main pipeline: build graph and score all sessions."""
    data_path = Path(data_dir)

    print("=" * 60)
    print("  Vigil -- Graph Feature Extraction")
    print("=" * 60)

    sessions_df = pd.read_parquet(data_path / "sessions.parquet")
    sessions_df = sessions_df.sort_values("timestamp").reset_index(drop=True)
    print(f"  Sessions: {len(sessions_df):,}")

    # Use first 30 days as baseline window
    min_date = pd.Timestamp(sessions_df["timestamp"].min())
    cutoff = (min_date + pd.Timedelta(days=30)).isoformat()
    print(f"  Baseline cutoff: {cutoff[:10]}")

    graph = AccessGraph()
    graph.build_baseline(sessions_df, cutoff)
    print(f"  Baseline graph: {graph.G_baseline.number_of_nodes()} nodes, "
          f"{graph.G_baseline.number_of_edges()} edges")

    # Track per-entity accumulated resources for the current window
    entity_session_resources = defaultdict(set)

    # Score all sessions
    print("  Scoring sessions...")
    records = []
    for i, (_, row) in enumerate(sessions_df.iterrows()):
        eid = row["entity_id"]
        resource = row["resource_accessed"]
        entity_session_resources[eid].add(resource)

        scores = graph.score_session(eid, resource, entity_session_resources)
        scores["session_id"] = row["session_id"]
        scores["entity_id"] = eid
        records.append(scores)

        if (i + 1) % 50000 == 0:
            print(f"    Scored {i+1:,} / {len(sessions_df):,} sessions")

    graph_df = pd.DataFrame(records)
    graph_df.to_parquet(data_path / "graph_scores.parquet", index=False)

    # Summary
    print()
    print("-" * 60)
    print("  GRAPH FEATURES SUMMARY")
    print("-" * 60)
    print(f"  Graph score distribution:")
    print(f"    Mean:  {graph_df['graph_score'].mean():.4f}")
    print(f"    Std:   {graph_df['graph_score'].std():.4f}")
    print(f"    P95:   {graph_df['graph_score'].quantile(0.95):.4f}")
    print(f"    P99:   {graph_df['graph_score'].quantile(0.99):.4f}")
    print(f"    Max:   {graph_df['graph_score'].max():.4f}")
    print("-" * 60)

    return graph_df


def main():
    parser = argparse.ArgumentParser(description="Vigil Graph Feature Extraction")
    parser.add_argument("--data-dir", type=str, default="data")
    args = parser.parse_args()
    compute_graph_features(data_dir=args.data_dir)


if __name__ == "__main__":
    main()
