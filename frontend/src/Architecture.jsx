import React from 'react';

export default function Architecture() {
  return (
    <div style={{ paddingBottom: '40px' }}>
      <div className="page-header">
        <h2>System Architecture & ML Pipeline</h2>
        <p>A deep dive into Vigil's AI-powered threat detection engine</p>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
        
        {/* Executive Summary */}
        <div className="card">
          <div className="card-title" style={{ marginBottom: '16px' }}>1. The Vigil Philosophy</div>
          <p style={{ lineHeight: '1.6', color: 'var(--text-secondary)' }}>
            Traditional security systems rely on rigid, signature-based rules that fail against novel, zero-day, or "low-and-slow" intrusions. Vigil takes a fundamentally different approach: <strong>Behavioral Anomaly Detection</strong>. By learning the normal rhythms, connection graphs, and sequential patterns of every user and service account, Vigil detects deviations from the norm. This domain-agnostic approach works equally well for cloud infrastructure, IT networks, and OT/IoT edge environments.
          </p>
        </div>

        {/* Pipeline Overview */}
        <div className="card">
          <div className="card-title" style={{ marginBottom: '16px' }}>2. The Tri-Pillar ML Pipeline</div>
          <p style={{ lineHeight: '1.6', color: 'var(--text-secondary)', marginBottom: '16px' }}>
            Vigil evaluates every session through three independent, specialized machine learning pillars before fusing them into a final risk verdict.
          </p>
          
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '20px', marginTop: '20px' }}>
            <div style={{ padding: '16px', background: 'var(--bg-secondary)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-default)' }}>
              <h4 style={{ color: 'var(--accent-emerald)', marginBottom: '8px' }}>Pillar A: Statistical Profiling</h4>
              <p style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: '1.5' }}>
                <strong>Method:</strong> Dynamic Baseline Matrix (Z-Score & KDE)<br/><br/>
                <strong>How it works:</strong> Tracks geospatial locations, operating hours, and device novelties. It calculates probability density for numerical features and tracks categorical novelty (e.g. seeing a MAC address for the first time).<br/><br/>
                <strong>Targets:</strong> Credential Stuffing, Impossible Travel.
              </p>
            </div>

            <div style={{ padding: '16px', background: 'var(--bg-secondary)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-default)' }}>
              <h4 style={{ color: 'var(--accent-cyan)', marginBottom: '8px' }}>Pillar B: Sequential Mining</h4>
              <p style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: '1.5' }}>
                <strong>Method:</strong> Markov Chains / Sequence Modeling<br/><br/>
                <strong>How it works:</strong> Evaluates the exact sequence of API calls or network requests. Attackers exploring a system (reconnaissance) leave sequential footprints that deviate from standard automated scripts or normal user workflows.<br/><br/>
                <strong>Targets:</strong> Low-and-Slow attacks, Insider Drift.
              </p>
            </div>

            <div style={{ padding: '16px', background: 'var(--bg-secondary)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-default)' }}>
              <h4 style={{ color: 'var(--accent-amber)', marginBottom: '8px' }}>Pillar C: Graph Neural Networks</h4>
              <p style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: '1.5' }}>
                <strong>Method:</strong> Graph Convolutional Autoencoder (GCN)<br/><br/>
                <strong>How it works:</strong> Models the entire network as a graph (Entities = Nodes, Access = Edges). The GCN performs unsupervised link prediction. If an edge (access attempt) has a high reconstruction error, it means the topology of that connection is highly abnormal.<br/><br/>
                <strong>Targets:</strong> Lateral Movement, Privilege Escalation.
              </p>
            </div>
          </div>
        </div>

        {/* Fusion Engine */}
        <div className="card">
          <div className="card-title" style={{ marginBottom: '16px' }}>3. The Gradient Boosting Fusion Engine</div>
          <p style={{ lineHeight: '1.6', color: 'var(--text-secondary)' }}>
            <strong>Algorithm:</strong> Extreme Gradient Boosting (XGBoost)<br/><br/>
            Instead of relying on a simple weighted average, Vigil feeds the outputs of the three pillars (Profile Score, Sequence Score, Graph Score) alongside raw session metadata into an XGBoost classifier. The Fusion Engine learns complex, non-linear relationships between the pillars. For example, it learns that a slight geographic anomaly combined with a high Graph reconstruction error is incredibly indicative of compromised credentials being used for Lateral Movement.
            <br/><br/>
            The Fusion model outputs two things:
          </p>
          <ul style={{ paddingLeft: '24px', marginTop: '12px', lineHeight: '1.6', color: 'var(--text-secondary)' }}>
            <li><strong>Risk Score (0.0 - 1.0):</strong> The calibrated probability that the session is malicious.</li>
            <li><strong>Anomaly Classification:</strong> Multi-class categorization into specific MITRE ATT&CK tactics (e.g., Brute Force, Device Spoofing).</li>
          </ul>
        </div>

        {/* Efficiency & Scalability */}
        <div className="card">
          <div className="card-title" style={{ marginBottom: '16px' }}>4. Efficiency & Scalability</div>
          <p style={{ lineHeight: '1.6', color: 'var(--text-secondary)' }}>
            Vigil is designed for high-throughput, low-latency environments like SOC (Security Operations Centers):
          </p>
          <ul style={{ paddingLeft: '24px', marginTop: '12px', lineHeight: '1.6', color: 'var(--text-secondary)' }}>
            <li><strong>O(1) Profile Lookups:</strong> Statistical baselines are pre-computed and stored in rapid-access memory architectures, allowing O(1) latency for evaluating Pillar A.</li>
            <li><strong>Sparse Matrix Math:</strong> The Graph Convolutional Network (GCN) is implemented using optimized sparse matrix multiplications in PyTorch, avoiding the memory overhead of dense graph representations.</li>
            <li><strong>Parquet Data Lake:</strong> Logs and embeddings are stored in columnar Apache Parquet format, allowing rapid analytical querying and partitioned batch-retraining without stalling the real-time inference pipeline.</li>
            <li><strong>Cold-Start Resilience:</strong> For new users with no baseline, Vigil falls back to <em>Cohort-Level Baselines</em> (e.g., comparing a new HR employee against the aggregate behavior of the HR department) to prevent false positives.</li>
          </ul>
        </div>

      </div>
    </div>
  );
}
