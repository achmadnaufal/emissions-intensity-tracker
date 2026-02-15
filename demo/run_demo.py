"""
Emissions Intensity Tracker — live demo
Run: python demo/run_demo.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd
from src.main import EmissionsIntensityTracker

DATA = os.path.join(os.path.dirname(__file__), "../data/extended_emissions_data.csv")

print("=" * 60)
print("  Emissions Intensity Tracker — Demo")
print("=" * 60)

tracker = EmissionsIntensityTracker()
df = tracker.load_data(DATA)
print(f"\n✓ Loaded {len(df)} records from {os.path.basename(DATA)}")
print(f"  Operations: {df['operation_id'].nunique()} | Years: {sorted(df['year'].unique())}")

# Calculate emission intensity
df_processed = tracker.calculate_emission_intensity(
    df,
    scope_cols=["scope1_tco2e", "scope2_tco2e", "scope3_tco2e"],
    production_col="production_tonnes"
)
print(f"\n✓ Calculated Scope 1+2+3 emission intensities")
print(f"  Avg intensity: {df_processed['intensity_tco2e_per_unit'].mean():.4f} tCO2e/tonne")
print(f"  Best performer: {df_processed.loc[df_processed['intensity_tco2e_per_unit'].idxmin(), 'operation_id']} "
      f"({df_processed['intensity_tco2e_per_unit'].min():.4f} tCO2e/t)")

# Trend analysis
trends = tracker.calculate_trend(df_processed, group_by="operation_id", time_col="year")
print(f"\n✓ Year-over-year trend analysis ({len(trends)} operations):")
print(f"  {'Operation':<25} {'YoY Change':>12}  {'Avg Annual':>12}  {'Latest (tCO2e)':>15}")
print(f"  {'-'*65}")
for op, t in list(trends.items())[:5]:
    arrow = "↓" if t['total_yoy_change_pct'] < 0 else "↑"
    print(f"  {op:<25} {arrow}{abs(t['total_yoy_change_pct']):>10.1f}%  {t['avg_annual_change_pct']:>11.2f}%  {t['latest_emissions']:>15,.1f}")

# Paris pathway
pathway = tracker.calculate_paris_aligned_pathway(50000, scenario="1.5c")
print(f"\n✓ Paris 1.5°C Pathway (from 50,000 tCO2e baseline):")
print(f"  Annual reduction rate : {pathway['annual_rate_pct']}% CAGR (SBTi ACA)")
print(f"  2030 budget           : {pathway['budget_2030']:,.0f} tCO2e")
print(f"  2050 budget           : {pathway['annual_pathway'][2050]:,.0f} tCO2e")
print(f"  Total reduction       : {pathway['total_reduction_pct']}% vs baseline")

# Benchmark
bench = tracker.benchmark_against_sector(0.038, sector="coal_mining")
print(f"\n✓ Sector benchmark (coal_mining):")
print(f"  Measured intensity    : {bench['measured_intensity']} tCO2e/tonne")
print(f"  Sector average        : {bench['sector_average']} tCO2e/tonne")
print(f"  Deviation from avg    : {bench['deviation_from_avg_pct']:+.1f}%")
print(f"  Performance band      : {bench['performance_band'].upper()}")
print(f"  Reduction to avg      : {bench['reduction_needed_to_avg']:.4f} tCO2e/t")

# Reduction target
target = tracker.calculate_carbon_reduction_target(0.038, target_reduction_pct=25, years_to_target=5)
print(f"\n✓ Carbon reduction roadmap (25% in 5 years):")
print(f"  Current intensity     : {target['current_intensity']} tCO2e/unit")
print(f"  Target intensity      : {target['target_intensity']} tCO2e/unit")
for i, t in enumerate(target["annual_targets"], 1):
    print(f"  Year {i}               : {t:.4f} tCO2e/unit")

print("\n" + "=" * 60)
print("  ✅ Demo complete")
print("=" * 60)
