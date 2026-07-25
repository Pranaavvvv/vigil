"""
Vigil -- GRU Sequence Anomaly Detector
=======================================
Implements FR-3.1: per-session anomaly scoring via a GRU
that learns to predict the next session's features from
each entity's history. Prediction error = anomaly score.

Usage:
    python -m detection.sequence_model --data-dir data
"""

import argparse
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader


# ── Feature encoding ─────────────────────────────────────────────────

def encode_sessions(sessions_df: pd.DataFrame) -> tuple:
    """
    Encode raw session features into numerical vectors for the GRU.

    Features per session (11-dim):
      0: hour_of_day (0-23, normalized to 0-1)
      1: day_of_week (0-6, normalized to 0-1)
      2: session_duration (log-normalized)
      3: geo_lat (normalized)
      4: geo_lng (normalized)
      5-7: auth_method (one-hot, 3 dims)
      8: resource_hash (hashed to 0-1)
      9: device_hash (hashed to 0-1)
      10: command_count (normalized)
    """
    # Build lookup tables for categorical encoding
    auth_methods = sorted(sessions_df["auth_method"].unique())
    auth_to_idx = {a: i for i, a in enumerate(auth_methods)}
    n_auth = len(auth_methods)

    records = []
    for _, row in sessions_df.iterrows():
        ts = pd.Timestamp(row["timestamp"])
        hour = (ts.hour + ts.minute / 60.0) / 24.0
        dow = ts.dayofweek / 6.0
        dur = np.log1p(max(float(row["session_duration"]), 0))

        geo_parts = str(row["geo_location"]).split(",")
        lat = float(geo_parts[0]) / 90.0 if len(geo_parts) == 2 else 0.0
        lng = float(geo_parts[1]) / 180.0 if len(geo_parts) == 2 else 0.0

        # Auth one-hot (3 dims)
        auth_vec = [0.0] * min(n_auth, 3)
        idx = auth_to_idx.get(row["auth_method"], 0)
        if idx < len(auth_vec):
            auth_vec[idx] = 1.0

        # Resource and device as hashed values
        res_hash = (hash(row["resource_accessed"]) % 10000) / 10000.0
        dev_hash = (hash(row["device_fingerprint"]) % 10000) / 10000.0

        # Command count
        try:
            cmds = json.loads(row["command_sequence"])
            cmd_count = len(cmds) / 15.0  # normalize
        except (json.JSONDecodeError, TypeError):
            cmd_count = 0.0

        feat = [hour, dow, dur, lat, lng] + auth_vec[:3] + [res_hash, dev_hash, cmd_count]
        # Pad to 11 dims if auth has < 3 categories
        while len(feat) < 11:
            feat.append(0.0)
        records.append(feat[:11])

    return np.array(records, dtype=np.float32)


class EntitySequenceDataset(Dataset):
    """
    Creates variable-length sequences per entity.
    Each sample: (input_sequence, target_sequence) for next-step prediction.
    """
    def __init__(self, features: np.ndarray, entity_ids: np.ndarray,
                 max_seq_len: int = 50):
        self.sequences = []
        self.targets = []

        # Group by entity
        unique_entities = np.unique(entity_ids)
        for eid in unique_entities:
            mask = entity_ids == eid
            entity_feats = features[mask]
            if len(entity_feats) < 3:
                continue

            # Truncate to max_seq_len for memory
            if len(entity_feats) > max_seq_len:
                # Use last max_seq_len sessions
                entity_feats = entity_feats[-max_seq_len:]

            # Input: sessions 0..n-2, Target: sessions 1..n-1
            self.sequences.append(torch.tensor(entity_feats[:-1]))
            self.targets.append(torch.tensor(entity_feats[1:]))

    def __len__(self):
        return len(self.sequences)

    def __getitem__(self, idx):
        return self.sequences[idx], self.targets[idx]


def collate_fn(batch):
    """Pad sequences to same length within batch."""
    seqs, targets = zip(*batch)
    lengths = [len(s) for s in seqs]
    max_len = max(lengths)
    feat_dim = seqs[0].shape[1]

    padded_seqs = torch.zeros(len(seqs), max_len, feat_dim)
    padded_targets = torch.zeros(len(seqs), max_len, feat_dim)
    mask = torch.zeros(len(seqs), max_len, dtype=torch.bool)

    for i, (s, t) in enumerate(zip(seqs, targets)):
        padded_seqs[i, :len(s)] = s
        padded_targets[i, :len(t)] = t
        mask[i, :len(s)] = True

    return padded_seqs, padded_targets, mask


# ── GRU Model ────────────────────────────────────────────────────────

class SessionGRU(nn.Module):
    """
    GRU-based next-session predictor.
    Prediction error (MSE per timestep) is the anomaly score.
    """
    def __init__(self, input_dim: int = 11, hidden_dim: int = 64,
                 num_layers: int = 2, dropout: float = 0.2):
        super().__init__()
        self.gru = nn.GRU(input_dim, hidden_dim, num_layers=num_layers,
                          batch_first=True, dropout=dropout if num_layers > 1 else 0.0)
        self.fc = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, input_dim),
        )

    def forward(self, x):
        out, _ = self.gru(x)
        return self.fc(out)


def train_gru(data_dir: str = "data", epochs: int = 15, lr: float = 1e-3,
              batch_size: int = 64, hidden_dim: int = 64):
    """Train the GRU on normal sessions and score all sessions."""
    data_path = Path(data_dir)

    print("=" * 60)
    print("  Vigil -- GRU Sequence Model Training")
    print("=" * 60)

    # Load data
    sessions_df = pd.read_parquet(data_path / "sessions.parquet")
    labels_df = pd.read_parquet(data_path / "labels.parquet")

    # Sort by entity + time for proper sequence ordering
    sessions_df = sessions_df.sort_values(["entity_id", "timestamp"]).reset_index(drop=True)
    labels_df = labels_df.set_index("session_id")

    print(f"  Sessions: {len(sessions_df):,}")

    # Encode features
    print("  Encoding features...")
    features = encode_sessions(sessions_df)
    entity_ids = sessions_df["entity_id"].values
    session_ids = sessions_df["session_id"].values

    # Split: train on NORMAL sessions only (anomaly labels not used in training)
    normal_mask = sessions_df["session_id"].isin(
        labels_df[labels_df["label"] == 0].index
    ).values
    train_features = features[normal_mask]
    train_entity_ids = entity_ids[normal_mask]

    print(f"  Training on {normal_mask.sum():,} normal sessions")

    # Dataset
    dataset = EntitySequenceDataset(train_features, train_entity_ids, max_seq_len=50)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True,
                        collate_fn=collate_fn, num_workers=0)

    # Model
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = SessionGRU(input_dim=features.shape[1], hidden_dim=hidden_dim).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    criterion = nn.MSELoss(reduction="none")

    # Train
    print(f"  Training for {epochs} epochs on {device}...")
    for epoch in range(epochs):
        model.train()
        total_loss = 0.0
        n_batches = 0
        for seqs, targets, mask in loader:
            seqs, targets, mask = seqs.to(device), targets.to(device), mask.to(device)
            optimizer.zero_grad()
            preds = model(seqs)
            loss = criterion(preds, targets)
            loss = (loss * mask.unsqueeze(-1)).sum() / mask.sum()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            total_loss += loss.item()
            n_batches += 1
        avg_loss = total_loss / max(n_batches, 1)
        if (epoch + 1) % 5 == 0 or epoch == 0:
            print(f"    Epoch {epoch+1:>3d}/{epochs}: loss={avg_loss:.6f}")

    # Save model
    model_path = data_path / "gru_model.pt"
    torch.save(model.state_dict(), model_path)
    print(f"  Model saved to {model_path}")

    # Score ALL sessions (inference)
    print("  Scoring all sessions...")
    model.eval()
    sequence_scores = np.zeros(len(sessions_df), dtype=np.float32)

    # Score per entity: prediction error on their full sequence
    unique_entities = np.unique(entity_ids)
    with torch.no_grad():
        for eid in unique_entities:
            mask = entity_ids == eid
            idx = np.where(mask)[0]
            if len(idx) < 2:
                sequence_scores[idx] = 0.5  # Default for single-session entities
                continue

            ent_feats = features[idx]
            # Run through model
            inp = torch.tensor(ent_feats[:-1]).unsqueeze(0).to(device)
            pred = model(inp).squeeze(0).cpu().numpy()
            actual = ent_feats[1:]

            # Per-session MSE
            errors = np.mean((pred - actual) ** 2, axis=1)
            # Normalize to 0-1
            if errors.max() > errors.min():
                errors = (errors - errors.min()) / (errors.max() - errors.min())

            # First session gets median score
            sequence_scores[idx[0]] = float(np.median(errors)) if len(errors) > 0 else 0.5
            sequence_scores[idx[1:]] = errors

    # Save scores
    score_df = pd.DataFrame({
        "session_id": session_ids,
        "entity_id": entity_ids,
        "sequence_score": sequence_scores,
    })
    score_df.to_parquet(data_path / "sequence_scores.parquet", index=False)

    # Summary
    print()
    print("-" * 60)
    print("  SEQUENCE MODEL SUMMARY")
    print("-" * 60)
    print(f"  Score distribution:")
    print(f"    Mean:  {sequence_scores.mean():.4f}")
    print(f"    Std:   {sequence_scores.std():.4f}")
    print(f"    P50:   {np.percentile(sequence_scores, 50):.4f}")
    print(f"    P95:   {np.percentile(sequence_scores, 95):.4f}")
    print(f"    P99:   {np.percentile(sequence_scores, 99):.4f}")
    print(f"    Max:   {sequence_scores.max():.4f}")

    # Check if anomalies score higher
    session_id_to_idx = {sid: i for i, sid in enumerate(session_ids)}
    anom_scores = []
    norm_scores = []
    for sid, row in labels_df.iterrows():
        if sid in session_id_to_idx:
            idx = session_id_to_idx[sid]
            if row["label"] == 1:
                anom_scores.append(sequence_scores[idx])
            else:
                norm_scores.append(sequence_scores[idx])

    print(f"  Normal mean score:    {np.mean(norm_scores):.4f}")
    print(f"  Anomalous mean score: {np.mean(anom_scores):.4f}")
    print(f"  Separation ratio:     {np.mean(anom_scores) / max(np.mean(norm_scores), 1e-6):.2f}x")
    print("-" * 60)

    return score_df


def main():
    parser = argparse.ArgumentParser(description="Vigil GRU Sequence Model")
    parser.add_argument("--data-dir", type=str, default="data")
    parser.add_argument("--epochs", type=int, default=15)
    parser.add_argument("--hidden-dim", type=int, default=64)
    args = parser.parse_args()
    train_gru(data_dir=args.data_dir, epochs=args.epochs, hidden_dim=args.hidden_dim)


if __name__ == "__main__":
    main()
