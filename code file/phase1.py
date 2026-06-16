import pandas as pd
import numpy as np

print("=" * 80)
print("PHASE 1: Y VARIABLE ENGINEERING")
print("=" * 80)

# Load raw Astram data
df = pd.read_csv('../data file/Astram event data_anonymized - Astram event data_anonymizedb40ac87.csv')

# Calculate duration if not present
df['start_datetime'] = pd.to_datetime(df['start_datetime'], errors='coerce')
df['end_datetime'] = pd.to_datetime(df['end_datetime'], errors='coerce')
df['duration_minutes'] = ((df['end_datetime'] - df['start_datetime']).dt.total_seconds() / 60).fillna(60)
df['duration_hours'] = df['duration_minutes'] / 60

# Re-use impact score logic from demo_cases_final.py
def calculate_impact_score(row):
    score = 5.0
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
    
    priority = str(row.get('priority', 'Low')).lower()
    if 'high' in priority:
        score += 1.5
    elif 'medium' in priority:
        score += 0.5
    else:
        score -= 0.5
    
    closure = str(row.get('requires_road_closure', 'No')).upper()
    if closure == 'YES':
        score += 2.0
    
    try:
        duration = float(row.get('duration_hours', 1))
        score += min(duration / 15, 1.0)
    except:
        pass
    
    return max(1, min(10, score))

df['impact_score'] = df.apply(calculate_impact_score, axis=1)

# Save the resulting dataset
df.to_csv('../data file/astram_with_impact_score.csv', index=False)
print("Saved astram_with_impact_score.csv successfully.")
