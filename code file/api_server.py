"""
Gridlock REST API Server (v2)
Flask wrapper around the RecommendationEngine for traffic-police deployment.
"""

import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

from flask import Flask, jsonify, request
from flask_cors import CORS

from recommendation_engine import RecommendationEngine

# ---------------------------------------------------------------------------
# App & engine bootstrap
# ---------------------------------------------------------------------------

app = Flask(__name__)
CORS(app)

engine = RecommendationEngine()

API_VERSION = "2.0-escalated"

# Derived reference lists straight from the engine's own data
VALID_CORRIDORS: List[str] = sorted(engine.location_profiles.keys())
VALID_EVENT_TYPES: List[str] = sorted(engine.event_profiles.keys())

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _error_response(message: str, status: int = 400, details: Any = None) -> Tuple:
    body: Dict[str, Any] = {"error": message, "timestamp": _now_iso()}
    if details is not None:
        body["details"] = details
    return jsonify(body), status


def _safe_float(val: Any, default=None) -> Any:
    if val is None:
        return default
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _safe_int(val: Any, default=None) -> Any:
    if val is None:
        return default
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


def _safe_bool(val: Any, default=None) -> Any:
    if val is None:
        return default
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.lower() in ("true", "1", "yes")
    return bool(val)


# ---------------------------------------------------------------------------
# Health & status
# ---------------------------------------------------------------------------


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy",
        "timestamp": _now_iso(),
        "version": API_VERSION,
    })


@app.route("/status", methods=["GET"])
def status():
    active_count = 0
    if hasattr(engine, "conflict_detector") and hasattr(engine.conflict_detector, "active_events"):
        active_count = len(engine.conflict_detector.active_events)
    return jsonify({
        "status": "operational",
        "active_events": active_count,
        "timestamp": _now_iso(),
    })


# ---------------------------------------------------------------------------
# v2/recommend
# ---------------------------------------------------------------------------


@app.route("/v2/recommend", methods=["POST"])
def recommend():
    data = request.get_json(silent=True)
    if not data:
        return _error_response("Request body must be valid JSON.")

    event_id = data.get("event_id") or str(uuid.uuid4())

    try:
        result = engine.recommend(
            impact_score=_safe_float(data.get("impact_score")),
            event_type=data.get("event_type"),
            corridor=data.get("corridor"),
            zone=data.get("zone"),
            duration_hours=_safe_float(data.get("duration_hours")),
            hour=_safe_int(data.get("hour")),
            crowd_size=_safe_int(data.get("crowd_size")),
            road_closure=_safe_bool(data.get("road_closure")),
            affected_length_km=_safe_float(data.get("affected_length_km")),
            live_traffic_index=_safe_float(data.get("live_traffic_index")),
        )
    except Exception as exc:
        return _error_response("Recommendation engine error.", status=500, details=str(exc))

    # Attach API-level metadata
    result["event_id"] = event_id
    result["success"] = True

    # Run validation if the validator is available
    validation_errors: List[str] = []
    if hasattr(engine, "validator") and hasattr(engine.validator, "validate"):
        try:
            is_valid, errors = engine.validator.validate(
                _safe_float(data.get("impact_score"), 0),
                data.get("event_type", ""),
                data.get("corridor", ""),
                data.get("zone", ""),
                _safe_float(data.get("duration_hours"), 0),
                _safe_int(data.get("hour"), 12),
                _safe_int(data.get("crowd_size"), 0),
                _safe_float(data.get("affected_length_km"), 0),
                _safe_float(data.get("live_traffic_index"), 0),
            )
            validation_errors = errors if not is_valid else []
        except Exception:
            pass
    result["validation_errors"] = validation_errors

    # Run conflict detection if available
    escalations: List[str] = []
    conflicts: List[str] = []
    if hasattr(engine, "conflict_detector"):
        cd = engine.conflict_detector
        if hasattr(cd, "check_corridor_conflict"):
            try:
                corridor_conflicts = cd.check_corridor_conflict(
                    data.get("corridor", ""),
                    data.get("event_type", ""),
                    _safe_float(data.get("duration_hours"), 1),
                )
                if corridor_conflicts:
                    conflicts = corridor_conflicts
            except Exception:
                pass
    result["escalations"] = escalations
    result["conflicts"] = conflicts
    result["escalation_required"] = len(conflicts) > 0 or len(escalations) > 0

    return jsonify(result)


# ---------------------------------------------------------------------------
# v2/validate
# ---------------------------------------------------------------------------


@app.route("/v2/validate", methods=["POST"])
def validate():
    data = request.get_json(silent=True)
    if not data:
        return _error_response("Request body must be valid JSON.")

    if not hasattr(engine, "validator") or not hasattr(engine.validator, "validate"):
        return _error_response(
            "Validator not available on this engine instance.",
            status=501,
        )

    try:
        is_valid, errors = engine.validator.validate(
            _safe_float(data.get("impact_score"), 0),
            data.get("event_type", ""),
            data.get("corridor", ""),
            data.get("zone", ""),
            _safe_float(data.get("duration_hours"), 0),
            _safe_int(data.get("hour"), 12),
            _safe_int(data.get("crowd_size"), 0),
            _safe_float(data.get("affected_length_km"), 0),
            _safe_float(data.get("live_traffic_index"), 0),
        )
    except Exception as exc:
        return _error_response("Validation error.", status=500, details=str(exc))

    return jsonify({"valid": is_valid, "errors": errors})


# ---------------------------------------------------------------------------
# v2/conflicts/check
# ---------------------------------------------------------------------------


@app.route("/v2/conflicts/check", methods=["POST"])
def check_conflicts():
    data = request.get_json(silent=True)
    if not data:
        return _error_response("Request body must be valid JSON.")

    corridor = data.get("corridor", "")
    event_type = data.get("event_type", "")
    duration_hours = _safe_float(data.get("duration_hours"), 1)
    zone = data.get("zone", "")
    manpower_needed = _safe_int(data.get("manpower_needed"), 0)

    corridor_conflicts: List[str] = []
    manpower_conflicts: List[str] = []

    if hasattr(engine, "conflict_detector"):
        cd = engine.conflict_detector
        if hasattr(cd, "check_corridor_conflict"):
            try:
                result = cd.check_corridor_conflict(corridor, event_type, duration_hours)
                if result:
                    corridor_conflicts = result
            except Exception as exc:
                return _error_response("Conflict check error.", status=500, details=str(exc))

        # Manpower conflict: check if total active-event manpower + requested > threshold
        if hasattr(cd, "active_events") and manpower_needed and manpower_needed > 0:
            try:
                for eid, evt in cd.active_events.items():
                    evt_manpower = evt.get("manpower_needed", 0) if isinstance(evt, dict) else 0
                    if evt_manpower > 0 and zone and evt.get("zone") == zone:
                        manpower_conflicts.append(
                            f"Event {eid} in {zone} is using {evt_manpower} officers"
                        )
            except Exception:
                pass
    else:
        return jsonify({
            "corridor_conflicts": [],
            "manpower_conflicts": [],
            "has_conflicts": False,
            "message": "Conflict detector not available on this engine instance.",
        })

    return jsonify({
        "corridor_conflicts": corridor_conflicts,
        "manpower_conflicts": manpower_conflicts,
        "has_conflicts": len(corridor_conflicts) > 0 or len(manpower_conflicts) > 0,
    })


# ---------------------------------------------------------------------------
# v2/events/active
# ---------------------------------------------------------------------------


@app.route("/v2/events/active", methods=["GET"])
def active_events():
    if not hasattr(engine, "conflict_detector") or not hasattr(engine.conflict_detector, "active_events"):
        return jsonify({"active_events": [], "count": 0})

    events = engine.conflict_detector.active_events
    event_list = []
    for eid, evt in events.items():
        entry = {"event_id": eid}
        if isinstance(evt, dict):
            entry.update(evt)
        event_list.append(entry)

    return jsonify({"active_events": event_list, "count": len(event_list)})


# ---------------------------------------------------------------------------
# v2/reference
# ---------------------------------------------------------------------------


@app.route("/v2/reference/corridors", methods=["GET"])
def reference_corridors():
    return jsonify({"corridors": VALID_CORRIDORS})


@app.route("/v2/reference/event_types", methods=["GET"])
def reference_event_types():
    return jsonify({"event_types": VALID_EVENT_TYPES})


# ---------------------------------------------------------------------------
# Generic error handlers
# ---------------------------------------------------------------------------


@app.errorhandler(404)
def not_found(_e):
    return _error_response("Endpoint not found.", status=404)


@app.errorhandler(405)
def method_not_allowed(_e):
    return _error_response("Method not allowed.", status=405)


@app.errorhandler(500)
def internal_error(_e):
    return _error_response("Internal server error.", status=500)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    app.run(host="0.0.0.0", port=port, debug=True)
