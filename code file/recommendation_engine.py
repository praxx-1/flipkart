"""
PHASE 4: RECOMMENDATION ENGINE
Convert Impact Score (0-10) → Actionable Police Recommendations
"""

import pandas as pd
import numpy as np
from typing import Dict, List

# ============================================================================
# RECOMMENDATION ENGINE CLASS
# ============================================================================

class RecommendationEngine:
    """
    Converts predicted congestion impact score into actionable recommendations
    for traffic police deployment and management.
    """
    
    def __init__(self):
        """Initialize corridor and zone mappings"""
        
        # Major corridors and their alternate routes
        self.corridor_diversions = {
            'Mysore Road': ['HSR Layout', 'Sankey Road', 'ORR'],
            'Bellary Road 1': ['Sankey Road', 'Whitefield Road'],
            'Bellary Road 2': ['Outer Ring Road', 'Bangalore-Mysore Road'],
            'ORR North': ['White Field Road', 'Hebbal Bypass'],
            'ORR East 1': ['Koramangala', 'Sarjapur Road'],
            'ORR East 2': ['Whitefield Road', 'Marathahalli Bridge'],
            'CBD-2': ['ORR North', 'ORR South', 'HSR Layout'],
            'Bangalore-Mysore Road': ['Tumkur Road', 'Hosur Road'],
            'Hosur Road': ['Sarjapur Road', 'Bannerghatta Road'],
            'Tumkur Road': ['ORR North', 'Peenya Industrial Area']
        }
        
        # Critical barricade points by corridor
        self.barricade_points = {
            'Mysore Road': ['Hegde Nagar Junction', 'Langford Town', 'Cox Town'],
            'Bellary Road 1': ['Sankey Road Junction', 'Jeevan Bhima Nagar'],
            'Bellary Road 2': ['Sankey Road Junction', 'Yeshwantpur Station'],
            'ORR North': ['Hebbal Junction', 'Yelahanka Junction'],
            'ORR East 1': ['Koramangala Junction', 'Indiranagar'],
            'ORR East 2': ['Marathahalli Bridge', 'Whitefield Junction'],
            'CBD-2': ['Queens Statue Circle', 'Sankey Road', 'Ulsoor Lake'],
            'Bangalore-Mysore Road': ['Tumkur Road Junction', 'Electronic City'],
            'Hosur Road': ['Koramangala Junction', 'Sarjapur Road Junction'],
            'Tumkur Road': ['Jalahalli Junction', 'Peenya Junction']
        }
    
    # ========================================================================
    # CORE RECOMMENDATION LOGIC
    # ========================================================================
    
    def recommend(self, impact_score: float, 
                  event_type: str = None,
                  corridor: str = None,
                  zone: str = None,
                  duration_hours: float = None) -> Dict:
        """
        Generate recommendations based on impact score and event details.
        
        Args:
            impact_score: Predicted impact (0-10)
            event_type: Type of event (public_event, accident, etc.)
            corridor: Affected corridor
            zone: Administrative zone
            duration_hours: Expected event duration
            
        Returns:
            Dictionary with complete recommendations
        """
        
        # Round score to 1 decimal
        impact_score = round(impact_score, 1)
        
        # Clamp to 0-10 range
        impact_score = max(0, min(10, impact_score))
        
        # Get manpower recommendation
        manpower = self._recommend_manpower(impact_score)
        
        # Get barricade locations
        barricades = self._recommend_barricades(impact_score, corridor)
        
        # Get diversion routes
        diversions = self._recommend_diversions(impact_score, corridor)
        
        # Get setup/cleanup times
        setup_cleanup = self._recommend_timing(impact_score, duration_hours)
        
        # Get impact category
        category = self._categorize_impact(impact_score)
        
        # Build recommendation object
        recommendation = {
            'impact_score': impact_score,
            'category': category,
            'manpower': manpower,
            'barricades': barricades,
            'diversions': diversions,
            'setup_cleanup': setup_cleanup,
            'summary': self._build_summary(impact_score, manpower, barricades, corridor)
        }
        
        return recommendation
    
    # ========================================================================
    # MANPOWER RECOMMENDATION
    # ========================================================================
    
    def _recommend_manpower(self, score: float) -> Dict:
        """Recommend police officer deployment based on impact score"""
        
        if score <= 2:
            return {
                'min_officers': 5,
                'max_officers': 10,
                'recommended': 8,
                'level': 'MINIMAL',
                'description': 'Basic traffic management only'
            }
        elif score <= 4:
            return {
                'min_officers': 10,
                'max_officers': 20,
                'recommended': 15,
                'level': 'LOW',
                'description': 'Standard traffic control, 1-2 alternate routes'
            }
        elif score <= 6:
            return {
                'min_officers': 20,
                'max_officers': 35,
                'recommended': 28,
                'level': 'MODERATE',
                'description': 'Moderate traffic management, multiple diversions'
            }
        elif score <= 8:
            return {
                'min_officers': 35,
                'max_officers': 50,
                'recommended': 42,
                'level': 'HIGH',
                'description': 'Heavy traffic control, full barricading'
            }
        else:  # > 8
            return {
                'min_officers': 50,
                'max_officers': 70,
                'recommended': 60,
                'level': 'CRITICAL',
                'description': 'Maximum deployment, all available routes controlled'
            }
    
    # ========================================================================
    # BARRICADE RECOMMENDATION
    # ========================================================================
    
    def _recommend_barricades(self, score: float, corridor: str = None) -> Dict:
        """Recommend barricade locations and extent"""
        
        locations = []
        
        # Get corridor-specific barricades
        if corridor and corridor in self.barricade_points:
            corridor_barricades = self.barricade_points[corridor]
        else:
            corridor_barricades = ['Main junction', 'Secondary junction']
        
        if score <= 2:
            return {
                'count': 0,
                'locations': [],
                'level': 'NONE',
                'description': 'No barricades needed'
            }
        elif score <= 4:
            return {
                'count': 1,
                'locations': corridor_barricades[:1],
                'level': 'MINIMAL',
                'description': 'Main junction only'
            }
        elif score <= 6:
            return {
                'count': 2,
                'locations': corridor_barricades[:2],
                'level': 'MODERATE',
                'description': 'Main junction + secondary junctions'
            }
        elif score <= 8:
            return {
                'count': 3,
                'locations': corridor_barricades[:3],
                'level': 'HEAVY',
                'description': 'All major junctions in corridor'
            }
        else:  # > 8
            return {
                'count': len(corridor_barricades),
                'locations': corridor_barricades,
                'level': 'FULL',
                'description': 'Complete corridor closure, all junctions controlled'
            }
    
    # ========================================================================
    # DIVERSION ROUTE RECOMMENDATION
    # ========================================================================
    
    def _recommend_diversions(self, score: float, corridor: str = None) -> Dict:
        """Recommend alternate routes for traffic diversion"""
        
        # Get corridor-specific diversions
        if corridor and corridor in self.corridor_diversions:
            available_routes = self.corridor_diversions[corridor]
        else:
            available_routes = ['ORR', 'HSR Layout', 'Whitefield Road']
        
        if score <= 2:
            return {
                'primary': None,
                'secondary': None,
                'level': 'NONE',
                'description': 'Normal traffic flow, no diversions needed'
            }
        elif score <= 4:
            return {
                'primary': available_routes[0] if len(available_routes) > 0 else 'ORR',
                'secondary': None,
                'level': 'MINIMAL',
                'description': f'Minor diversion to {available_routes[0] if len(available_routes) > 0 else "alternate route"}'
            }
        elif score <= 6:
            return {
                'primary': available_routes[0] if len(available_routes) > 0 else 'ORR',
                'secondary': available_routes[1] if len(available_routes) > 1 else 'HSR Layout',
                'level': 'MODERATE',
                'description': f'Divert via {available_routes[0] if len(available_routes) > 0 else "primary"} and {available_routes[1] if len(available_routes) > 1 else "secondary"}'
            }
        elif score <= 8:
            routes_to_use = available_routes[:2] if len(available_routes) >= 2 else available_routes
            return {
                'primary': routes_to_use[0],
                'secondary': routes_to_use[1] if len(routes_to_use) > 1 else 'ORR',
                'tertiary': available_routes[2] if len(available_routes) > 2 else 'Parallel Road',
                'level': 'HEAVY',
                'description': f'Heavy diversions: Primary via {routes_to_use[0]}, Secondary via {routes_to_use[1] if len(routes_to_use) > 1 else "ORR"}'
            }
        else:  # > 8
            return {
                'primary': available_routes[0] if len(available_routes) > 0 else 'ORR North',
                'secondary': available_routes[1] if len(available_routes) > 1 else 'HSR Layout',
                'tertiary': available_routes[2] if len(available_routes) > 2 else 'Whitefield Road',
                'quaternary': 'Bangalore-Mysore Road' if len(available_routes) < 4 else available_routes[3],
                'level': 'CRITICAL',
                'description': 'All available routes activated, maximum traffic diversion'
            }
    
    # ========================================================================
    # TIMING RECOMMENDATION
    # ========================================================================
    
    def _recommend_timing(self, score: float, duration_hours: float = None) -> Dict:
        """Recommend setup, event, and cleanup timings"""
        
        # Default duration if not provided
        if duration_hours is None:
            duration_hours = 4
        
        if score <= 2:
            return {
                'setup_hours_before': 0.5,
                'event_hours': duration_hours,
                'cleanup_hours_after': 0.5,
                'total_impact_hours': duration_hours + 1,
                'description': 'Minimal setup/cleanup'
            }
        elif score <= 4:
            return {
                'setup_hours_before': 1,
                'event_hours': duration_hours,
                'cleanup_hours_after': 0.5,
                'total_impact_hours': duration_hours + 1.5,
                'description': 'Standard setup and cleanup'
            }
        elif score <= 6:
            return {
                'setup_hours_before': 1.5,
                'event_hours': duration_hours,
                'cleanup_hours_after': 1,
                'total_impact_hours': duration_hours + 2.5,
                'description': 'Extended setup, moderate cleanup'
            }
        elif score <= 8:
            return {
                'setup_hours_before': 2,
                'event_hours': duration_hours,
                'cleanup_hours_after': 1.5,
                'total_impact_hours': duration_hours + 3.5,
                'description': 'Full setup period, comprehensive cleanup'
            }
        else:  # > 8
            return {
                'setup_hours_before': 3,
                'event_hours': duration_hours,
                'cleanup_hours_after': 2,
                'total_impact_hours': duration_hours + 5,
                'description': 'Maximum setup time, full traffic restoration protocol'
            }
    
    # ========================================================================
    # IMPACT CATEGORIZATION
    # ========================================================================
    
    def _categorize_impact(self, score: float) -> str:
        """Categorize impact level"""
        
        if score <= 2:
            return "🟢 LOW"
        elif score <= 4:
            return "🟡 LOW-MODERATE"
        elif score <= 6:
            return "🟠 MODERATE"
        elif score <= 8:
            return "🔴 HIGH"
        else:
            return "⛔ CRITICAL"
    
    # ========================================================================
    # BUILD SUMMARY
    # ========================================================================
    
    def _build_summary(self, score: float, manpower: Dict, 
                       barricades: Dict, corridor: str = None) -> str:
        """Build human-readable summary"""
        
        corridor_str = f"on {corridor}" if corridor else ""
        
        summary = f"""
Impact Score: {score}/10
Manpower: Deploy {manpower['recommended']} officers ({manpower['min_officers']}-{manpower['max_officers']})
Barricades: {barricades['count']} locations - {barricades['level']} level
Setup Required: Yes
Estimated Congestion: {score * 0.75:.1f} km² affected
Recommendation Level: {manpower['level']}
        """.strip()
        
        return summary


# ============================================================================
# FORMATTED OUTPUT
# ============================================================================

def print_recommendation(rec: Dict, event_name: str = "Event"):
    """Print recommendation in formatted way"""
    
    print("\n" + "=" * 80)
    print(f"RECOMMENDATION: {event_name}")
    print("=" * 80)
    
    print(f"\n📊 Impact Assessment")
    print(f"   Score: {rec['impact_score']}/10")
    print(f"   Category: {rec['category']}")
    
    print(f"\n👮 Manpower Deployment")
    print(f"   Level: {rec['manpower']['level']}")
    print(f"   Recommended: {rec['manpower']['recommended']} officers")
    print(f"   Range: {rec['manpower']['min_officers']}-{rec['manpower']['max_officers']} officers")
    print(f"   Details: {rec['manpower']['description']}")
    
    print(f"\n🚧 Barricade Setup")
    print(f"   Level: {rec['barricades']['level']}")
    print(f"   Count: {rec['barricades']['count']} locations")
    if rec['barricades']['locations']:
        for i, loc in enumerate(rec['barricades']['locations'], 1):
            print(f"   {i}. {loc}")
    print(f"   Details: {rec['barricades']['description']}")
    
    print(f"\n🛣️  Traffic Diversions")
    div = rec['diversions']
    print(f"   Level: {div['level']}")
    if div['primary']:
        print(f"   Primary: {div['primary']}")
    if div.get('secondary'):
        print(f"   Secondary: {div['secondary']}")
    if div.get('tertiary'):
        print(f"   Tertiary: {div['tertiary']}")
    if div.get('quaternary'):
        print(f"   Quaternary: {div['quaternary']}")
    print(f"   Details: {div['description']}")
    
    print(f"\n⏰ Time Management")
    setup = rec['setup_cleanup']
    print(f"   Setup Time: {setup['setup_hours_before']:.1f} hours before")
    print(f"   Event Duration: {setup['event_hours']:.1f} hours")
    print(f"   Cleanup Time: {setup['cleanup_hours_after']:.1f} hours after")
    print(f"   Total Traffic Impact: {setup['total_impact_hours']:.1f} hours")
    print(f"   Details: {setup['description']}")
    
    print(f"\n📝 Summary")
    print(rec['summary'])
    print("\n" + "=" * 80)


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    
    print("\n" + "=" * 80)
    print("PHASE 4: RECOMMENDATION ENGINE")
    print("=" * 80)
    
    # Initialize engine
    engine = RecommendationEngine()
    
    # Example 1: LOW impact event
    print("\n\n📋 EXAMPLE 1: Vehicle Breakdown (Low Impact)")
    rec1 = engine.recommend(
        impact_score=2.5,
        event_type='accident',
        corridor='Mysore Road',
        zone='Hebbal',
        duration_hours=1
    )
    print_recommendation(rec1, "Vehicle Breakdown on Mysore Road")
    
    # Example 2: MODERATE impact event
    print("\n\n📋 EXAMPLE 2: Construction (Moderate Impact)")
    rec2 = engine.recommend(
        impact_score=5.8,
        event_type='construction',
        corridor='Bellary Road 1',
        zone='Yeshwantpur',
        duration_hours=6
    )
    print_recommendation(rec2, "Road Construction on Bellary Road")
    
    # Example 3: HIGH impact event
    print("\n\n📋 EXAMPLE 3: Public Event (High Impact)")
    rec3 = engine.recommend(
        impact_score=8.2,
        event_type='public_event',
        corridor='CBD-2',
        zone='Central',
        duration_hours=4
    )
    print_recommendation(rec3, "Concert at M Chinnaswamy Stadium")
    
    # Example 4: CRITICAL impact event
    print("\n\n📋 EXAMPLE 4: VIP Movement (Critical Impact)")
    rec4 = engine.recommend(
        impact_score=9.5,
        event_type='vip_movement',
        corridor='ORR North',
        zone='Hebbal',
        duration_hours=2
    )
    print_recommendation(rec4, "VIP Movement - High Priority")
    
    print("\n\n✅ Recommendation Engine Ready for Phase 5 (Dashboard)")
