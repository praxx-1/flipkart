# ESCALATION DEPLOYMENT GUIDE - TODAY (EOD)

## ✅ WHAT'S BEEN ESCALATED

### 1. **Input Validation** ✅
- Strict type checking (no garbage in)
- Range validation (0-23 hours, 0-10 scores, etc.)
- Enum validation (corridors, zones, event types)
- Returns detailed error messages

### 2. **Conflict Detection** ✅
- Detects simultaneous events on same corridor
- Checks zone-level manpower capacity
- Auto-resolution strategies (prioritize vs escalate)

### 3. **Escalation Rules Engine** ✅
- Zone → City (score ≥7.5 OR queue ≥5km OR affected ≥5000)
- City → State (score ≥8.5 OR road closure OR manpower >150)
- Emergency Protocol (score ≥9.0 OR queue ≥8km)
- Resource Shortage (insufficient manpower)

### 4. **Audit Logging** ✅
- Immutable decision trail (who, when, what, why)
- Structured JSON format
- Real-time log file: `/tmp/traffic_audit/decisions.log`

### 5. **REST API** ✅
- `/v2/recommend` - Main endpoint
- `/v2/validate` - Pre-validation
- `/v2/conflicts/check` - Conflict detection
- `/v2/escalations/evaluate` - Rule evaluation
- `/v2/events/active` - Real-time event dashboard

---

## 🚀 DEPLOYMENT STEPS (30 mins)

### STEP 1: Install Dependencies (5 mins)
```bash
pip install -r requirements.txt
```

### STEP 2: Test Core Engine (5 mins)
```bash
python escalated_engine.py
# Should print 2 test cases with JSON output
# Look for "escalation_required": true in test case 2
```

### STEP 3: Start API Server (2 mins)
```bash
# Option A: Development (for testing)
python api_server.py
# Server will start on http://localhost:5000

# Option B: Production (requires gunicorn)
gunicorn -w 4 -b 0.0.0.0:5000 api_server.py
# 4 worker threads, binds to 0.0.0.0:5000
```

### STEP 4: Test API Endpoints (5 mins)
```bash
# Health check
curl -X GET http://localhost:5000/health

# Get corridors
curl -X GET http://localhost:5000/v2/reference/corridors

# Test recommendation (no escalation)
curl -X POST http://localhost:5000/v2/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "accident",
    "corridor": "ORR East 2",
    "zone": "East Zone 2",
    "impact_score": 5.5,
    "hour": 14
  }'

# Test escalation trigger
curl -X POST http://localhost:5000/v2/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "procession",
    "corridor": "ORR East 2",
    "zone": "East Zone 2",
    "impact_score": 9.0,
    "crowd_size": 20000,
    "hour": 17,
    "road_closure": true
  }'
# Should return: "escalation_required": true
```

### STEP 5: Check Audit Logs (2 mins)
```bash
tail -f /tmp/traffic_audit/decisions.log
# You'll see entries like:
# 2025-06-20 14:32:01 | INFO | EVENT:EVT_... | DECISION:ENGINE | SCORE:5.5 | ...
# 2025-06-20 14:33:22 | CRITICAL | ESCALATION:EVT_... | ZONE → CITY | ...
```

### STEP 6: Integration Check (5 mins)
Confirm integration points:
- [ ] Existing system calls `/v2/recommend` instead of Python class directly
- [ ] Audit logs are being written to `/tmp/traffic_audit/`
- [ ] Active events dashboard at `/v2/events/active` is accessible
- [ ] Error responses include validation details

---

## 📋 KEY ESCALATION SCENARIOS

### Scenario 1: Minor Incident (No Escalation)
```json
POST /v2/recommend
{
  "event_id": "EVT_001",
  "event_type": "vehicle_breakdown",
  "corridor": "Tumkur Road",
  "zone": "North Zone 1",
  "impact_score": 3.2,
  "duration_hours": 0.5,
  "hour": 10,
  "crowd_size": 50
}

Response:
{
  "escalation_required": false,
  "escalations": [],
  "manpower": {"recommended": 4}
}
```

### Scenario 2: Medium Event (Zone Escalation)
```json
POST /v2/recommend
{
  "event_id": "EVT_002",
  "event_type": "public_event",
  "corridor": "CBD-2",
  "zone": "Central",
  "impact_score": 7.2,
  "crowd_size": 8000,
  "duration_hours": 3,
  "hour": 16,
  "road_closure": false
}

Response:
{
  "escalation_required": true,
  "escalations": [
    {
      "rule": "zone_to_city",
      "action": "ESCALATE_TO_CITY_COMMISSIONER",
      "notification": {
        "sms": "City Commissioner",
        "alert_type": "URGENT"
      }
    }
  ],
  "manpower": {"recommended": 45}
}
```

### Scenario 3: Critical Event (State Escalation)
```json
POST /v2/recommend
{
  "event_id": "EVT_003",
  "event_type": "procession",
  "corridor": "ORR East 2",
  "zone": "East Zone 2",
  "impact_score": 9.1,
  "crowd_size": 25000,
  "duration_hours": 4,
  "hour": 17,
  "road_closure": true,
  "affected_length_km": 8.5
}

Response:
{
  "escalation_required": true,
  "escalations": [
    {
      "rule": "city_to_state",
      "action": "ESCALATE_TO_STATE_POLICE",
      "notification": {
        "sms": "State Police Chief",
        "email": "state.police@karnataka.gov.in",
        "alert_type": "CRITICAL"
      }
    },
    {
      "rule": "emergency_protocol",
      "action": "ACTIVATE_EMERGENCY_PROTOCOL",
      "notification": {
        "phone_call": "Zone Commissioner + City Commissioner",
        "alert_type": "EMERGENCY"
      }
    }
  ],
  "manpower": {"recommended": 85}
}
```

---

## 🔗 INTEGRATION WITH EXISTING SYSTEM

### From Python (Old)
```python
from recommendation_engine import RecommendationEngine
engine = RecommendationEngine()
rec = engine.recommend(...)  # Returns Dict
```

### To REST API (New) - Option A: Via HTTP
```python
import requests

response = requests.post(
    "http://localhost:5000/v2/recommend",
    json={
        "event_type": "accident",
        "corridor": "ORR East 2",
        "impact_score": 5.5,
    }
)
rec = response.json()
```

### To REST API (New) - Option B: Direct Import
```python
from escalated_engine import EscalatedRecommendationEngine
engine = EscalatedRecommendationEngine()
result = engine.recommend(
    event_id="EVT_001",
    event_type="accident",
    corridor="ORR East 2",
    impact_score=5.5,
)
# result includes: escalations, conflicts, validation_errors
```

---

## 📊 MONITORING & OBSERVABILITY

### Real-Time Dashboard
```bash
# View active events
curl -X GET http://localhost:5000/v2/events/active

# Check event status
curl -X GET http://localhost:5000/v2/events/EVT_001

# Mark event as resolved
curl -X POST http://localhost:5000/v2/events/EVT_001/resolve
```

### Audit Trail
```bash
# All decisions logged to:
cat /tmp/traffic_audit/decisions.log

# Format:
# TIMESTAMP | LEVEL | EVENT_ID | ACTION | SCORE | CATEGORY | ESCALATION
# 2025-06-20 14:32:01 | INFO | EVT_001 | DECISION:ENGINE | SCORE:5.5 | MODERATE | false
# 2025-06-20 14:35:22 | CRITICAL | EVT_002 | ESCALATION:EVT_002 | ZONE→CITY | reason
```

### Performance Metrics
```bash
# Recommendation latency (should be <200ms)
time curl -X POST http://localhost:5000/v2/recommend \
  -H "Content-Type: application/json" \
  -d '{"event_type":"accident","corridor":"ORR East 2"}'

# Concurrent request handling (4 workers = ~400 req/sec)
ab -n 100 -c 10 http://localhost:5000/health
```

---

## ⚠️ CRITICAL CONFIGS TO VERIFY

### 1. Escalation Thresholds
File: `escalated_engine.py` → `EscalationRulesEngine.RULES`

Current:
- Zone→City: score ≥7.5 (can adjust to 7.0 or 8.0)
- City→State: score ≥8.5 (can adjust)
- Emergency: score ≥9.0 (can adjust)

### 2. Manpower Capacity
File: `api_server.py` → `check_manpower_conflict()`
```python
available_capacity: int = 200  # Per zone, adjust if needed
```

### 3. Audit Log Location
File: `escalated_engine.py` → `AuditLogger.__init__()`
```python
log_dir: str = "/tmp/traffic_audit"  # Change to /var/log/traffic if needed
```

---

## 🔧 TROUBLESHOOTING

### Issue: "ValidationError: event_type not recognized"
**Fix:** Ensure event_type is one of:
`vip_movement, procession, public_event, accident, construction, vehicle_breakdown, pot_hole, water_logging, tree_fall, congestion`

### Issue: "Module not found: escalated_engine"
**Fix:** Ensure `escalated_engine.py` is in same directory as `api_server.py`

### Issue: Escalations not triggering
**Check:**
1. Score is actually ≥7.5 for zone escalation
2. Impact score calculation (multiply by time_factor)
3. Log file: `tail /tmp/traffic_audit/decisions.log`

### Issue: API timeout
**Fix:** Start with `python api_server.py`, then scale to `gunicorn -w 8`

---

## 📱 QUICK DEPLOYMENT CHECKLIST

- [ ] Python 3.8+ installed
- [ ] `pip install -r requirements.txt` completed
- [ ] `escalated_engine.py` tested (run directly)
- [ ] `api_server.py` started (development or production)
- [ ] Health endpoint responding: `curl http://localhost:5000/health`
- [ ] Sample recommendation works: `curl POST /v2/recommend`
- [ ] Audit logs being written: `tail /tmp/traffic_audit/decisions.log`
- [ ] Conflict detector is active: `curl /v2/events/active`
- [ ] Escalation rules evaluated correctly (test with high-impact event)

---

## 📞 SUPPORT & ESCALATION MATRIX

| Issue | Escalate To | Timeline |
|-------|------------|----------|
| Minor validation error | Engineering team | 1 hour |
| Escalation threshold not met | Traffic Commissioner | 15 mins |
| API unavailable | Ops team + Engineering | 5 mins |
| Audit logs not writing | Ops + Security | 15 mins |
| Manpower shortage detected | State Police HQ | IMMEDIATE |

---

## 🎯 PHASE 6 (Tomorrow)

Once deployed today:
1. Monitor escalation accuracy for 24 hours
2. Collect feedback from field officers
3. Tune thresholds based on real events
4. Add real-time TomTom API integration
5. Connect to SMS/email notification system

---

**Deployment Owner:** Engineering Team  
**Target Completion:** Today EOD  
**Rollback Plan:** Revert to original `recommendation_engine.py`  
**Monitoring:** Slack alerts on CRITICAL escalations  

Good luck! 🚀
