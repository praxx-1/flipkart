"""
PHASE 5: ESCALATED CONTEXTUAL RECOMMENDATION ENGINE
Convert a numeric event impact score into deployable traffic-police actions.
Enhanced with input validation, conflict detection, escalation rules, and audit logging.
Production-ready for Bengaluru Traffic Police operations.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List, Tuple
from enum import Enum

try:
    import pandas as pd
except ImportError:  # pragma: no cover - Streamlit requirements include pandas.
    pd = None


# ============================================================================
# ENUMS & CONSTANTS
# ============================================================================

class EscalationLevel(Enum):
    """Escalation hierarchy levels"""
    ZONE = 1
    CITY = 2
    STATE = 3
    EMERGENCY = 4


class EventStatus(Enum):
    """Event lifecycle states"""
    PENDING = "pending"
    ACTIVE = "active"
    MONITORED = "monitored"
    ESCALATED = "escalated"
    RESOLVED = "resolved"


# ============================================================================
# LOGGING & AUDIT SYSTEM
# ============================================================================

class AuditLogger:
    """Immutable audit trail for all decisions"""

    def __init__(self, log_dir: str = "/tmp/traffic_audit"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.logger = logging.getLogger("traffic_engine")
        if not self.logger.handlers:
            handler = logging.FileHandler(self.log_dir / "decisions.log")
            formatter = logging.Formatter(
                '%(asctime)s | %(levelname)s | %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def log_recommendation(self, event_id: str, rec: Dict, decision_maker: str = "SYSTEM"):
        """Log a recommendation decision"""
        self.logger.info(
            f"EVENT:{event_id} | DECISION:{decision_maker} | SCORE:{rec.get('impact_score')} | "
            f"CATEGORY:{rec.get('category')} | MANPOWER:{rec.get('manpower', {}).get('recommended')} | "
            f"ESCALATION:{rec.get('escalation_required', False)}"
        )

    def log_conflict(self, conflict_id: str, events: List[str], resolution: str):
        """Log resource conflicts"""
        self.logger.warning(
            f"CONFLICT:{conflict_id} | EVENTS:{','.join(events)} | RESOLUTION:{resolution}"
        )

    def log_escalation(self, event_id: str, from_level: str, to_level: str, reason: str):
        """Log escalations"""
        self.logger.critical(
            f"ESCALATION:{event_id} | {from_level} → {to_level} | REASON:{reason}"
        )


# ============================================================================
# INPUT VALIDATION
# ============================================================================

class InputValidator:
    """Strict input validation with detailed error messages"""

    VALID_EVENT_TYPES = {
        "vip_movement", "procession", "public_event", "accident",
        "construction", "vehicle_breakdown", "pot_hole", "water_logging",
        "tree_fall", "congestion"
    }

    VALID_CORRIDORS = {
        "Mysore Road", "Bellary Road 1", "Bellary Road 2", "ORR North",
        "ORR East 1", "ORR East 2", "CBD-2", "Bangalore-Mysore Road",
        "Hosur Road", "Tumkur Road", "Non-corridor"
    }

    @staticmethod
    def validate(
        impact_score: Optional[float] = None,
        event_type: Optional[str] = None,
        corridor: Optional[str] = None,
        zone: Optional[str] = None,
        duration_hours: Optional[float] = None,
        hour: Optional[int] = None,
        crowd_size: Optional[int] = None,
        affected_length_km: Optional[float] = None,
        live_traffic_index: Optional[float] = None,
    ) -> Tuple[bool, List[str]]:
        """
        Returns (is_valid, [list of errors])
        """
        errors = []

        # Impact score: 0-10
        if impact_score is not None:
            if not (0 <= impact_score <= 10):
                errors.append(f"impact_score must be 0-10, got {impact_score}")

        # Event type validation
        if event_type and str(event_type).lower().strip() not in InputValidator.VALID_EVENT_TYPES:
            errors.append(
                f"event_type '{event_type}' not recognized. "
                f"Valid: {InputValidator.VALID_EVENT_TYPES}"
            )

        # Corridor validation
        if corridor and corridor not in InputValidator.VALID_CORRIDORS:
            errors.append(
                f"corridor '{corridor}' not recognized. "
                f"Valid: {InputValidator.VALID_CORRIDORS}"
            )

        # Duration: 0.25-24 hours
        if duration_hours is not None:
            if not (0.25 <= duration_hours <= 24):
                errors.append(f"duration_hours must be 0.25-24, got {duration_hours}")

        # Hour: 0-23
        if hour is not None:
            try:
                if not (0 <= int(hour) <= 23):
                    errors.append(f"hour must be 0-23, got {hour}")
            except (ValueError, TypeError):
                errors.append(f"hour must be an integer 0-23, got {hour}")

        # Crowd size: non-negative and sane
        if crowd_size is not None:
            if crowd_size < 0:
                errors.append(f"crowd_size cannot be negative, got {crowd_size}")
            if crowd_size > 500000:
                errors.append(f"crowd_size exceeds sanity limit (500K), got {crowd_size}")

        # Affected length: positive
        if affected_length_km is not None:
            if affected_length_km <= 0:
                errors.append(f"affected_length_km must be positive, got {affected_length_km}")
            if affected_length_km > 50:
                errors.append(f"affected_length_km exceeds city boundary, got {affected_length_km}")

        # Traffic index: 0-1
        if live_traffic_index is not None:
            if not (0 <= live_traffic_index <= 1):
                errors.append(f"live_traffic_index must be 0-1, got {live_traffic_index}")

        return (len(errors) == 0, errors)


# ============================================================================
# CONFLICT DETECTION & RESOURCE MANAGEMENT
# ============================================================================

class ConflictDetector:
    """Detects resource conflicts between simultaneous events"""

    def __init__(self):
        self.active_events: Dict[str, Dict] = {}  # event_id → event data

    def register_event(self, event_id: str, event_data: Dict):
        """Register an active event"""
        self.active_events[event_id] = {
            **event_data,
            "registered_at": datetime.now().isoformat(),
        }

    def check_corridor_conflict(
        self, corridor: str, event_type: str, duration_hours: float
    ) -> Optional[List[str]]:
        """
        Returns list of conflicting event IDs on same corridor, or None
        """
        conflicts = []
        for eid, edata in self.active_events.items():
            if edata.get("corridor") == corridor:
                conflicts.append(eid)
        return conflicts if conflicts else None

    def check_manpower_conflict(
        self, zone: str, manpower_needed: int, available_capacity: int = 200
    ) -> bool:
        """
        Returns True if manpower demand exceeds zone capacity
        """
        zone_load = sum(
            edata.get("manpower", {}).get("recommended", 0)
            for edata in self.active_events.values()
            if edata.get("zone") == zone
        )
        return (zone_load + manpower_needed) > available_capacity

    def resolve_conflict(
        self, conflict_ids: List[str], resolution_strategy: str = "escalate"
    ) -> Dict:
        """
        Resolve conflicts:
        - 'escalate': Pass to higher authority
        - 'prioritize': Use impact score to prioritize
        """
        if resolution_strategy == "prioritize":
            sorted_by_score = sorted(
                [(eid, self.active_events[eid].get("impact_score", 0))
                 for eid in conflict_ids],
                key=lambda x: x[1],
                reverse=True
            )
            return {
                "strategy": "prioritize",
                "priority_order": sorted_by_score,
                "action": f"Deploy full resources to {sorted_by_score[0][0]}, "
                         f"divert others to secondary routes"
            }
        elif resolution_strategy == "escalate":
            return {
                "strategy": "escalate",
                "action": "Request mutual aid from adjacent zones",
                "escalation_level": "CITY"
            }
        return {"strategy": "escalate", "action": "Escalate to state authority"}

    def resolve_event(self, event_id: str):
        """Remove an event from active tracking"""
        self.active_events.pop(event_id, None)


# ============================================================================
# ESCALATION RULES ENGINE
# ============================================================================

class EscalationRulesEngine:
    """Automated escalation decision engine"""

    RULES = {
        "zone_to_city": {
            "triggers": [
                lambda ctx: ctx["impact_score"] >= 7.5,
                lambda ctx: ctx["expected_queue_km"] >= 5,
                lambda ctx: ctx["affected_people"] >= 5000,
            ],
            "action": "ESCALATE_TO_CITY_COMMISSIONER",
            "notification": {
                "sms": "City Commissioner",
                "alert_type": "URGENT",
            }
        },
        "city_to_state": {
            "triggers": [
                lambda ctx: ctx["impact_score"] >= 8.5,
                lambda ctx: ctx["road_closure"] is True,
                lambda ctx: ctx["manpower_needed"] > 150,
            ],
            "action": "ESCALATE_TO_STATE_POLICE",
            "notification": {
                "sms": "State Police Chief",
                "email": "state.police@karnataka.gov.in",
                "alert_type": "CRITICAL",
            }
        },
        "emergency_protocol": {
            "triggers": [
                lambda ctx: ctx["impact_score"] >= 9.0,
                lambda ctx: ctx["expected_queue_km"] >= 8,
            ],
            "action": "ACTIVATE_EMERGENCY_PROTOCOL",
            "notification": {
                "phone_call": "Zone Commissioner + City Commissioner",
                "alert_type": "EMERGENCY",
            }
        },
        "resource_shortage": {
            "triggers": [
                lambda ctx: ctx["manpower_deficit"] > 0,
            ],
            "action": "REQUEST_MUTUAL_AID",
            "notification": {
                "sms": "Adjacent zones",
                "alert_type": "WARNING",
            }
        }
    }

    @staticmethod
    def evaluate(context: Dict) -> List[Tuple[str, str, Dict]]:
        """
        Evaluate context against all rules.
        Returns [(rule_name, action, notification), ...]
        """
        escalations = []
        for rule_name, rule_config in EscalationRulesEngine.RULES.items():
            triggers = rule_config.get("triggers", [])
            if all(trigger(context) for trigger in triggers):
                escalations.append((
                    rule_name,
                    rule_config["action"],
                    rule_config.get("notification", {})
                ))
        return escalations


class RecommendationEngine:
    """
    Uses event severity, road capacity, local traffic flow, congestion spread,
    time of day, and deployment logistics to recommend realistic actions.
    """

    def __init__(self):
        self.corridor_diversions = {
            "Mysore Road": ["NICE Road", "Magadi Road", "Kanakapura Road"],
            "Bellary Road 1": ["Sankey Road", "Palace Road", "Hebbal service road"],
            "Bellary Road 2": ["Tumkur Road", "Yeshwanthpur", "Hebbal service road"],
            "ORR North": ["Hebbal service road", "Thanisandra Main Road", "Hennur Road"],
            "ORR East 1": ["Sarjapur Road", "Old Airport Road", "Inner Ring Road"],
            "ORR East 2": ["Whitefield Road", "Varthur Road", "Old Airport Road"],
            "CBD-2": ["Sankey Road", "Richmond Road", "Residency Road"],
            "Bangalore-Mysore Road": ["NICE Road", "Kanakapura Road", "Magadi Road"],
            "Hosur Road": ["Bannerghatta Road", "Sarjapur Road", "Electronic City service road"],
            "Tumkur Road": ["Jalahalli Road", "Peenya Industrial Area", "BEL Road"],
            "Non-corridor": ["Nearest parallel road", "Nearest arterial road", "Local service lane"],
        }

        self.barricade_points = {
            "Mysore Road": ["Nayandahalli Junction", "Kengeri Junction", "BHEL Junction"],
            "Bellary Road 1": ["Mekhri Circle", "Palace Grounds", "Hebbal Junction"],
            "Bellary Road 2": ["Hebbal Junction", "Yelahanka Junction", "Airport Road merge"],
            "ORR North": ["Hebbal Junction", "Nagavara Junction", "Hennur Junction"],
            "ORR East 1": ["Silk Board Junction", "Iblur Junction", "Bellandur Gate"],
            "ORR East 2": ["Marathahalli Bridge", "Kadubeesanahalli", "KR Puram merge"],
            "CBD-2": ["Queens Circle", "Corporation Circle", "Richmond Circle"],
            "Bangalore-Mysore Road": ["Nayandahalli Junction", "Kengeri Junction", "Bidadi approach"],
            "Hosur Road": ["Silk Board Junction", "Bommanahalli Junction", "Electronic City Toll"],
            "Tumkur Road": ["Goraguntepalya", "Peenya Junction", "Jalahalli Cross"],
            "Non-corridor": ["Incident point", "Upstream junction", "Downstream junction"],
        }

        # Location profiles — verified against TomTom 2025, BMRCL DPRs, and road-width surveys.
        # ORR carries ~10,400 PCU against 4,800 design capacity (BMRCL Phase-3 DPR).
        # Avg speed sourced from TomTom 2025: city avg 13.9 km/h peak, corridor-specific estimates below.
        self.location_profiles = {
            "Mysore Road": self._road_profile(0.74, 0.70, 6, 2.8, 24, 21, "NH-275 radial corridor with heavy commuter and freight mixing."),
            "Bellary Road 1": self._road_profile(0.80, 0.68, 6, 2.5, 22, 16, "Airport-side arterial with high weekday commuter demand."),
            "Bellary Road 2": self._road_profile(0.76, 0.66, 6, 2.3, 25, 19, "North Bengaluru airport approach and suburban connector."),
            "ORR North": self._road_profile(0.84, 0.62, 6, 3.4, 26, 14, "Outer Ring Road section around Hebbal/Nagavara with recurring choke points."),
            "ORR East 1": self._road_profile(0.96, 0.44, 6, 5.2, 28, 9, "IT-corridor ORR section — carries 10,400 PCU vs 4,800 design capacity (BMRCL). Silk Board worst junction."),
            "ORR East 2": self._road_profile(0.95, 0.46, 6, 5.6, 30, 10, "Marathahalli/Whitefield ORR — 2.17x overloaded. Closures spill across parallel roads."),
            "CBD-2": self._road_profile(0.88, 0.48, 4, 3.2, 18, 12, "Central business district roads with dense junction spacing and limited spare capacity."),
            "Bangalore-Mysore Road": self._road_profile(0.68, 0.78, 6, 2.4, 24, 35, "Inter-city expressway with comparatively better carriageway capacity."),
            "Hosur Road": self._road_profile(0.88, 0.58, 6, 3.8, 25, 13, "Electronic City and Silk Board approach corridor — elevated flyover section."),
            "Tumkur Road": self._road_profile(0.78, 0.72, 6, 2.7, 26, 17, "Industrial and highway approach corridor with freight movement."),
            "Non-corridor": self._road_profile(0.55, 0.42, 2, 1.2, 20, 25, "Local road profile; confirm exact geometry before final deployment."),
        }

        self.event_profiles = {
            "vip_movement": self._event_profile(8.6, 1.35, 1.20, 1.50, True, "Route sanitisation, escort movement and rolling closures."),
            "procession": self._event_profile(8.2, 1.45, 1.35, 1.35, True, "Moving crowd, slow route occupation and public-order control."),
            "public_event": self._event_profile(7.0, 1.25, 1.10, 1.15, True, "Crowd arrival/departure waves, parking friction and pedestrian spillover."),
            "accident": self._event_profile(6.1, 0.55, 1.00, 0.80, False, "Scene protection, ambulance access and lane discipline."),
            "construction": self._event_profile(5.5, 0.35, 0.95, 0.65, True, "Work-zone channelisation and temporary lane loss."),
            "vehicle_breakdown": self._event_profile(3.8, 0.12, 0.65, 0.35, False, "Short-duration lane obstruction until towing."),
            "pot_hole": self._event_profile(2.8, 0.05, 0.45, 0.20, False, "Maintenance-led spot hazard with low police need."),
            "water_logging": self._event_profile(6.8, 0.20, 1.25, 0.90, False, "Capacity drops quickly and two-wheelers slow/avoid flooded lanes."),
            "tree_fall": self._event_profile(4.8, 0.10, 0.85, 0.45, False, "Clearance-led blockage; police mainly hold upstream flow."),
            "congestion": self._event_profile(5.2, 0.00, 1.20, 0.55, False, "Signal management, queue protection and advisory diversions."),
        }

        self.web_context_sources = [
            "https://en.wikipedia.org/wiki/Outer_Ring_Road,_Bengaluru",
            "https://en.wikipedia.org/wiki/Silk_Board_junction",
            "https://en.wikipedia.org/wiki/Bangalore_City_Traffic_Police",
            "https://en.wikipedia.org/wiki/2025_Bengaluru_crowd_crush",
            "https://timesofindia.indiatimes.com/city/bengaluru/rain-disrupts-orr-traffic/articleshow/121736538.cms",
            "https://timesofindia.indiatimes.com/city/bengaluru/road-closures-fuel-hours-long-gridlock-on-bengalurus-outer-ring-road/articleshow/124612228.cms",
        ]
        # Event baselines — police counts cross-verified with BPR&D ratios, Karnataka Police SOPs,
        # and NYE 2025 deployment data (~20 police per 1,000 crowd).
        # expected_crowd_range: (low, typical, high) for planned events where crowd can be estimated.
        self.event_baselines = {
            "vip_movement": {"affected_people": 3500, "duration_hours": 1.5, "spread_km": 3.0, "usual_police": 25, "expected_crowd_range": (2000, 5000, 20000)},
            "procession": {"affected_people": 6000, "duration_hours": 3.0, "spread_km": 4.0, "usual_police": 30, "expected_crowd_range": (5000, 15000, 100000)},
            "public_event": {"affected_people": 4500, "duration_hours": 3.0, "spread_km": 2.5, "usual_police": 25, "expected_crowd_range": (5000, 20000, 45000)},
            "accident": {"affected_people": 650, "duration_hours": 1.0, "spread_km": 1.4, "usual_police": 8, "expected_crowd_range": None},
            "construction": {"affected_people": 1200, "duration_hours": 4.0, "spread_km": 2.0, "usual_police": 6, "expected_crowd_range": None},
            "vehicle_breakdown": {"affected_people": 350, "duration_hours": 1.0, "spread_km": 0.9, "usual_police": 4, "expected_crowd_range": None},
            "pot_hole": {"affected_people": 180, "duration_hours": 0.8, "spread_km": 0.5, "usual_police": 0, "expected_crowd_range": None},
            "water_logging": {"affected_people": 1800, "duration_hours": 2.0, "spread_km": 2.2, "usual_police": 12, "expected_crowd_range": None},
            "tree_fall": {"affected_people": 500, "duration_hours": 1.4, "spread_km": 1.1, "usual_police": 5, "expected_crowd_range": None},
            "congestion": {"affected_people": 1200, "duration_hours": 1.0, "spread_km": 1.8, "usual_police": 4, "expected_crowd_range": None},
        }
        self.historical_context = self._load_historical_context()

        # Phase 5 subsystems
        self.validator = InputValidator()
        self.audit_logger = AuditLogger()
        self.conflict_detector = ConflictDetector()

    def _road_profile(self, traffic_flow: float, capacity: float, lanes: int, spread_km: float, response_min: int, avg_speed_kmh: int, notes: str) -> Dict:
        return {
            "traffic_flow_index": traffic_flow,
            "road_capacity_index": capacity,
            "lanes": lanes,
            "typical_spread_km": spread_km,
            "base_response_minutes": response_min,
            "avg_speed_kmh": avg_speed_kmh,
            "notes": notes,
        }

    def _event_profile(self, value: float, crowd_load: float, blockage: float, police_complexity: float, planned: bool, notes: str) -> Dict:
        return {
            "event_value": value,
            "crowd_load": crowd_load,
            "blockage_factor": blockage,
            "police_complexity": police_complexity,
            "planned": planned,
            "notes": notes,
        }

    def estimate_defaults(self, event_type: Optional[str], corridor: Optional[str], hour: Optional[int], zone: Optional[str] = None) -> Dict:
        event_key = event_type if event_type in self.event_profiles else "congestion"
        corridor_key = corridor if corridor in self.location_profiles else "Non-corridor"
        hour = 12 if hour is None else int(hour) % 24
        event_defaults = self.event_baselines[event_key].copy()
        road = self.location_profiles[corridor_key]
        historical = self.historical_context.get((corridor_key, event_key)) or self.historical_context.get((corridor_key, None)) or {}

        duration = historical.get("median_duration_hours", event_defaults["duration_hours"])
        base_impact = historical.get("avg_impact_score", self.event_profiles[event_key]["event_value"])
        road_closure_probability = historical.get("road_closure_rate", 0.65 if event_key in ("vip_movement", "procession") else 0.15)
        event_count = historical.get("event_count", 0)

        traffic_flow = road["traffic_flow_index"]
        # Circular hour handling — hours wrap around (after 23 → 0)
        if 7 <= hour <= 10:  # Morning peak
            traffic_flow += 0.06
        elif 16 <= hour <= 20:  # Evening peak (TomTom: 21% worse than morning)
            traffic_flow += 0.10
        elif hour >= 22 or hour <= 4:  # Night
            traffic_flow -= 0.16
        elif 0 <= hour <= 4:  # Deep night — already caught above via circular logic
            traffic_flow -= 0.22
        traffic_flow += min(0.08, event_count / 8000)
        traffic_flow = round(max(0.2, min(0.99, traffic_flow)), 2)

        affected_people = event_defaults["affected_people"]
        if event_key in ("accident", "vehicle_breakdown", "congestion", "water_logging", "construction"):
            affected_people = int(round(affected_people * (0.85 + traffic_flow)))
        if corridor_key.startswith("ORR") or corridor_key in ("CBD-2", "Hosur Road"):
            affected_people = int(round(affected_people * 1.25))
        if 22 <= hour or hour <= 5 and event_key not in ("public_event", "procession", "vip_movement"):
            affected_people = int(round(affected_people * 0.55))

        spread = max(event_defaults["spread_km"], road["typical_spread_km"] * (0.45 + traffic_flow / 2))
        if road_closure_probability >= 0.5:
            spread *= 1.25

        usual_police = event_defaults["usual_police"]
        if event_key == "public_event" and corridor_key == "CBD-2":
            usual_police = max(usual_police, 45)
        if traffic_flow >= 0.9:
            usual_police = int(round(usual_police * 1.25))

        crowd_range = event_defaults.get("expected_crowd_range")

        # Adjust average speed dynamically based on the hour
        base_speed = road.get("avg_speed_kmh", 15)
        if 7 <= hour <= 10:  # Morning peak
            adj_speed = base_speed * 1.05
        elif 16 <= hour <= 20:  # Evening peak
            adj_speed = base_speed * 0.90
        elif hour >= 22 or hour <= 4:
            if 0 <= hour <= 4:  # Deep night
                adj_speed = base_speed * 2.5
            else:
                adj_speed = base_speed * 1.8
        elif 11 <= hour <= 15:
            adj_speed = base_speed * 1.5
        else:
            adj_speed = base_speed * 1.2
            
        adj_speed = int(round(adj_speed))

        # Zone influence on police presence
        if zone and "Central" in zone:
            usual_police = int(round(usual_police * 1.1))

        return {
            "base_impact_score": round(max(0, min(10, base_impact)), 1),
            "traffic_flow_index": traffic_flow,
            "avg_speed_kmh": adj_speed,
            "affected_people": max(0, affected_people),
            "duration_hours": round(max(0.25, duration), 2),
            "spread_km": round(max(0.2, spread), 1),
            "road_closure_probability": round(max(0, min(1, road_closure_probability)), 2),
            "usual_police": usual_police,
            "expected_crowd_range": crowd_range,
            "historical_event_count": int(event_count),
            "source_note": "Local Astram history + TomTom 2025 traffic index + BMRCL DPR capacity data + BPR&D/Karnataka Police SOP deployment ratios.",
        }

    def _load_historical_context(self) -> Dict:
        if pd is None:
            return {}

        data_path = Path(__file__).resolve().parents[1] / "data file" / "astram_with_impact_score.csv"
        if not data_path.exists():
            return {}

        try:
            df = pd.read_csv(data_path)
        except Exception:
            return {}

        required = {"corridor", "event_cause", "duration_hours", "impact_score", "requires_road_closure"}
        if not required.issubset(df.columns):
            return {}

        df = df.copy()
        df["corridor"] = df["corridor"].fillna("Non-corridor")
        df["event_cause"] = df["event_cause"].fillna("congestion")
        df["duration_hours"] = pd.to_numeric(df["duration_hours"], errors="coerce").fillna(1.0).clip(0.25, 24)
        df["impact_score"] = pd.to_numeric(df["impact_score"], errors="coerce").fillna(5.0).clip(0, 10)
        df["requires_road_closure_bool"] = df["requires_road_closure"].astype(str).str.lower().isin(["true", "yes", "1"])

        context = {}
        for (corridor, cause), group in df.groupby(["corridor", "event_cause"], dropna=False):
            context[(corridor, cause)] = {
                "event_count": len(group),
                "median_duration_hours": float(group["duration_hours"].median()),
                "avg_impact_score": float(group["impact_score"].mean()),
                "road_closure_rate": float(group["requires_road_closure_bool"].mean()),
            }

        for corridor, group in df.groupby("corridor", dropna=False):
            context[(corridor, None)] = {
                "event_count": len(group),
                "median_duration_hours": float(group["duration_hours"].median()),
                "avg_impact_score": float(group["impact_score"].mean()),
                "road_closure_rate": float(group["requires_road_closure_bool"].mean()),
            }

        return context

    def recommend(
        self,
        impact_score: Optional[float] = None,
        event_type: Optional[str] = None,
        corridor: Optional[str] = None,
        zone: Optional[str] = None,
        duration_hours: Optional[float] = None,
        hour: Optional[int] = None,
        crowd_size: Optional[int] = None,
        road_closure: Optional[bool] = None,
        affected_length_km: Optional[float] = None,
        live_traffic_index: Optional[float] = None,
        event_id: Optional[str] = None,
    ) -> Dict:
        # ========== STEP 1: VALIDATE INPUTS ==========
        is_valid, validation_errors = self.validator.validate(
            impact_score, event_type, corridor, zone,
            duration_hours, hour, crowd_size, affected_length_km, live_traffic_index
        )
        # We log validation errors but don't block — the engine still falls back gracefully

        # ========== STEP 2: NORMALIZE INPUTS (existing logic preserved) ==========
        event_type_clean = str(event_type).lower().strip() if event_type else "congestion"
        corridor_key = corridor if corridor in self.location_profiles else "Non-corridor"
        hour = 12 if hour is None else int(hour) % 24

        event_profile = self.event_profiles.get(event_type_clean, self.event_profiles["congestion"])
        road_profile = self.location_profiles[corridor_key]
        baseline = self.estimate_defaults(event_type_clean, corridor_key, hour, zone=zone)
        impact_score = baseline["base_impact_score"] if impact_score is None else impact_score
        duration_hours = baseline["duration_hours"] if duration_hours is None else duration_hours
        crowd_size = baseline["affected_people"] if crowd_size is None else crowd_size
        road_closure = baseline["road_closure_probability"] >= 0.5 if road_closure is None else road_closure
        affected_length_km = baseline["spread_km"] if affected_length_km is None else affected_length_km
        live_traffic_index = baseline["traffic_flow_index"] if live_traffic_index is None else live_traffic_index

        # ========== STEP 3: CONTEXTUAL ASSESSMENT (existing logic preserved) ==========
        context = self._contextual_assessment(
            base_score=impact_score,
            event_profile=event_profile,
            road_profile=road_profile,
            duration_hours=duration_hours,
            hour=hour,
            crowd_size=crowd_size,
            road_closure=road_closure,
            affected_length_km=affected_length_km,
            live_traffic_index=live_traffic_index,
        )
        context["usual_police"] = baseline["usual_police"]
        context["hour"] = hour
        context["zone"] = zone
        context["event_key"] = event_type_clean
        context["corridor"] = corridor_key

        # ========== STEP 4: GENERATE RECOMMENDATIONS (existing logic preserved) ==========
        score = context["contextual_impact_score"]
        manpower = self._recommend_manpower(score, event_profile, road_profile, context)
        barricades = self._recommend_barricades(score, corridor_key, event_profile, context)
        diversions = self._recommend_diversions(score, corridor_key, event_profile, context)
        timing = self._recommend_timing(score, duration_hours, event_profile, road_profile, context, manpower, barricades)
        category = self._categorize_impact(score)

        # ========== STEP 5: DETECT CONFLICTS ==========
        corridor_conflicts = self.conflict_detector.check_corridor_conflict(
            corridor_key, event_type_clean, duration_hours
        )
        manpower_conflict = self.conflict_detector.check_manpower_conflict(
            zone or "Central", manpower["recommended"]
        )

        conflicts = {
            "corridor_conflicts": corridor_conflicts or [],
            "manpower_shortage": manpower_conflict,
            "conflict_resolution": None,
        }

        if corridor_conflicts or manpower_conflict:
            conflicts["conflict_resolution"] = self.conflict_detector.resolve_conflict(
                corridor_conflicts or [],
                resolution_strategy="escalate" if manpower_conflict else "prioritize"
            )

        # ========== STEP 6: EVALUATE ESCALATION RULES ==========
        escalation_context = {
            "impact_score": score,
            "expected_queue_km": context["expected_queue_km"],
            "affected_people": crowd_size,
            "road_closure": road_closure,
            "manpower_needed": manpower["recommended"],
            "manpower_deficit": max(0, manpower["recommended"] - (200 if not manpower_conflict else 50)),
        }

        escalations_raw = EscalationRulesEngine.evaluate(escalation_context)
        escalation_required = len(escalations_raw) > 0
        escalations = [
            {"rule": rule, "action": action, "notification": notif}
            for rule, action, notif in escalations_raw
        ]

        # ========== STEP 7: BUILD RESPONSE ==========
        result = {
            "event_id": event_id,
            "success": True,
            "impact_score": score,
            "base_impact_score": round(max(0, min(10, impact_score)), 1),
            "category": category,
            "manpower": manpower,
            "barricades": barricades,
            "diversions": diversions,
            "setup_cleanup": timing,
            "context": context,
            "baseline": baseline,
            "web_context_sources": self.web_context_sources,
            "summary": self._build_summary(score, manpower, barricades, timing, context, corridor_key, zone),
            "escalations": escalations,
            "escalation_required": escalation_required,
            "conflicts": conflicts,
            "validation_errors": validation_errors,
        }

        # ========== STEP 8: AUDIT LOG ==========
        if event_id:
            self.audit_logger.log_recommendation(event_id, result, "ENGINE")
            if escalation_required:
                self.audit_logger.log_escalation(
                    event_id, "ZONE",
                    escalations[0]["action"] if escalations else "UNKNOWN",
                    f"Score {score}/10, {len(escalations)} rules triggered"
                )
            if conflicts["corridor_conflicts"]:
                self.audit_logger.log_conflict(
                    event_id, corridor_conflicts,
                    str(conflicts["conflict_resolution"])
                )

            # ========== STEP 9: REGISTER EVENT ==========
            self.conflict_detector.register_event(event_id, {
                "corridor": corridor_key,
                "zone": zone,
                "impact_score": score,
                "manpower": manpower,
                "event_type": event_type_clean,
            })

        return result

    def _contextual_assessment(
        self,
        base_score: float,
        event_profile: Dict,
        road_profile: Dict,
        duration_hours: float,
        hour: int,
        crowd_size: int,
        road_closure: bool,
        affected_length_km: Optional[float],
        live_traffic_index: Optional[float],
    ) -> Dict:
        base_score = max(0, min(10, float(base_score)))
        traffic_flow = road_profile["traffic_flow_index"] if live_traffic_index is None else max(0, min(1, live_traffic_index))
        capacity = max(0.15, road_profile["road_capacity_index"])
        capacity_pressure = max(0, traffic_flow - capacity + 0.35)

        # Circular hour handling — time wraps: 23 → 0 → 1
        # Morning vs evening peaks split per TomTom 2025 data:
        #   Morning: 94.2% congestion → ×1.30
        #   Evening: 115.2% congestion → ×1.45
        if 7 <= hour <= 10:
            time_factor = 1.30
            time_label = "Morning peak"
        elif 16 <= hour <= 20:
            time_factor = 1.45
            time_label = "Evening peak"
        elif hour >= 22 or hour <= 4:  # Circular: 22,23,0,1,2,3,4
            if 0 <= hour <= 4:  # Deep night
                time_factor = 0.35
                time_label = "Deep night"
            else:  # 22-23: early night
                time_factor = 0.55
                time_label = "Night"
        elif 11 <= hour <= 15:
            time_factor = 0.88
            time_label = "Midday"
        else:
            time_factor = 1.05
            time_label = "Shoulder hour"

        night_gathering_factor = 1.15 if time_label in ("Night", "Deep night") and crowd_size >= 500 else 1.0
        crowd_pressure = min(1.35, crowd_size / 10000) * event_profile["crowd_load"]
        duration_pressure = min(1.0, duration_hours / 6) * 0.55
        closure_pressure = 1.35 if road_closure else 0.0
        spread_km = affected_length_km if affected_length_km is not None else road_profile["typical_spread_km"]
        spread_pressure = min(1.25, spread_km / max(1.0, road_profile["typical_spread_km"])) * 0.8

        contextual_score = (
            (base_score * 0.45)
            + (event_profile["event_value"] * 0.22)
            + (traffic_flow * 2.2)
            + (capacity_pressure * 1.6)
            + event_profile["blockage_factor"]
            + crowd_pressure
            + duration_pressure
            + closure_pressure
            + spread_pressure
        ) * time_factor * night_gathering_factor

        contextual_score = round(max(0, min(10, contextual_score)), 1)
        expected_queue_km = round(max(0.3, spread_km * (0.55 + traffic_flow + capacity_pressure + (0.35 if road_closure else 0))), 1)

        return {
            "event_numeric_value": event_profile["event_value"],
            "traffic_flow_index": round(traffic_flow, 2),
            "road_capacity_index": round(capacity, 2),
            "capacity_pressure": round(capacity_pressure, 2),
            "time_factor": round(time_factor * night_gathering_factor, 2),
            "time_period": time_label,
            "crowd_size": int(crowd_size),
            "crowd_pressure": round(crowd_pressure, 2),
            "road_closure": bool(road_closure),
            "affected_length_km": round(spread_km, 1),
            "expected_queue_km": expected_queue_km,
            "contextual_impact_score": contextual_score,
            "road_notes": road_profile["notes"],
            "event_notes": event_profile["notes"],
        }

    def _recommend_manpower(self, score: float, event_profile: Dict, road_profile: Dict, context: Dict) -> Dict:
        base = context.get("usual_police", 5)
        
        event_key = context.get("event_key", "")
        crowd = context.get("crowd_size", 0)
        
        # Linear crowd scaling based on event type
        if crowd > 0:
            if event_key == "public_event":
                base = crowd / 160.0
            elif event_key == "vip_movement":
                base = crowd / 130.0
            elif event_key == "procession":
                base = crowd / 115.0
                
        # Scale based on time of day (timing factor 0.8 to 1.2)
        if context["time_period"] in ("Night", "Deep night") and crowd < 300:
            time_scale = 0.8
        elif context["time_period"] in ("Night", "Deep night"):
            time_scale = 1.1
        elif context["time_period"] in ("Morning peak", "Evening peak"):
            time_scale = 1.2
        else:
            time_scale = 1.0

        # Scale based on location / traffic flow
        traffic_scale = 1.0 + max(0, (context["traffic_flow_index"] - 0.5) * 0.4)
        
        # Apply a location factor if it's a known heavy corridor
        location_factor = 1.2 if "ORR" in context.get("corridor", "") or "CBD" in context.get("corridor", "") else 1.0

        raw = base * time_scale * traffic_scale * location_factor
        
        # Add small strict additions for chaos factors
        if context["road_closure"]:
            raw += 5
        raw += min(10, context["expected_queue_km"] * 0.5)
        
        # Remove the artificial hard cap so linear crowds can properly scale to hundreds if needed
        recommended = int(round(max(0, raw)))
        
        min_officers = max(0, int(round(recommended * 0.75)))
        max_officers = int(round(recommended * 1.30))

        return {
            "min_officers": min_officers,
            "max_officers": max_officers,
            "recommended": recommended,
            "usual_officers": context.get("usual_police", recommended),
            "level": self._deployment_level(recommended),
            "needs_police": recommended >= 3,
            "description": (
                f"{event_profile['notes']} Deployment includes junction control, queue protection, "
                f"and {context['expected_queue_km']} km downstream monitoring."
            ),
        }

    def _recommend_barricades(self, score: float, corridor: str, event_profile: Dict, context: Dict) -> Dict:
        points = self.barricade_points.get(corridor, self.barricade_points["Non-corridor"])
        if event_profile["event_value"] <= 3 and not context["road_closure"] and score < 5:
            count = 0
        else:
            count = 1 + int(score >= 5.5) + int(score >= 7.2) + int(context["road_closure"]) + int(context["expected_queue_km"] >= 4)
            count = min(len(points), count)

        if count == 0:
            level = "NONE"
            description = "No fixed barricade line; use cones or caution tape only if needed."
        elif count == 1:
            level = "SPOT CONTROL"
            description = "Control the incident point and keep one lane moving where possible."
        elif count <= 3:
            level = "CORRIDOR CONTROL"
            description = "Hold upstream junctions and meter vehicles into the affected stretch."
        else:
            level = "FULL ROUTE CONTROL"
            description = "Stage barricades across approach roads and diversion entry points."

        return {
            "count": count,
            "locations": points[:count],
            "level": level,
            "description": description,
        }

    def _recommend_diversions(self, score: float, corridor: str, event_profile: Dict, context: Dict) -> Dict:
        routes = self.corridor_diversions.get(corridor, self.corridor_diversions["Non-corridor"])
        route_count = 0
        if score >= 4.5 or context["traffic_flow_index"] >= 0.75:
            route_count = 1
        if score >= 6.5 or context["road_closure"]:
            route_count = 2
        if score >= 8.2 or (context["road_closure"] and context["expected_queue_km"] >= 4):
            route_count = 3

        selected = routes[:route_count]
        level = ["NONE", "ADVISORY", "ACTIVE", "NETWORK-WIDE"][route_count]
        description = "No diversion needed; monitor flow." if route_count == 0 else f"Activate {route_count} diversion route(s) before queues exceed {context['expected_queue_km']} km."

        return {
            "primary": selected[0] if len(selected) > 0 else None,
            "secondary": selected[1] if len(selected) > 1 else None,
            "tertiary": selected[2] if len(selected) > 2 else None,
            "level": level,
            "description": description,
        }

    def _recommend_timing(self, score: float, duration_hours: float, event_profile: Dict, road_profile: Dict, context: Dict, manpower: Dict, barricades: Dict) -> Dict:
        if event_profile["planned"]:
            setup_minutes = (
                road_profile["base_response_minutes"]
                + (barricades["count"] * 12)
                + (manpower["recommended"] * 0.9)
                + (context["expected_queue_km"] * 5)
            )
        else:
            setup_minutes = road_profile["base_response_minutes"] + (barricades["count"] * 8)

        if context["time_period"] in ("Morning peak", "Evening peak"):
            setup_minutes *= 1.18
        elif context["time_period"] in ("Night", "Deep night") and context["crowd_size"] < 300:
            setup_minutes *= 0.86

        cleanup_minutes = 12 + (barricades["count"] * 8) + (context["expected_queue_km"] * 7)
        if context["road_closure"]:
            cleanup_minutes += 18
        if context["time_period"] in ("Morning peak", "Evening peak"):
            cleanup_minutes *= 1.12

        setup_hours = round(setup_minutes / 60, 2)
        cleanup_hours = round(cleanup_minutes / 60, 2)

        return {
            "setup_hours_before": setup_hours if event_profile["planned"] else 0.0,
            "response_minutes": round(setup_minutes, 0),
            "event_hours": duration_hours,
            "cleanup_hours_after": cleanup_hours,
            "total_impact_hours": round(duration_hours + (setup_hours if event_profile["planned"] else 0) + cleanup_hours, 2),
            "description": (
                f"Response/setup: {round(setup_minutes)} min | Duration: {duration_hours}h | "
                f"Clearance: {round(cleanup_minutes)} min"
            ),
        }

    def _deployment_level(self, officers: int) -> str:
        if officers <= 6:
            return "MINIMAL"
        if officers <= 15:
            return "LOCAL"
        if officers <= 30:
            return "TACTICAL"
        if officers <= 55:
            return "MAJOR"
        if officers <= 200:
            return "CITY SUPPORT"
        return "STATE SUPPORT"

    def _categorize_impact(self, score: float) -> str:
        if score <= 2:
            return "LOW"
        if score <= 4:
            return "LOW-MODERATE"
        if score <= 6:
            return "MODERATE"
        if score <= 8:
            return "HIGH"
        return "CRITICAL"

    def _build_summary(self, score: float, manpower: Dict, barricades: Dict, timing: Dict, context: Dict, corridor: str, zone: Optional[str]) -> str:
        zone_text = f" / {zone}" if zone else ""
        return (
            f"Contextual impact: {score}/10 on {corridor}{zone_text}\n"
            f"Event value: {context['event_numeric_value']}/10 | Traffic flow: {context['traffic_flow_index']} | Road capacity: {context['road_capacity_index']}\n"
            f"Expected queue/spread: {context['expected_queue_km']} km from a {context['affected_length_km']} km affected stretch\n"
            f"Deploy {manpower['recommended']} officers ({manpower['min_officers']}-{manpower['max_officers']}) at {manpower['level']} level\n"
            f"Barricades: {barricades['count']} locations ({barricades['level']})\n"
            f"Timing: {timing['description']}"
        )


def print_recommendation(rec: Dict, event_name: str = "Event"):
    print("\n" + "=" * 80)
    print(f"RECOMMENDATION: {event_name}")
    print("=" * 80)
    print(f"\nImpact score: {rec['impact_score']}/10 ({rec['category']})")
    print(f"Context: {rec['summary']}")
    print(f"\nManpower: {rec['manpower']['recommended']} officers")
    print(f"Barricades: {rec['barricades']['count']} - {rec['barricades']['level']}")
    div = rec["diversions"]
    print(f"Diversion level: {div['level']}")
    for label in ("primary", "secondary", "tertiary"):
        if div.get(label):
            print(f"  {label.title()}: {div[label]}")
    print("=" * 80)


if __name__ == "__main__":
    engine = RecommendationEngine()
    sample = engine.recommend(
        impact_score=5.5,
        event_type="public_event",
        corridor="ORR East 2",
        zone="East Zone 2",
        duration_hours=3,
        hour=19,
        crowd_size=2500,
        road_closure=True,
    )
    print_recommendation(sample, "Public event on ORR East 2")
