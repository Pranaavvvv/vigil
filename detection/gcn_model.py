"""
Vigil -- Graph Convolutional Network (GCN) Anomaly Detector
===========================================================
Trains an unsupervised Graph Autoencoder (GAE) to detect Lateral Movement.
It learns topological embeddings for Entities and Resources.
Low probability edges are flagged as anomalies.
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F

class GCNLayer(nn.Module):
    """Simple GCN layer: A * X * W"""
    def __init__(self, in_features, out_features):
        super().__init__()
        self.linear = nn.Linear(in_features, out_features, bias=False)

    def forward(self, x, adj):
        support = self.linear(x)
        output = torch.sparse.mm(adj, support)
        return output

class GraphAutoencoder(nn.Module):
    def __init__(self, num_nodes, hidden_dim=64, embed_dim=32):
        super().__init__()
        # Use an embedding layer as initial node features
        self.node_features = nn.Embedding(num_nodes, hidden_dim)
        self.gcn1 = GCNLayer(hidden_dim, hidden_dim)
        self.gcn2 = GCNLayer(hidden_dim, embed_dim)
        self.dropout = nn.Dropout(0.2)

    def forward(self, adj):
        x = self.node_features.weight
        x = F.relu(self.gcn1(x, adj))
        x = self.dropout(x)
        z = self.gcn2(x, adj)
        return z

def build_normalized_adjacency(num_nodes, edges):
    """Builds D^{-1/2} A D^{-1/2} normalized adjacency matrix."""
    # A = A + I
    indices = torch.tensor(edges, dtype=torch.long).t()
    if len(edges) == 0:
        indices = torch.empty((2, 0), dtype=torch.long)
    values = torch.ones(indices.shape[1], dtype=torch.float32)
    
    # Add self loops
    self_loops = torch.arange(num_nodes, dtype=torch.long).unsqueeze(0).repeat(2, 1)
    self_values = torch.ones(num_nodes, dtype=torch.float32)
    
    indices = torch.cat([indices, self_loops], dim=1)
    values = torch.cat([values, self_values], dim=0)
    
    # Create sparse A
    A = torch.sparse_coo_tensor(indices, values, size=(num_nodes, num_nodes)).coalesce()
    
    # Calculate D
    degrees = torch.sparse.sum(A, dim=1).to_dense()
    d_inv_sqrt = torch.pow(degrees, -0.5)
    d_inv_sqrt[torch.isinf(d_inv_sqrt)] = 0.0
    
    # Multiply D^{-1/2} A D^{-1/2}
    # For a sparse matrix A, scaling rows and cols is:
    # A_norm[i,j] = A[i,j] * d_inv_sqrt[i] * d_inv_sqrt[j]
    indices = A.indices()
    values = A.values()
    row, col = indices[0], indices[1]
    norm_values = values * d_inv_sqrt[row] * d_inv_sqrt[col]
    
    return torch.sparse_coo_tensor(indices, norm_values, size=(num_nodes, num_nodes)).coalesce()

def train_gcn(data_dir: str = "data", epochs: int = 50, lr: float = 0.01):
    data_path = Path(data_dir)
    print("=" * 60)
    print("  Vigil -- GCN Topology Model Training")
    print("=" * 60)

    # 1. Load Data
    sessions_df = pd.read_parquet(data_path / "sessions.parquet")
    labels_df = pd.read_parquet(data_path / "labels.parquet")
    
    # Use normal sessions for training baseline topology
    normal_sids = labels_df[labels_df["label"] == 0]["session_id"].values
    train_sessions = sessions_df[sessions_df["session_id"].isin(normal_sids)]
    
    # 2. Build Bipartite Graph (Entities <-> Resources)
    unique_entities = sessions_df["entity_id"].unique()
    unique_resources = sessions_df["resource_accessed"].unique()
    
    entity_to_id = {ent: i for i, ent in enumerate(unique_entities)}
    resource_to_id = {res: i + len(unique_entities) for i, res in enumerate(unique_resources)}
    num_nodes = len(unique_entities) + len(unique_resources)
    
    print(f"  Nodes: {num_nodes:,} ({len(unique_entities):,} entities, {len(unique_resources):,} resources)")
    
    # Extract edges for training (undirected)
    train_edges = []
    for _, row in train_sessions.iterrows():
        u = entity_to_id[row["entity_id"]]
        v = resource_to_id[row["resource_accessed"]]
        train_edges.append([u, v])
        train_edges.append([v, u]) # undirected
        
    print(f"  Training edges: {len(train_edges):,}")
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    adj_norm = build_normalized_adjacency(num_nodes, train_edges).to(device)
    
    # 3. Model Setup
    model = GraphAutoencoder(num_nodes, hidden_dim=64, embed_dim=32).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    
    # Edge indices for positive training samples
    pos_edge_idx = torch.tensor(train_edges, dtype=torch.long).t().to(device)
    
    print(f"  Training for {epochs} epochs on {device}...")
    for epoch in range(epochs):
        model.train()
        optimizer.zero_grad()
        
        # Forward pass to get node embeddings
        z = model(adj_norm)
        
        # Positive edge scores (inner product of embeddings)
        u_pos, v_pos = pos_edge_idx[0], pos_edge_idx[1]
        pos_scores = (z[u_pos] * z[v_pos]).sum(dim=1)
        
        # Negative edge sampling
        neg_u = torch.randint(0, len(unique_entities), (len(u_pos),)).to(device)
        neg_v = torch.randint(len(unique_entities), num_nodes, (len(v_pos),)).to(device)
        neg_scores = (z[neg_u] * z[neg_v]).sum(dim=1)
        
        # Contrastive BCE Loss
        pos_loss = F.binary_cross_entropy_with_logits(pos_scores, torch.ones_like(pos_scores))
        neg_loss = F.binary_cross_entropy_with_logits(neg_scores, torch.zeros_like(neg_scores))
        loss = pos_loss + neg_loss
        
        loss.backward()
        optimizer.step()
        
        if (epoch + 1) % 10 == 0:
            print(f"    Epoch {epoch+1:>3d}/{epochs} | Loss: {loss.item():.4f}")

    # 4. Inference / Scoring ALL sessions
    print("  Scoring all sessions...")
    model.eval()
    with torch.no_grad():
        z = model(adj_norm)
        
    gcn_scores = []
    
    for _, row in sessions_df.iterrows():
        u = entity_to_id[row["entity_id"]]
        v = resource_to_id[row["resource_accessed"]]
        
        # Compute predicted probability of this edge
        u_emb = z[u].unsqueeze(0)
        v_emb = z[v].unsqueeze(0)
        score_logit = (u_emb * v_emb).sum().item()
        
        # Convert logit to probability
        edge_prob = 1.0 / (1.0 + np.exp(-score_logit))
        
        # Anomaly score is inverse of edge probability
        anomaly_score = 1.0 - edge_prob
        gcn_scores.append(anomaly_score)
        
    score_df = pd.DataFrame({
        "session_id": sessions_df["session_id"].values,
        "gcn_score": gcn_scores
    })
    
    # Save scores
    score_df.to_parquet(data_path / "gcn_scores.parquet", index=False)
    
    print()
    print("-" * 60)
    print("  GCN MODEL SUMMARY")
    print("-" * 60)
    print(f"  Mean Anomaly Score: {np.mean(gcn_scores):.4f}")
    print(f"  P99 Anomaly Score:  {np.percentile(gcn_scores, 99):.4f}")
    print("-" * 60)

    return score_df

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=str, default="data")
    parser.add_argument("--epochs", type=int, default=10)
    args = parser.parse_args()
    train_gcn(data_dir=args.data_dir, epochs=args.epochs)

if __name__ == "__main__":
    main()
