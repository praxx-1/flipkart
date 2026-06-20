"""
INTEGRATION EXAMPLES - Connect Existing Traffic System to Escalated Engine
Use these code snippets to integrate with your existing Bengaluru traffic system.
"""

import requests
import json
from typing import Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# EXAMPLE 1: HTTP CLIENT FOR REST API
# ============================================================================

class TrafficRecommendationClient:
    """
    HTTP client to call the escalated recommendation API.
    Use this if API is running on a separate server.
    """
    
    def __init__(self, api_url: str = "http://localhost:5000"):
        self.api_url = api_url
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def recommend(self, event_data: Dict) -> Dict:
        """Call /v2/recommend endpoint"""
        try:
            response = self.session.post(
                f"{self.api_url}/v2/recommend",
                json=event_data,
                timeout=5
            )
            result = response.json()
            
            if response.status_code != 200:
                logger.error(f"API error: {result.get('validation_errors')}")
            
            return result
        except requests.exceptions.RequestException as e:
            logger.error(f"API connection error: {e}")
            return {"error": str(e), "success": False}
    
    def validate(self, event_data: Dict) -> Dict:
        """Call /v2/validate endpoint"""
        response = self.session.post(
            f"{self.api_url}/v2/validate",
            json=event_data,
            timeout=5
        )
        return response.json()
    
    def check_conflicts(self, corridor: str, zone: str, manpower: int) -> Dict:
        """Call /v2/conflicts/check endpoint"""
        response = self.session.post(
            f"{self.api_url}/v2/conflicts/check",
            json={
                "corridor": corridor,
                "zone": zone,
                "manpower_needed": manpower,
            },
            timeout=5
        )
        return response.json()
    
    def get_active_events(self) -> Dict:
        """Call /v2/events/active endpoint"""
        response = self.session.get(
            f"{self.api_url}/v2/events/active",
            timeout=5
        )
        return response.json()
    
    def resolve_event(self, event_id: str) -> Dict:
        """Call /v2/events/{event_id}/resolve endpoint"""
        response = self.session.post(
            f"{self.api_url}/v2/events/{event_id}/resolve",
            timeout=5
        )
        return response.json()


# ============================================================================
# EXAMPLE 2: DIRECT IMPORT (SAME PROCESS)
# ============================================================================

class TrafficRecommendationDirect:
    """
    Direct import if engine is in same process.
    Faster, no HTTP overhead, but tightly coupled.
    """
    
    def __init__(self):
        from escalated_engine import EscalatedRecommendationEngine
        self.engine = EscalatedRecommendationEngine()
    
    def recommend(self, event_id: str, **kwargs) -> Dict:
        """Call engine directly"""
        return self.engine.recommend(event_id=event_id, **kwargs)
    
    def get_active_events(self) -> list:
        """Get list of active events"""
        return list(self.engine.conflict_detector.active_events.keys())


# ============================================================================
# EXAMPLE 3: INTEGRATION WITH EXISTING TRAFFIC MANAGEMENT SYSTEM
# ============================================================================

class TrafficPoliceDispatcher:
    """
    Example integration with existing traffic dispatch system.
    This would replace or augment your current dispatch logic.
    """
    
    def __init__(self, use_http: bool = False, api_url: str = "http://localhost:5000"):
        """
        Initialize dispatcher.
        
        Args:
            use_http: If True, use HTTP API. If False, direct import.
            api_url: URL of the API server if use_http=True
        """
        if use_http:
            self.client = TrafficRecommendationClient(api_url)
        else:
            self.client = TrafficRecommendationDirect()
        
        self.escalation_handlers = {
            "ESCALATE_TO_CITY_COMMISSIONER": self._notify_city_commissioner,
            "ESCALATE_TO_STATE_POLICE": self._notify_state_police,
            "ACTIVATE_EMERGENCY_PROTOCOL": self._activate_emergency_protocol,
            "REQUEST_MUTUAL_AID": self._request_mutual_aid,
        }
    
    def handle_traffic_event(self, event_data: Dict) -> Dict:
        """
        Main dispatcher method. Call this when a traffic event occurs.
        
        Args:
            event_data: {
                "event_id": "EVT_001",
                "event_type": "accident",
                "corridor": "ORR East 2",
                "zone": "East Zone 2",
                "hour": 14,
                ...
            }
        
        Returns:
            Deployment action with all details
        """
        logger.info(f"Handling event: {event_data.get('event_id')}")
        
        # Get recommendation from engine
        recommendation = self.client.recommend(event_data)
        
        if not recommendation.get("success"):
            logger.error(f"Recommendation failed: {recommendation.get('validation_errors')}")
            return {
                "success": False,
                "error": recommendation.get("validation_errors"),
            }
        
        rec = recommendation.get("recommendation", {})
        escalations = recommendation.get("escalations", [])
        conflicts = recommendation.get("conflicts", {})
        
        # Build deployment action
        action = {
            "event_id": event_data.get("event_id"),
            "timestamp": datetime.now().isoformat(),
            "impact_score": rec.get("impact_score"),
            "category": rec.get("category"),
            "deployment": {
                "manpower": rec.get("manpower", {}).get("recommended"),
                "manpower_range": (
                    rec.get("manpower", {}).get("min_officers"),
                    rec.get("manpower", {}).get("max_officers")
                ),
                "barricades": rec.get("barricades", {}).get("count"),
                "diversion_routes": [
                    rec.get("diversions", {}).get("primary"),
                    rec.get("diversions", {}).get("secondary"),
                    rec.get("diversions", {}).get("tertiary"),
                ],
            },
            "timing": rec.get("setup_cleanup"),
            "conflict_alerts": conflicts.get("corridor_conflicts", []),
            "escalations": [],
        }
        
        # Handle escalations
        if escalations:
            logger.warning(f"Event {event_data.get('event_id')} requires escalations")
            for esc in escalations:
                action["escalations"].append({
                    "rule": esc["rule"],
                    "action": esc["action"],
                    "notification": esc.get("notification"),
                })
                # Execute escalation handler
                handler = self.escalation_handlers.get(esc["action"])
                if handler:
                    handler(event_data, esc, rec)
        
        logger.info(f"Deployment action ready for {event_data.get('event_id')}")
        return action
    
    # ===== ESCALATION HANDLERS =====
    
    def _notify_city_commissioner(self, event_data, escalation, recommendation):
        """Notify city commissioner"""
        message = (
            f"URGENT: Event {event_data.get('event_id')} on {event_data.get('corridor')}\n"
            f"Impact: {recommendation.get('impact_score')}/10\n"
            f"Queue expected: {recommendation.get('context', {}).get('expected_queue_km')} km\n"
            f"Manpower needed: {recommendation.get('manpower', {}).get('recommended')}"
        )
        logger.critical(f"CITY COMMISSIONER ALERT: {message}")
        # TODO: Integrate with actual SMS/email system
        # send_sms("city.commissioner", message)
    
    def _notify_state_police(self, event_data, escalation, recommendation):
        """Notify state police"""
        message = (
            f"CRITICAL: Event {event_data.get('event_id')} escalated to STATE level\n"
            f"Corridor: {event_data.get('corridor')}\n"
            f"Impact: {recommendation.get('impact_score')}/10 - {recommendation.get('category')}\n"
            f"Road closure required: {recommendation.get('context', {}).get('road_closure')}"
        )
        logger.critical(f"STATE POLICE ALERT: {message}")
        # TODO: Integrate with state police notification system
    
    def _activate_emergency_protocol(self, event_data, escalation, recommendation):
        """Activate emergency protocol"""
        logger.critical(f"EMERGENCY PROTOCOL ACTIVATED for {event_data.get('event_id')}")
        # TODO: Trigger emergency sirens, close all diversions, alert public
    
    def _request_mutual_aid(self, event_data, escalation, recommendation):
        """Request mutual aid from adjacent zones"""
        zone = event_data.get("zone")
        logger.warning(f"MUTUAL AID REQUEST for zone {zone}")
        # TODO: Contact adjacent zone commanders


# ============================================================================
# EXAMPLE 4: INTEGRATION WITH EXISTING DISPATCH SYSTEM
# ============================================================================

class LegacySystemAdapter:
    """
    Adapter to integrate new escalated engine with legacy dispatch system.
    Translates between old format and new format.
    """
    
    def __init__(self):
        self.dispatcher = TrafficPoliceDispatcher(use_http=False)
    
    def process_legacy_event(self, legacy_event: Dict) -> Dict:
        """
        Convert legacy event format to new format and get recommendation.
        
        Legacy format (old):
        {
            "id": "INC_123",
            "type": "ACCIDENT",
            "road": "ORR East",
            "location": "Silk Board",
            "severity": 5,
            ...
        }
        
        New format:
        {
            "event_id": "EVT_...",
            "event_type": "accident",
            "corridor": "ORR East 2",
            "zone": "East Zone 2",
            "impact_score": 5,
            ...
        }
        """
        
        # Map legacy to new format
        event_mapping = {
            "ACCIDENT": "accident",
            "CONGESTION": "congestion",
            "VIP": "vip_movement",
            "PROCESSION": "procession",
            "CONSTRUCTION": "construction",
            "BREAKDOWN": "vehicle_breakdown",
        }
        
        road_mapping = {
            "ORR East": "ORR East 2",
            "ORR North": "ORR North",
            "ORR West": "ORR North",  # approximation
            "CBD": "CBD-2",
            "Mysore Rd": "Mysore Road",
            "Hosur": "Hosur Road",
        }
        
        new_event = {
            "event_id": legacy_event.get("id", "EVT_UNKNOWN"),
            "event_type": event_mapping.get(legacy_event.get("type", "CONGESTION").upper(), "congestion"),
            "corridor": road_mapping.get(legacy_event.get("road", ""), "Non-corridor"),
            "impact_score": legacy_event.get("severity", 5),
            "duration_hours": legacy_event.get("duration", 1),
            "hour": datetime.now().hour,
        }
        
        # Get recommendation
        return self.dispatcher.handle_traffic_event(new_event)


# ============================================================================
# EXAMPLE 5: COMMAND-LINE USAGE
# ============================================================================

def cli_example():
    """Example command-line usage"""
    
    # Initialize dispatcher (direct import, faster)
    dispatcher = TrafficPoliceDispatcher(use_http=False)
    
    # Example event
    event = {
        "event_id": "EVT_20250620_ACCIDENT_001",
        "event_type": "accident",
        "corridor": "ORR East 2",
        "zone": "East Zone 2",
        "hour": 17,  # 5 PM
        "duration_hours": 1.5,
        "crowd_size": 200,
        "impact_score": 6.5,
    }
    
    # Get deployment action
    action = dispatcher.handle_traffic_event(event)
    
    # Print results
    print(json.dumps(action, indent=2, default=str))
    
    # Extract key actions
    print("\n" + "="*80)
    print("DEPLOYMENT SUMMARY")
    print("="*80)
    print(f"Event: {action['event_id']}")
    print(f"Impact: {action['impact_score']}/10 ({action['category']})")
    print(f"Deploy: {action['deployment']['manpower']} officers")
    print(f"Setup: {action['timing']['response_minutes']} minutes")
    
    if action['escalations']:
        print(f"\n⚠️  ESCALATIONS REQUIRED ({len(action['escalations'])}):")
        for esc in action['escalations']:
            print(f"  - {esc['action']}")


# ============================================================================
# EXAMPLE 6: ASYNC MONITORING WITH ACTIVE EVENTS
# ============================================================================

def monitor_active_events():
    """
    Monitor currently active events and check for conflicts.
    Run this in a separate thread/process.
    """
    import time
    
    client = TrafficRecommendationClient()
    
    while True:
        try:
            active = client.get_active_events()
            print(f"[{datetime.now()}] Active events: {active['count']}")
            
            for event in active['active_events']:
                print(f"  - {event['event_id']}: {event['corridor']} "
                      f"(Impact: {event['impact_score']}, Manpower: {event['manpower']})")
            
            time.sleep(30)  # Check every 30 seconds
        
        except Exception as e:
            print(f"Error monitoring: {e}")
            time.sleep(60)


# ============================================================================
# EXAMPLE 7: PYTHON SCRIPT - QUICK START
# ============================================================================

if __name__ == "__main__":
    """
    Quick start: python integration.py
    """
    
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python integration.py [scenario]")
        print("Scenarios:")
        print("  1. Simple accident")
        print("  2. Escalated procession")
        print("  3. Critical VIP movement")
        sys.exit(1)
    
    scenario = sys.argv[1]
    
    dispatcher = TrafficPoliceDispatcher(use_http=False)
    
    scenarios = {
        "1": {
            "event_id": "EVT_001_ACCIDENT",
            "event_type": "accident",
            "corridor": "Tumkur Road",
            "zone": "North Zone 1",
            "impact_score": 3.5,
            "hour": 10,
        },
        "2": {
            "event_id": "EVT_002_PROCESSION",
            "event_type": "procession",
            "corridor": "ORR East 2",
            "zone": "East Zone 2",
            "impact_score": 8.0,
            "crowd_size": 15000,
            "hour": 16,
            "road_closure": True,
        },
        "3": {
            "event_id": "EVT_003_VIP",
            "event_type": "vip_movement",
            "corridor": "CBD-2",
            "zone": "Central",
            "impact_score": 9.2,
            "hour": 17,
            "duration_hours": 2,
        }
    }
    
    event = scenarios.get(scenario)
    if not event:
        print(f"Unknown scenario: {scenario}")
        sys.exit(1)
    
    action = dispatcher.handle_traffic_event(event)
    print(json.dumps(action, indent=2, default=str))
