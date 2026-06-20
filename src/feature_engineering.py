"""
PHASE 2: FEATURE ENGINEERING
Transform raw Astram data + impact score into ML-ready features
"""

import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder
import pickle

print("=" * 80)
print("PHASE 2: FEATURE ENGINEERING")
print("=" * 80)

# ============================================================================
# 1. LOAD DATA WITH Y VARIABLE
# ============================================================================

df = pd.read_csv('../data/astram_with_impact_score.csv')
print(f"\n✅ Loaded data: {df.shape}")
print(f"Columns: {df.columns.tolist()}")

# ============================================================================
# 2. TIME-BASED FEATURES
# ============================================================================

print("\n" + "=" * 80)
print("ENGINEERING: TIME FEATURES")
print("=" * 80)

# Convert event_datetime to datetime
df['start_datetime'] = pd.to_datetime(df['start_datetime'], errors='coerce')

# Extract time components
df['hour'] = df['start_datetime'].dt.hour
df['day_of_week'] = df['start_datetime'].dt.dayofweek  # 0=Monday, 6=Sunday
df['month'] = df['start_datetime'].dt.month
df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)  # Sat/Sun = 1

# Peak hour indicator (peak hours: 7-10 AM, 4-8 PM)
df['is_peak_hour'] = ((df['hour'].isin([7, 8, 9, 10]) | 
                      df['hour'].isin([16, 17, 18, 19, 20]))).astype(int)

# Time period categorization
def categorize_time_period(hour):
    if 5 <= hour < 12:
        return 0  # Morning
    elif 12 <= hour < 17:
        return 1  # Afternoon
    elif 17 <= hour < 21:
        return 2  # Evening
    else:
        return 3  # Night

df['time_period'] = df['hour'].apply(categorize_time_period)

print("\n✅ Time Features Created:")
print(f"   - hour (0-23)")
print(f"   - day_of_week (0-6)")
print(f"   - month (1-12)")
print(f"   - is_weekend (0/1)")
print(f"   - is_peak_hour (0/1)")
print(f"   - time_period (0-3)")

# ============================================================================
# 3. EVENT TYPE & CAUSE FEATURES
# ============================================================================

print("\n" + "=" * 80)
print("ENGINEERING: EVENT TYPE & CAUSE")
print("=" * 80)

# Encode event_type
le_event = LabelEncoder()
df['event_type'] = le_event.fit_transform(df['event_type'].astype(str))
print(f"\n✅ event_type encoded: {len(le_event.classes_)} categories")
print(f"   Classes: {le_event.classes_}")

# Encode event_cause
le_cause = LabelEncoder()
df['event_cause'] = le_cause.fit_transform(df['event_cause'].astype(str))
print(f"\n✅ event_cause encoded: {len(le_cause.classes_)} categories")
print(f"   Classes: {le_cause.classes_}")

# ============================================================================
# 4. LOCATION FEATURES
# ============================================================================

print("\n" + "=" * 80)
print("ENGINEERING: LOCATION FEATURES")
print("=" * 80)

# Top corridors
top_corridors = df['corridor'].value_counts().head(10).index.tolist()

# Encode corridor (top corridors separate, others = 'Other')
df['corridor_encoded'] = df['corridor'].apply(
    lambda x: top_corridors.index(x) if x in top_corridors else len(top_corridors)
)

print(f"\n✅ corridor encoded: Top 10 corridors")
for i, corr in enumerate(top_corridors):
    print(f"   {i}: {corr}")

# Encode zone
le_zone = LabelEncoder()
df['zone'] = le_zone.fit_transform(df['zone'].astype(str))
print(f"\n✅ zone encoded: {len(le_zone.classes_)} zones")

# ============================================================================
# 5. EVENT PRIORITY & CHARACTERISTICS
# ============================================================================

print("\n" + "=" * 80)
print("ENGINEERING: EVENT CHARACTERISTICS")
print("=" * 80)

# High priority
df['is_high_priority'] = (df['priority'] == 'HIGH').astype(int)
print(f"✅ is_high_priority: {df['is_high_priority'].sum()} HIGH priority events")

# Road closure
df['requires_road_closure_bool'] = (df['requires_road_closure'] == 'YES').astype(int)
print(f"✅ requires_road_closure_bool: {df['requires_road_closure_bool'].sum()} closures")

# Planned vs Unplanned
df['is_planned'] = (df['event_type'] == 'planned').astype(int)
print(f"✅ is_planned: {df['is_planned'].sum()} planned events")

# ============================================================================
# 6. INTERACTION FEATURES
# ============================================================================

print("\n" + "=" * 80)
print("ENGINEERING: INTERACTION FEATURES")
print("=" * 80)

# Major event (public_event or procession)
major_event_types = ['public_event', 'procession']
df['is_major_event'] = df['event_type'].isin(major_event_types).astype(int)
print(f"✅ is_major_event: {df['is_major_event'].sum()} major events")

# Major corridor
major_corridors = ['Mysore Road', 'Bellary Road 1', 'Bellary Road 2', 
                   'ORR North', 'ORR East 1', 'ORR East 2']
df['is_major_corridor'] = df['corridor'].isin(major_corridors).astype(int)
print(f"✅ is_major_corridor: {df['is_major_corridor'].sum()} events on major corridors")

# Critical situation (HIGH priority + closure)
df['critical_situation'] = ((df['is_high_priority'] == 1) & 
                            (df['requires_road_closure_bool'] == 1)).astype(int)
print(f"✅ critical_situation: {df['critical_situation'].sum()} critical situations")

# ============================================================================
# 7. RISK SCORES
# ============================================================================

print("\n" + "=" * 80)
print("ENGINEERING: RISK SCORES")
print("=" * 80)

# Corridor risk score (normalized average impact by corridor)
corridor_avg_impact = df.groupby('corridor_encoded')['impact_score'].mean()
corridor_avg_impact = (corridor_avg_impact - corridor_avg_impact.min()) / (corridor_avg_impact.max() - corridor_avg_impact.min())
df['corridor_risk_score'] = df['corridor_encoded'].map(corridor_avg_impact).fillna(0.5)

# Zone risk score
zone_avg_impact = df.groupby('zone')['impact_score'].mean()
zone_avg_impact = (zone_avg_impact - zone_avg_impact.min()) / (zone_avg_impact.max() - zone_avg_impact.min())
df['zone_risk_score'] = df['zone'].map(zone_avg_impact).fillna(0.5)

# Hour risk score
hour_avg_impact = df.groupby('hour')['impact_score'].mean()
hour_avg_impact = (hour_avg_impact - hour_avg_impact.min()) / (hour_avg_impact.max() - hour_avg_impact.min())
df['hour_risk_score'] = df['hour'].map(hour_avg_impact).fillna(0.5)

print("\n✅ Risk Scores Created:")
print(f"   - corridor_risk_score (0-1)")
print(f"   - zone_risk_score (0-1)")
print(f"   - hour_risk_score (0-1)")

# ============================================================================
# 8. FEATURE SELECTION FOR MODELING
# ============================================================================

print("\n" + "=" * 80)
print("SELECTING FEATURES FOR ML MODEL")
print("=" * 80)

feature_list = [
    'hour',                          # Time: hour of day
    'day_of_week',                   # Time: day of week
    'month',                         # Time: month
    'is_weekend',                    # Time: is weekend
    'is_peak_hour',                  # Time: is peak hour
    'time_period',                   # Time: morning/afternoon/evening
    'event_type',                    # Event: type (encoded)
    'event_cause',                   # Event: cause (encoded)
    'corridor_encoded',              # Location: corridor
    'zone',                          # Location: zone
    'is_high_priority',              # Severity: high priority
    'requires_road_closure_bool',    # Severity: road closure
    'is_planned',                    # Severity: is planned
    'is_major_event',                # Interaction: is major event
    'is_major_corridor',             # Interaction: is major corridor
    'critical_situation',            # Interaction: critical situation
    'corridor_risk_score',           # Risk: corridor
    'zone_risk_score',               # Risk: zone
    'hour_risk_score'                # Risk: hour
]

X = df[feature_list].copy()
y = df['impact_score'].copy()

print(f"\n✅ Total Features: {len(feature_list)}")
print(f"   Features: {feature_list}")

# ============================================================================
# 9. HANDLE MISSING VALUES
# ============================================================================

print("\n" + "=" * 80)
print("HANDLING MISSING VALUES")
print("=" * 80)

print(f"\nMissing values before:")
print(X.isnull().sum()[X.isnull().sum() > 0])

# Fill missing with median
X = X.fillna(X.median())

print(f"\nMissing values after: {X.isnull().sum().sum()}")

# ============================================================================
# 10. VALIDATION & STATISTICS
# ============================================================================

print("\n" + "=" * 80)
print("FEATURE STATISTICS")
print("=" * 80)

print("\nFeature Summary:")
print(X.describe().round(2))

print("\nTarget (Impact Score) Summary:")
print(f"Mean: {y.mean():.2f}")
print(f"Std: {y.std():.2f}")
print(f"Min: {y.min():.2f}")
print(f"Max: {y.max():.2f}")

# ============================================================================
# 11. SAVE OUTPUTS
# ============================================================================

print("\n" + "=" * 80)
print("SAVING OUTPUTS")
print("=" * 80)

output_dir = '../data/'

# Save features with target
output_df = X.copy()
output_df['impact_score'] = y
output_df.to_csv(f'{output_dir}features_for_modeling.csv', index=False)
print(f"✅ Saved: features_for_modeling.csv ({output_df.shape})")

# Save encoders
with open(f'{output_dir}label_encoders.pkl', 'wb') as f:
    pickle.dump({
        'event_type': le_event,
        'event_cause': le_cause,
        'zone': le_zone
    }, f)
print(f"✅ Saved: label_encoders.pkl")

# ============================================================================
# SUMMARY
# ============================================================================

print("\n" + "=" * 80)
print("PHASE 2 COMPLETE ✅")
print("=" * 80)

print(f"""
📊 Features Created:

TIME (6):
  - hour, day_of_week, month, is_weekend, is_peak_hour, time_period

EVENT (2):
  - event_type, event_cause

LOCATION (2):
  - corridor_encoded, zone

SEVERITY (3):
  - is_high_priority, requires_road_closure_bool, is_planned

INTERACTION (3):
  - is_major_event, is_major_corridor, critical_situation

RISK (3):
  - corridor_risk_score, zone_risk_score, hour_risk_score

═══════════════════════════════════════
Total: 19 Features
Target: impact_score (1-10)
Samples: {len(X):,}

Ready for Phase 3: Model Training ✅
""")

print("=" * 80)
