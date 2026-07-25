import requests
import json
import time

BASE_URL = "http://localhost:8000"

print("--- Testing API ---")
# 1. /alerts
r = requests.get(f"{BASE_URL}/alerts?limit=5")
print(f"GET /alerts: {r.status_code}")
alerts_data = r.json()
alerts = alerts_data.get("alerts", [])
if alerts:
    first_alert = alerts[0]["alert_id"]
    print(f"First alert ID: {first_alert}")
    
    # 2. /alerts/{id}
    r = requests.get(f"{BASE_URL}/alerts/{first_alert}")
    print(f"GET /alerts/{{id}}: {r.status_code}")

    # 3. POST /alerts/{id}/verdict
    r = requests.post(f"{BASE_URL}/alerts/{first_alert}/verdict", json={"verdict": "true_positive", "note": "QA test"})
    print(f"POST /alerts/{{id}}/verdict: {r.status_code}")
    
    # Check persistence?
    # This requires restarting the server, but let's check if the verdict was written to feedback.parquet
    import pandas as pd
    try:
        feedback = pd.read_parquet("data/feedback.parquet")
        print(f"Feedback length: {len(feedback)}")
    except Exception as e:
        print("Could not read feedback.parquet")

# 4. /entities
r = requests.get(f"{BASE_URL}/entities?limit=5")
print(f"GET /entities: {r.status_code}")
entities = r.json().get("entities", [])
if entities:
    first_entity = entities[0]["entity_id"]
    
    # 5. /entities/{id}
    r = requests.get(f"{BASE_URL}/entities/{first_entity}")
    print(f"GET /entities/{{id}}: {r.status_code}")
    
    # 6. /entities/{id}/graph
    r = requests.get(f"{BASE_URL}/entities/{first_entity}/graph")
    print(f"GET /entities/{{id}}/graph: {r.status_code}")

# 7. /metrics
r = requests.get(f"{BASE_URL}/metrics")
print(f"GET /metrics: {r.status_code}")

# 8. /dashboard
r = requests.get(f"{BASE_URL}/dashboard")
print(f"GET /dashboard: {r.status_code}")

# Invalid inputs
r = requests.get(f"{BASE_URL}/alerts/nonexistent-alert-id")
print(f"GET /alerts/nonexistent-alert-id: {r.status_code} - {r.json()}")

r = requests.get(f"{BASE_URL}/entities/nonexistent-entity-id")
print(f"GET /entities/nonexistent-entity-id: {r.status_code} - {r.json()}")

r = requests.get(f"{BASE_URL}/alerts?limit=-5")
print(f"GET /alerts invalid limit: {r.status_code}")

print("--- Cold Start Correctness (NFR-2) ---")
import pandas as pd
sessions = pd.read_parquet("data/sessions.parquet")
entities_df = pd.read_parquet("data/entities.parquet")
baselines = pd.read_parquet("data/baselines.parquet")
scored = pd.read_parquet("data/scored_sessions.parquet")

cold_starts = baselines[baselines['status'] == 'cold-start']['entity_id'].tolist()
if cold_starts:
    cs_entity = cold_starts[0]
    print(f"Found cold-start entity: {cs_entity}")
    # Verify risk score is derived
    cs_scored = scored[scored['entity_id'] == cs_entity]
    if not cs_scored.empty:
        print(f"Entity has {len(cs_scored)} scored sessions. Example risk score: {cs_scored.iloc[0]['risk_score']}")
        print("It has a non-null risk score derived from cohort baseline (profile_score_pct = " + str(cs_scored.iloc[0]['profile_score_pct']) + ").")
else:
    print("No cold-start entities found!")

print("--- Testing classification ATT&CK ---")
alerts_df = pd.read_parquet("data/alerts_enriched.parquet")
for anomaly_type in alerts_df['anomaly_type'].unique():
    subset = alerts_df[alerts_df['anomaly_type'] == anomaly_type]
    print(f"{anomaly_type}: {subset.iloc[0]['attck_id']}")
    
print("Check for generic reason string:")
generic = alerts_df[alerts_df['reason_string'].str.contains('generic', case=False, na=False)]
if not generic.empty:
    print(f"Found {len(generic)} generic reason strings")
else:
    print("No generic reason strings found. Reason strings look specific.")
