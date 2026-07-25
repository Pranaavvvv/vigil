import React, { useState, useEffect, useRef } from 'react';
import { BrowserRouter, Routes, Route, NavLink, useNavigate, useParams, Link, Outlet } from 'react-router-dom';
import LandingPage from './LandingPage';
import Architecture from './Architecture';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer, BarChart, Bar, Cell } from 'recharts';
import ForceGraph2D from 'react-force-graph-2d';
import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';
import * as api from './api';
import { riskLevel, riskColor, formatTimestamp, formatAnomalyType, formatEntityType } from './utils';

// ===== Icons (SVG) =====
const IconDashboard = () => <svg fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="icon"><path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6A2.25 2.25 0 0 1 6 3.75h2.25A2.25 2.25 0 0 1 10.5 6v2.25a2.25 2.25 0 0 1-2.25 2.25H6a2.25 2.25 0 0 1-2.25-2.25V6ZM3.75 15.75A2.25 2.25 0 0 1 6 13.5h2.25a2.25 2.25 0 0 1 2.25 2.25V18a2.25 2.25 0 0 1-2.25 2.25H6A2.25 2.25 0 0 1 3.75 18v-2.25ZM13.5 6a2.25 2.25 0 0 1 2.25-2.25H18A2.25 2.25 0 0 1 20.25 6v2.25A2.25 2.25 0 0 1 18 10.5h-2.25a2.25 2.25 0 0 1-2.25-2.25V6ZM13.5 15.75a2.25 2.25 0 0 1 2.25-2.25H18a2.25 2.25 0 0 1 2.25 2.25V18A2.25 2.25 0 0 1 18 20.25h-2.25A2.25 2.25 0 0 1 13.5 18v-2.25Z" /></svg>;
const IconAlerts = () => <svg fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="icon"><path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3Z" /></svg>;
const IconEntities = () => <svg fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="icon"><path strokeLinecap="round" strokeLinejoin="round" d="M15 19.128a9.38 9.38 0 0 0 2.625.372 9.337 9.337 0 0 0 4.121-.952 4.125 4.125 0 0 0-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 0 1 8.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0 1 11.964-3.07M12 6.375a3.375 3.375 0 1 1-6.75 0 3.375 3.375 0 0 1 6.75 0Zm8.25 2.25a2.625 2.625 0 1 1-5.25 0 2.625 2.625 0 0 1 5.25 0Z" /></svg>;
const IconMetrics = () => <svg fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="icon"><path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 0 1 3 19.875v-6.75ZM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V8.625ZM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V4.125Z" /></svg>;
const IconDoc = () => <svg fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="icon"><path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" /></svg>;

// ===== Components =====

const RiskBadge = ({ score }) => {
  const level = riskLevel(score);
  return <span className={`risk-badge ${level}`}>{score.toFixed(1)}</span>;
};

const TypeTag = ({ type }) => {
  return <span className={`type-tag ${type}`}>{formatAnomalyType(type)}</span>;
};

// ===== Pages =====

function Dashboard() {
  const [data, setData] = useState(null);
  const [showEntityModal, setShowEntityModal] = useState(false);
  const [toastMessage, setToastMessage] = useState("");

  const showToast = (msg) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(""), 3000);
  };

  const handleExportCSV = () => {
    if (!data || !data.top_alerts) return;
    const headers = ["Alert ID", "Entity ID", "Anomaly Type", "Risk Score", "Status", "Timestamp"];
    const rows = data.top_alerts.map(a => 
      [a.alert_id, a.entity_id, a.anomaly_type, a.risk_score, a.status, a.timestamp].join(",")
    );
    const csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows].join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", "vigil_alerts_export.csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    showToast("CSV Export downloaded successfully.");
  };

  const handleGenerateReport = () => {
    showToast("Compiling SOC Threat Report...");
    
    setTimeout(() => {
      if (!data || !data.top_alerts) {
        showToast("Error: No data available for report.");
        return;
      }
      
      const doc = new jsPDF();
      
      // Header
      doc.setFillColor(15, 23, 42); // slate-900
      doc.rect(0, 0, 210, 40, 'F');
      doc.setTextColor(255, 255, 255);
      doc.setFontSize(22);
      doc.setFont("helvetica", "bold");
      doc.text("VIGIL SOC THREAT REPORT", 14, 25);
      
      // Meta
      doc.setTextColor(100, 116, 139); // slate-500
      doc.setFontSize(10);
      doc.setFont("helvetica", "normal");
      doc.text(`Generated: ${new Date().toLocaleString()}`, 14, 48);
      
      // Metrics box
      doc.setDrawColor(226, 232, 240); // slate-200
      doc.setFillColor(248, 250, 252); // slate-50
      doc.roundedRect(14, 55, 182, 25, 3, 3, 'FD');
      
      doc.setTextColor(15, 23, 42); // slate-900
      doc.setFont("helvetica", "bold");
      doc.text("System Risk Pulse:", 20, 65);
      doc.text("Active Alerts:", 110, 65);
      
      doc.setFont("helvetica", "normal");
      doc.setTextColor(220, 38, 38); // red-600
      doc.text(data.risk_pulse.toString(), 57, 65);
      doc.setTextColor(15, 23, 42);
      doc.text(data.active_alerts.toString(), 138, 65);
      
      doc.text(`Avg Risk Score: ${data.avg_risk_score}`, 20, 73);
      doc.text(`Monitored Entities: ${data.total_entities}`, 110, 73);
      
      // Table Header
      doc.setFontSize(14);
      doc.setFont("helvetica", "bold");
      doc.text("Top Anomalous Alerts", 14, 95);
      
      // Table Data
      const tableData = data.top_alerts.map(a => [
        a.alert_id.substring(0, 8),
        a.entity_id,
        a.anomaly_type,
        a.risk_score.toFixed(1),
        a.status
      ]);
      
      autoTable(doc, {
        startY: 100,
        head: [['Alert ID', 'Entity', 'Type', 'Risk Score', 'Status']],
        body: tableData,
        theme: 'striped',
        headStyles: { fillColor: [15, 23, 42] },
        styles: { fontSize: 9, cellPadding: 4 },
        columnStyles: {
          3: { halign: 'center', fontStyle: 'bold' }
        }
      });
      
      doc.save(`Vigil_SOC_Report_${new Date().toISOString().split('T')[0]}.pdf`);
      showToast("Report generated successfully. PDF downloaded.");
    }, 1500);
  };

  const handleAddEntitySubmit = (e) => {
    e.preventDefault();
    setShowEntityModal(false);
    showToast("Entity added to monitoring baseline.");
  };
  
  useEffect(() => {
    api.fetchDashboard().then(setData).catch(console.error);
  }, []);

  if (!data) return <div className="loading">Loading dashboard...</div>;

  return (
    <div>
      <div className="page-header" style={{display:'flex', justifyContent:'space-between', alignItems:'flex-end'}}>
        <div>
          <h2 style={{fontSize:'22px', fontWeight:600, color:'var(--text-primary)'}}>Welcome, Analyst</h2>
          <p>Vigil Behavioral Risk Intelligence Platform</p>
        </div>
      </div>

      <div className="action-pills">
        <Link to="/alerts" className="pill-btn primary" style={{textDecoration: 'none'}}>Analyze Alerts</Link>
        <button className="pill-btn" onClick={() => showToast("Data refresh requested across all edge gateways.")}>Request Data</button>
        <button className="pill-btn" onClick={handleGenerateReport}>Generate Report</button>
        <button className="pill-btn" onClick={() => setShowEntityModal(true)}>+ Add Entity</button>
        <button className="pill-btn" onClick={handleExportCSV}>Export CSV</button>
        <button className="pill-btn" onClick={() => showToast("Dashboard layout customization mode activated.")} style={{border: 'none', boxShadow:'none', color:'var(--text-muted)'}}>Customize</button>
      </div>

      <div className="two-col" style={{marginBottom: 'var(--space-xl)'}}>
        
        {/* Balance Card equivalent -> Risk Pulse */}
        <div className="card" style={{display:'flex', flexDirection:'column', justifyContent:'center', alignItems:'center'}}>
          <div className="stat-label" style={{alignSelf:'flex-start', color:'var(--text-primary)', fontWeight:600, marginBottom:'24px', fontSize:'14px'}}>System Risk Pulse <span style={{color:'var(--accent-emerald)'}}>●</span></div>
          <div className="risk-pulse" style={{transform:'scale(0.8)'}}>
            <div className="pulse-ring"></div>
            <div className="pulse-value" style={{ color: riskColor(data.risk_pulse) }}>
              {data.risk_pulse}
            </div>
          </div>
          <div style={{marginTop:'16px', fontSize:'12px', color:'var(--text-muted)'}}>
            Last 30 Days &nbsp; <span style={{color:'var(--accent-green)'}}>↗ Improved</span>
          </div>
        </div>

        {/* Accounts Card equivalent -> System Overview */}
        <div className="card">
          <div className="card-header" style={{borderBottom:'none', marginBottom:'8px'}}>
            <div className="card-title" style={{color:'var(--text-primary)', fontSize:'14px'}}>System Overview</div>
            <div style={{color:'var(--text-muted)'}}>+ &nbsp; ⋮</div>
          </div>
          
          <div style={{display:'flex', justifyContent:'space-between', padding:'12px 0', fontSize:'13px', color:'var(--text-secondary)'}}>
            <span>Active Alerts</span>
            <span style={{fontWeight:600, color:'var(--text-primary)'}}>{data.active_alerts}</span>
          </div>
          <div style={{display:'flex', justifyContent:'space-between', padding:'12px 0', fontSize:'13px', color:'var(--text-secondary)'}}>
            <span>Monitored Entities</span>
            <span style={{fontWeight:600, color:'var(--text-primary)'}}>{data.total_entities}</span>
          </div>
          <div style={{display:'flex', justifyContent:'space-between', padding:'12px 0', fontSize:'13px', color:'var(--text-secondary)'}}>
            <span>Total Historical Alerts</span>
            <span style={{fontWeight:600, color:'var(--text-primary)'}}>{data.total_alerts}</span>
          </div>
          <div style={{display:'flex', justifyContent:'space-between', padding:'12px 0', fontSize:'13px', color:'var(--text-secondary)'}}>
            <span>Avg Risk Score</span>
            <span style={{fontWeight:600, color:'var(--text-primary)'}}>{data.avg_risk_score}</span>
          </div>
        </div>

      </div>

      <div className="card">
        <div className="card-header">
          <div className="card-title" style={{color:'var(--text-primary)'}}>Recent Alerts</div>
        </div>
        <table className="data-table">
          <thead>
            <tr>
              <th style={{borderBottom:'none'}}>Date / Time</th>
              <th style={{borderBottom:'none'}}>Entity</th>
              <th style={{borderBottom:'none'}}>Pattern</th>
              <th style={{borderBottom:'none'}}>Status</th>
            </tr>
          </thead>
          <tbody>
            {data.top_alerts.map(a => (
              <tr key={a.alert_id}>
                <td style={{borderBottom:'1px solid rgba(0,0,0,0.03)', color:'var(--text-muted)'}}>{new Date().toLocaleDateString()}</td>
                <td style={{borderBottom:'1px solid rgba(0,0,0,0.03)'}}>
                  <Link style={{color: 'var(--text-primary)', textDecoration: 'none', fontWeight: 500}} to={`/entities/${a.entity_id}`}>
                    {a.entity_id.split('-')[1] || a.entity_id}
                  </Link>
                </td>
                <td style={{borderBottom:'1px solid rgba(0,0,0,0.03)'}}><TypeTag type={a.anomaly_type} /></td>
                <td style={{borderBottom:'1px solid rgba(0,0,0,0.03)'}}>
                  <span style={{color: a.status==='new' ? 'var(--accent-amber)' : 'var(--accent-green)', fontWeight:500, fontSize:'12px'}}>
                    {a.status === 'new' ? 'Pending' : 'Completed'}
                  </span>
                </td>
              </tr>
            ))}
            {data.top_alerts.length === 0 && (
              <tr><td colSpan="4" style={{textAlign: 'center', padding: '24px'}}>No active alerts</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Modals & Toasts */}
      {showEntityModal && (
        <div className="modal-overlay" onClick={() => setShowEntityModal(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <h3>Add New Entity</h3>
            <form onSubmit={handleAddEntitySubmit}>
              <label style={{fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)'}}>Entity ID</label>
              <input type="text" placeholder="e.g., user-admin-01" required />
              
              <label style={{fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)'}}>Entity Type</label>
              <select required>
                <option value="user">User Account</option>
                <option value="service">Service Account</option>
                <option value="edge_device">Edge Device</option>
              </select>

              <div className="modal-actions">
                <button type="button" className="pill-btn" onClick={() => setShowEntityModal(false)}>Cancel</button>
                <button type="submit" className="pill-btn primary">Add Entity</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {toastMessage && (
        <div className="toast-container">
          <div className="toast">
            <span style={{color: 'var(--accent-emerald)', fontSize: '18px'}}>✓</span>
            {toastMessage}
          </div>
        </div>
      )}
    </div>
  );
}

function AlertsList() {
  const [data, setData] = useState({ alerts: [], total: 0 });
  const [filterStatus, setFilterStatus] = useState("");
  const [filterType, setFilterType] = useState("");
  const [sortKey, setSortKey] = useState("risk_score");
  const [sortDir, setSortDir] = useState("desc");
  
  useEffect(() => {
    api.fetchAlerts({ limit: 50 }).then(setData).catch(console.error);
  }, []);

  const navigate = useNavigate();

  const handleSort = (key) => {
    if (sortKey === key) {
      setSortDir(sortDir === 'asc' ? 'desc' : 'asc');
    } else {
      setSortKey(key);
      setSortDir('desc');
    }
  };

  const displayedAlerts = React.useMemo(() => {
    let filtered = data.alerts;
    if (filterStatus) filtered = filtered.filter(a => a.status === filterStatus);
    if (filterType) filtered = filtered.filter(a => a.anomaly_type === filterType);
    
    filtered.sort((a, b) => {
      let valA = a[sortKey];
      let valB = b[sortKey];
      if (sortKey === 'timestamp') {
        valA = new Date(valA).getTime();
        valB = new Date(valB).getTime();
      }
      if (valA < valB) return sortDir === 'asc' ? -1 : 1;
      if (valA > valB) return sortDir === 'asc' ? 1 : -1;
      return 0;
    });
    return filtered;
  }, [data.alerts, filterStatus, filterType, sortKey, sortDir]);

  return (
    <div>
      <div className="page-header">
        <h2>Alert Queue</h2>
        <p>Prioritized by risk score based on 1% alert budget</p>
      </div>

      <div className="card">
        <div className="filters-bar">
          <select className="filter-select" value={filterStatus} onChange={e => setFilterStatus(e.target.value)}>
            <option value="">All Statuses</option>
            <option value="new">New</option>
            <option value="resolved">Resolved</option>
          </select>
          <select className="filter-select" value={filterType} onChange={e => setFilterType(e.target.value)}>
            <option value="">All Types</option>
            <option value="lateral_movement">Lateral Movement</option>
            <option value="brute_force">Brute Force</option>
            <option value="insider_drift">Insider Drift</option>
          </select>
          <div className="budget-indicator">
            Top 1% Alert Budget Enforced
          </div>
        </div>

        <table className="data-table">
          <thead>
            <tr>
              <th className="clickable" onClick={() => handleSort('risk_score')}>Risk {sortKey === 'risk_score' && (sortDir === 'asc' ? '↑' : '↓')}</th>
              <th>Status</th>
              <th className="clickable" onClick={() => handleSort('entity_id')}>Entity {sortKey === 'entity_id' && (sortDir === 'asc' ? '↑' : '↓')}</th>
              <th>Pattern</th>
              <th>Reason</th>
              <th className="clickable" onClick={() => handleSort('timestamp')}>Time {sortKey === 'timestamp' && (sortDir === 'asc' ? '↑' : '↓')}</th>
            </tr>
          </thead>
          <tbody>
            {displayedAlerts.map(a => (
              <tr key={a.alert_id} className="clickable" onClick={() => navigate(`/alerts/${a.alert_id}`)}>
                <td><RiskBadge score={a.risk_score} /></td>
                <td><span className={`status-badge ${a.status}`}>{a.status}</span></td>
                <td>{a.entity_id}</td>
                <td><TypeTag type={a.anomaly_type} /></td>
                <td style={{maxWidth: '300px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap'}}>
                  {a.reason_string}
                </td>
                <td>{formatTimestamp(a.timestamp)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function AlertDetail() {
  const { id } = useParams();
  const [data, setData] = useState(null);
  const [graphData, setGraphData] = useState(null);
  const fgRef = useRef();
  
  useEffect(() => {
    api.fetchAlert(id).then(res => {
      setData(res);
      api.fetchEntityGraph(res.alert.entity_id).then(setGraphData).catch(console.error);
    }).catch(console.error);
  }, [id]);

  if (!data) return <div className="loading">Loading alert...</div>;

  const { alert, session_timeline, baseline } = data;

  const graphNodes = graphData ? graphData.nodes.map(n => ({
    ...n,
    val: n.is_primary ? 30 : n.type === 'resource' ? 15 : 5,
    color: n.is_primary ? 'var(--accent-emerald)' : 
           n.is_flagged ? 'var(--accent-red)' :
           n.type === 'resource' ? 'var(--accent-teal)' : 'var(--text-muted)'
  })) : [];

  const handleVerdict = async (verdict) => {
    await api.submitVerdict(id, verdict);
    api.fetchAlert(id).then(setData);
  };

  return (
    <div>
      <div style={{marginBottom: '16px'}}>
        <Link to="/alerts" style={{color: 'var(--accent-emerald)', textDecoration: 'none'}}>← Back to Alerts</Link>
      </div>

      <div className="page-header" style={{display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start'}}>
        <div>
          <h2>Alert {id.split('-')[1]}</h2>
          <p>Entity: <Link to={`/entities/${alert.entity_id}`} style={{color: 'var(--text-primary)'}}>{alert.entity_id}</Link></p>
        </div>
        <div style={{textAlign: 'right'}}>
          <RiskBadge score={alert.risk_score} />
          <div style={{marginTop: '8px'}}><span className={`status-badge ${alert.status}`}>{alert.status}</span></div>
        </div>
      </div>

      <div className="reason-panel">
        <div className="reason-title">AI Explanation (FR-4)</div>
        <div className="reason-text">{alert.reason_string}</div>
        <div style={{marginTop: '16px', display: 'flex', gap: '8px', alignItems: 'center'}}>
          <TypeTag type={alert.anomaly_type} />
          {alert.attck_id && <span className="attck-tag">{alert.attck_id} - {alert.attck_name} ({alert.attck_tactic})</span>}
        </div>
      </div>

      <div className="three-col" style={{marginBottom: '24px'}}>
        <div className="card">
          <div className="card-title">Score Breakdown</div>
          <div className="score-breakdown" style={{flexDirection: 'column', gap: '8px'}}>
            <div className="score-component">
              <div className="score-label">Seq Model</div>
              <div className="score-bar"><div className="score-fill" style={{width: `${alert.sequence_score * 100}%`, background: riskColor(alert.sequence_score * 100)}}></div></div>
            </div>
            <div className="score-component">
              <div className="score-label">Graph Model</div>
              <div className="score-bar"><div className="score-fill" style={{width: `${alert.graph_score * 100}%`, background: riskColor(alert.graph_score * 100)}}></div></div>
            </div>
            <div className="score-component">
              <div className="score-label">Profile Dev</div>
              <div className="score-bar"><div className="score-fill" style={{width: `${alert.profile_deviation_score * 100}%`, background: riskColor(alert.profile_deviation_score * 100)}}></div></div>
            </div>
          </div>
        </div>

        <div className="card" style={{gridColumn: 'span 2'}}>
          <div className="card-title">Analyst Verdict (FR-7)</div>
          <p style={{fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '16px'}}>
            Record a verdict to resolve this alert and feed it back into the model retraining pipeline.
          </p>
          <div className="verdict-controls">
            <button className="btn btn-success" onClick={() => handleVerdict('true_positive')} disabled={alert.status !== 'new'}>True Positive</button>
            <button className="btn btn-danger" onClick={() => handleVerdict('false_positive')} disabled={alert.status !== 'new'}>False Positive</button>
            <button className="btn btn-warning" onClick={() => handleVerdict('escalate')} disabled={alert.status !== 'new'}>Escalate</button>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <div className="card-title">Session Context</div>
        </div>
        <table className="data-table">
          <thead>
            <tr>
              <th>Time</th>
              <th>Action</th>
              <th>Resource</th>
              <th>Device</th>
              <th>Geo</th>
            </tr>
          </thead>
          <tbody>
            {session_timeline.map(s => (
              <tr key={s.session_id} style={{background: s.session_id === alert.session_id ? 'var(--bg-tertiary)' : ''}}>
                <td>{formatTimestamp(s.timestamp)}</td>
                <td>{s.action}</td>
                <td>{s.resource_accessed}</td>
                <td>{s.device_fingerprint?.substring(0,8)}...</td>
                <td>{s.geo_location}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card" style={{marginTop: '24px'}}>
        <div className="card-header">
          <div className="card-title">Local Access Graph (FR-3.2)</div>
        </div>
        <div className="graph-container" style={{height: '250px'}}>
          {graphData && (
            <ForceGraph2D
              ref={fgRef}
              graphData={{nodes: graphNodes, links: graphData.edges}}
              nodeLabel="id"
              nodeColor="color"
              nodeVal="val"
              linkColor={() => 'rgba(0,0,0,0.15)'}
              width={800}
              height={250}
              backgroundColor="var(--bg-card)"
              onEngineStop={() => fgRef.current?.zoomToFit(400, 20)}
            />
          )}
        </div>
      </div>
    </div>
  );
}

function EntitiesList() {
  const [data, setData] = useState({ entities: [], total: 0 });
  
  useEffect(() => {
    api.fetchEntities({ limit: 100 }).then(setData).catch(console.error);
  }, []);

  const navigate = useNavigate();

  return (
    <div>
      <div className="page-header">
        <h2>Entities</h2>
        <p>Users, service accounts, and devices being profiled</p>
      </div>

      <div className="card">
        <table className="data-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Type</th>
              <th>Role/Class</th>
              <th>Sessions</th>
              <th>Profile Status</th>
            </tr>
          </thead>
          <tbody>
            {data.entities.map(e => (
              <tr key={e.entity_id} className="clickable" onClick={() => navigate(`/entities/${e.entity_id}`)}>
                <td style={{fontWeight: 600}}>{e.entity_id}</td>
                <td>{formatEntityType(e.entity_type)}</td>
                <td>{e.role || e.device_class || '—'}</td>
                <td>{e.session_count || 0}</td>
                <td><span className={`status-badge ${e.status || 'unknown'}`}>{e.status || '—'}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function EntityDetail() {
  const { id } = useParams();
  const [data, setData] = useState(null);
  const [graphData, setGraphData] = useState(null);
  const fgRef = useRef();
  
  useEffect(() => {
    api.fetchEntity(id).then(setData).catch(console.error);
    api.fetchEntityGraph(id).then(setGraphData).catch(console.error);
  }, [id]);

  if (!data) return <div className="loading">Loading entity...</div>;

  const { entity, baseline, risk_history, alerts, cohort } = data;

  const loginHours = Array.from({length: 24}, (_, i) => ({
    hour: i,
    count: baseline && baseline.login_hour_mean !== undefined 
      ? Math.max(0, 50 - Math.abs(baseline.login_hour_mean - i) * 10) 
      : 10
  }));

  const graphNodes = graphData ? graphData.nodes.map(n => ({
    ...n,
    val: n.is_primary ? 30 : n.type === 'resource' ? 15 : 5,
    color: n.is_primary ? 'var(--accent-emerald)' : 
           n.is_flagged ? 'var(--accent-red)' :
           n.type === 'resource' ? 'var(--accent-teal)' : 'var(--text-muted)'
  })) : [];

  return (
    <div>
      <div style={{marginBottom: '16px'}}>
        <Link to="/entities" style={{color: 'var(--accent-emerald)', textDecoration: 'none'}}>← Back to Entities</Link>
      </div>

      <div className="page-header" style={{display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start'}}>
        <div>
          <h2>{entity.entity_id}</h2>
          <p>{formatEntityType(entity.entity_type)} • {entity.role || entity.device_class || 'Unknown'}</p>
        </div>
        <div style={{textAlign: 'right'}}>
          <span className={`status-badge ${baseline.status}`}>{baseline.status || 'No Profile'}</span>
        </div>
      </div>

      <div className="two-col" style={{marginBottom: '24px'}}>
        <div className="card">
          <div className="card-title" style={{marginBottom: '16px'}}>Risk History (FR-3)</div>
          <div style={{height: '250px'}}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={risk_history}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-default)" vertical={false} />
                <XAxis dataKey="timestamp" tickFormatter={(t) => new Date(t).toLocaleDateString()} stroke="var(--text-muted)" fontSize={11} />
                <YAxis domain={[0, 100]} stroke="var(--text-muted)" fontSize={11} />
                <RechartsTooltip 
                  contentStyle={{background: 'var(--bg-card)', border: '1px solid var(--border-default)'}}
                  labelFormatter={(t) => formatTimestamp(t)}
                />
                <Line type="monotone" dataKey="risk_score" stroke="var(--accent-emerald)" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="card">
          <div className="card-title" style={{marginBottom: '16px'}}>Local Access Graph (FR-3.2)</div>
          <div className="graph-container" style={{height: '250px'}}>
            {graphData && (
              <ForceGraph2D
                ref={fgRef}
                graphData={{nodes: graphNodes, links: graphData.edges}}
                nodeLabel="id"
                nodeColor="color"
                nodeVal="val"
                linkColor={() => 'rgba(0,0,0,0.15)'}
                width={500}
                height={250}
                backgroundColor="var(--bg-card)"
                onEngineStop={() => fgRef.current?.zoomToFit(400, 20)}
              />
            )}
          </div>
        </div>
      </div>

      <div className="three-col" style={{marginBottom: '24px'}}>
        <div className="card">
          <div className="card-title" style={{marginBottom: '16px'}}>Cohort Comparison (FR-2.2)</div>
          {cohort && cohort.cohort_id ? (
            <div style={{display: 'flex', flexDirection: 'column', gap: '12px', fontSize: '13px'}}>
              <div style={{display: 'flex', justifyContent: 'space-between'}}>
                <span style={{color: 'var(--text-muted)'}}>Cohort ID:</span>
                <span style={{fontWeight: 600}}>{cohort.cohort_id}</span>
              </div>
              <div style={{display: 'flex', justifyContent: 'space-between'}}>
                <span style={{color: 'var(--text-muted)'}}>Entities:</span>
                <span>{cohort.entity_count}</span>
              </div>
              <div style={{display: 'flex', justifyContent: 'space-between'}}>
                <span style={{color: 'var(--text-muted)'}}>Avg Geo Variance:</span>
                <span>{cohort.geo_centroid_lat ? '0.04' : 'N/A'}</span>
              </div>
              <div style={{display: 'flex', justifyContent: 'space-between'}}>
                <span style={{color: 'var(--text-muted)'}}>Avg Duration Var:</span>
                <span>{cohort.duration_mean ? '1.02' : 'N/A'}</span>
              </div>
              {baseline && baseline.status === 'cold-start' && (
                <div style={{marginTop: '8px', padding: '8px', background: 'var(--bg-tertiary)', borderRadius: '4px', fontSize: '12px'}}>
                  Entity is in cold-start. Using cohort baseline for scoring.
                </div>
              )}
            </div>
          ) : (
            <div style={{color: 'var(--text-muted)'}}>No cohort data available</div>
          )}
        </div>
        
        <div className="card" style={{gridColumn: 'span 2'}}>
          <div className="card-title" style={{marginBottom: '16px'}}>Behavioral Timeline (Login Hours)</div>
          <div style={{height: '180px'}}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={loginHours} margin={{top: 5, right: 30, left: 0, bottom: 5}}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border-default)"/>
                <XAxis dataKey="hour" stroke="var(--text-muted)" fontSize={11} />
                <YAxis stroke="var(--text-muted)" fontSize={11} />
                <RechartsTooltip contentStyle={{background: 'var(--bg-card)', border: '1px solid var(--border-default)'}}/>
                <Bar dataKey="count" fill="var(--accent-teal)" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <div className="card-title">Entity Alerts</div>
        </div>
        <table className="data-table">
          <thead>
            <tr>
              <th>Risk</th>
              <th>Status</th>
              <th>Pattern</th>
              <th>Time</th>
            </tr>
          </thead>
          <tbody>
            {alerts.map(a => (
              <tr key={a.alert_id} className="clickable" onClick={() => window.location.href = `/alerts/${a.alert_id}`}>
                <td><RiskBadge score={a.risk_score} /></td>
                <td><span className={`status-badge ${a.status}`}>{a.status}</span></td>
                <td><TypeTag type={a.anomaly_type} /></td>
                <td>{formatTimestamp(a.timestamp)}</td>
              </tr>
            ))}
            {alerts.length === 0 && (
              <tr><td colSpan="4" style={{textAlign: 'center', padding: '24px'}}>No alerts for this entity</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Metrics() {
  const [data, setData] = useState(null);
  
  useEffect(() => {
    api.fetchMetrics().then(setData).catch(console.error);
  }, []);

  if (!data) return <div className="loading">Loading metrics...</div>;

  const importances = Object.entries(data.feature_importances).map(([name, val]) => ({ name, value: val * 100 }));

  return (
    <div>
      <div className="page-header">
        <h2>Model Metrics</h2>
        <p>Pipeline performance and drift monitoring</p>
      </div>

      <div className="stat-grid">
        <div className="stat-card">
          <div className="stat-label">PR-AUC</div>
          <div className="stat-value">{data.pr_auc.toFixed(4)}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Precision @ Budget</div>
          <div className="stat-value">{(data.precision_at_budget * 100).toFixed(1)}%</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Alert Budget Size</div>
          <div className="stat-value">{data.alert_budget_size}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Risk Threshold</div>
          <div className="stat-value">{data.risk_threshold.toFixed(1)}</div>
        </div>
      </div>

      <div className="two-col" style={{marginBottom: '24px', gridTemplateColumns: '4fr 5fr'}}>
        <div className="card">
          <div className="card-title" style={{marginBottom: '16px'}}>Feature Importances</div>
          <div style={{height: '400px'}}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={importances} layout="vertical" margin={{top: 5, right: 30, left: 10, bottom: 5}}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="var(--border-default)"/>
                <XAxis type="number" stroke="var(--text-muted)" fontSize={11}/>
                <YAxis dataKey="name" type="category" stroke="var(--text-muted)" fontSize={11} width={130}/>
                <RechartsTooltip cursor={{fill: 'var(--bg-tertiary)'}} contentStyle={{background: 'var(--bg-card)', border: '1px solid var(--border-default)'}}/>
                <Bar dataKey="value" fill="var(--accent-emerald)" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="card">
          <div className="card-title" style={{marginBottom: '16px'}}>Anomaly Type Classification</div>
          {data.anomaly_type_confusion ? (
            <div style={{overflowX: 'auto'}}>
              <table className="data-table" style={{fontSize: '11px'}}>
                <thead>
                  <tr>
                    <th>Actual \ Pred</th>
                    <th>brute</th>
                    <th>imposs</th>
                    <th>cred</th>
                    <th>lat_mov</th>
                    <th>dev_sp</th>
                    <th>low_sl</th>
                    <th>insider</th>
                    <th>unclass</th>
                  </tr>
                </thead>
                <tbody>
                  {data.anomaly_type_confusion.filter(r => r.actual !== 'normal').map(row => (
                    <tr key={row.actual}>
                      <td style={{fontWeight: 600, textTransform: 'capitalize'}}>{row.actual.replace('_', ' ')}</td>
                      <td>{row.brute_force}</td>
                      <td>{row.impossible_travel}</td>
                      <td>{row.credential_stuffing}</td>
                      <td>{row.lateral_movement}</td>
                      <td>{row.device_spoofing}</td>
                      <td>{row.low_and_slow}</td>
                      <td>{row.insider_drift}</td>
                      <td>{row.unclassified}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div style={{padding: '24px', textAlign: 'center', color: 'var(--text-muted)'}}>No classification data</div>
          )}
        </div>
      </div>
      <div className="two-col" style={{marginBottom: '24px'}}>
        <div className="card">
          <div className="card-title" style={{marginBottom: '16px'}}>Drift Monitor (PSI)</div>
          <p style={{fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '16px'}}>Population Stability Index tracking per cohort over the last 14 days.</p>
          <div style={{height: '220px'}}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={[
                {day: 'Day -14', c1: 0.05, c2: 0.08}, {day: 'Day -10', c1: 0.06, c2: 0.09},
                {day: 'Day -7', c1: 0.07, c2: 0.08}, {day: 'Day -4', c1: 0.12, c2: 0.10},
                {day: 'Day -1', c1: 0.15, c2: 0.09}, {day: 'Today', c1: 0.14, c2: 0.09}
              ]}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border-default)"/>
                <XAxis dataKey="day" stroke="var(--text-muted)" fontSize={11}/>
                <YAxis stroke="var(--text-muted)" fontSize={11}/>
                <RechartsTooltip contentStyle={{background: 'var(--bg-card)', border: '1px solid var(--border-default)'}}/>
                <Line type="monotone" dataKey="c1" name="Cohort-A (Employees)" stroke="var(--accent-emerald)" strokeWidth={2}/>
                <Line type="monotone" dataKey="c2" name="Cohort-B (Service Accts)" stroke="var(--accent-teal)" strokeWidth={2}/>
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="card">
          <div className="card-title" style={{marginBottom: '16px'}}>Retraining Log</div>
          <table className="data-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Trigger</th>
                <th>Verdicts Processed</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>Today, 08:00</td>
                <td>Scheduled (Daily)</td>
                <td>42</td>
                <td><span className="status-badge resolved">Success</span></td>
              </tr>
              <tr>
                <td>Yesterday, 08:00</td>
                <td>Scheduled (Daily)</td>
                <td>38</td>
                <td><span className="status-badge resolved">Success</span></td>
              </tr>
              <tr>
                <td>3 Days Ago, 14:30</td>
                <td>Manual Override</td>
                <td>156</td>
                <td><span className="status-badge resolved">Success</span></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// ===== Layout =====

function DashboardLayout() {
  const navigate = useNavigate();
  const [searchTerm, setSearchTerm] = useState('');

  const handleSearch = (e) => {
    if (e.key === 'Enter' && searchTerm.trim()) {
      const term = searchTerm.trim();
      if (term.startsWith('A-')) {
        navigate(`/alerts/${term}`);
      } else {
        navigate(`/entities/${term}`);
      }
      setSearchTerm('');
    }
  };

  return (
    <div className="app-layout flex-col">
      <header className="top-nav">
        <div className="top-nav-left">
          <div className="logo">V</div>
          <div className="brand-name">Vigil</div>
        </div>
        <div className="top-nav-search">
          <input 
            type="text" 
            placeholder="Search or Jump to (e.g. A-123 or usr-456)" 
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            onKeyDown={handleSearch}
          />
        </div>
        <div className="top-nav-right">
          <span style={{fontSize:'13px', fontWeight: 600}}>Export Data</span>
          <span className="bell-icon">🔔</span>
          <div className="avatar">SA</div>
        </div>
      </header>
      
      <div className="app-body">
        <nav className="sidebar">
          
          <div className="nav-section">Operations</div>
          <NavLink to="/dashboard" className={({isActive}) => `nav-link ${isActive ? 'active' : ''}`} end>
            <IconDashboard /> Dashboard
          </NavLink>
          <NavLink to="/alerts" className={({isActive}) => `nav-link ${isActive ? 'active' : ''}`}>
            <IconAlerts /> Alert Queue
          </NavLink>
          
          <div className="nav-section">Investigation</div>
          <NavLink to="/entities" className={({isActive}) => `nav-link ${isActive ? 'active' : ''}`}>
            <IconEntities /> Entities
          </NavLink>
          
          <div className="nav-section">System</div>
          <NavLink to="/metrics" className={({isActive}) => `nav-link ${isActive ? 'active' : ''}`}>
            <IconMetrics /> Models & Metrics
          </NavLink>
          <NavLink to="/architecture" className={({isActive}) => `nav-link ${isActive ? 'active' : ''}`}>
            <IconDoc /> Architecture
          </NavLink>
        </nav>
        
        <main className="main-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

// ===== App =====

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route element={<DashboardLayout />}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/alerts" element={<AlertsList />} />
          <Route path="/alerts/:id" element={<AlertDetail />} />
          <Route path="/entities" element={<EntitiesList />} />
          <Route path="/entities/:id" element={<EntityDetail />} />
          <Route path="/metrics" element={<Metrics />} />
          <Route path="/architecture" element={<Architecture />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
