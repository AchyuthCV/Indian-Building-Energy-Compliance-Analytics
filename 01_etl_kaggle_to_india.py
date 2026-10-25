import numpy as np
import pandas as pd

print("⏳ Ingesting Kaggle train.csv...")
df_kaggle = pd.read_csv("train.csv")

# Filter for Commercial / Non-Residential Facility Types
commercial_keywords = [
    "Office",
    "Commercial",
    "Data_Center",
    "Health",
    "Retail",
    "Education",
    "Lodging",
]
df = df_kaggle[
    df_kaggle["facility_type"].str.contains(
        "|".join(commercial_keywords), case=False, na=False
    )
].copy()

# 1. Convert Site EUI (kBtu/sqft) to Indian EPI (kWh/m2/year)
# 1 kBtu/sq ft = 3.1512 kWh/sq m
df["actual_epi_kwh_sqm"] = (df["site_eui"] * 3.1512).round(2)

# Convert Floor Area from sq ft to sq m
df["built_up_area_sqm"] = (df["floor_area"] * 0.092903).round(2)

# 2. Map Kaggle Facility Types to Indian Commercial Categories
facility_mapping = {
    "Office_Uncategorized": "Commercial Office",
    "Commercial_Other": "Commercial Office",
    "Commercial_Unknown": "Commercial Office",
    "Data_Center": "IT Park",
    "Health_Care_Inpatient": "Hospital",
    "Health_Care_Outpatient_Uncategorized": "Hospital",
    "Retail_Uncategorized": "Shopping Mall",
    "Retail_Enclosed_Mall": "Shopping Mall",
    "Retail_Strip_Shopping_Center": "Shopping Mall",
    "Lodging_Hotel": "BPO",
}
df["property_type"] = (
    df["facility_type"].map(facility_mapping).fillna("Commercial Office")
)

# 3. Map Kaggle Anonymized States to Indian Cities & Climate Zones
state_mapping = {
    "State_1": ("Mumbai", "Maharashtra", "Warm & Humid"),
    "State_2": ("Bengaluru", "Karnataka", "Moderate"),
    "State_4": ("Delhi-NCR", "Delhi", "Composite"),
    "State_6": ("Hyderabad", "Telangana", "Hot & Dry"),
    "State_8": ("Chennai", "Tamil Nadu", "Warm & Humid"),
    "State_10": ("Kolkata", "West Bengal", "Warm & Humid"),
    "State_11": ("Ahmedabad", "Gujarat", "Hot & Dry"),
}

default_loc = ("Mumbai", "Maharashtra", "Warm & Humid")
df["city"] = df["State_Factor"].map(
    lambda x: state_mapping.get(x, default_loc)[0]
)
df["state"] = df["State_Factor"].map(
    lambda x: state_mapping.get(x, default_loc)[1]
)
df["climate_zone"] = df["State_Factor"].map(
    lambda x: state_mapping.get(x, default_loc)[2]
)

# 4. Synthesize Operational Features aligned with Indian Standards
np.random.seed(42)
n = len(df)

df["building_id"] = [f"IND-BLD-{10000+i}" for i in range(n)]
df["building_name"] = [
    f"{df['city'].iloc[i]} Commercial Complex {i+1}" for i in range(n)
]
df["building_age_years"] = np.random.randint(2, 30, size=n)
df["ac_area_pct"] = np.random.uniform(40, 95, size=n).round(1)

# Operating hours per week based on property type
op_hrs = []
for p in df["property_type"]:
  if p == "BPO" or p == "Hospital":
    op_hrs.append(np.random.randint(140, 168))
  elif p == "IT Park":
    op_hrs.append(np.random.randint(90, 140))
  else:
    op_hrs.append(np.random.randint(50, 80))
df["operating_hours_per_week"] = op_hrs

# 5. Connected Load & Solar Integration
df["connected_load_kw"] = (
    df["built_up_area_sqm"] * np.random.uniform(0.07, 0.12, size=n)
).round(2)
has_solar = np.random.choice([0, 1], size=n, p=[0.6, 0.4])
df["rooftop_solar_kw"] = (
    has_solar
    * (df["built_up_area_sqm"] * np.random.uniform(0.005, 0.02, size=n))
).round(2)
df["annual_solar_kwh"] = (df["rooftop_solar_kw"] * 1450).round(2)
df["annual_grid_kwh"] = (df["actual_epi_kwh_sqm"] * df["built_up_area_sqm"]).round(
    2
)

# 6. Apply Official BEE Benchmark Limits
bee_1star = []
bee_5star = []
for i in range(n):
  p = df["property_type"].iloc[i]
  c = df["climate_zone"].iloc[i]

  if p == "Commercial Office":
    limit, target = (190, 110) if c in ["Warm & Humid", "Hot & Dry"] else (160, 95)
  elif p == "BPO":
    limit, target = (340, 210)
  elif p == "Shopping Mall":
    limit, target = (380, 240)
  elif p == "Hospital":
    limit, target = (300, 180)
  else:  # IT Park
    limit, target = (250, 150)

  bee_1star.append(limit)
  bee_5star.append(target)

df["bee_1star_limit_epi"] = bee_1star
df["bee_5star_target_epi"] = bee_5star

# 7. Penalty Calculations
df["is_non_compliant"] = df["actual_epi_kwh_sqm"] > df["bee_1star_limit_epi"]
df["excess_kwh_per_sqm"] = (
    df["actual_epi_kwh_sqm"] - df["bee_1star_limit_epi"]
).clip(lower=0)
df["total_excess_kwh"] = (
    df["excess_kwh_per_sqm"] * df["built_up_area_sqm"]
).round(2)
df["penalty_exposure_inr"] = (df["total_excess_kwh"] * 3.5).round(2)

# Export clean standardized dataset
export_cols = [
    "building_id",
    "building_name",
    "city",
    "state",
    "climate_zone",
    "property_type",
    "built_up_area_sqm",
    "building_age_years",
    "ac_area_pct",
    "operating_hours_per_week",
    "connected_load_kw",
    "rooftop_solar_kw",
    "annual_solar_kwh",
    "annual_grid_kwh",
    "actual_epi_kwh_sqm",
    "bee_1star_limit_epi",
    "bee_5star_target_epi",
    "is_non_compliant",
    "excess_kwh_per_sqm",
    "total_excess_kwh",
    "penalty_exposure_inr",
]

df_clean = df[export_cols].dropna().reset_index(drop=True)
df_clean.to_csv("india_building_energy_clean.csv", index=False)

print(
    f"✅ Successfully converted Kaggle data to 'india_building_energy_clean.csv'!"
)
print(f"📊 Total Buildings Processed: {len(df_clean)}")
print(f"⚠️ Non-Compliant Count: {df_clean['is_non_compliant'].sum()}")
print(
    f"💰 Total Regulatory Exposure: ₹{round(df_clean['penalty_exposure_inr'].sum() / 1e7, 2)} Crores"
)