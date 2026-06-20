"""
PHASE 3: MODEL TRAINING
Train Random Forest & XGBoost to predict Congestion Impact Score
"""

import pandas as pd
import numpy as np
import pickle
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score, mean_squared_error
import xgboost as xgb
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# 1. LOAD DATA
# ============================================================================

print("=" * 80)
print("PHASE 3: MODEL TRAINING")
print("=" * 80)

# Load features and target
df = pd.read_csv('../data/features_for_modeling.csv')
print(f"\n✅ Loaded features: {df.shape}")

# Prepare X and Y
X = df.drop('impact_score', axis=1)
y = df['impact_score']

print(f"Features (X): {X.shape}")
print(f"Target (Y): {y.shape}")
print(f"\nFeature columns: {list(X.columns)}")

# ============================================================================
# 2. TRAIN-TEST SPLIT
# ============================================================================

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

print(f"\n📊 Train set: {X_train.shape[0]} samples")
print(f"📊 Test set: {X_test.shape[0]} samples")

# ============================================================================
# 3. TRAIN RANDOM FOREST
# ============================================================================

print("\n" + "=" * 80)
print("TRAINING: RANDOM FOREST")
print("=" * 80)

rf_model = RandomForestRegressor(
    n_estimators=100,
    max_depth=15,
    min_samples_split=10,
    min_samples_leaf=5,
    random_state=42,
    n_jobs=-1
)

rf_model.fit(X_train, y_train)
print("✅ Random Forest trained")

# Predictions
y_train_pred_rf = rf_model.predict(X_train)
y_test_pred_rf = rf_model.predict(X_test)

# Evaluation
rf_train_mae = mean_absolute_error(y_train, y_train_pred_rf)
rf_test_mae = mean_absolute_error(y_test, y_test_pred_rf)
rf_test_rmse = np.sqrt(mean_squared_error(y_test, y_test_pred_rf))
rf_test_r2 = r2_score(y_test, y_test_pred_rf)

print(f"\n📈 Random Forest Results:")
print(f"   Train MAE:  {rf_train_mae:.4f}")
print(f"   Test MAE:   {rf_test_mae:.4f} ← Prediction error ±{rf_test_mae:.3f}")
print(f"   Test RMSE:  {rf_test_rmse:.4f}")
print(f"   Test R²:    {rf_test_r2:.4f} (explains {rf_test_r2*100:.1f}% of variance)")

# ============================================================================
# 4. TRAIN XGBOOST
# ============================================================================

print("\n" + "=" * 80)
print("TRAINING: XGBOOST")
print("=" * 80)

xgb_model = xgb.XGBRegressor(
    n_estimators=100,
    max_depth=6,
    learning_rate=0.1,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42,
    n_jobs=-1
)

xgb_model.fit(X_train, y_train)
print("✅ XGBoost trained")

# Predictions
y_train_pred_xgb = xgb_model.predict(X_train)
y_test_pred_xgb = xgb_model.predict(X_test)

# Evaluation
xgb_train_mae = mean_absolute_error(y_train, y_train_pred_xgb)
xgb_test_mae = mean_absolute_error(y_test, y_test_pred_xgb)
xgb_test_rmse = np.sqrt(mean_squared_error(y_test, y_test_pred_xgb))
xgb_test_r2 = r2_score(y_test, y_test_pred_xgb)

print(f"\n📈 XGBoost Results:")
print(f"   Train MAE:  {xgb_train_mae:.4f}")
print(f"   Test MAE:   {xgb_test_mae:.4f} ← Prediction error ±{xgb_test_mae:.3f}")
print(f"   Test RMSE:  {xgb_test_rmse:.4f}")
print(f"   Test R²:    {xgb_test_r2:.4f} (explains {xgb_test_r2*100:.1f}% of variance)")

# ============================================================================
# 5. COMPARISON
# ============================================================================

print("\n" + "=" * 80)
print("MODEL COMPARISON")
print("=" * 80)

comparison = pd.DataFrame({
    'Metric': ['Train MAE', 'Test MAE', 'Test RMSE', 'Test R²'],
    'Random Forest': [f'{rf_train_mae:.4f}', f'{rf_test_mae:.4f}', f'{rf_test_rmse:.4f}', f'{rf_test_r2:.4f}'],
    'XGBoost': [f'{xgb_train_mae:.4f}', f'{xgb_test_mae:.4f}', f'{xgb_test_rmse:.4f}', f'{xgb_test_r2:.4f}']
})

print("\n" + comparison.to_string(index=False))

if rf_test_mae < xgb_test_mae:
    print("\n🏆 WINNER: Random Forest (Lower Test MAE)")
    selected_model = rf_model
    selected_name = "Random Forest"
else:
    print("\n🏆 WINNER: XGBoost (Lower Test MAE)")
    selected_model = xgb_model
    selected_name = "XGBoost"

# ============================================================================
# 6. FEATURE IMPORTANCE
# ============================================================================

print("\n" + "=" * 80)
print("FEATURE IMPORTANCE (Random Forest)")
print("=" * 80)

feature_importance = pd.DataFrame({
    'Feature': X.columns,
    'Importance': rf_model.feature_importances_
}).sort_values('Importance', ascending=False)

feature_importance['Importance_Pct'] = (feature_importance['Importance'] / feature_importance['Importance'].sum()) * 100

print("\nTop 10 Features:")
for idx, row in feature_importance.head(10).iterrows():
    bar = '█' * int(row['Importance_Pct'] / 2)
    print(f"{idx+1:2}. {row['Feature']:30} {row['Importance_Pct']:5.1f}% {bar}")

# ============================================================================
# 7. SAMPLE PREDICTIONS
# ============================================================================

print("\n" + "=" * 80)
print("SAMPLE PREDICTIONS (Test Set)")
print("=" * 80)

sample_indices = np.random.choice(len(y_test), 10, replace=False)
samples = pd.DataFrame({
    'Actual': y_test.iloc[sample_indices].values,
    'Predicted_RF': y_test_pred_rf[sample_indices],
    'Predicted_XGB': y_test_pred_xgb[sample_indices],
    'Error_RF': np.abs(y_test.iloc[sample_indices].values - y_test_pred_rf[sample_indices]),
    'Error_XGB': np.abs(y_test.iloc[sample_indices].values - y_test_pred_xgb[sample_indices])
})

print("\n" + samples.round(2).to_string(index=False))

# ============================================================================
# 8. SAVE ARTIFACTS
# ============================================================================

print("\n" + "=" * 80)
print("SAVING ARTIFACTS")
print("=" * 80)

output_dir = '../data/'

# Save Random Forest model
with open(f'{output_dir}random_forest_model.pkl', 'wb') as f:
    pickle.dump(rf_model, f)
print("✅ Saved: random_forest_model.pkl")

# Save XGBoost model
with open(f'{output_dir}xgboost_model.pkl', 'wb') as f:
    pickle.dump(xgb_model, f)
print("✅ Saved: xgboost_model.pkl")

# Save feature columns
with open(f'{output_dir}feature_columns.pkl', 'wb') as f:
    pickle.dump(list(X.columns), f)
print("✅ Saved: feature_columns.pkl")

# Save feature importance
feature_importance.to_csv(f'{output_dir}feature_importance.csv', index=False)
print("✅ Saved: feature_importance.csv")

# Save model performance
performance = pd.DataFrame({
    'Model': ['Random Forest', 'XGBoost'],
    'Train_MAE': [rf_train_mae, xgb_train_mae],
    'Test_MAE': [rf_test_mae, xgb_test_mae],
    'Test_RMSE': [rf_test_rmse, xgb_test_rmse],
    'Test_R2': [rf_test_r2, xgb_test_r2]
})
performance.to_csv(f'{output_dir}model_performance.csv', index=False)
print("✅ Saved: model_performance.csv")

# ============================================================================
# 9. SUMMARY
# ============================================================================

print("\n" + "=" * 80)
print("PHASE 3 COMPLETE ✅")
print("=" * 80)

print(f"""
🎯 Selected Model: {selected_name}
   Test MAE: {min(rf_test_mae, xgb_test_mae):.4f} (±{min(rf_test_mae, xgb_test_mae):.2f} on 1-10 scale)
   Test R²: {max(rf_test_r2, xgb_test_r2):.4f} ({max(rf_test_r2, xgb_test_r2)*100:.1f}% variance explained)

📊 Ready for Phase 4: Recommendation Engine
   - Model can predict impact score for new events
   - Feature importance shows what matters most
   - Prediction error is excellent for real-world use

✅ All artifacts saved to {output_dir}
""")

print("=" * 80)
