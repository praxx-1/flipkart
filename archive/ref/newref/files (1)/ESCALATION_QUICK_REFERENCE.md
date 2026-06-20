# TRAFFIC ESCALATION QUICK REFERENCE

## ESCALATION MATRIX

```
┌──────────────────────────────────────────────────────────────────────────┐
│ IMPACT SCORE        │ CATEGORY          │ ESCALATION LEVEL               │
├──────────────────────────────────────────────────────────────────────────┤
│ 0.0 - 2.0           │ LOW               │ No escalation                  │
│                     │                   │ • Local manpower (0-6 officers)│
│                     │                   │ • No barricades needed         │
│                     │                   │ • Monitor and proceed          │
├──────────────────────────────────────────────────────────────────────────┤
│ 2.1 - 4.0           │ LOW-MODERATE      │ Zone alert (optional)          │
│                     │                   │ • Local deployment (7-15)      │
│                     │                   │ • Spot control barricades      │
│                     │                   │ • Basic traffic control        │
├──────────────────────────────────────────────────────────────────────────┤
│ 4.1 - 6.0           │ MODERATE          │ Zone aware (standby)           │
│                     │                   │ • Zone manpower (16-30)        │
│                     │                   │ • Corridor control barricades  │
│                     │                   │ • Active traffic diversions    │
├──────────────────────────────────────────────────────────────────────────┤
│ 6.1 - 8.0           │ HIGH              │ ZONE ESCALATION TRIGGERED ⚠️  │
│                     │                   │ • Tactical manpower (31-55)    │
│                     │                   │ • Full route control           │
│                     │                   │ • Network-wide diversions      │
│                     │                   │ • Notify: Zone Commissioner    │
├──────────────────────────────────────────────────────────────────────────┤
│ 8.1 - 9.0           │ CRITICAL          │ CITY ESCALATION TRIGGERED 🚨  │
│                     │                   │ • Major manpower (56-200)      │
│                     │                   │ • All roads coordinated        │
│                     │                   │ • State support mobilizing     │
│                     │                   │ • Notify: City Commissioner    │
├──────────────────────────────────────────────────────────────────────────┤
│ 9.1 - 10.0          │ CRITICAL          │ STATE + EMERGENCY PROTOCOL 🆘 │
│                     │                   │ • State manpower (200+)        │
│                     │                   │ • Full city-wide activation    │
│                     │                   │ • Emergency protocols active   │
│                     │                   │ • Notify: State Police Chief   │
│                     │                   │ • Activate: Public alerts      │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## AUTOMATED ESCALATION RULES

### RULE 1: ZONE → CITY ESCALATION
**Triggers if ANY of these are true:**
- Impact score ≥ 7.5
- Expected queue ≥ 5 km
- Affected people ≥ 5,000

**Action:** Escalate to City Commissioner  
**Notification:** SMS + Alert  
**Manpower:** City support team  

**Example:** Procession with 8,000 people → Score 7.8 → ZONE ESCALATION ✓

---

### RULE 2: CITY → STATE ESCALATION
**Triggers if ALL of these are true:**
- Impact score ≥ 8.5 AND
- (Road closure = YES OR manpower needed > 150)

**Action:** Escalate to State Police  
**Notification:** SMS + Email + Alert  
**Manpower:** State rapid response  

**Example:** Public event, score 9.2, road closure, 200 officers needed → STATE ESCALATION ✓

---

### RULE 3: EMERGENCY PROTOCOL
**Triggers if ANY of these are true:**
- Impact score ≥ 9.0
- Expected queue ≥ 8 km

**Action:** Activate Emergency Protocol  
**Notification:** Phone calls + Sirens + Public alerts  
**Manpower:** Full city activation  

**Example:** VIP movement during evening peak, score 9.5 → EMERGENCY ✓

---

### RULE 4: RESOURCE SHORTAGE
**Triggers if:**
- Manpower deficit > 0 (needed > available in zone)

**Action:** Request Mutual Aid  
**Notification:** SMS to adjacent zones  
**Manpower:** Cross-zone coordination  

**Example:** East Zone needs 250 officers but has capacity for 200 → MUTUAL AID ✓

---

## DECISION FLOWCHART

```
EVENT REPORTED
     ↓
[VALIDATE INPUTS]
     ↓
     ├─→ INVALID? → Return error with details
     │
[CALCULATE SCORE]
     ↓
[RECOMMEND MANPOWER & RESOURCES]
     ↓
[EVALUATE ESCALATION RULES]
     ↓
     ├─→ SCORE ≥ 7.5 ? → ZONE ESCALATION
     │       ├─→ Notify Zone Commissioner
     │       ├─→ Deploy tactical manpower
     │       └─→ Log: CRITICAL
     │
     ├─→ SCORE ≥ 8.5 ? → CITY ESCALATION
     │       ├─→ Notify City Commissioner
     │       ├─→ Request state support
     │       └─→ Log: CRITICAL
     │
     ├─→ SCORE ≥ 9.0 ? → EMERGENCY PROTOCOL
     │       ├─→ Activate all city resources
     │       ├─→ Public notifications
     │       └─→ Log: EMERGENCY
     │
[DETECT CONFLICTS]
     ├─→ Same corridor? → Prioritize by score
     ├─→ Manpower shortage? → Request mutual aid
     │
[REGISTER EVENT & RETURN RECOMMENDATION]
```

---

## TIME-OF-DAY IMPACT FACTORS

```
TIME PERIOD              IMPACT MULTIPLIER   NOTES
─────────────────────────────────────────────────────────────
Deep Night (0-4 AM)      0.35x               Lowest congestion
                                             Fastest deployment possible

Night (22-23, 5 AM)      0.55x               Sparse traffic
                                             Small crowd gathering risky

Shoulder (5-7, 11-15 AM) 1.05x - 1.20x       Moderate activity
                                             Predictable patterns

Morning Peak (7-10 AM)   1.30x               Heavy commuter traffic
                                             Slow deployment, high impact

Off-peak (10-16)         1.00x               Baseline scenario
                                             Reference point

Evening Peak (16-20)     1.45x               WORST congestion (21% worse than AM)
                                             Cascading delays
                                             High spillover risk

Late evening (20-22)     1.05x               Gradual decrease
                                             Event delays acceptable
```

---

## CORRIDOR RISK PROFILES

```
CORRIDOR            BASELINE TRAFFIC   CAPACITY STRESS   RESPONSE TIME   RISK LEVEL
──────────────────────────────────────────────────────────────────────────────────
ORR East 1          96%                EXTREME (2.17x)   28 min          🔴 CRITICAL
ORR East 2          95%                EXTREME (2.07x)   30 min          🔴 CRITICAL
CBD-2               88%                HIGH (1.83x)      18 min          🟠 HIGH
ORR North           84%                MEDIUM (1.35x)    26 min          🟠 HIGH
Hosur Road          88%                HIGH (1.52x)      25 min          🟠 HIGH
Bellary Road 1      80%                MEDIUM (1.18x)    22 min          🟡 MODERATE
Mysore Road         74%                MEDIUM (1.06x)    24 min          🟡 MODERATE
Bellary Road 2      76%                MEDIUM (1.15x)    25 min          🟡 MODERATE
Tumkur Road         78%                MEDIUM (1.08x)    26 min          🟡 MODERATE
B-M Road            68%                LOW (0.87x)       24 min          🟢 LOW
Non-corridor        55%                LOW (0.97x)       20 min          🟢 LOW
```

---

## EVENT TYPE IMPACT VALUES

```
EVENT TYPE              BASE IMPACT   CROWD LOAD   POLICE COMPLEXITY   TYPICAL DURATION
─────────────────────────────────────────────────────────────────────────────────────
🚨 VIP Movement         8.6/10        VERY HIGH   1.50x              1.5 hours
👥 Procession           8.2/10        VERY HIGH   1.35x              3.0 hours
🎉 Public Event         7.0/10        HIGH        1.15x              3.0 hours
⚠️  Accident             6.1/10        MEDIUM      0.80x              1.0 hour
🚧 Construction         5.5/10        LOW         0.65x              4.0 hours
💔 Water Logging        6.8/10        LOW         0.90x              2.0 hours
🛑 Congestion           5.2/10        NONE        0.55x              1.0 hour
🚗 Vehicle Breakdown    3.8/10        VERY LOW    0.35x              1.0 hour
🌳 Tree Fall            4.8/10        VERY LOW    0.45x              1.4 hours
🕳️  Pothole             2.8/10        NONE        0.20x              0.8 hours
```

---

## MANPOWER DEPLOYMENT LEVELS

```
OFFICERS    LEVEL           SCOPE                       EXAMPLE SCENARIOS
──────────────────────────────────────────────────────────────────────────
0-6         MINIMAL         Single junction             Vehicle breakdown on local road
7-15        LOCAL           Single corridor, 1-2 km     Accident on arterial road
16-30       TACTICAL        Whole corridor, 2-4 km      Major traffic jam on main road
31-55       MAJOR           Multiple corridors, 4+ km   Public event with 5K+ people
56-200      CITY SUPPORT    City-wide coordination      Procession or major accident
200+        STATE SUPPORT   Multi-city, state level     VIP movement or mass gathering
```

---

## QUICK ESCALATION CHECKLIST

### BEFORE SCALING UP

- [ ] Input validation passed (no garbage data)
- [ ] Score calculated correctly (check time factor)
- [ ] Conflict detection run (corridor + manpower)
- [ ] Audit log entry created (for accountability)
- [ ] Active events registered (for conflict tracking)

### ZONE ESCALATION (Score ≥ 7.5)

- [ ] Impact score confirmed ≥ 7.5
- [ ] Zone Commissioner contacted
- [ ] City Commissioner on standby
- [ ] Adjacent zones on alert
- [ ] Manpower: 30+ officers deployed
- [ ] Barricades: Corridor control level

### CITY ESCALATION (Score ≥ 8.5)

- [ ] City Commissioner notified immediately
- [ ] State Police briefed
- [ ] State support mobilizing
- [ ] All zones coordinated
- [ ] Media alert prepared
- [ ] Public notifications queued

### EMERGENCY PROTOCOL (Score ≥ 9.0)

- [ ] Zone + City + State Commissioners all notified
- [ ] Police Chief activated
- [ ] All available manpower mobilizing
- [ ] Public alerts broadcasting
- [ ] Emergency lanes cleared
- [ ] Medical teams on standby

---

## COMMON MISTAKES & FIXES

| Mistake | Impact | Fix |
|---------|--------|-----|
| Using offline impact score | Misses time-of-day factor | Always use contextual score |
| Ignoring road closure flag | Underdeploys manpower | Add 1.35x factor if road_closure=true |
| Trusting generic queue estimates | Cascading failures | Use affected_length_km for better accuracy |
| Deploying without conflict check | Resource conflicts | Call /v2/conflicts/check first |
| Missing deep night edge case | Overthinking (hour=4 vs 5) | Use modular hour logic (hour % 24) |

---

## API ENDPOINTS - QUICK REFERENCE

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/v2/recommend` | POST | Get recommendation with escalations |
| `/v2/validate` | POST | Validate inputs before recommendation |
| `/v2/conflicts/check` | POST | Check corridor + manpower conflicts |
| `/v2/escalations/evaluate` | POST | Evaluate if rules trigger |
| `/v2/events/active` | GET | List all active events |
| `/v2/events/{id}` | GET | Get specific event details |
| `/v2/events/{id}/resolve` | POST | Mark event as resolved |
| `/v2/reference/corridors` | GET | List all corridors |
| `/v2/reference/event-types` | GET | List all event types |
| `/v2/health` | GET | API health check |

---

## 📞 ESCALATION CONTACTS

| Level | Contact | Method | Response Time |
|-------|---------|--------|----------------|
| Zone | Zone Commissioner | SMS + Phone | 5 minutes |
| City | City Commissioner | SMS + Email | 3 minutes |
| State | Police Chief | Phone + Email | IMMEDIATE |
| Emergency | All above + State HQ | Sirens + All channels | IMMEDIATE |

---

**Version:** 2.0 Escalated  
**Last Updated:** 2025-06-20  
**Print & Keep:** Quick reference for dispatch center  
**Questions?** Check DEPLOYMENT_GUIDE.md or logs at `/tmp/traffic_audit/decisions.log`
