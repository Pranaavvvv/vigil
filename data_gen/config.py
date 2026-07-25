"""
Vigil data-generation configuration.
All tunable constants live here so the generator is easy to reconfigure.
"""

# ── Entity counts (FR-1.1) ──────────────────────────────────────────
NUM_USERS = 250
NUM_SERVICE_ACCOUNTS = 100
NUM_EDGE_DEVICES = 50
# Total: 400 entities

# ── Time range ──────────────────────────────────────────────────────
TIME_RANGE_DAYS = 90  # ~3 months of history

# ── Graduation threshold (FR-2: cold-start boundary) ────────────────
GRADUATION_THRESHOLD = 20

# ── Anomaly injection rates (fraction of total normal sessions) ─────
# Overall target: 0.5-3% anomalous. We aim for ~2% total.
INJECTION_RATES = {
    "brute_force": 0.0035,
    "impossible_travel": 0.0030,
    "credential_stuffing": 0.0030,
    "lateral_movement": 0.0030,
    "device_spoofing": 0.0025,
    "low_and_slow": 0.0025,
    "insider_drift": 0.0025,
}
# Sum ≈ 2.0%

# ── EWMA decay factor (FR-2.3) ─────────────────────────────────────
EWMA_ALPHA = 0.1

# ── Cohort keys ─────────────────────────────────────────────────────
USER_ROLES = [
    "finance-analyst", "engineer", "hr-specialist",
    "operations", "executive", "data-analyst",
    "security-ops", "it-support",
]

SERVICE_ROLES = [
    "database-svc", "api-gateway-svc", "batch-processor",
    "monitoring-svc", "deployment-svc", "cache-svc",
]

DEVICE_CLASSES = [
    "POS-terminal", "HVAC-controller", "security-camera",
    "environmental-sensor", "access-control", "industrial-plc",
]

# ── Geo locations (US cities for entity home bases) ─────────────────
CITY_COORDS = {
    "new_york":      (40.7128, -74.0060),
    "chicago":       (41.8781, -87.6298),
    "houston":       (29.7604, -95.3698),
    "phoenix":       (33.4484, -112.0740),
    "san_francisco": (37.7749, -122.4194),
    "seattle":       (47.6062, -122.3321),
    "denver":        (39.7392, -104.9903),
    "atlanta":       (33.7490, -84.3880),
    "boston":         (42.3601, -71.0589),
    "miami":         (25.7617, -80.1918),
    "dallas":        (32.7767, -96.7970),
    "los_angeles":   (34.0522, -118.2437),
}

# ── Resource pools ──────────────────────────────────────────────────
USER_RESOURCES = [
    "email-server", "sharepoint", "code-repo", "finance-db",
    "hr-portal", "erp-system", "vpn-gateway", "admin-console",
    "file-server", "analytics-dashboard", "crm-system",
    "ticket-system", "wiki", "build-server", "staging-env",
    "prod-db-readonly", "backup-storage", "compliance-portal",
    "training-platform", "video-conf",
]

SERVICE_RESOURCES = [
    "api-gateway", "primary-db", "replica-db", "redis-cache",
    "message-queue", "storage-bucket", "monitoring-api",
    "deployment-target", "config-store", "secret-manager",
    "logging-service", "metrics-collector", "cdn-origin",
    "search-index", "ml-inference",
]

DEVICE_RESOURCES = [
    "telemetry-server", "firmware-update", "config-endpoint",
    "command-control", "maintenance-portal", "data-collector",
    "edge-gateway", "ntp-server", "certificate-authority",
    "ota-update-server",
]

# ── Command vocabularies ────────────────────────────────────────────
USER_COMMANDS = [
    "login", "read_email", "send_email", "download_file",
    "upload_file", "browse", "run_query", "edit_document",
    "access_portal", "logout", "search", "view_report",
    "approve_request", "submit_form",
]

SERVICE_COMMANDS = [
    "authenticate", "query_db", "write_cache", "read_cache",
    "call_api", "process_batch", "generate_report", "sync_data",
    "healthcheck", "terminate", "rotate_credentials", "flush_cache",
]

DEVICE_COMMANDS = [
    "connect", "send_telemetry", "receive_config", "firmware_check",
    "report_status", "execute_command", "upload_logs", "disconnect",
    "self_test", "calibrate",
]

# ── Auth methods per entity type ────────────────────────────────────
AUTH_METHODS = {
    "user":            ["password", "mfa", "sso"],
    "service_account": ["api_key", "certificate", "oauth_token"],
    "edge_device":     ["certificate", "pre_shared_key", "device_token"],
}
