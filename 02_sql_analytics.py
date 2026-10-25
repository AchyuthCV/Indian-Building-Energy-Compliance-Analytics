import sqlite3
import pandas as pd

# 1. Load Clean Dataset and Connect to SQLite
print("⏳ Loading 'india_building_energy_clean.csv' into SQLite database...")
df = pd.read_csv("india_building_energy_clean.csv")

conn = sqlite3.connect("building_energy.db")

# Write to SQLite Table
df.to_sql("fact_building_energy", conn, if_exists="replace", index=False)
print("✅ Database 'building_energy.db' created with table 'fact_building_energy'.\n")

# Query 1: City & Climate Zone Breakdown
query_city_summary = """
SELECT 
    city,
    climate_zone,
    COUNT(building_id) AS total_buildings,
    SUM(is_non_compliant) AS non_compliant_count,
    ROUND(CAST(SUM(is_non_compliant) AS FLOAT) / COUNT(building_id) * 100, 1) AS non_compliant_pct,
    ROUND(AVG(actual_epi_kwh_sqm), 2) AS avg_actual_epi,
    ROUND(AVG(bee_1star_limit_epi), 2) AS avg_1star_limit,
    ROUND(SUM(penalty_exposure_inr) / 10000000.0, 2) AS total_penalty_crores_inr
FROM fact_building_energy
GROUP BY city, climate_zone
ORDER BY total_penalty_crores_inr DESC;
"""

# Query 2: Property Type Non-Compliance Exposure
query_property_summary = """
SELECT 
    property_type,
    COUNT(building_id) AS total_buildings,
    SUM(is_non_compliant) AS non_compliant_count,
    ROUND(AVG(actual_epi_kwh_sqm), 2) AS avg_actual_epi,
    ROUND(SUM(penalty_exposure_inr) / 10000000.0, 2) AS total_penalty_crores_inr
FROM fact_building_energy
GROUP BY property_type
ORDER BY total_penalty_crores_inr DESC;
"""

# Execute and Print Summaries
print("--- 🌆 City & Climate Zone Non-Compliance Summary ---")
city_summary = pd.read_sql_query(query_city_summary, conn)
print(city_summary.to_string(index=False))

print("\n--- 🏢 Property Type Exposure Summary ---")
prop_summary = pd.read_sql_query(query_property_summary, conn)
print(prop_summary.to_string(index=False))

conn.close()