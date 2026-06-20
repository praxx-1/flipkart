"""
TRAFFIC POLICE RECOMMENDATION ENGINE - API SERVER
Production-ready Flask application for Bengaluru Traffic Management System
Deploy with: gunicorn -w 4 -b 0.0.0.0:5000 api_server.py
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import logging
import json
import uuid
from escalated_engine import (
    EscalatedRecommendationEngine,
    InputValidator,
    EscalationRulesEngine,
)

# ============================================================================
# FLASK APP SETUP
# ============================================================================

app = Flask(__name__)
CORS(app)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize engine (singleton)
engine = EscalatedRecommendationEngine(audit_log_dir="/tmp/traffic_audit")

# ============================================================================
# HEALTH & STATUS ENDPOINTS
# ============================================================================

@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0-escalated",
    }), 200


@app.route("/status", methods=["GET"])
def status():
    """Engine status and active events"""
    return jsonify({
        "status": "operational",
        "active_events": len(engine.conflict_detector.active_events),
        "timestamp": datetime.now().isoformat(),
    }), 200


# ============================================================================
# CORE ENDPOINTS
# ============================================================================

@app.route("/v2/recommend", methods=["POST"])
def recommend():
    """
    Main recommendation endpoint.
    
    POST /v2/recommend with JSON:
    {
        "event_id": "EVT_20250620_001",  # or auto-generated if not provided
        "impact_score": 5.5,              # optional, 0-10
        "event_type": "accident",         # vip_movement, procession, etc.
        "corridor": "ORR East 2",         # required
        "zone": "East Zone 2",            # optional
        "duration_hours": 1.5,            # optional
        "hour": 19,                       # optional, 0-23
        "crowd_size": 200,                # optional
        "road_closure": false,            # optional
        "affected_length_km": 2.0,        # optional
        "live_traffic_index": 0.85        # optional, 0-1
    }
    """
    try:
        data = request.get_json() or {}
        
        # Auto-generate event_id if not provided
        event_id = data.get("event_id", f"EVT_{uuid.uuid4().hex[:8].upper()}")
        
        # Extract parameters
        result = engine.recommend(
            event_id=event_id,
            impact_score=data.get("impact_score"),
            event_type=data.get("event_type"),
            corridor=data.get("corridor"),
            zone=data.get("zone"),
            duration_hours=data.get("duration_hours"),
            hour=data.get("hour"),
            crowd_size=data.get("crowd_size"),
            road_closure=data.get("road_closure"),
            affected_length_km=data.get("affected_length_km"),
            live_traffic_index=data.get("live_traffic_index"),
        )
        
        # Return with appropriate status code
        status_code = 400 if not result["success"] else 200
        return jsonify(result), status_code
    
    except Exception as e:
        logger.error(f"Recommendation error: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }), 500


@app.route("/v2/validate", methods=["POST"])
def validate():
    """
    Validate event parameters without generating a recommendation.
    Returns detailed validation errors if any.
    """
    try:
        data = request.get_json() or {}
        
        is_valid, errors = InputValidator.validate(
            impact_score=data.get("impact_score"),
            event_type=data.get("event_type"),
            corridor=data.get("corridor"),
            zone=data.get("zone"),
            duration_hours=data.get("duration_hours"),
            hour=data.get("hour"),
            crowd_size=data.get("crowd_size"),
            affected_length_km=data.get("affected_length_km"),
            live_traffic_index=data.get("live_traffic_index"),
        )
        
        return jsonify({
            "valid": is_valid,
            "errors": errors,
            "timestamp": datetime.now().isoformat(),
        }), 200
    
    except Exception as e:
        logger.error(f"Validation error: {str(e)}")
        return jsonify({"error": str(e)}), 500


# ============================================================================
# CONFLICT & ESCALATION ENDPOINTS
# ============================================================================

@app.route("/v2/conflicts/check", methods=["POST"])
def check_conflicts():
    """
    Check for resource conflicts before deploying.
    
    POST with JSON:
    {
        "corridor": "ORR East 2",
        "event_type": "accident",
        "duration_hours": 1.5,
        "zone": "East Zone 2",
        "manpower_needed": 25
    }
    """
    try:
        data = request.get_json() or {}
        
        corridor = data.get("corridor")
        event_type = data.get("event_type")
        duration = data.get("duration_hours", 1.0)
        zone = data.get("zone")
        manpower = data.get("manpower_needed", 0)
        
        corridor_conflicts = engine.conflict_detector.check_corridor_conflict(
            corridor, event_type, duration
        )
        manpower_conflict = engine.conflict_detector.check_manpower_conflict(
            zone or "Central", manpower
        )
        
        return jsonify({
            "corridor_conflicts": corridor_conflicts or [],
            "manpower_shortage": manpower_conflict,
            "has_conflicts": bool(corridor_conflicts or manpower_conflict),
            "timestamp": datetime.now().isoformat(),
        }), 200
    
    except Exception as e:
        logger.error(f"Conflict check error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/v2/escalations/evaluate", methods=["POST"])
def evaluate_escalations():
    """
    Evaluate if a scenario triggers escalation rules.
    
    POST with JSON:
    {
        "impact_score": 8.5,
        "expected_queue_km": 6.0,
        "affected_people": 5000,
        "road_closure": true,
        "manpower_needed": 150
    }
    """
    try:
        data = request.get_json() or {}
        
        context = {
            "impact_score": data.get("impact_score", 0),
            "expected_queue_km": data.get("expected_queue_km", 0),
            "affected_people": data.get("affected_people", 0),
            "road_closure": data.get("road_closure", False),
            "manpower_needed": data.get("manpower_needed", 0),
            "manpower_deficit": max(0, data.get("manpower_needed", 0) - 100),
        }
        
        escalations = EscalationRulesEngine.evaluate(context)
        
        return jsonify({
            "escalations": [
                {
                    "rule": rule,
                    "action": action,
                    "notification": notif
                }
                for rule, action, notif in escalations
            ],
            "triggered": len(escalations) > 0,
            "timestamp": datetime.now().isoformat(),
        }), 200
    
    except Exception as e:
        logger.error(f"Escalation evaluation error: {str(e)}")
        return jsonify({"error": str(e)}), 500


# ============================================================================
# REFERENCE & CONFIGURATION ENDPOINTS
# ============================================================================

@app.route("/v2/reference/corridors", methods=["GET"])
def get_corridors():
    """Get list of all supported corridors"""
    return jsonify({
        "corridors": list(engine.location_profiles.keys()),
        "count": len(engine.location_profiles),
    }), 200


@app.route("/v2/reference/event-types", methods=["GET"])
def get_event_types():
    """Get list of all supported event types"""
    return jsonify({
        "event_types": list(engine.event_profiles.keys()),
        "count": len(engine.event_profiles),
    }), 200


@app.route("/v2/reference/zones", methods=["GET"])
def get_zones():
    """Get list of all supported zones"""
    return jsonify({
        "zones": list(InputValidator.VALID_ZONES),
        "count": len(InputValidator.VALID_ZONES),
    }), 200


@app.route("/v2/reference/corridor/<corridor_name>", methods=["GET"])
def get_corridor_details(corridor_name):
    """Get detailed profile for a corridor"""
    profile = engine.location_profiles.get(corridor_name)
    if not profile:
        return jsonify({
            "error": f"Corridor '{corridor_name}' not found"
        }), 404
    
    diversions = engine.corridor_diversions.get(corridor_name, [])
    barricades = engine.barricade_points.get(corridor_name, [])
    
    return jsonify({
        "corridor": corridor_name,
        "profile": profile,
        "diversion_routes": diversions,
        "barricade_points": barricades,
    }), 200


# ============================================================================
# ACTIVE EVENTS MANAGEMENT
# ============================================================================

@app.route("/v2/events/active", methods=["GET"])
def get_active_events():
    """Get list of currently active events"""
    events = []
    for event_id, event_data in engine.conflict_detector.active_events.items():
        events.append({
            "event_id": event_id,
            "corridor": event_data.get("corridor"),
            "zone": event_data.get("zone"),
            "impact_score": event_data.get("impact_score"),
            "manpower": event_data.get("manpower", {}).get("recommended"),
            "registered_at": event_data.get("registered_at"),
        })
    
    return jsonify({
        "active_events": events,
        "count": len(events),
        "timestamp": datetime.now().isoformat(),
    }), 200


@app.route("/v2/events/<event_id>", methods=["GET"])
def get_event(event_id):
    """Get details of a specific event"""
    event = engine.conflict_detector.active_events.get(event_id)
    if not event:
        return jsonify({
            "error": f"Event '{event_id}' not found"
        }), 404
    
    return jsonify({
        "event_id": event_id,
        "details": event,
    }), 200


@app.route("/v2/events/<event_id>/resolve", methods=["POST"])
def resolve_event(event_id):
    """Mark an event as resolved"""
    if event_id not in engine.conflict_detector.active_events:
        return jsonify({
            "error": f"Event '{event_id}' not found"
        }), 404
    
    # Remove from active events
    del engine.conflict_detector.active_events[event_id]
    
    engine.audit_logger.logger.info(f"EVENT_RESOLVED: {event_id}")
    
    return jsonify({
        "success": True,
        "event_id": event_id,
        "action": "resolved",
        "timestamp": datetime.now().isoformat(),
    }), 200


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(400)
def bad_request(error):
    return jsonify({"error": "Bad request", "message": str(error)}), 400


@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal error: {str(error)}")
    return jsonify({"error": "Internal server error"}), 500


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    # Development server (use gunicorn in production)
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False,
        threaded=True,
    )
