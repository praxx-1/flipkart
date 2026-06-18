"""
PHASE 4: CONTEXTUAL RECOMMENDATION ENGINE
Convert a numeric event impact score into deployable traffic-police actions.
"""

from typing import Dict, List, Optional


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

        self.location_profiles = {
            "Mysore Road": self._road_profile(0.76, 0.67, 6, 2.8, 24, "NH-275 radial corridor with heavy commuter and freight mixing."),
            "Bellary Road 1": self._road_profile(0.78, 0.72, 6, 2.5, 22, "Airport-side arterial with high weekday commuter demand."),
            "Bellary Road 2": self._road_profile(0.74, 0.70, 6, 2.3, 25, "North Bengaluru airport approach and suburban connector."),
            "ORR North": self._road_profile(0.82, 0.68, 6, 3.4, 26, "Outer Ring Road section around Hebbal/Nagavara with recurring choke points."),
            "ORR East 1": self._road_profile(0.94, 0.62, 6, 5.2, 28, "IT-corridor ORR section around Silk Board, Iblur, Bellandur and Sarjapur links."),
            "ORR East 2": self._road_profile(0.96, 0.60, 6, 5.6, 30, "Marathahalli/Whitefield ORR section where closures can spill across parallel roads."),
            "CBD-2": self._road_profile(0.88, 0.48, 4, 3.2, 18, "Central business district roads with dense junction spacing and limited spare capacity."),
            "Bangalore-Mysore Road": self._road_profile(0.72, 0.76, 6, 2.4, 24, "Inter-city radial road with comparatively better carriageway capacity."),
            "Hosur Road": self._road_profile(0.86, 0.66, 6, 3.8, 25, "Electronic City and Silk Board approach corridor."),
            "Tumkur Road": self._road_profile(0.78, 0.74, 6, 2.7, 26, "Industrial and highway approach corridor with freight movement."),
            "Non-corridor": self._road_profile(0.55, 0.42, 2, 1.2, 20, "Local road profile; confirm exact geometry before final deployment."),
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
            "https://timesofindia.indiatimes.com/city/bengaluru/rain-disrupts-orr-traffic/articleshow/121736538.cms",
            "https://timesofindia.indiatimes.com/city/bengaluru/road-closures-fuel-hours-long-gridlock-on-bengalurus-outer-ring-road/articleshow/124612228.cms",
        ]

    def _road_profile(self, traffic_flow: float, capacity: float, lanes: int, spread_km: float, response_min: int, notes: str) -> Dict:
        return {
            "traffic_flow_index": traffic_flow,
            "road_capacity_index": capacity,
            "lanes": lanes,
            "typical_spread_km": spread_km,
            "base_response_minutes": response_min,
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

    def recommend(
        self,
        impact_score: float,
        event_type: Optional[str] = None,
        corridor: Optional[str] = None,
        zone: Optional[str] = None,
        duration_hours: Optional[float] = None,
        hour: Optional[int] = None,
        crowd_size: int = 0,
        road_closure: bool = False,
        affected_length_km: Optional[float] = None,
        live_traffic_index: Optional[float] = None,
    ) -> Dict:
        event_type_clean = str(event_type).lower().strip() if event_type else "congestion"
        corridor_key = corridor if corridor in self.location_profiles else "Non-corridor"
        duration_hours = duration_hours if duration_hours is not None else 1.0
        hour = 12 if hour is None else int(hour) % 24

        event_profile = self.event_profiles.get(event_type_clean, self.event_profiles["congestion"])
        road_profile = self.location_profiles[corridor_key]
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

        score = context["contextual_impact_score"]
        manpower = self._recommend_manpower(score, event_profile, road_profile, context)
        barricades = self._recommend_barricades(score, corridor_key, event_profile, context)
        diversions = self._recommend_diversions(score, corridor_key, event_profile, context)
        timing = self._recommend_timing(score, duration_hours, event_profile, road_profile, context, manpower, barricades)
        category = self._categorize_impact(score)

        return {
            "impact_score": score,
            "base_impact_score": round(max(0, min(10, impact_score)), 1),
            "category": category,
            "manpower": manpower,
            "barricades": barricades,
            "diversions": diversions,
            "setup_cleanup": timing,
            "context": context,
            "web_context_sources": self.web_context_sources,
            "summary": self._build_summary(score, manpower, barricades, timing, context, corridor_key, zone),
        }

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

        if 7 <= hour <= 10 or 16 <= hour <= 20:
            time_factor = 1.22
            time_label = "Peak commute"
        elif 22 <= hour or hour <= 5:
            time_factor = 0.68
            time_label = "Night"
        elif 11 <= hour <= 15:
            time_factor = 0.92
            time_label = "Midday"
        else:
            time_factor = 1.0
            time_label = "Shoulder hour"

        night_gathering_factor = 1.15 if time_label == "Night" and crowd_size >= 500 else 1.0
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
        incident_units = 2 + (score * 1.25)
        crowd_units = min(26, context["crowd_size"] / 350)
        traffic_units = 4 + (context["traffic_flow_index"] * 12) + (context["capacity_pressure"] * 10)
        closure_units = 8 if context["road_closure"] else 0
        spread_units = min(12, context["expected_queue_km"] * 1.4)
        complexity_units = event_profile["police_complexity"] * 5
        raw = incident_units + crowd_units + traffic_units + closure_units + spread_units + complexity_units

        if context["time_period"] == "Night" and context["crowd_size"] < 300:
            raw *= 0.78
        elif context["time_period"] == "Night":
            raw *= 1.08

        recommended = int(round(max(2, min(90, raw))))
        min_officers = max(0, int(round(recommended * 0.75)))
        max_officers = int(round(recommended * 1.30))

        return {
            "min_officers": min_officers,
            "max_officers": max_officers,
            "recommended": recommended,
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

        if context["time_period"] == "Peak commute":
            setup_minutes *= 1.18
        elif context["time_period"] == "Night" and context["crowd_size"] < 300:
            setup_minutes *= 0.86

        cleanup_minutes = 12 + (barricades["count"] * 8) + (context["expected_queue_km"] * 7)
        if context["road_closure"]:
            cleanup_minutes += 18
        if context["time_period"] == "Peak commute":
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
        return "CITY SUPPORT"

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
