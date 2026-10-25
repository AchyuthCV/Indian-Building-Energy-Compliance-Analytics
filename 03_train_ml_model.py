import pandas as pd
import numpy as np
import sqlite3
from sklearn.model_selection import train_test_split
from sklearn.linear_model import Ridge
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
import xgboost as xgb
import shap

# 1. Load Data from SQLite
conn = sqlite3.connect("building_energy.db")
df = pd.read_sql_query("SELECT * FROM fact_building_energy", conn)
conn.close()

# Prepare Features (X) and Log Target (y)
feature_cols = [
    'city', 'climate_zone', 'property_type', 'built_up_area_sqm',
    'building_age_years', 'ac_area_pct', 'operating_hours_per_week',
    'connected_load_kw', 'rooftop_solar_kw'
]

X = df[feature_cols]
y_log = np.log1p(df['actual_epi_kwh_sqm'])

cat_features = ['city', 'climate_zone', 'property_type']
num_features = [c for c in feature_cols if c not in cat_features]

# Preprocessor Pipeline
preprocessor = ColumnTransformer(
    transformers=[
        ('cat', OneHotEncoder(drop='first', sparse_output=False), cat_features),
        ('num', 'passthrough', num_features)
    ]
)

X_train, X_test, y_train, y_test = train_test_split(X, y_log, test_size=0.2, random_state=42)

# 2. Train Ridge Baseline
ridge_pipe = Pipeline([
    ('pre', preprocessor),
    ('reg', Ridge(alpha=1.0))
])
ridge_pipe.fit(X_train, y_train)
ridge_preds = np.expm1(ridge_pipe.predict(X_test))
y_test_actual = np.expm1(y_test)

ridge_r2 = r2_score(y_test_actual, ridge_preds)
ridge_rmse = np.sqrt(mean_squared_error(y_test_actual, ridge_preds))

# 3. Train XGBoost Model
X_train_trans = preprocessor.fit_transform(X_train)
X_test_trans = preprocessor.transform(X_test)

xgb_model = xgb.XGBRegressor(n_estimators=150, learning_rate=0.08, max_depth=6, random_state=42)
xgb_model.fit(X_train_trans, y_train)
xgb_preds = np.expm1(xgb_model.predict(X_test_trans))

xgb_r2 = r2_score(y_test_actual, xgb_preds)
xgb_rmse = np.sqrt(mean_squared_error(y_test_actual, xgb_preds))

print("--- 🤖 Model Evaluation Results ---")
print(f"Ridge Regression -> R²: {ridge_r2:.4f} | RMSE: {ridge_rmse:.2f} kWh/sqm")
print(f"XGBoost Regressor -> R²: {xgb_r2:.4f} | RMSE: {xgb_rmse:.2f} kWh/sqm")

# 4. Generate Predictions & Outlier Residual Risk Flags
X_full_trans = preprocessor.transform(X)
df['predicted_epi_kwh_sqm'] = np.expm1(xgb_model.predict(X_full_trans)).round(2)
df['epi_residual'] = (df['actual_epi_kwh_sqm'] - df['predicted_epi_kwh_sqm']).round(2)

# Flag Outliers: Buildings where actual exceeds predicted by >20%
df['is_outlier_risk'] = df['actual_epi_kwh_sqm'] > (df['predicted_epi_kwh_sqm'] * 1.20)

# Save updated table back to SQLite
conn = sqlite3.connect("building_energy.db")
df.to_sql("fact_building_energy", conn, if_exists="replace", index=False)
conn.close()
print("\n✅ Predictions and Outlier Flags saved to 'building_energy.db'.")

# 5. Compute SHAP Values
print("⏳ Computing SHAP Feature Importance...")
explainer = shap.TreeExplainer(xgb_model)
shap_values = explainer.shap_values(X_full_trans)

# Get transformed feature names
cat_encoder = preprocessor.named_transformers_['cat']
encoded_cat_names = cat_encoder.get_feature_names_out(cat_features).tolist()
all_feature_names = encoded_cat_names + num_features

mean_abs_shap = np.abs(shap_values).mean(axis=0)
shap_df = pd.DataFrame({
    'feature': all_feature_names,
    'mean_abs_shap': mean_abs_shap
}).sort_values(by='mean_abs_shap', ascending=False)

print("\n--- 💡 Top SHAP Feature Drivers ---")
print(shap_df.head(8).to_string(index=False))