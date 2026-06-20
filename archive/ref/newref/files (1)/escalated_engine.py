"""
PHASE 5: ESCALATED CONTEXTUAL RECOMMENDATION ENGINE
Enhanced with real-time conflict detection, validation, escalation rules, and audit logging.
Production-ready for Bengaluru Traffic Police operations.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List, Tuple
from enum import Enum
import hashlib

try:
    import pandas as pd
except ImportError:
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
            f"ESCALATION:{rec.get('escalation_required')}"
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
    
    VALID_ZONES = {
        "North", "South", "East", "West", "Central", 
        "East Zone 1", "East Zone 2", "North Zone 1", "North Zone 2"
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
        if event_type and event_type.lower() not in InputValidator.VALID_EVENT_TYPES:
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
        
        # Zone validation
        if zone and zone not in InputValidator.VALID_ZONES:
            errors.append(
                f"zone '{zone}' not recognized. "
                f"Valid: {InputValidator.VALID_ZONES}"
            )
        
        # Duration: 0.25-24 hours
        if duration_hours is not None:
            if not (0.25 <= duration_hours <= 24):
                errors.append(f"duration_hours must be 0.25-24, got {duration_hours}")
        
        # Hour: 0-23
        if hour is not None:
            if not (0 <= hour <= 23):
                errors.append(f"hour must be 0-23, got {hour}")
        
        # Crowd size: non-negative
        if crowd_size is not None:
            if crowd_size < 0:
                errors.append(f"crowd_size cannot be negative, got {crowd_size}")
            if crowd_size > 500000:  # Sanity check: Bengaluru population ~10M
                errors.append(f"crowd_size exceeds sanity limit (500K), got {crowd_size}")
        
        # Affected length: positive
        if affected_length_km is not None:
            if affected_length_km <= 0:
                errors.append(f"affected_length_km must be positive, got {affected_length_km}")
            if affected_length_km > 50:  # No road stretch in BLR is 50+ km
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
        - 'divert': Reroute lower-priority event
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


# ============================================================================
# ENHANCED RECOMMENDATION ENGINE
# ============================================================================

class EscalatedRecommendationEngine:
    """
    Enhanced engine with validation, conflict detection, escalation rules,
    and audit logging.
    """
    
    def __init__(self, audit_log_dir: str = "/tmp/traffic_audit"):
        self.audit_logger = AuditLogger(audit_log_dir)
        self.conflict_detector = ConflictDetector()
        self.validator = InputValidator()
        
        # Base corridors and profiles (from original)
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

        self.location_profiles = {
            "Mysore Road": {"traffic_flow_index": 0.74, "road_capacity_index": 0.70, "lanes": 6, "typical_spread_km": 2.8, "base_response_minutes": 24, "avg_speed_kmh": 21},
            "Bellary Road 1": {"traffic_flow_index": 0.80, "road_capacity_index": 0.68, "lanes": 6, "typical_spread_km": 2.5, "base_response_minutes": 22, "avg_speed_kmh": 16},
            "Bellary Road 2": {"traffic_flow_index": 0.76, "road_capacity_index": 0.66, "lanes": 6, "typical_spread_km": 2.3, "base_response_minutes": 25, "avg_speed_kmh": 19},
            "ORR North": {"traffic_flow_index": 0.84, "road_capacity_index": 0.62, "lanes": 6, "typical_spread_km": 3.4, "base_response_minutes": 26, "avg_speed_kmh": 14},
            "ORR East 1": {"traffic_flow_index": 0.96, "road_capacity_index": 0.44, "lanes": 6, "typical_spread_km": 5.2, "base_response_minutes": 28, "avg_speed_kmh": 9},
            "ORR East 2": {"traffic_flow_index": 0.95, "road_capacity_index": 0.46, "lanes": 6, "typical_spread_km": 5.6, "base_response_minutes": 30, "avg_speed_kmh": 10},
            "CBD-2": {"traffic_flow_index": 0.88, "road_capacity_index": 0.48, "lanes": 4, "typical_spread_km": 3.2, "base_response_minutes": 18, "avg_speed_kmh": 12},
            "Bangalore-Mysore Road": {"traffic_flow_index": 0.68, "road_capacity_index": 0.78, "lanes": 6, "typical_spread_km": 2.4, "base_response_minutes": 24, "avg_speed_kmh": 35},
            "Hosur Road": {"traffic_flow_index": 0.88, "road_capacity_index": 0.58, "lanes": 6, "typical_spread_km": 3.8, "base_response_minutes": 25, "avg_speed_kmh": 13},
            "Tumkur Road": {"traffic_flow_index": 0.78, "road_capacity_index": 0.72, "lanes": 6, "typical_spread_km": 2.7, "base_response_minutes": 26, "avg_speed_kmh": 17},
            "Non-corridor": {"traffic_flow_index": 0.55, "road_capacity_index": 0.42, "lanes": 2, "typical_spread_km": 1.2, "base_response_minutes": 20, "avg_speed_kmh": 25},
        }

        self.event_profiles = {
            "vip_movement": {"event_value": 8.6, "crowd_load": 1.35, "blockage_factor": 1.20, "police_complexity": 1.50, "planned": True},
            "procession": {"event_value": 8.2, "crowd_load": 1.45, "blockage_factor": 1.35, "police_complexity": 1.35, "planned": True},
            "public_event": {"event_value": 7.0, "crowd_load": 1.25, "blockage_factor": 1.10, "police_complexity": 1.15, "planned": True},
            "accident": {"event_value": 6.1, "crowd_load": 0.55, "blockage_factor": 1.00, "police_complexity": 0.80, "planned": False},
            "construction": {"event_value": 5.5, "crowd_load": 0.35, "blockage_factor": 0.95, "police_complexity": 0.65, "planned": True},
            "vehicle_breakdown": {"event_value": 3.8, "crowd_load": 0.12, "blockage_factor": 0.65, "police_complexity": 0.35, "planned": False},
            "pot_hole": {"event_value": 2.8, "crowd_load": 0.05, "blockage_factor": 0.45, "police_complexity": 0.20, "planned": False},
            "water_logging": {"event_value": 6.8, "crowd_load": 0.20, "blockage_factor": 1.25, "police_complexity": 0.90, "planned": False},
            "tree_fall": {"event_value": 4.8, "crowd_load": 0.10, "blockage_factor": 0.85, "police_complexity": 0.45, "planned": False},
            "congestion": {"event_value": 5.2, "crowd_load": 0.00, "blockage_factor": 1.20, "police_complexity": 0.55, "planned": False},
        }

        self.event_baselines = {
            "vip_movement": {"affected_people": 3500, "duration_hours": 1.5, "spread_km": 3.0, "usual_police": 25},
            "procession": {"affected_people": 6000, "duration_hours": 3.0, "spread_km": 4.0, "usual_police": 30},
            "public_event": {"affected_people": 4500, "duration_hours": 3.0, "spread_km": 2.5, "usual_police": 25},
            "accident": {"affected_people": 650, "duration_hours": 1.0, "spread_km": 1.4, "usual_police": 8},
            "construction": {"affected_people": 1200, "duration_hours": 4.0, "spread_km": 2.0, "usual_police": 6},
            "vehicle_breakdown": {"affected_people": 350, "duration_hours": 1.0, "spread_km": 0.9, "usual_police": 4},
            "pot_hole": {"affected_people": 180, "duration_hours": 0.8, "spread_km": 0.5, "usual_police": 0},
            "water_logging": {"affected_people": 1800, "duration_hours": 2.0, "spread_km": 2.2, "usual_police": 12},
            "tree_fall": {"affected_people": 500, "duration_hours": 1.4, "spread_km": 1.1, "usual_police": 5},
            "congestion": {"affected_people": 1200, "duration_hours": 1.0, "spread_km": 1.8, "usual_police": 4},
        }
    
    def recommend(
        self,
        event_id: str,
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
    ) -> Dict:
        """
        Main recommendation endpoint with full escalation logic.
        
        Returns dict with:
        - recommendation: Core recommendation data
        - escalations: List of triggered escalation rules
        - conflicts: Any resource conflicts detected
        - validation_errors: Any input errors
        """
        
        # ========== STEP 1: VALIDATE INPUTS ==========
        is_valid, errors = self.validator.validate(
            impact_score, event_type, corridor, zone, 
            duration_hours, hour, crowd_size, affected_length_km, live_traffic_index
        )
        
        if not is_valid:
            return {
                "event_id": event_id,
                "success": False,
                "validation_errors": errors,
                "recommendation": None,
                "escalations": [],
            }
        
        # ========== STEP 2: NORMALIZE INPUTS ==========
        event_type_clean = str(event_type or "congestion").lower().strip()
        corridor_key = corridor if corridor in self.location_profiles else "Non-corridor"
        hour = 12 if hour is None else int(hour) % 24
        
        event_profile = self.event_profiles.get(event_type_clean, self.event_profiles["congestion"])
        road_profile = self.location_profiles[corridor_key]
        baseline = {
            "base_impact_score": impact_score or event_profile["event_value"],
            "affected_people": crowd_size or self.event_baselines[event_type_clean]["affected_people"],
            "duration_hours": duration_hours or self.event_baselines[event_type_clean]["duration_hours"],
            "spread_km": affected_length_km or self.event_baselines[event_type_clean]["spread_km"],
            "traffic_flow_index": live_traffic_index or road_profile["traffic_flow_index"],
            "usual_police": self.event_baselines[event_type_clean]["usual_police"],
        }
        
        # ========== STEP 3: CALCULATE CONTEXTUAL SCORE ==========
        context = self._contextual_assessment(
            base_score=baseline["base_impact_score"],
            event_profile=event_profile,
            road_profile=road_profile,
            duration_hours=baseline["duration_hours"],
            hour=hour,
            crowd_size=baseline["affected_people"],
            road_closure=road_closure or False,
            affected_length_km=baseline["spread_km"],
            live_traffic_index=baseline["traffic_flow_index"],
        )
        
        score = context["contextual_impact_score"]
        
        # ========== STEP 4: GENERATE RECOMMENDATIONS ==========
        manpower = self._recommend_manpower(score, event_profile, road_profile, context)
        barricades = self._recommend_barricades(score, corridor_key, event_profile, context)
        diversions = self._recommend_diversions(score, corridor_key, event_profile, context)
        timing = self._recommend_timing(score, baseline["duration_hours"], event_profile, road_profile, context, manpower, barricades)
        
        # ========== STEP 5: DETECT CONFLICTS ==========
        corridor_conflicts = self.conflict_detector.check_corridor_conflict(
            corridor_key, event_type_clean, baseline["duration_hours"]
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
            "affected_people": baseline["affected_people"],
            "road_closure": road_closure or False,
            "manpower_needed": manpower["recommended"],
            "manpower_deficit": max(0, manpower["recommended"] - (200 if not manpower_conflict else 50)),
        }
        
        escalations = EscalationRulesEngine.evaluate(escalation_context)
        escalation_required = len(escalations) > 0
        
        # ========== STEP 7: BUILD FINAL RESPONSE ==========
        recommendation = {
            "event_id": event_id,
            "timestamp": datetime.now().isoformat(),
            "impact_score": score,
            "base_impact_score": round(max(0, min(10, baseline["base_impact_score"])), 1),
            "category": self._categorize_impact(score),
            "manpower": manpower,
            "barricades": barricades,
            "diversions": diversions,
            "setup_cleanup": timing,
            "context": context,
            "baseline": baseline,
        }
        
        result = {
            "event_id": event_id,
            "success": True,
            "recommendation": recommendation,
            "escalations": [
                {
                    "rule": rule,
                    "action": action,
                    "notification": notif
                }
                for rule, action, notif in escalations
            ],
            "escalation_required": escalation_required,
            "conflicts": conflicts,
            "validation_errors": [],
        }
        
        # ========== STEP 8: AUDIT LOG ==========
        self.audit_logger.log_recommendation(event_id, recommendation, "ENGINE")
        if escalation_required:
            self.audit_logger.log_escalation(
                event_id,
                "ZONE",
                escalations[0][1] if escalations else "UNKNOWN",
                f"Score {score}/10, {len(escalations)} rules triggered"
            )
        if conflicts["corridor_conflicts"]:
            self.audit_logger.log_conflict(
                event_id,
                corridor_conflicts,
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
    
    # ========== HELPER METHODS (Simplified from original) ==========
    
    def _contextual_assessment(self, base_score, event_profile, road_profile, 
                              duration_hours, hour, crowd_size, road_closure, 
                              affected_length_km, live_traffic_index):
        traffic_flow = road_profile["traffic_flow_index"] if live_traffic_index is None else live_traffic_index
        
        if 7 <= hour <= 10:
            time_factor = 1.30
            time_label = "Morning peak"
        elif 16 <= hour <= 20:
            time_factor = 1.45
            time_label = "Evening peak"
        elif hour >= 22 or hour <= 4:
            time_factor = 0.45 if 0 <= hour <= 4 else 0.55
            time_label = "Deep night" if 0 <= hour <= 4 else "Night"
        else:
            time_factor = 1.0
            time_label = "Off-peak"
        
        capacity_pressure = max(0, traffic_flow - road_profile["road_capacity_index"] + 0.35)
        crowd_pressure = min(1.35, crowd_size / 10000) * event_profile["crowd_load"]
        closure_pressure = 1.35 if road_closure else 0
        spread_km = affected_length_km or road_profile["typical_spread_km"]
        
        contextual_score = (
            (base_score * 0.45) +
            (event_profile["event_value"] * 0.22) +
            (traffic_flow * 2.2) +
            (capacity_pressure * 1.6) +
            event_profile["blockage_factor"] +
            crowd_pressure +
            closure_pressure +
            (spread_km / max(1.0, road_profile["typical_spread_km"]) * 0.8)
        ) * time_factor
        
        contextual_score = round(max(0, min(10, contextual_score)), 1)
        expected_queue_km = round(max(0.3, spread_km * (0.55 + traffic_flow + capacity_pressure + (0.35 if road_closure else 0))), 1)
        
        return {
            "contextual_impact_score": contextual_score,
            "traffic_flow_index": round(traffic_flow, 2),
            "time_period": time_label,
            "expected_queue_km": expected_queue_km,
            "crowd_size": crowd_size,
            "road_closure": bool(road_closure),
            "affected_length_km": round(spread_km, 1),
        }
    
    def _recommend_manpower(self, score, event_profile, road_profile, context):
        base = context.get("usual_police", 5)
        raw = base * (1.0 + (context["traffic_flow_index"] - 0.5) * 0.4)
        if context["road_closure"]:
            raw += 5
        raw += min(10, context["expected_queue_km"] * 0.5)
        
        recommended = int(round(max(0, raw)))
        return {
            "recommended": recommended,
            "min_officers": max(0, int(round(recommended * 0.75))),
            "max_officers": int(round(recommended * 1.30)),
            "level": self._deployment_level(recommended),
        }
    
    def _recommend_barricades(self, score, corridor, event_profile, context):
        points = self.barricade_points.get(corridor, self.barricade_points["Non-corridor"])
        count = min(len(points), 1 + int(score >= 5.5) + int(score >= 7.2) + int(context["road_closure"]))
        level = ["NONE", "SPOT CONTROL", "CORRIDOR CONTROL", "FULL ROUTE CONTROL"][min(count, 3)]
        return {
            "count": count,
            "locations": points[:count],
            "level": level,
        }
    
    def _recommend_diversions(self, score, corridor, event_profile, context):
        routes = self.corridor_diversions.get(corridor, self.corridor_diversions["Non-corridor"])
        route_count = int(score >= 4.5) + int(score >= 6.5) + int(score >= 8.2)
        level = ["NONE", "ADVISORY", "ACTIVE", "NETWORK-WIDE"][min(route_count, 3)]
        selected = routes[:route_count]
        return {
            "primary": selected[0] if len(selected) > 0 else None,
            "secondary": selected[1] if len(selected) > 1 else None,
            "tertiary": selected[2] if len(selected) > 2 else None,
            "level": level,
        }
    
    def _recommend_timing(self, score, duration, event_profile, road_profile, context, manpower, barricades):
        setup_mins = road_profile["base_response_minutes"] + (barricades["count"] * 12) + (manpower["recommended"] * 0.9)
        cleanup_mins = 12 + (barricades["count"] * 8) + (context["expected_queue_km"] * 7)
        if context["road_closure"]:
            cleanup_mins += 18
        
        return {
            "response_minutes": round(setup_mins),
            "event_hours": duration,
            "cleanup_hours_after": round(cleanup_mins / 60, 2),
            "total_impact_hours": round(duration + cleanup_mins / 60, 2),
        }
    
    def _deployment_level(self, officers):
        levels = [(6, "MINIMAL"), (15, "LOCAL"), (30, "TACTICAL"), (55, "MAJOR"), (200, "CITY SUPPORT")]
        for threshold, level in levels:
            if officers <= threshold:
                return level
        return "STATE SUPPORT"
    
    def _categorize_impact(self, score):
        if score <= 2: return "LOW"
        if score <= 4: return "LOW-MODERATE"
        if score <= 6: return "MODERATE"
        if score <= 8: return "HIGH"
        return "CRITICAL"


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    engine = EscalatedRecommendationEngine()
    
    # Test case 1: Normal event (should not escalate)
    result = engine.recommend(
        event_id="EVT_20250620_001",
        impact_score=5.5,
        event_type="accident",
        corridor="ORR East 2",
        zone="East Zone 2",
        duration_hours=1.5,
        hour=19,
        crowd_size=200,
        road_closure=False,
    )
    print(json.dumps(result, indent=2, default=str))
    
    # Test case 2: Critical event (should escalate)
    print("\n" + "="*80 + "\n")
    result = engine.recommend(
        event_id="EVT_20250620_002",
        impact_score=9.2,
        event_type="procession",
        corridor="ORR East 2",
        zone="East Zone 2",
        duration_hours=4.0,
        hour=17,
        crowd_size=15000,
        road_closure=True,
        affected_length_km=6.0,
    )
    print(json.dumps(result, indent=2, default=str))
