# Emissions Intensity Tracker

Scope 1, 2, and 3 greenhouse gas emissions intensity tracking for coal operations

## Features
- Data ingestion from CSV/Excel input files
- Automated analysis and KPI calculation
- Summary statistics and trend reporting
- Sample data generator for testing and development

## Installation

```bash
pip install -r requirements.txt
```

## Quick Start

```python
from src.main import EmissionsIntensityTracker

analyzer = EmissionsIntensityTracker()
df = analyzer.load_data("data/sample.csv")
result = analyzer.analyze(df)
print(result)
```

## Data Format

Expected CSV columns: `operation_id, year, scope1_tco2e, scope2_tco2e, scope3_tco2e, production_tonnes, intensity_tco2e_t`

## Project Structure

```
emissions-intensity-tracker/
├── src/
│   ├── main.py          # Core analysis logic
│   └── data_generator.py # Sample data generator
├── data/                # Data directory (gitignored for real data)
├── examples/            # Usage examples
├── requirements.txt
└── README.md
```

## License

MIT License — free to use, modify, and distribute.

## New: Environmental Restoration Calculator

Convert emissions reductions to biodiversity impact metrics for post-mining land restoration:

```python
from src.restoration_calculator import RestorationCalculator

calc = RestorationCalculator()

# Calculate habitat restoration from carbon reduction
habitat = calc.calculate_habitat_restoration(
    emissions_reduction_tco2e=500,
    habitat_type="native_forest"  # or "wetland", "grassland", "agroforestry"
)
print(f"Restorable habitat: {habitat['habitat_area_hectares']} hectares")

# Project species recovery
species = calc.calculate_species_recovery(
    habitat_area_hectares=75,
    baseline_species_count=0,
    years=10
)
print(f"Species recovered: {species['projected_species_final']}")

# Tree planting impact
trees = calc.calculate_tree_planting_impact(
    trees_planted=5000,
    tree_survival_rate_pct=85,  # Conservative estimate
    years=30
)
print(f"Carbon: {trees['carbon_sequestered_tco2e']} tCO2e")
print(f"Habitat equivalent: {trees['habitat_hectares_equivalent']} hectares")
```

### Habitat Restoration Types

- **Native Forest**: 0.15 ha/tCO2e (baseline conversion)
- **Wetland**: 0.18 ha/tCO2e (higher biodiversity density)
- **Grassland**: 0.12 ha/tCO2e (lower management intensity)
- **Agroforestry**: 0.20 ha/tCO2e (productive + biodiversity combined)

### Species Recovery Timeline

- **Year 0-2**: Pioneer species (0-15% capacity)
- **Year 2-5**: Early succession (15-50% capacity)
- **Year 5-10**: Mid-succession (50-80% capacity)
- **Year 10+**: Mature ecosystem (80-100% capacity)

## Emissions Scope Calculator

Calculate Scope 1, 2, and 3 emissions:

```python
from src.calculations.scope_calculator import EmissionsCalculator

calc = EmissionsCalculator('Mine A')
scope1 = calc.calculate_scope1_diesel(liters=50000)
scope2 = calc.calculate_scope2_electricity(kwh=250000)
scope3 = calc.calculate_scope3_shipping(tons=5000, distance_km=150)
```

## Usage Examples

### Paris-Aligned Reduction Pathway

```python
from src.main import EmissionsIntensityTracker

tracker = EmissionsIntensityTracker()
pathway = tracker.calculate_paris_aligned_pathway(
    current_emissions_tco2e=80_000,
    base_year=2025,
    target_year=2050,
    scenario="1.5c",
)
print(f"2030 budget: {pathway['budget_2030']:,.0f} tCO2e")
print(f"Total reduction by 2050: {pathway['total_reduction_pct']:.1f}%")
```

### Benchmark Against Sector

```python
result = tracker.benchmark_against_sector(0.045, sector="coal_mining")
print(f"Performance: {result['performance_band']}")         # above_average
print(f"Deviation:   {result['deviation_from_avg_pct']:+.1f}%")
print(f"Gap to best: {result['reduction_needed_to_best']:.4f} tCO2e/t")
```

Refer to the `tests/` directory for comprehensive example implementations.
