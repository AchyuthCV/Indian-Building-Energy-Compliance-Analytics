import sqlite3
import pandas as pd

# 1. Connect to SQLite Database
conn = sqlite3.connect("building_energy.db")

# Load full dataset with ML predictions and flags
df_fact = pd.read_sql_query("SELECT * FROM fact_building_energy", conn)

# 2. Generate Dimension Table: Dim_Location
dim_location = df_fact[['city', 'state', 'climate_zone']].drop_duplicates().reset_index(drop=True)
dim_location['location_id'] = [f"LOC-{101 + i}" for i in range(len(dim_location))]

# Map location_id back to fact table
df_fact = df_fact.merge(dim_location, on=['city', 'state', 'climate_zone'], how='left')

# 3. Save Tables for Power BI
df_fact.to_csv("fact_building_energy_pbi.csv", index=False)
dim_location.to_csv("dim_location_pbi.csv", index=False)

conn.close()

print("✅ Power BI CSVs successfully generated:")
print("   - fact_building_energy_pbi.csv")
print("   - dim_location_pbi.csv")