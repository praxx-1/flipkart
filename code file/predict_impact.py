"""
PREDICT: Use trained model to forecast impact score for new events
"""

import pandas as pd
import numpy as np
import pickle

# ============================================================================
# LOAD SAVED MODEL & ARTIFACTS
# ============================================================================

output_dir = '../data file/'

# Load model
with open(f'{output_dir}random_forest_model.pkl', 'rb') as f:
    model = pickle.load(f)
print("✅ Loaded model")

# Load feature columns (to ensure correct order)
with open(f'{output_dir}feature_columns.pkl', 'rb') as f:
    feature_columns = pickle.load(f)
print(f"✅ Loaded {len(feature_columns)} feature columns")

# ============================================================================
# EXAMPLE: PREDICT FOR A NEW EVENT
# ============================================================================

print("\n" + "=" * 80)
print("EXAMPLE: PREDICT IMPACT FOR NEW EVENT")
print("=" * 80)

# Example: Cricket match at M Chinnaswamy Stadium
new_event = {
    'hour': 14,                          # 2 PM
    'day_of_week': 4,                   # Friday
    'month': 7,                          # July
    'is_weekend': 0,                     # No (Friday is workday)
    'is_peak_hour': 1,                  # Yes (2-6 PM is peak)
    'time_period': 2,                   # Afternoon
    'event_type': 1,                     # Public event
    'event_cause': 0,                    # (encoded)
    'corridor_encoded': 8,               # CBD area
    'zone': 4,                          # Central zone
    'is_high_priority': 1,              # Yes
    'requires_road_closure_bool': 1,    # Yes
    'is_planned': 1,                    # Yes (planned event)
    'is_major_event': 1,                # Yes (cricket match)
    'is_major_corridor': 1,             # Yes (CBD)
    'critical_situation': 1,            # Yes
    'corridor_risk_score': 0.85,        # High risk corridor
    'zone_risk_score': 0.80,            # Central zone risk
    'hour_risk_score': 0.75             # Peak hour risk
}

# Convert to DataFrame with correct column order
new_event_df = pd.DataFrame([new_event])[feature_columns]

print("\n📋 New Event Features:")
print(new_event_df.to_string(index=False))

# Make prediction
predicted_score = model.predict(new_event_df)[0]
print(f"\n🎯 Predicted Impact Score: {predicted_score:.2f}/10")

# Interpretation
if predicted_score <= 3:
    impact = "🟢 LOW"
elif predicted_score <= 6:
    impact = "🟡 MODERATE"
else:
    impact = "🔴 SEVERE"

print(f"   Interpretation: {impact}")

# ============================================================================
# BATCH PREDICTION EXAMPLE
# ============================================================================

print("\n" + "=" * 80)
print("BATCH PREDICTION: 5 DIFFERENT EVENTS")
print("=" * 80)

# Load test data to show predictions
test_data = pd.read_csv(f'{output_dir}features_for_modeling.csv')
test_features = test_data.drop('impact_score', axis=1)
test_actual = test_data['impact_score']

# Predict on first 5
sample_idx = [0, 1, 2, 3, 4]
predictions = model.predict(test_features.iloc[sample_idx])

results = pd.DataFrame({
    'Event': [f'Event {i+1}' for i in sample_idx],
    'Actual Score': test_actual.iloc[sample_idx].values,
    'Predicted Score': predictions,
    'Error': np.abs(test_actual.iloc[sample_idx].values - predictions)
})

print("\n" + results.round(2).to_string(index=False))
print(f"\nAverage Error: {results['Error'].mean():.4f} (±{results['Error'].mean():.2f} on 1-10 scale)")

# ============================================================================
# HOW TO USE IN YOUR CODE
# ============================================================================

print("\n" + "=" * 80)
print("HOW TO USE IN YOUR CODE")
print("=" * 80)

code_example = """
# 1. Load model once
import pickle
with open('random_forest_model.pkl', 'rb') as f:
    model = pickle.load(f)

# 2. Prepare features for new event
import pandas as pd
new_event = pd.DataFrame([{
    'hour': 14,
    'day_of_week': 4,
    ... (all 19 features)
}])

# 3. Make prediction
score = model.predict(new_event)[0]  # Returns float like 8.7

# 4. Use the score
if score > 7:
    deploy_officers = 50
    barricade_locations = ['Queens Statue', 'Sankey Rd']
else:
    deploy_officers = 15
    barricade_locations = []
"""

print(code_example)

print("\n" + "=" * 80)
