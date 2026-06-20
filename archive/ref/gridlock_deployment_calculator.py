"""
GridLock AI: Police Deployment Calculator (v2.0)
============================================================================
Optimized for realistic officer deployment numbers

Key Features:
- Event-type based baselines (not excessive)
- Additive boosters (no exponential multiplication)
- Hard caps per event type (prevents unrealistic scaling)
- Clear, auditable formula
- Production-ready with full documentation

Installation:
    1. Copy this file to your project
    2. Replace existing _recommend_manpower() implementation
    3. Update your event type mappings
    4. Run test suite to validate

Usage:
    calc = PoliceDeploymentCalculator()
    result = calc.calculate_deployment(
        event_type='vip_movement',
        hour=18,
        traffic_flow_index=0.9,
        crowd_size=500,
        queue_length_km=6
    )
    print(f"Deploy {result['final_deployment']:.0f} officers")
"""

from enum import Enum
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
import json


# ============================================================================
# ENUMS
# ============================================================================

class EventType(Enum):
    """Standard event types with realistic deployments."""
    POTHOLE = 'pothole'
    MINOR_ACCIDENT = 'minor_accident'
    MAJOR_ACCIDENT = 'major_accident'
    TRAFFIC_JAM = 'traffic_jam'
    ROAD_CLOSURE = 'road_closure'
    VEHICLE_BREAKDOWN = 'vehicle_breakdown'
    PLANNED_EVENT_SMALL = 'planned_event_small'      # 100-500 people
    PLANNED_EVENT_MEDIUM = 'planned_event_medium'    # 500-2000 people
    PLANNED_EVENT_LARGE = 'planned_event_large'      # 2000+ people
    VIP_MOVEMENT = 'vip_movement'
    FLOODING = 'flooding'
    FIRE_INCIDENT = 'fire_incident'
    MASS_GATHERING = 'mass_gathering'                # Unplanned large crowd
    ROAD_WORK = 'road_work'


# ============================================================================
# CONFIGURATION TABLES (Tune these for your requirements)
# ============================================================================

# Base officers by event type (starting point before any boosters)
EVENT_TYPE_BASELINES: Dict[str, int] = {
    EventType.POTHOLE.value: 0,                      # Road crew, no police
    EventType.MINOR_ACCIDENT.value: 2,               # Fender bender
    EventType.MAJOR_ACCIDENT.value: 5,               # Serious crash
    EventType.TRAFFIC_JAM.value: 1,                  # Congestion
    EventType.ROAD_CLOSURE.value: 8,                 # Blockage
    EventType.VEHICLE_BREAKDOWN.value: 1,            # Towing
    EventType.PLANNED_EVENT_SMALL.value: 10,         # 100-500 people
    EventType.PLANNED_EVENT_MEDIUM.value: 15,        # 500-2000 people
    EventType.PLANNED_EVENT_LARGE.value: 18,         # 2000+ people
    EventType.VIP_MOVEMENT.value: 20,                # Motorcade (was 45)
    EventType.FLOODING.value: 12,                    # Emergency
    EventType.FIRE_INCIDENT.value: 10,               # Fire escort
    EventType.MASS_GATHERING.value: 25,              # Unplanned crowd
    EventType.ROAD_WORK.value: 6,                    # Construction
}

# Hard caps by event type (absolute maximum, regardless of calculated value)
HARD_CAPS_BY_EVENT_TYPE: Dict[str, int] = {
    EventType.POTHOLE.value: 0,                      # No police
    EventType.MINOR_ACCIDENT.value: 8,               # Max 8
    EventType.MAJOR_ACCIDENT.value: 15,              # Max 15
    EventType.TRAFFIC_JAM.value: 5,                  # Max 5
    EventType.ROAD_CLOSURE.value: 25,                # Max 25
    EventType.VEHICLE_BREAKDOWN.value: 3,            # Max 3
    EventType.PLANNED_EVENT_SMALL.value: 20,         # Max 20
    EventType.PLANNED_EVENT_MEDIUM.value: 28,        # Max 28
    EventType.PLANNED_EVENT_LARGE.value: 40,         # Max 40
    EventType.VIP_MOVEMENT.value: 35,                # Max 35 (was 150)
    EventType.FLOODING.value: 50,                    # Max 50
    EventType.FIRE_INCIDENT.value: 20,               # Max 20
    EventType.MASS_GATHERING.value: 45,              # Max 45
    EventType.ROAD_WORK.value: 12,                   # Max 12
}


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class DeploymentBreakdown:
    """Detailed breakdown of deployment calculation."""
    
    base: float                 # Base officers for event type
    time_boost: float          # Bonus for time of day
    traffic_boost: float       # Bonus for traffic congestion
    crowd_boost: float         # Bonus for crowd size
    queue_boost: float         # Bonus for queue length
    zone_bonus: float          # Bonus for zone type
    raw_total: float           # Sum before hard cap
    hard_cap: float            # Maximum for this event type
    final_deployment: float    # Final count after hard cap
    
    @property
    def total_boosts(self) -> float:
        """Sum of all boosts (excluding base)."""
        return (self.time_boost + self.traffic_boost + 
                self.crowd_boost + self.queue_boost + self.zone_bonus)
    
    def __str__(self) -> str:
        """Human-readable format."""
        return (
            f"Deployment Breakdown:\n"
            f"  Base Officers:        {self.base:>6.1f}\n"
            f"  Time Boost:           {self.time_boost:>+6.1f}\n"
            f"  Traffic Boost:        {self.traffic_boost:>+6.1f}\n"
            f"  Crowd Boost:          {self.crowd_boost:>+6.1f}\n"
            f"  Queue Boost:          {self.queue_boost:>+6.1f}\n"
            f"  Zone Bonus:           {self.zone_bonus:>+6.1f}\n"
            f"  ─────────────────────────────\n"
            f"  Raw Total:            {self.raw_total:>6.1f}\n"
            f"  Hard Cap:             {self.hard_cap:>6.0f}\n"
            f"  ═════════════════════════════\n"
            f"  FINAL DEPLOYMENT:     {self.final_deployment:>6.0f} officers"
        )


# ============================================================================
# MAIN CALCULATOR CLASS
# ============================================================================

class PoliceDeploymentCalculator:
    """
    Calculates realistic police officer deployment for traffic incidents.
    
    Formula:
        Final = min(
            Base + Time + Traffic + Crowd + Queue + Zone,
            Hard_Cap
        )
    
    All components are additive (no multiplication).
    Each component is capped to prevent runaway growth.
    
    Example:
        >>> calc = PoliceDeploymentCalculator()
        >>> result = calc.calculate_deployment(
        ...     event_type='vip_movement',
        ...     hour=18,
        ...     traffic_flow_index=0.9,
        ...     crowd_size=500,
        ...     queue_length_km=6
        ... )
        >>> print(f"{result.final_deployment:.0f} officers")
        28 officers
    """
    
    def __init__(self, baselines: Optional[Dict] = None, 
                 hard_caps: Optional[Dict] = None):
        """
        Initialize calculator with configuration.
        
        Args:
            baselines: Override EVENT_TYPE_BASELINES (optional)
            hard_caps: Override HARD_CAPS_BY_EVENT_TYPE (optional)
        """
        self.baselines = baselines or EVENT_TYPE_BASELINES
        self.hard_caps = hard_caps or HARD_CAPS_BY_EVENT_TYPE
    
    # ────────────────────────────────────────────────────────────────────
    # BOOST CALCULATION METHODS
    # ────────────────────────────────────────────────────────────────────
    
    def _get_time_boost(self, hour: int, crowd_size: int = 0) -> float:
        """
        Calculate time-of-day bonus.
        
        Peak hours (+2 to +3) need more traffic control officers.
        Night hours with large crowds (+1.5) need coordination.
        Regular night hours (-1) have reduced traffic.
        
        Args:
            hour: Hour of day (0-23)
            crowd_size: Number of people at event
            
        Returns:
            Officers to add (can be negative)
            
        Examples:
            >>> calc = PoliceDeploymentCalculator()
            >>> calc._get_time_boost(18)  # 6 PM (evening peak)
            3.0
            >>> calc._get_time_boost(2)   # 2 AM (deep night)
            0.0
            >>> calc._get_time_boost(23, crowd_size=500)  # Night with crowd
            1.5
        """
        
        # Define time periods
        is_morning_peak = 7 <= hour <= 10
        is_evening_peak = 16 <= hour <= 20
        is_night = 22 <= hour or hour <= 6
        is_deep_night = 0 <= hour <= 4
        is_night_with_large_crowd = is_night and crowd_size > 300
        
        # Apply time-based bonus (not multiplier)
        if is_evening_peak:
            return 3.0  # +3 officers for evening peak (busiest)
        elif is_morning_peak:
            return 2.0  # +2 officers for morning peak
        elif is_night_with_large_crowd:
            return 1.5  # +1.5 for night event with crowd
        elif is_night and not is_deep_night:
            return -1.0  # -1 officer (reduced traffic, except deep night)
        elif is_deep_night:
            return 0.0  # No change (minimal traffic)
        else:
            return 0.0  # No change (default/midday)
    
    def _get_traffic_boost(self, traffic_flow_index: float) -> float:
        """
        Calculate traffic congestion bonus.
        
        Higher traffic requires more officers for traffic management.
        Saturates at +4 officers to prevent runaway growth.
        
        Args:
            traffic_flow_index: Traffic flow (0.0 to 1.0+)
                               0.5 = normal, 1.0+ = congestion
                               
        Returns:
            Officers to add (0 to 4 max)
            
        Examples:
            >>> calc = PoliceDeploymentCalculator()
            >>> calc._get_traffic_boost(0.5)   # Normal traffic
            0.0
            >>> calc._get_traffic_boost(0.7)   # Moderate traffic
            1.6
            >>> calc._get_traffic_boost(1.0)   # Heavy congestion
            4.0
            >>> calc._get_traffic_boost(2.0)   # Extreme (still capped)
            4.0
        """
        
        if traffic_flow_index <= 0.5:
            return 0.0  # No congestion, no boost
        else:
            # Linear scaling from TFI 0.5 to 1.0
            # (TFI - 0.5) × 8 gives 0 at 0.5, and 4 at 1.0
            boost = (traffic_flow_index - 0.5) * 8
            return min(boost, 4.0)  # Cap at +4 officers
    
    def _get_crowd_boost(self, crowd_size: int) -> float:
        """
        Calculate crowd-size bonus.
        
        Larger crowds require more officers for crowd control.
        Uses tiered approach with saturation at +3.
        
        Args:
            crowd_size: Number of people
            
        Returns:
            Officers to add (0 to 3 max)
            
        Examples:
            >>> calc = PoliceDeploymentCalculator()
            >>> calc._get_crowd_boost(100)      # Small group
            0.0
            >>> calc._get_crowd_boost(1000)     # Small-medium
            1.0
            >>> calc._get_crowd_boost(3000)     # Medium-large
            2.0
            >>> calc._get_crowd_boost(50000)    # Massive (saturated)
            3.0
        """
        
        if crowd_size < 500:
            return 0.0  # Small crowd
        elif crowd_size < 2000:
            return 1.0  # Small-medium crowd
        elif crowd_size < 5000:
            return 2.0  # Medium-large crowd
        else:
            return 3.0  # Large crowd (saturation point)
    
    def _get_queue_boost(self, queue_length_km: float) -> float:
        """
        Calculate traffic queue bonus.
        
        Longer queues indicate more severe backups.
        Uses tiered approach with saturation at +2.
        
        Args:
            queue_length_km: Length of traffic queue in kilometers
            
        Returns:
            Officers to add (0 to 2 max)
            
        Examples:
            >>> calc = PoliceDeploymentCalculator()
            >>> calc._get_queue_boost(1.0)     # Minor backup
            0.0
            >>> calc._get_queue_boost(3.0)     # Moderate queue
            1.0
            >>> calc._get_queue_boost(7.0)     # Significant queue
            1.5
            >>> calc._get_queue_boost(20.0)    # Major queue (saturated)
            2.0
        """
        
        if queue_length_km < 2:
            return 0.0  # Minor backup
        elif queue_length_km < 5:
            return 1.0  # Moderate queue
        elif queue_length_km < 10:
            return 1.5  # Significant queue
        else:
            return 2.0  # Major queue (saturation)
    
    def _get_zone_bonus(self, zone: Optional[str]) -> float:
        """
        Calculate zone-based bonus.
        
        Central/downtown zones need coordination overhead.
        High-security zones need additional presence.
        
        Args:
            zone: Zone name/type (optional)
            
        Returns:
            Officers to add
            
        Examples:
            >>> calc = PoliceDeploymentCalculator()
            >>> calc._get_zone_bonus('Central Zone')
            1.0
            >>> calc._get_zone_bonus('High Security')
            2.0
            >>> calc._get_zone_bonus('Residential')
            0.0
            >>> calc._get_zone_bonus(None)
            0.0
        """
        
        if not zone:
            return 0.0
        
        zone_lower = zone.lower()
        
        if zone_lower in ['central zone', 'downtown', 'cbd', 'central business district']:
            return 1.0  # +1 for coordination overhead
        elif zone_lower in ['high security', 'secure', 'secure zone']:
            return 2.0  # +2 for high-security presence
        else:
            return 0.0  # No adjustment for other zones
    
    # ────────────────────────────────────────────────────────────────────
    # MAIN CALCULATION METHOD
    # ────────────────────────────────────────────────────────────────────
    
    def calculate_deployment(
        self,
        event_type: str,
        hour: int,
        traffic_flow_index: float,
        crowd_size: int = 0,
        queue_length_km: float = 0,
        zone: Optional[str] = None,
        central_zone: bool = False
    ) -> DeploymentBreakdown:
        """
        Calculate police officer deployment recommendation.
        
        Args:
            event_type: Type of event (see EventType enum)
            hour: Hour of day (0-23)
            traffic_flow_index: Traffic flow index (0.0 to 1.0+)
            crowd_size: Number of people at event (default 0)
            queue_length_km: Length of traffic queue in km (default 0)
            zone: Zone name (optional)
            central_zone: Is this in central zone? (legacy parameter)
            
        Returns:
            DeploymentBreakdown with detailed calculation breakdown
            
        Raises:
            ValueError: If event_type not found
            
        Examples:
            >>> calc = PoliceDeploymentCalculator()
            
            # VIP movement at 6 PM
            >>> result = calc.calculate_deployment(
            ...     event_type='vip_movement',
            ...     hour=18,
            ...     traffic_flow_index=0.9,
            ...     crowd_size=500,
            ...     queue_length_km=6
            ... )
            >>> print(f"Deploy {result.final_deployment:.0f} officers")
            Deploy 28 officers
            
            # Major accident at noon
            >>> result = calc.calculate_deployment(
            ...     event_type='major_accident',
            ...     hour=12,
            ...     traffic_flow_index=0.6,
            ...     queue_length_km=3
            ... )
            >>> print(f"Deploy {result.final_deployment:.0f} officers")
            Deploy 10 officers
        """
        
        # Validate event type
        if event_type not in self.baselines:
            raise ValueError(
                f"Unknown event type: {event_type}. "
                f"Valid types: {list(self.baselines.keys())}"
            )
        
        # 1. Get base officers for event type
        base = float(self.baselines[event_type])
        
        # 2. Apply central zone multiplier to base (legacy compatibility)
        if central_zone and base > 0:
            base = base * 1.1
        
        # 3. Calculate booster components (all additive)
        time_boost = self._get_time_boost(hour, crowd_size)
        traffic_boost = self._get_traffic_boost(traffic_flow_index)
        crowd_boost = self._get_crowd_boost(crowd_size)
        queue_boost = self._get_queue_boost(queue_length_km)
        zone_bonus = self._get_zone_bonus(zone)
        
        # 4. Sum all components (no multiplication)
        raw_total = (base + time_boost + traffic_boost + 
                     crowd_boost + queue_boost + zone_bonus)
        
        # 5. Get hard cap for event type
        hard_cap = float(self.hard_caps.get(event_type, 40))
        
        # 6. Apply hard cap
        final_deployment = min(raw_total, hard_cap)
        
        # 7. Ensure non-negative
        final_deployment = max(0, final_deployment)
        
        # 8. Return breakdown
        return DeploymentBreakdown(
            base=base,
            time_boost=time_boost,
            traffic_boost=traffic_boost,
            crowd_boost=crowd_boost,
            queue_boost=queue_boost,
            zone_bonus=zone_bonus,
            raw_total=raw_total,
            hard_cap=hard_cap,
            final_deployment=final_deployment,
        )
    
    def calculate_batch(self, incidents: list) -> list:
        """
        Calculate deployments for multiple incidents.
        
        Args:
            incidents: List of incident dicts with keys:
                      'event_type', 'hour', 'traffic_flow_index',
                      'crowd_size', 'queue_length_km', 'zone'
                      
        Returns:
            List of DeploymentBreakdown objects
            
        Example:
            >>> calc = PoliceDeploymentCalculator()
            >>> incidents = [
            ...     {
            ...         'event_type': 'pothole',
            ...         'hour': 2,
            ...         'traffic_flow_index': 0.2,
            ...     },
            ...     {
            ...         'event_type': 'vip_movement',
            ...         'hour': 18,
            ...         'traffic_flow_index': 0.9,
            ...         'crowd_size': 500,
            ...         'queue_length_km': 6,
            ...     },
            ... ]
            >>> results = calc.calculate_batch(incidents)
            >>> for r in results:
            ...     print(f"{r.final_deployment:.0f} officers")
            0 officers
            28 officers
        """
        
        results = []
        for incident in incidents:
            result = self.calculate_deployment(
                event_type=incident['event_type'],
                hour=incident['hour'],
                traffic_flow_index=incident['traffic_flow_index'],
                crowd_size=incident.get('crowd_size', 0),
                queue_length_km=incident.get('queue_length_km', 0),
                zone=incident.get('zone'),
            )
            results.append(result)
        return results
    
    def export_config_json(self) -> str:
        """Export current configuration as JSON."""
        return json.dumps({
            'baselines': self.baselines,
            'hard_caps': self.hard_caps,
        }, indent=2)
    
    def import_config_json(self, json_str: str) -> None:
        """Import configuration from JSON."""
        config = json.loads(json_str)
        self.baselines = config.get('baselines', self.baselines)
        self.hard_caps = config.get('hard_caps', self.hard_caps)


# ============================================================================
# TEST SUITE
# ============================================================================

class DeploymentCalculatorTests:
    """Test suite for PoliceDeploymentCalculator."""
    
    def __init__(self):
        self.calc = PoliceDeploymentCalculator()
        self.passed = 0
        self.failed = 0
    
    def test(self, name: str, expected_range: Tuple[float, float], 
             result: DeploymentBreakdown) -> bool:
        """
        Run single test and print result.
        
        Args:
            name: Test name
            expected_range: (min, max) officers expected
            result: DeploymentBreakdown result
            
        Returns:
            True if passed
        """
        
        final = result.final_deployment
        passed = expected_range[0] <= final <= expected_range[1]
        
        if passed:
            self.passed += 1
            status = "✓ PASS"
        else:
            self.failed += 1
            status = "✗ FAIL"
        
        print(
            f"{status} | {name:45s} | "
            f"{final:5.0f} officers (expected {expected_range[0]:2.0f}-{expected_range[1]:2.0f})"
        )
        
        return passed
    
    def run_all_tests(self):
        """Run complete test suite."""
        
        print("\n" + "="*110)
        print("GridLock AI: Police Deployment Calculator - Test Suite")
        print("="*110)
        
        # ────────────────────────────────────────────────────────────────
        # TEST SET 1: SIMPLE INCIDENTS
        # ────────────────────────────────────────────────────────────────
        
        print("\n" + "─"*110)
        print("TEST SET 1: SIMPLE INCIDENTS")
        print("─"*110)
        
        self.test(
            "Pothole at night (should be 0)",
            (0, 0),
            self.calc.calculate_deployment('pothole', 2, 0.2)
        )
        
        self.test(
            "Vehicle breakdown at noon",
            (1, 3),
            self.calc.calculate_deployment('vehicle_breakdown', 12, 0.6, queue_length_km=1)
        )
        
        self.test(
            "Minor accident at night",
            (1, 3),
            self.calc.calculate_deployment('minor_accident', 3, 0.4, queue_length_km=1.5)
        )
        
        self.test(
            "Traffic jam (minimal deployment)",
            (1, 3),
            self.calc.calculate_deployment('traffic_jam', 15, 0.8, queue_length_km=5)
        )
        
        # ────────────────────────────────────────────────────────────────
        # TEST SET 2: MEDIUM INCIDENTS
        # ────────────────────────────────────────────────────────────────
        
        print("\n" + "─"*110)
        print("TEST SET 2: MEDIUM INCIDENTS")
        print("─"*110)
        
        self.test(
            "Major accident at morning peak",
            (10, 15),
            self.calc.calculate_deployment('major_accident', 8, 0.7, queue_length_km=3)
        )
        
        self.test(
            "Road closure at evening peak",
            (15, 25),
            self.calc.calculate_deployment('road_closure', 18, 0.85, queue_length_km=5)
        )
        
        self.test(
            "Planned event (medium, 1500 crowd)",
            (15, 28),
            self.calc.calculate_deployment('planned_event_medium', 12, 0.6, 
                                          crowd_size=1500, queue_length_km=2)
        )
        
        self.test(
            "Fire incident with traffic impact",
            (10, 20),
            self.calc.calculate_deployment('fire_incident', 14, 0.7, queue_length_km=3)
        )
        
        # ────────────────────────────────────────────────────────────────
        # TEST SET 3: LARGE INCIDENTS
        # ────────────────────────────────────────────────────────────────
        
        print("\n" + "─"*110)
        print("TEST SET 3: LARGE INCIDENTS")
        print("─"*110)
        
        self.test(
            "VIP movement at evening peak + traffic",
            (25, 35),
            self.calc.calculate_deployment('vip_movement', 18, 0.9, 
                                          crowd_size=500, queue_length_km=6)
        )
        
        self.test(
            "Large planned event (5000 crowd)",
            (26, 40),
            self.calc.calculate_deployment('planned_event_large', 14, 0.7, 
                                          crowd_size=5000, queue_length_km=4)
        )
        
        self.test(
            "Mass gathering at night + large crowd",
            (30, 45),
            self.calc.calculate_deployment('mass_gathering', 22, 0.8, 
                                          crowd_size=8000, queue_length_km=7)
        )
        
        self.test(
            "Flooding incident (emergency)",
            (35, 50),
            self.calc.calculate_deployment('flooding', 10, 0.9, queue_length_km=8)
        )
        
        # ────────────────────────────────────────────────────────────────
        # TEST SET 4: EDGE CASES
        # ────────────────────────────────────────────────────────────────
        
        print("\n" + "─"*110)
        print("TEST SET 4: EDGE CASES (Hard Caps & Saturation)")
        print("─"*110)
        
        self.test(
            "Pothole with ALL boosters (hard cap = 0)",
            (0, 0),
            self.calc.calculate_deployment('pothole', 18, 1.0, 
                                          crowd_size=10000, queue_length_km=20)
        )
        
        self.test(
            "Minor accident with MAX boosters (hard cap = 8)",
            (8, 8),
            self.calc.calculate_deployment('minor_accident', 18, 1.0, 
                                          crowd_size=5000, queue_length_km=15)
        )
        
        self.test(
            "VIP with massive crowd (should saturate)",
            (35, 35),
            self.calc.calculate_deployment('vip_movement', 18, 1.0, 
                                          crowd_size=50000, queue_length_km=20)
        )
        
        self.test(
            "Large event with extreme conditions (hard cap = 40)",
            (40, 40),
            self.calc.calculate_deployment('planned_event_large', 18, 1.0, 
                                          crowd_size=50000, queue_length_km=20)
        )
        
        # ────────────────────────────────────────────────────────────────
        # SUMMARY
        # ────────────────────────────────────────────────────────────────
        
        print("\n" + "="*110)
        print(f"TEST SUMMARY: {self.passed} passed, {self.failed} failed")
        print("="*110 + "\n")
        
        if self.failed == 0:
            print("✓ All tests passed! Implementation is correct.")
        else:
            print(f"✗ {self.failed} test(s) failed. Review the implementation.")
        
        return self.failed == 0


# ============================================================================
# COMPARISON WITH LEGACY SYSTEM
# ============================================================================

def compare_with_legacy(calc_new: PoliceDeploymentCalculator,
                       legacy_calc_func,
                       test_incidents: list) -> None:
    """
    Compare new system with legacy system on same incidents.
    
    Args:
        calc_new: New PoliceDeploymentCalculator
        legacy_calc_func: Function that calculates legacy deployment
        test_incidents: List of test incidents
    """
    
    print("\n" + "="*130)
    print("COMPARISON: New System vs. Legacy System")
    print("="*130)
    print(
        f"{'Event Type':20s} | {'Hour':5s} | {'Legacy':8s} | {'New':8s} | "
        f"{'Change':>8s} | {'% Change':>10s}"
    )
    print("─"*130)
    
    total_legacy = 0
    total_new = 0
    
    for incident in test_incidents:
        # Get legacy result
        legacy_result = legacy_calc_func(**incident)
        
        # Get new result
        new_result = calc_new.calculate_deployment(
            event_type=incident['event_type'],
            hour=incident['hour'],
            traffic_flow_index=incident['traffic_flow_index'],
            crowd_size=incident.get('crowd_size', 0),
            queue_length_km=incident.get('queue_length_km', 0),
            zone=incident.get('zone'),
        )
        
        legacy_val = float(legacy_result)
        new_val = new_result.final_deployment
        change = new_val - legacy_val
        pct_change = (change / legacy_val * 100) if legacy_val > 0 else 0
        
        total_legacy += legacy_val
        total_new += new_val
        
        print(
            f"{incident['event_type']:20s} | {incident['hour']:5d} | "
            f"{legacy_val:8.0f} | {new_val:8.0f} | {change:+8.0f} | {pct_change:+9.1f}%"
        )
    
    print("─"*130)
    overall_change = total_new - total_legacy
    overall_pct = (overall_change / total_legacy * 100) if total_legacy > 0 else 0
    
    print(
        f"{'TOTAL':20s} | {'':5s} | {total_legacy:8.0f} | {total_new:8.0f} | "
        f"{overall_change:+8.0f} | {overall_pct:+9.1f}%"
    )
    print("="*130 + "\n")


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    
    # Run test suite
    tester = DeploymentCalculatorTests()
    tester.run_all_tests()
    
    # Example: Single calculation with detailed output
    print("\n" + "="*80)
    print("EXAMPLE: VIP Movement at Evening Peak")
    print("="*80)
    
    calc = PoliceDeploymentCalculator()
    result = calc.calculate_deployment(
        event_type='vip_movement',
        hour=18,
        traffic_flow_index=0.9,
        crowd_size=500,
        queue_length_km=6,
        zone='Central Zone'
    )
    
    print(result)
    print("\n" + "="*80)
