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
        
        # Normalise event_type string
        event_type_clean = str(event_type).lower().strip() if event_type else ''

        # Get manpower recommendation
        manpower = self._recommend_manpower(impact_score, event_type_clean)
        
        # Get barricade locations
        barricades = self._recommend_barricades(impact_score, corridor, event_type_clean)
        
        # Get diversion routes
        diversions = self._recommend_diversions(impact_score, corridor, event_type_clean)
        
        # Get setup/cleanup times
        setup_cleanup = self._recommend_timing(impact_score, duration_hours, event_type_clean)
        
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
    # EVENT TYPE PROFILES
    # Each event type has a base manpower range, barricade need, and
    # diversion need that OVERRIDES the generic score-only logic.
    # Priority (High/Medium/Low) is used as a MULTIPLIER within the profile.
    # ========================================================================

    def _get_event_profile(self, event_type: str) -> Dict:
        """
        Return a realistic deployment profile per event type.
        Fields:
          - needs_police: Whether police traffic deployment is relevant
          - base_officers: Realistic recommended officers (not inflated)
          - officer_range: (min, max) realistic range
          - barricade_need: 'none' | 'low' | 'medium' | 'high'
          - diversion_need: 'none' | 'low' | 'medium' | 'high'
          - notes: human-readable context
        """
        profiles = {
            # ── Planned Events ──────────────────────────────────────────────
            'vip_movement': {
                'needs_police': True,
                'base_officers': 20,
                'officer_range': (15, 30),
                'barricade_need': 'high',
                'diversion_need': 'high',
                'notes': 'VIP security escort + route clearance required'
            },
            'procession': {
                'needs_police': True,
                'base_officers': 18,
                'officer_range': (12, 25),
                'barricade_need': 'high',
                'diversion_need': 'high',
                'notes': 'Crowd control + route management needed'
            },
            'public_event': {
                'needs_police': True,
                'base_officers': 12,
                'officer_range': (8, 20),
                'barricade_need': 'medium',
                'diversion_need': 'medium',
                'notes': 'Crowd & parking management, perimeter control'
            },
            # ── Unplanned / Infrastructure ───────────────────────────────
            'accident': {
                'needs_police': True,
                'base_officers': 6,
                'officer_range': (4, 10),
                'barricade_need': 'medium',
                'diversion_need': 'medium',
                'notes': 'Scene management + traffic flow around incident'
            },
            'construction': {
                'needs_police': False,
                'base_officers': 3,
                'officer_range': (2, 6),
                'barricade_need': 'medium',
                'diversion_need': 'medium',
                'notes': 'Construction crew handles safety; 1-2 officers for flow'
            },
            'vehicle_breakdown': {
                'needs_police': False,
                'base_officers': 2,
                'officer_range': (1, 4),
                'barricade_need': 'low',
                'diversion_need': 'low',
                'notes': 'Tow truck + minor traffic management; minimal police'
            },
            'pot_hole': {
                'needs_police': False,
                'base_officers': 1,
                'officer_range': (0, 2),
                'barricade_need': 'low',
                'diversion_need': 'none',
                'notes': 'BBMP/maintenance team; police rarely needed'
            },
            'water_logging': {
                'needs_police': True,
                'base_officers': 4,
                'officer_range': (3, 8),
                'barricade_need': 'medium',
                'diversion_need': 'medium',
                'notes': 'Route diversion + safety control required'
            },
            'tree_fall': {
                'needs_police': False,
                'base_officers': 2,
                'officer_range': (1, 4),
                'barricade_need': 'low',
                'diversion_need': 'low',
                'notes': 'BBMP clears; minimal traffic control needed'
            },
            'congestion': {
                'needs_police': True,
                'base_officers': 5,
                'officer_range': (3, 8),
                'barricade_need': 'low',
                'diversion_need': 'medium',
                'notes': 'Signal management + diversion advisory'
            },
        }
        # Fallback for unknown types
        return profiles.get(event_type, {
            'needs_police': True,
            'base_officers': 5,
            'officer_range': (3, 10),
            'barricade_need': 'low',
            'diversion_need': 'low',
            'notes': 'Standard traffic management'
        })

    def _priority_multiplier(self, impact_score: float) -> float:
        """
        Convert impact score into a priority multiplier (0.8 – 1.5).
        VIP at score 6 still gets more resources than pot_hole at score 9
        because the event profile caps the base differently.
        """
        if impact_score >= 9:
            return 1.5
        elif impact_score >= 7:
            return 1.2
        elif impact_score >= 5:
            return 1.0
        else:
            return 0.8

    # ========================================================================
    # MANPOWER RECOMMENDATION
    # ========================================================================

    def _recommend_manpower(self, score: float, event_type: str = '') -> Dict:
        """Recommend police officer deployment based on event type + impact score"""

        profile = self._get_event_profile(event_type)
        multiplier = self._priority_multiplier(score)

        base = profile['base_officers']
        lo, hi = profile['officer_range']

        recommended = max(lo, min(hi, round(base * multiplier)))

        if not profile['needs_police']:
            level = 'MONITORING'
            description = f"Police monitoring optional. {profile['notes']}"
        elif recommended <= 3:
            level = 'MINIMAL'
            description = profile['notes']
        elif recommended <= 8:
            level = 'LOW'
            description = profile['notes']
        elif recommended <= 15:
            level = 'MODERATE'
            description = profile['notes']
        elif recommended <= 22:
            level = 'HIGH'
            description = profile['notes']
        else:
            level = 'CRITICAL'
            description = profile['notes']

        return {
            'min_officers': lo,
            'max_officers': hi,
            'recommended': recommended,
            'level': level,
            'needs_police': profile['needs_police'],
            'description': description
        }

    # ========================================================================
    # BARRICADE RECOMMENDATION
    # ========================================================================
    
    def _recommend_barricades(self, score: float, corridor: str = None, event_type: str = '') -> Dict:
        """Recommend barricade locations and extent based on event type + score"""
        
        # Get corridor-specific barricades
        if corridor and corridor in self.barricade_points:
            corridor_barricades = self.barricade_points[corridor]
        else:
            corridor_barricades = ['Main junction', 'Secondary junction']

        profile = self._get_event_profile(event_type)
        need = profile['barricade_need']  # 'none' | 'low' | 'medium' | 'high'

        # Events that almost never need barricades
        if need == 'none' or event_type in ('pot_hole', 'tree_fall'):
            return {
                'count': 0,
                'locations': [],
                'level': 'NONE',
                'description': 'No barricades needed — maintenance crew handles the site'
            }

        # Low-need events: at most 1 cone/barrier at the spot
        if need == 'low':
            return {
                'count': 1,
                'locations': corridor_barricades[:1],
                'level': 'MINIMAL',
                'description': 'Single barrier/cone at incident spot'
            }

        # Medium-need events (accidents, construction, water-logging)
        if need == 'medium':
            if score >= 8:
                return {
                    'count': 2,
                    'locations': corridor_barricades[:2],
                    'level': 'MODERATE',
                    'description': 'Barricade incident zone + upstream junction'
                }
            else:
                return {
                    'count': 1,
                    'locations': corridor_barricades[:1],
                    'level': 'MINIMAL',
                    'description': 'Single barrier at incident point'
                }

        # High-need events (VIP, procession, public_event)
        if score >= 9:
            return {
                'count': len(corridor_barricades),
                'locations': corridor_barricades,
                'level': 'FULL',
                'description': 'Full route barricading, all junctions controlled'
            }
        elif score >= 7:
            return {
                'count': min(3, len(corridor_barricades)),
                'locations': corridor_barricades[:3],
                'level': 'HEAVY',
                'description': 'Major junctions barricaded along route'
            }
        else:
            return {
                'count': 2,
                'locations': corridor_barricades[:2],
                'level': 'MODERATE',
                'description': 'Entry & exit points barricaded'
            }
    
    # ========================================================================
    # DIVERSION ROUTE RECOMMENDATION
    # ========================================================================
    
    def _recommend_diversions(self, score: float, corridor: str = None, event_type: str = '') -> Dict:
        """Recommend alternate routes for traffic diversion based on event type + score"""
        
        # Get corridor-specific diversions
        if corridor and corridor in self.corridor_diversions:
            available_routes = self.corridor_diversions[corridor]
        else:
            available_routes = ['ORR', 'HSR Layout', 'Whitefield Road']

        profile = self._get_event_profile(event_type)
        need = profile['diversion_need']  # 'none' | 'low' | 'medium' | 'high'

        # Events that don't affect through traffic at all
        if need == 'none':
            return {
                'primary': None,
                'secondary': None,
                'level': 'NONE',
                'description': 'No diversion needed — spot repair, traffic flows normally'
            }

        # Minor incidents: advisory only
        if need == 'low':
            return {
                'primary': available_routes[0] if available_routes else 'Parallel Road',
                'secondary': None,
                'level': 'ADVISORY',
                'description': f'Optional advisory diversion via {available_routes[0] if available_routes else "alternate route"}'
            }

        # Medium need (accidents, construction, water-logging, congestion)
        if need == 'medium':
            if score >= 8:
                return {
                    'primary': available_routes[0] if available_routes else 'ORR',
                    'secondary': available_routes[1] if len(available_routes) > 1 else 'HSR Layout',
                    'level': 'MODERATE',
                    'description': f'Divert via {available_routes[0] if available_routes else "ORR"} and {available_routes[1] if len(available_routes) > 1 else "HSR Layout"}'
                }
            else:
                return {
                    'primary': available_routes[0] if available_routes else 'ORR',
                    'secondary': None,
                    'level': 'MINIMAL',
                    'description': f'Minor diversion via {available_routes[0] if available_routes else "alternate route"}'
                }

        # High need (VIP, procession, major public event)
        if score >= 9:
            return {
                'primary': available_routes[0] if available_routes else 'ORR North',
                'secondary': available_routes[1] if len(available_routes) > 1 else 'HSR Layout',
                'tertiary': available_routes[2] if len(available_routes) > 2 else 'Whitefield Road',
                'level': 'CRITICAL',
                'description': 'Full route clearance — all alternate corridors activated'
            }
        elif score >= 7:
            return {
                'primary': available_routes[0] if available_routes else 'ORR',
                'secondary': available_routes[1] if len(available_routes) > 1 else 'HSR Layout',
                'level': 'HEAVY',
                'description': f'Heavy diversion via {available_routes[0] if available_routes else "ORR"} and {available_routes[1] if len(available_routes) > 1 else "HSR Layout"}'
            }
        else:
            return {
                'primary': available_routes[0] if available_routes else 'ORR',
                'secondary': None,
                'level': 'MODERATE',
                'description': f'Divert traffic via {available_routes[0] if available_routes else "alternate route"}'
            }
    
    # ========================================================================
    # TIMING RECOMMENDATION
    # ========================================================================
    
    def _recommend_timing(self, score: float, duration_hours: float = None, event_type: str = '') -> Dict:
        """Recommend setup, event, and cleanup timings based on event type"""
        
        # Default duration if not provided
        if duration_hours is None:
            duration_hours = 1

        # Planned events need advance setup; unplanned events have no setup time
        planned_types = ('vip_movement', 'procession', 'public_event')
        unplanned_types = ('accident', 'vehicle_breakdown', 'pot_hole', 'tree_fall',
                           'water_logging', 'congestion')
        infrastructure_types = ('construction',)

        if event_type in planned_types:
            if score >= 9:
                setup = 2.0
                cleanup = 1.0
            elif score >= 7:
                setup = 1.5
                cleanup = 0.5
            else:
                setup = 1.0
                cleanup = 0.5
        elif event_type in infrastructure_types:
            # Construction: no police setup needed; just duration matters
            setup = 0.0
            cleanup = 0.5
        else:
            # Unplanned: no advance setup possible, cleanup after clearance
            setup = 0.0
            if score >= 8:
                cleanup = 1.0
            elif score >= 5:
                cleanup = 0.5
            else:
                cleanup = 0.25

        return {
            'setup_hours_before': setup,
            'event_hours': duration_hours,
            'cleanup_hours_after': cleanup,
            'total_impact_hours': round(duration_hours + setup + cleanup, 2),
            'description': (
                f"{'Pre-deployment: ' + str(setup) + 'h before | ' if setup > 0 else 'No advance setup (unplanned event) | '}"
                f"Duration: {duration_hours}h | "
                f"Clearance: {cleanup}h after"
            )
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
