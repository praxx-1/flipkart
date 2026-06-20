"""
PHASE 4: DEMO CASES (CORRECTED)
Generate predictions + recommendations on 5 real events from Astram dataset
"""

import pandas as pd
import numpy as np
import sys
sys.path.insert(0, '.')
from recommendation_engine import RecommendationEngine

print("=" * 80)
print("PHASE 4: DEMO CASES - REAL EVENT RECOMMENDATIONS")
print("=" * 80)

# ============================================================================
# 1. LOAD ASTRAM DATA
# ============================================================================

print("\n✅ Loading Astram dataset...")

df = pd.read_csv('../data/Astram event data_anonymized - Astram event data_anonymizedb40ac87.csv')
print(f"✅ Loaded: {df.shape[0]} events")

# Parse datetime
df['start_datetime'] = pd.to_datetime(df['start_datetime'], errors='coerce')
df['end_datetime'] = pd.to_datetime(df['end_datetime'], errors='coerce')

# Calculate duration
df['duration_minutes'] = ((df['end_datetime'] - df['start_datetime']).dt.total_seconds() / 60).fillna(60)
df['duration_hours'] = df['duration_minutes'] / 60

# ============================================================================
# 2. CREATE IMPACT SCORE
# ============================================================================

print("\n✅ Engineering impact scores...")

def calculate_impact_score(row):
    """Impact score based on event characteristics"""
    score = 5.0
    
    # Event cause impact (most important)
    cause = str(row.get('event_cause', '')).lower()
    if any(x in cause for x in ['public_event', 'procession']):
        score += 3.5
    elif 'accident' in cause:
        score += 2.5
    elif 'construction' in cause or 'vip' in cause:
        score += 2.0
    elif 'breakdown' in cause or 'congestion' in cause:
        score += 1.5
    elif any(x in cause for x in ['pot_hole', 'tree_fall', 'water']):
        score += 1.0
    else:
        score += 0.5
    
    # Priority impact
    priority = str(row.get('priority', 'Low')).lower()
    if 'high' in priority:
        score += 1.5
    elif 'medium' in priority:
        score += 0.5
    else:
        score -= 0.5
    
    # Road closure
    closure = str(row.get('requires_road_closure', 'No')).upper()
    if closure == 'YES':
        score += 2.0
    
    # Duration
    try:
        duration = float(row.get('duration_hours', 1))
        score += min(duration / 15, 1.0)
    except:
        pass
    
    return max(1, min(10, score))

df['impact_score'] = df.apply(calculate_impact_score, axis=1)

print(f"✅ Impact scores created:")
print(f"   Mean: {df['impact_score'].mean():.2f}/10")
print(f"   Std: {df['impact_score'].std():.2f}")
print(f"   Range: {df['impact_score'].min():.2f} - {df['impact_score'].max():.2f}")

# ============================================================================
# 3. SELECT 5 DIVERSE DEMO CASES
# ============================================================================

print("\n" + "=" * 80)
print("SELECTING 5 DIVERSE DEMO CASES")
print("=" * 80)

demo_cases = []

# Ensure we have valid dates
valid_df = df[df['start_datetime'].notna()].copy()

# Case 1: PUBLIC EVENT
print("\n1️⃣  Selecting: Public Event...")
mask = valid_df['event_cause'].str.contains('public', case=False, na=False)
if mask.sum() > 0:
    case1 = valid_df[mask].sample(1, random_state=42).iloc[0]
    demo_cases.append(('Public Event', case1))
    print(f"   Found: {case1['event_cause']} - Impact {case1['impact_score']:.1f}/10")

# Case 2: ACCIDENT (HIGH PRIORITY)
print("2️⃣  Selecting: High Priority Accident...")
mask = valid_df['event_cause'].str.contains('accident', case=False, na=False)
if mask.sum() > 0:
    high_priority = valid_df[mask & (valid_df['priority'] == 'High')]
    if len(high_priority) > 0:
        case2 = high_priority.sample(1, random_state=42).iloc[0]
    else:
        case2 = valid_df[mask].sample(1, random_state=42).iloc[0]
    demo_cases.append(('Accident (High Priority)', case2))
    print(f"   Found: {case2['event_cause']} - Impact {case2['impact_score']:.1f}/10")

# Case 3: CONSTRUCTION
print("3️⃣  Selecting: Construction Project...")
mask = valid_df['event_cause'].str.contains('construction', case=False, na=False)
if mask.sum() > 0:
    case3 = valid_df[mask].sample(1, random_state=42).iloc[0]
    demo_cases.append(('Construction Project', case3))
    print(f"   Found: {case3['event_cause']} - Impact {case3['impact_score']:.1f}/10")

# Case 4: VIP/PROCESSION
print("4️⃣  Selecting: VIP/Procession...")
mask = valid_df['event_cause'].str.contains('vip|procession', case=False, na=False)
if mask.sum() > 0:
    case4 = valid_df[mask].sample(1, random_state=42).iloc[0]
    demo_cases.append(('VIP/Procession', case4))
    print(f"   Found: {case4['event_cause']} - Impact {case4['impact_score']:.1f}/10")

# Case 5: VEHICLE BREAKDOWN
print("5️⃣  Selecting: Vehicle Breakdown...")
mask = valid_df['event_cause'].str.contains('breakdown', case=False, na=False)
if mask.sum() > 0:
    case5 = valid_df[mask].sample(1, random_state=42).iloc[0]
    demo_cases.append(('Vehicle Breakdown', case5))
    print(f"   Found: {case5['event_cause']} - Impact {case5['impact_score']:.1f}/10")

print(f"\n✅ Selected {len(demo_cases)} demo cases")

# ============================================================================
# 4. GENERATE RECOMMENDATIONS
# ============================================================================

print("\n" + "=" * 80)
print("GENERATING RECOMMENDATIONS")
print("=" * 80)

engine = RecommendationEngine()
results = []

for case_num, (case_name, event) in enumerate(demo_cases, 1):
    
    print(f"\n{'='*80}")
    print(f"CASE {case_num}: {case_name}")
    print(f"{'='*80}")
    
    # Extract event details
    event_cause = event.get('event_cause', 'Unknown')
    corridor = event.get('corridor', 'Non-corridor')
    zone = event.get('zone', 'Unknown') if pd.notna(event.get('zone')) else 'Unknown'
    priority = event.get('priority', 'Low')
    start_dt = event.get('start_datetime', 'Unknown')
    duration_h = event.get('duration_hours', 2)
    closure = event.get('requires_road_closure', 'No')
    impact_score = event['impact_score']
    
    print(f"\n📍 Event Details:")
    print(f"   Cause: {event_cause}")
    print(f"   Corridor: {corridor}")
    print(f"   Zone: {zone}")
    print(f"   Priority: {priority}")
    print(f"   Date/Time: {start_dt}")
    print(f"   Duration: {duration_h:.1f} hours")
    print(f"   Road Closure: {closure}")
    print(f"   Impact Score: {impact_score:.2f}/10")
    
    # Generate recommendations
    rec = engine.recommend(
        impact_score=impact_score,
        event_type=event_cause,
        corridor=corridor,
        zone=zone,
        duration_hours=duration_h
    )
    
    print(f"\n👮 Police Deployment: {rec['manpower']['recommended']} officers ({rec['manpower']['min_officers']}-{rec['manpower']['max_officers']})")
    print(f"🚧 Barricades: {rec['barricades']['count']} locations ({rec['barricades']['level']})")
    print(f"🛣️  Diversions: {rec['diversions']['level']}")
    print(f"⏰ Setup: {rec['setup_cleanup']['setup_hours_before']:.1f}h | Cleanup: {rec['setup_cleanup']['cleanup_hours_after']:.1f}h")
    
    # Store results
    results.append({
        'Case': case_num,
        'Name': case_name,
        'Event_Cause': event_cause,
        'Corridor': corridor,
        'Zone': zone,
        'Priority': priority,
        'Duration_Hours': round(duration_h, 1),
        'Impact_Score': round(impact_score, 2),
        'Officers': rec['manpower']['recommended'],
        'Officer_Range': f"{rec['manpower']['min_officers']}-{rec['manpower']['max_officers']}",
        'Barricade_Count': rec['barricades']['count'],
        'Barricade_Level': rec['barricades']['level'],
        'Diversion_Level': rec['diversions']['level'],
        'Primary_Route': rec['diversions'].get('primary', 'None'),
        'Setup_Hours': rec['setup_cleanup']['setup_hours_before'],
        'Cleanup_Hours': rec['setup_cleanup']['cleanup_hours_after'],
        'Total_Impact_Hours': rec['setup_cleanup']['total_impact_hours']
    })

# ============================================================================
# 5. SAVE RESULTS
# ============================================================================

print("\n" + "=" * 80)
print("SAVING RESULTS")
print("=" * 80)

output_dir = '../data/'

if len(results) > 0:
    results_df = pd.DataFrame(results)
    results_df.to_csv(f'{output_dir}demo_cases_results.csv', index=False)
    print(f"\n✅ Saved: demo_cases_results.csv ({len(results)} cases)")
    
    # Display summary
    print("\n" + "=" * 80)
    print("DEMO CASES SUMMARY TABLE")
    print("=" * 80)
    
    summary = results_df[['Case', 'Name', 'Impact_Score', 'Officers', 'Barricade_Level', 'Diversion_Level']]
    print("\n" + summary.to_string(index=False))
    
    # ====================================================================
    # 6. STATISTICS
    # ====================================================================
    
    print("\n" + "=" * 80)
    print("DEPLOYMENT STATISTICS")
    print("=" * 80)
    
    print(f"""
📊 Impact Scores:
   Min: {results_df['Impact_Score'].min():.1f}/10
   Max: {results_df['Impact_Score'].max():.1f}/10
   Average: {results_df['Impact_Score'].mean():.1f}/10

👮 Officer Deployment:
   Minimum: {results_df['Officers'].min()} officers
   Maximum: {results_df['Officers'].max()} officers
   Average: {results_df['Officers'].mean():.0f} officers
   Total Range: {results_df['Officer_Range'].unique().tolist()}

🚧 Barricade Setup:
   Total Locations: {results_df['Barricade_Count'].sum()} (across all cases)
   Levels Used: {results_df['Barricade_Level'].unique().tolist()}

🛣️  Traffic Diversions:
   Levels Used: {results_df['Diversion_Level'].unique().tolist()}

⏰ Time Impact:
   Max Setup: {results_df['Setup_Hours'].max():.1f} hours
   Max Cleanup: {results_df['Cleanup_Hours'].max():.1f} hours
   Max Total Impact: {results_df['Total_Impact_Hours'].max():.1f} hours
""")

    print("=" * 80)
    print("✅ PHASE 4 COMPLETE")
    print("=" * 80)
    print(f"""
🎯 What's Done:
   ✅ Recommendation Engine (converts score to actions)
   ✅ 5 Real Demo Cases (with actual Astram events)
   ✅ Full Recommendations (manpower, barricades, routes)
   ✅ CSV Output (demo_cases_results.csv)

🚀 Next: PHASE 5 - Streamlit Dashboard
   Ready to build interactive app for judges?
""")

else:
    print("❌ No demo cases selected - check data filtering")
