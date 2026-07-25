"""
Vigil — Synthetic Data Generator
=================================
Implements FR-1.1 through FR-1.5 and NFR-4 (reproducibility).

Generates synthetic access-log data for users, service accounts, and edge devices
with habitual baselines and injects the 8 named anomaly patterns at a configurable rate.

Usage:
    python -m data_gen.generate --seed 42
"""

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

# Resolve import depending on whether run as module or directly
try:
    from data_gen.config import *
except ImportError:
    from config import *


class VigilDataGenerator:
    """
    Generates synthetic behavioral data with injected anomaly patterns.

    The generator:
    1. Creates entity profiles with habitual baselines (login-hour distribution,
       home geo, resource set, device fingerprint).
    2. Samples "normal" sessions from those baselines with realistic noise.
    3. Injects 7 anomaly patterns at a configurable rate (0.5-3% of sessions total).
    4. Outputs features and labels into separate Parquet files (FR-1.5).
    """

    def __init__(self, seed: int = 42, output_dir: str = "data"):
        self.seed = seed
        self.rng = np.random.default_rng(seed)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.start_date = datetime(2024, 1, 1)
        self.end_date = self.start_date + timedelta(days=TIME_RANGE_DAYS)
        self.num_days = TIME_RANGE_DAYS

        self.entity_profiles: dict = {}
        self.sessions: list = []
        self.labels: list = []
        self._session_counter = 0

    # ── Helpers ──────────────────────────────────────────────────────

    def _next_session_id(self) -> str:
        self._session_counter += 1
        return f"sess-{self._session_counter:07d}"

    def _generate_ip(self, lat: float, lng: float) -> str:
        """Deterministic but plausible private IP from geo coordinates."""
        salt = int(self.rng.integers(0, 10000))
        h = hashlib.md5(f"{lat:.4f},{lng:.4f},{salt}".encode()).hexdigest()
        return f"10.{int(h[:2], 16) % 256}.{int(h[2:4], 16) % 256}.{int(h[4:6], 16) % 256}"

    def _stable_ip(self, lat: float, lng: float, entity_id: str) -> str:
        """A stable IP for an entity (same every call for same entity)."""
        h = hashlib.md5(f"{entity_id}:{lat:.4f},{lng:.4f}".encode()).hexdigest()
        return f"10.{int(h[:2], 16) % 256}.{int(h[2:4], 16) % 256}.{int(h[4:6], 16) % 256}"

    def _fingerprint(self, entity_id: str, variant: int = 0) -> str:
        return hashlib.sha256(f"{entity_id}-fp-{variant}".encode()).hexdigest()[:16]

    def _geo_noise(self, lat: float, lng: float, noise_km: float = 3.0):
        """Add Gaussian noise at ~km scale (1° ≈ 111 km)."""
        d = noise_km / 111.0
        return round(lat + self.rng.normal(0, d), 4), round(lng + self.rng.normal(0, d), 4)

    @staticmethod
    def _haversine_km(lat1, lon1, lat2, lon2) -> float:
        R = 6371
        dlat, dlon = np.radians(lat2 - lat1), np.radians(lon2 - lon1)
        a = np.sin(dlat / 2) ** 2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2) ** 2
        return R * 2 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))

    def _pick_city(self, choices=None):
        cities = choices or list(CITY_COORDS.keys())
        name = self.rng.choice(cities)
        return name, CITY_COORDS[name]

    # ── Entity generation (FR-1.1, FR-1.3) ──────────────────────────

    def generate_entities(self) -> pd.DataFrame:
        """Create entity profiles with habitual baselines."""
        entities = []
        cities = list(CITY_COORDS.keys())

        # ---- Users ----
        for i in range(NUM_USERS):
            city, (lat, lng) = self._pick_city()
            role = str(self.rng.choice(USER_ROLES))
            n_res = int(self.rng.integers(3, 9))
            resource_set = list(self.rng.choice(USER_RESOURCES, size=n_res, replace=False))

            # ~10% of users appear late → cold-start candidates
            if self.rng.random() < 0.10:
                first_day = int(self.rng.integers(self.num_days - 7, self.num_days - 1))
            else:
                first_day = int(self.rng.integers(0, 20))

            entities.append({
                "entity_id": f"user-{i:04d}",
                "entity_type": "user",
                "role": role,
                "device_class": None,
                "home_city": city,
                "home_lat": lat,
                "home_lng": lng,
                "login_hour_mu": float(np.clip(self.rng.normal(9.5, 2.5), 5, 21)),
                "login_hour_sigma": float(self.rng.uniform(0.5, 2.0)),
                "resource_set": resource_set,
                "primary_auth": str(self.rng.choice(AUTH_METHODS["user"])),
                "device_fingerprint": self._fingerprint(f"user-{i:04d}"),
                "dur_mu": float(self.rng.uniform(15, 120)),
                "dur_sigma": float(self.rng.uniform(5, 25)),
                "sessions_per_day": float(self.rng.uniform(1.5, 5.0)),
                "first_seen_day": first_day,
                "commands": USER_COMMANDS,
            })

        # ---- Service accounts ----
        dc_cities = cities[:4]  # data-center cities
        for i in range(NUM_SERVICE_ACCOUNTS):
            city, (lat, lng) = self._pick_city(dc_cities)
            role = str(self.rng.choice(SERVICE_ROLES))
            n_res = int(self.rng.integers(2, 7))
            resource_set = list(self.rng.choice(SERVICE_RESOURCES, size=n_res, replace=False))

            if self.rng.random() < 0.08:
                first_day = int(self.rng.integers(self.num_days - 5, self.num_days - 1))
            else:
                first_day = int(self.rng.integers(0, 10))

            entities.append({
                "entity_id": f"svc-{i:04d}",
                "entity_type": "service_account",
                "role": role,
                "device_class": None,
                "home_city": city,
                "home_lat": lat,
                "home_lng": lng,
                "login_hour_mu": 12.0,
                "login_hour_sigma": 6.0,
                "resource_set": resource_set,
                "primary_auth": str(self.rng.choice(AUTH_METHODS["service_account"])),
                "device_fingerprint": self._fingerprint(f"svc-{i:04d}"),
                "dur_mu": float(self.rng.uniform(1, 30)),
                "dur_sigma": float(self.rng.uniform(0.5, 10)),
                "sessions_per_day": float(self.rng.uniform(5, 20)),
                "first_seen_day": first_day,
                "commands": SERVICE_COMMANDS,
            })

        # ---- Edge devices ----
        for i in range(NUM_EDGE_DEVICES):
            city, (lat, lng) = self._pick_city()
            dc = str(self.rng.choice(DEVICE_CLASSES))
            n_res = int(self.rng.integers(2, 6))
            resource_set = list(self.rng.choice(DEVICE_RESOURCES, size=n_res, replace=False))

            if self.rng.random() < 0.15:
                first_day = int(self.rng.integers(self.num_days - 6, self.num_days - 1))
            else:
                first_day = int(self.rng.integers(0, 40))

            entities.append({
                "entity_id": f"dev-{i:04d}",
                "entity_type": "edge_device",
                "role": None,
                "device_class": dc,
                "home_city": city,
                "home_lat": lat,
                "home_lng": lng,
                "login_hour_mu": 12.0,
                "login_hour_sigma": 8.0,
                "resource_set": resource_set,
                "primary_auth": str(self.rng.choice(AUTH_METHODS["edge_device"])),
                "device_fingerprint": self._fingerprint(f"dev-{i:04d}"),
                "dur_mu": float(self.rng.uniform(0.5, 15)),
                "dur_sigma": float(self.rng.uniform(0.2, 5)),
                "sessions_per_day": float(self.rng.uniform(3, 15)),
                "first_seen_day": first_day,
                "commands": DEVICE_COMMANDS,
            })

        self.entity_profiles = {e["entity_id"]: e for e in entities}

        entity_df = pd.DataFrame([{
            "entity_id": e["entity_id"],
            "entity_type": e["entity_type"],
            "role": e["role"],
            "device_class": e["device_class"],
            "first_seen": (self.start_date + timedelta(days=e["first_seen_day"])).isoformat(),
        } for e in entities])

        return entity_df

    # ── Normal session sampling (FR-1.3) ─────────────────────────────

    def _make_session(self, profile, day_offset, *, label=0, pattern="normal",
                      override: dict | None = None):
        """Build one session record + label record."""
        date = self.start_date + timedelta(days=int(day_offset))
        hour = np.clip(self.rng.normal(profile["login_hour_mu"],
                                       profile["login_hour_sigma"]), 0, 23.99)
        h_int, m_int = int(hour), int((hour % 1) * 60)
        ts = date.replace(hour=h_int, minute=m_int,
                          second=int(self.rng.integers(0, 60)))

        lat, lng = self._geo_noise(profile["home_lat"], profile["home_lng"])
        resource = str(self.rng.choice(profile["resource_set"]))
        dur = max(0.5, float(self.rng.normal(profile["dur_mu"], profile["dur_sigma"])))
        n_cmds = int(self.rng.integers(3, 8))
        cmds = list(self.rng.choice(profile["commands"],
                                    size=min(n_cmds, len(profile["commands"])),
                                    replace=False))

        sid = self._next_session_id()
        cohort_key = profile["role"] or profile["device_class"]

        session = {
            "session_id": sid,
            "entity_id": profile["entity_id"],
            "entity_type": profile["entity_type"],
            "timestamp": ts.isoformat(),
            "source_ip": self._stable_ip(lat, lng, profile["entity_id"]),
            "geo_location": f"{lat},{lng}",
            "resource_accessed": resource,
            "auth_method": profile["primary_auth"],
            "session_duration": round(dur, 2),
            "command_sequence": json.dumps(cmds),
            "device_fingerprint": profile["device_fingerprint"],
            "role": cohort_key,
        }
        if override:
            session.update(override)
            sid = session["session_id"]  # in case overridden

        lbl = {
            "session_id": sid,
            "entity_id": profile["entity_id"],
            "timestamp": session["timestamp"],
            "label": label,
            "pattern_name": pattern,
        }

        self.sessions.append(session)
        self.labels.append(lbl)
        return session

    def generate_normal_sessions(self):
        """Sample normal sessions from every entity's habitual baseline."""
        for eid, prof in self.entity_profiles.items():
            for day in range(prof["first_seen_day"], self.num_days):
                n = max(1, int(self.rng.poisson(prof["sessions_per_day"])))
                for _ in range(n):
                    self._make_session(prof, day)

    # ── Anomaly injection (FR-1.4) ───────────────────────────────────

    def _eligible_entities(self, min_days: int = 10):
        """Return entity IDs that have enough history for anomaly injection."""
        return [eid for eid, p in self.entity_profiles.items()
                if (self.num_days - p["first_seen_day"]) > min_days]

    def inject_brute_force(self):
        """Rapid repeated auth attempts from same IP (T1110)."""
        n_total = max(1, int(len(self.sessions) * INJECTION_RATES["brute_force"]))
        n_attacks = max(1, n_total // 8)  # each attack = ~8 sessions
        eligible = self._eligible_entities(min_days=10)
        if not eligible:
            return
        targets = self.rng.choice(eligible, size=min(n_attacks, len(eligible)), replace=False)

        for eid in targets:
            prof = self.entity_profiles[eid]
            lo = prof["first_seen_day"] + 5
            if lo >= self.num_days:
                continue
            day = int(self.rng.integers(lo, self.num_days))
            base = self.start_date + timedelta(days=day, hours=int(self.rng.integers(0, 24)))
            ip = self._stable_ip(prof["home_lat"], prof["home_lng"], eid)
            n_attempts = int(self.rng.integers(5, 15))

            for j in range(n_attempts):
                ts = base + timedelta(seconds=int(j * self.rng.integers(3, 20)))
                sid = self._next_session_id()
                self.sessions.append({
                    "session_id": sid,
                    "entity_id": eid,
                    "entity_type": prof["entity_type"],
                    "timestamp": ts.isoformat(),
                    "source_ip": ip,
                    "geo_location": f"{prof['home_lat']},{prof['home_lng']}",
                    "resource_accessed": str(self.rng.choice(prof["resource_set"])),
                    "auth_method": prof["primary_auth"],
                    "session_duration": round(float(self.rng.uniform(0.05, 0.5)), 2),
                    "command_sequence": json.dumps(["login_attempt", "auth_failed"]),
                    "device_fingerprint": prof["device_fingerprint"],
                    "role": prof["role"] or prof["device_class"],
                })
                self.labels.append({
                    "session_id": sid, "entity_id": eid,
                    "timestamp": ts.isoformat(), "label": 1,
                    "pattern_name": "brute_force",
                })

    def inject_impossible_travel(self):
        """Two sessions from distant geos within short time (T1078)."""
        n = max(1, int(len(self.sessions) * INJECTION_RATES["impossible_travel"]) // 2)
        eligible = self._eligible_entities(min_days=10)
        if not eligible:
            return
        targets = self.rng.choice(eligible, size=min(n, len(eligible)), replace=False)
        far_cities = list(CITY_COORDS.keys())

        for eid in targets:
            prof = self.entity_profiles[eid]
            lo = prof["first_seen_day"] + 3
            if lo >= self.num_days:
                continue
            day = int(self.rng.integers(lo, self.num_days))

            # Pick a city far from home
            home = (prof["home_lat"], prof["home_lng"])
            remote_city = self.rng.choice([c for c in far_cities if c != prof["home_city"]])
            rlat, rlng = CITY_COORDS[remote_city]
            # Ensure it's actually far (>500 km)
            if self._haversine_km(home[0], home[1], rlat, rlng) < 500:
                rlat, rlng = CITY_COORDS["miami"] if prof["home_city"] != "miami" else CITY_COORDS["seattle"]

            base = self.start_date + timedelta(days=day, hours=int(self.rng.integers(8, 18)))

            # Session 1: home location
            sid1 = self._next_session_id()
            ts1 = base
            self.sessions.append({
                "session_id": sid1, "entity_id": eid,
                "entity_type": prof["entity_type"],
                "timestamp": ts1.isoformat(),
                "source_ip": self._generate_ip(home[0], home[1]),
                "geo_location": f"{home[0]},{home[1]}",
                "resource_accessed": str(self.rng.choice(prof["resource_set"])),
                "auth_method": prof["primary_auth"],
                "session_duration": round(float(self.rng.normal(prof["dur_mu"], prof["dur_sigma"])), 2),
                "command_sequence": json.dumps(["login", "browse", "logout"]),
                "device_fingerprint": prof["device_fingerprint"],
                "role": prof["role"] or prof["device_class"],
            })
            self.labels.append({"session_id": sid1, "entity_id": eid,
                                "timestamp": ts1.isoformat(), "label": 1,
                                "pattern_name": "impossible_travel"})

            # Session 2: remote location, 30-90 min later
            gap = timedelta(minutes=int(self.rng.integers(30, 90)))
            ts2 = ts1 + gap
            sid2 = self._next_session_id()
            self.sessions.append({
                "session_id": sid2, "entity_id": eid,
                "entity_type": prof["entity_type"],
                "timestamp": ts2.isoformat(),
                "source_ip": self._generate_ip(rlat, rlng),
                "geo_location": f"{rlat},{rlng}",
                "resource_accessed": str(self.rng.choice(prof["resource_set"])),
                "auth_method": prof["primary_auth"],
                "session_duration": round(float(self.rng.normal(prof["dur_mu"], prof["dur_sigma"])), 2),
                "command_sequence": json.dumps(["login", "download_file", "logout"]),
                "device_fingerprint": self._fingerprint(eid, variant=99),
                "role": prof["role"] or prof["device_class"],
            })
            self.labels.append({"session_id": sid2, "entity_id": eid,
                                "timestamp": ts2.isoformat(), "label": 1,
                                "pattern_name": "impossible_travel"})

    def inject_credential_stuffing(self):
        """Many entities hit from same small IP cluster (T1110.004)."""
        n = max(1, int(len(self.sessions) * INJECTION_RATES["credential_stuffing"]))
        # Create 3-5 "attacker IP clusters"
        n_clusters = int(self.rng.integers(3, 6))

        for _ in range(n_clusters):
            cluster_ip = f"10.{self.rng.integers(200, 255)}.{self.rng.integers(0, 256)}.{self.rng.integers(1, 255)}"
            # Pick 5-15 target entities
            n_targets = min(int(self.rng.integers(5, 16)), n // n_clusters)
            targets = self.rng.choice(self._eligible_entities(), size=n_targets, replace=False)
            day = int(self.rng.integers(30, self.num_days))
            base = self.start_date + timedelta(days=day, hours=int(self.rng.integers(1, 5)))

            for j, eid in enumerate(targets):
                prof = self.entity_profiles[eid]
                ts = base + timedelta(seconds=int(j * self.rng.integers(10, 60)))
                sid = self._next_session_id()
                self.sessions.append({
                    "session_id": sid, "entity_id": eid,
                    "entity_type": prof["entity_type"],
                    "timestamp": ts.isoformat(),
                    "source_ip": cluster_ip,
                    "geo_location": f"{self.rng.uniform(25, 48):.4f},{self.rng.uniform(-120, -70):.4f}",
                    "resource_accessed": str(self.rng.choice(prof["resource_set"])),
                    "auth_method": prof["primary_auth"],
                    "session_duration": round(float(self.rng.uniform(0.1, 2.0)), 2),
                    "command_sequence": json.dumps(["login_attempt", "credential_check"]),
                    "device_fingerprint": self._fingerprint("attacker", variant=int(self.rng.integers(0, 5))),
                    "role": prof["role"] or prof["device_class"],
                })
                self.labels.append({"session_id": sid, "entity_id": eid,
                                    "timestamp": ts.isoformat(), "label": 1,
                                    "pattern_name": "credential_stuffing"})

    def inject_lateral_movement(self):
        """Entity accesses unusual breadth of resources (T1021)."""
        n = max(1, int(len(self.sessions) * INJECTION_RATES["lateral_movement"]) // 4)
        eligible = self._eligible_entities(min_days=15)
        if not eligible:
            return
        targets = self.rng.choice(eligible, size=min(n, len(eligible)), replace=False)

        all_resources = USER_RESOURCES + SERVICE_RESOURCES + DEVICE_RESOURCES

        for eid in targets:
            prof = self.entity_profiles[eid]
            lo = prof["first_seen_day"] + 10
            if lo >= self.num_days:
                continue
            day = int(self.rng.integers(lo, self.num_days))
            base = self.start_date + timedelta(days=day, hours=int(self.rng.integers(1, 5)))

            # Access 4-8 resources NOT in their normal set
            novel_resources = [r for r in all_resources if r not in prof["resource_set"]]
            n_hops = int(self.rng.integers(4, 9))
            hop_resources = list(self.rng.choice(novel_resources, size=min(n_hops, len(novel_resources)), replace=False))

            for j, res in enumerate(hop_resources):
                ts = base + timedelta(minutes=int(j * self.rng.integers(5, 30)))
                sid = self._next_session_id()
                self.sessions.append({
                    "session_id": sid, "entity_id": eid,
                    "entity_type": prof["entity_type"],
                    "timestamp": ts.isoformat(),
                    "source_ip": self._stable_ip(prof["home_lat"], prof["home_lng"], eid),
                    "geo_location": f"{prof['home_lat']},{prof['home_lng']}",
                    "resource_accessed": res,
                    "auth_method": prof["primary_auth"],
                    "session_duration": round(float(self.rng.uniform(2, 20)), 2),
                    "command_sequence": json.dumps(["login", "enumerate", "access_resource", "exfiltrate"]),
                    "device_fingerprint": prof["device_fingerprint"],
                    "role": prof["role"] or prof["device_class"],
                })
                self.labels.append({"session_id": sid, "entity_id": eid,
                                    "timestamp": ts.isoformat(), "label": 1,
                                    "pattern_name": "lateral_movement"})

    def inject_device_spoofing(self):
        """Device fingerprint changes unexpectedly (T1200)."""
        n = max(1, int(len(self.sessions) * INJECTION_RATES["device_spoofing"]))
        eligible = self._eligible_entities(min_days=10)
        if not eligible:
            return
        targets = self.rng.choice(eligible, size=min(n, len(eligible)), replace=False)

        for eid in targets:
            prof = self.entity_profiles[eid]
            lo = prof["first_seen_day"] + 5
            if lo >= self.num_days:
                continue
            day = int(self.rng.integers(lo, self.num_days))

            spoofed_fp = self._fingerprint(eid, variant=int(self.rng.integers(50, 100)))
            self._make_session(prof, day, label=1, pattern="device_spoofing",
                               override={
                                   "session_id": self._next_session_id(),
                                   "device_fingerprint": spoofed_fp,
                               })

    def inject_low_and_slow(self):
        """Gradually increasing duration + unusual resources over multiple days (T1041)."""
        n = max(1, int(len(self.sessions) * INJECTION_RATES["low_and_slow"]) // 6)
        eligible = self._eligible_entities(min_days=30)
        if not eligible:
            return
        targets = self.rng.choice(eligible, size=min(n, len(eligible)), replace=False)

        novel_pool = USER_RESOURCES + SERVICE_RESOURCES
        for eid in targets:
            prof = self.entity_profiles[eid]
            lo = prof["first_seen_day"] + 15
            hi = self.num_days - 10
            if lo >= hi:
                continue
            start_day = int(self.rng.integers(lo, hi))

            # 5-10 sessions over 7-14 days, each slightly longer
            n_sessions = int(self.rng.integers(5, 11))
            base_dur = prof["dur_mu"]

            for j in range(n_sessions):
                day = start_day + int(j * self.rng.integers(1, 3))
                if day >= self.num_days:
                    break
                # Duration escalates
                escalated_dur = base_dur * (1 + 0.3 * (j + 1))
                # Gradually use novel resources
                novel_res = [r for r in novel_pool if r not in prof["resource_set"]]
                resource = str(self.rng.choice(novel_res)) if self.rng.random() < 0.3 + 0.1 * j else str(self.rng.choice(prof["resource_set"]))

                sid = self._next_session_id()
                ts = self.start_date + timedelta(
                    days=day,
                    hours=int(np.clip(self.rng.normal(prof["login_hour_mu"], prof["login_hour_sigma"]), 0, 23)),
                    minutes=int(self.rng.integers(0, 60)),
                )
                self.sessions.append({
                    "session_id": sid, "entity_id": eid,
                    "entity_type": prof["entity_type"],
                    "timestamp": ts.isoformat(),
                    "source_ip": self._stable_ip(prof["home_lat"], prof["home_lng"], eid),
                    "geo_location": f"{prof['home_lat']},{prof['home_lng']}",
                    "resource_accessed": resource,
                    "auth_method": prof["primary_auth"],
                    "session_duration": round(escalated_dur, 2),
                    "command_sequence": json.dumps(["login", "browse", "download_file", "compress", "upload_file"]),
                    "device_fingerprint": prof["device_fingerprint"],
                    "role": prof["role"] or prof["device_class"],
                })
                self.labels.append({"session_id": sid, "entity_id": eid,
                                    "timestamp": ts.isoformat(), "label": 1,
                                    "pattern_name": "low_and_slow"})

    def inject_insider_drift(self):
        """Slow shift in access patterns over weeks (T1078.002)."""
        n = max(1, int(len(self.sessions) * INJECTION_RATES["insider_drift"]) // 8)
        eligible = self._eligible_entities(min_days=45)
        if not eligible:
            return
        targets = self.rng.choice(eligible, size=min(n, len(eligible)), replace=False)

        for eid in targets:
            prof = self.entity_profiles[eid]
            lo = prof["first_seen_day"] + 20
            hi = self.num_days - 20
            if lo >= hi:
                continue
            drift_start = int(self.rng.integers(lo, hi))

            # Over 15-25 days, behavior gradually shifts
            n_drift_days = int(self.rng.integers(15, 26))
            # Shift login hour by 3-6 hours
            hour_shift = float(self.rng.choice([-1, 1])) * self.rng.uniform(3, 6)
            novel_pool = [r for r in USER_RESOURCES + SERVICE_RESOURCES if r not in prof["resource_set"]]

            for j in range(n_drift_days):
                day = drift_start + j
                if day >= self.num_days:
                    break

                progress = j / n_drift_days  # 0→1
                shifted_hour = prof["login_hour_mu"] + hour_shift * progress
                # Increasingly use novel resources
                use_novel = self.rng.random() < 0.1 + 0.5 * progress

                sid = self._next_session_id()
                ts = self.start_date + timedelta(
                    days=day,
                    hours=int(np.clip(shifted_hour + self.rng.normal(0, prof["login_hour_sigma"]), 0, 23)),
                    minutes=int(self.rng.integers(0, 60)),
                )
                resource = str(self.rng.choice(novel_pool)) if (use_novel and novel_pool) else str(self.rng.choice(prof["resource_set"]))

                self.sessions.append({
                    "session_id": sid, "entity_id": eid,
                    "entity_type": prof["entity_type"],
                    "timestamp": ts.isoformat(),
                    "source_ip": self._stable_ip(prof["home_lat"], prof["home_lng"], eid),
                    "geo_location": f"{prof['home_lat']},{prof['home_lng']}",
                    "resource_accessed": resource,
                    "auth_method": prof["primary_auth"],
                    "session_duration": round(float(self.rng.normal(prof["dur_mu"] * (1 + 0.2 * progress), prof["dur_sigma"])), 2),
                    "command_sequence": json.dumps(["login", "browse", "access_portal", "search", "download_file"]),
                    "device_fingerprint": prof["device_fingerprint"],
                    "role": prof["role"] or prof["device_class"],
                })
                self.labels.append({"session_id": sid, "entity_id": eid,
                                    "timestamp": ts.isoformat(), "label": 1,
                                    "pattern_name": "insider_drift"})

    # ── Main pipeline ────────────────────────────────────────────────

    def generate(self) -> dict:
        """
        Run the full generation pipeline.
        Returns a summary dict for verification.
        """
        print("=" * 60)
        print("  Vigil -- Synthetic Data Generator")
        print("=" * 60)
        print(f"  Seed: {self.seed}")
        print(f"  Output: {self.output_dir.resolve()}")
        print()

        # Step 1: entities
        print("[1/3] Generating entity profiles ...")
        entity_df = self.generate_entities()
        entity_df.to_parquet(self.output_dir / "entities.parquet", index=False)
        print(f"       {len(entity_df)} entities "
              f"({(entity_df.entity_type == 'user').sum()} users, "
              f"{(entity_df.entity_type == 'service_account').sum()} svc accts, "
              f"{(entity_df.entity_type == 'edge_device').sum()} devices)")

        # Step 2: normal sessions
        print("[2/3] Sampling normal sessions ...")
        self.generate_normal_sessions()
        n_normal = len(self.sessions)
        print(f"       {n_normal:,} normal sessions generated")

        # Step 3: inject anomalies
        print("[3/3] Injecting anomaly patterns ...")
        self.inject_brute_force()
        self.inject_impossible_travel()
        self.inject_credential_stuffing()
        self.inject_lateral_movement()
        self.inject_device_spoofing()
        self.inject_low_and_slow()
        self.inject_insider_drift()

        n_total = len(self.sessions)
        n_anomalous = n_total - n_normal

        # Build DataFrames
        sessions_df = pd.DataFrame(self.sessions)
        labels_df = pd.DataFrame(self.labels)

        # Sort by timestamp for temporal ordering
        sessions_df = sessions_df.sort_values("timestamp").reset_index(drop=True)
        labels_df = labels_df.sort_values("timestamp").reset_index(drop=True)

        # Write Parquet (FR-1.5: labels separate from features)
        sessions_df.to_parquet(self.output_dir / "sessions.parquet", index=False)
        labels_df.to_parquet(self.output_dir / "labels.parquet", index=False)

        # Summary
        pattern_counts = labels_df[labels_df.label == 1]["pattern_name"].value_counts()
        anomaly_rate = n_anomalous / n_total * 100

        print()
        print("-" * 60)
        print("  GENERATION SUMMARY")
        print("-" * 60)
        print(f"  Entities:          {len(entity_df)}")
        print(f"  Total sessions:    {n_total:,}")
        print(f"  Normal sessions:   {n_normal:,}")
        print(f"  Anomalous:         {n_anomalous:,} ({anomaly_rate:.2f}%)")
        print()
        print("  Pattern breakdown:")
        for pattern, count in pattern_counts.items():
            pct = count / n_total * 100
            print(f"    {pattern:<25s} {count:>6,}  ({pct:.3f}%)")
        print()

        # Cold-start entity check
        entity_session_counts = labels_df.groupby("entity_id").size()
        cold_start = (entity_session_counts < GRADUATION_THRESHOLD).sum()
        print(f"  Cold-start entities (< {GRADUATION_THRESHOLD} sessions): {cold_start}")
        print(f"  Output files:")
        print(f"    {self.output_dir.resolve() / 'sessions.parquet'}")
        print(f"    {self.output_dir.resolve() / 'labels.parquet'}")
        print(f"    {self.output_dir.resolve() / 'entities.parquet'}")
        print("-" * 60)

        return {
            "n_entities": len(entity_df),
            "n_sessions": n_total,
            "n_normal": n_normal,
            "n_anomalous": n_anomalous,
            "anomaly_rate": anomaly_rate,
            "pattern_counts": pattern_counts.to_dict(),
            "cold_start_entities": int(cold_start),
        }


# ── CLI entry point ──────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Vigil Synthetic Data Generator")
    parser.add_argument("--seed", type=int, default=42, help="Random seed (NFR-4)")
    parser.add_argument("--output-dir", type=str, default="data",
                        help="Output directory for Parquet files")
    args = parser.parse_args()

    gen = VigilDataGenerator(seed=args.seed, output_dir=args.output_dir)
    gen.generate()


if __name__ == "__main__":
    main()
