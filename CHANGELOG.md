# Changelog

All notable changes to the Emissions Intensity Tracker project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.7.0] - 2026-03-25

### Added
- **Carbon Tax Exposure Calculator** (`src/carbon_tax_exposure_calculator.py`) — TCFD-aligned financial risk quantification for carbon pricing
  - Four IEA carbon price trajectories: NZE 2050, SDS (1.8°C), Announced Pledges (NDCs), STEPS (2.5°C)
  - Linear interpolation for any assessment year 2020–2060
  - Scope 1+2 operational exposure and optional Scope 3 downstream coal combustion exposure
  - Incremental exposure net of existing carbon tax already paid
  - Cost per tonne of coal produced and exposure as % of hypothetical revenue
  - Risk classification: low / medium / high / critical by USD threshold
  - All-scenario comparison (4 scenarios at a single year)
  - Multi-year projection across a list of target years
- Unit tests: 18 new tests in `tests/test_carbon_tax_exposure_calculator.py`

## [1.6.0] - 2026-03-23

### Added
- `src/calculations/scope3_downstream.py` — GHG Protocol Scope 3 downstream emissions
  - `CoalShipment` dataclass with full input validation
  - `Scope3DownstreamCalculator` class covering:
    - Category 9: downstream transportation (barge, vessel, rail, truck)
    - Category 11: use of sold products (coal combustion at customer sites)
    - Category 12: end-of-life treatment (fly ash landfill)
  - `generate_report()` — full breakdown with sector and grade splits
  - `intensity_tCO2e_per_tonne()` — downstream Scope 3 intensity metric
  - Coal grade emission factors: anthracite, bituminous, sub-bituminous, lignite
- `data/sample_coal_shipments.csv` — 12 realistic shipment records (Indonesia + export)
- 25 unit tests in `tests/test_scope3_downstream.py`

### References
- GHG Protocol Corporate Value Chain (Scope 3) Standard
- IPCC AR5 GWP-100 values

## [1.5.0] - 2026-03-21

### Added
- **Scope 3 Upstream Calculator** (`src/calculations/scope3_upstream.py`) — GHG Protocol Category 1–4 upstream emissions
  - Cat 1: Purchased goods (ANFO explosives, tyres) with EcoInvent 3.9 emission factors
  - Cat 2: Capital goods (structural steel embodied carbon, World Steel Assoc. factors)
  - Cat 3: Upstream fuel lifecycle (well-to-tank diesel addition)
  - Cat 4: Inbound logistics (road freight 0.096 kg/t-km, rail 0.028 kg/t-km)
  - `benchmark()` method comparing operation intensity vs industry average
  - `UpstreamEmissionsResult` dataclass for structured reporting
- **Sample data** — `data/scope3_upstream_sample.csv` with 8 major Indonesian coal operations
- **Unit tests** — 14 new tests in `tests/test_scope3_upstream.py`

## [1.4.0] - 2026-03-15

### Added
- **Paris-Aligned Pathway Calculator** — `calculate_paris_aligned_pathway()`: Generates annual emissions budgets following SBTi 1.5°C (4.2% CAGR) or 2°C (2.5% CAGR) reduction rates with 2030 interim budget
- **Sector Benchmarking** — `benchmark_against_sector()`: Benchmarks operations against industry averages and best-practice for coal mining, thermal power, cement, and steel
- **Unit Tests** — 12 new tests in `tests/test_paris_pathway.py` covering pathway monotonicity, band classification, and error handling
- **README** — Added pathway and benchmarking usage examples

## [1.3.0] - 2026-03-12

### Added

- **Environmental Restoration Calculator** (`src/restoration_calculator.py`):
  - `calculate_habitat_restoration()`: Convert carbon reductions to habitat area (4 habitat types)
  - `calculate_species_recovery()`: Project species richness recovery over time
  - `calculate_tree_planting_impact()`: Assess carbon and biodiversity impact of tree plantings
  - `compare_remediation_scenarios()`: Compare multiple restoration approaches
  - Support for habitat types: native forest, wetland, grassland, agroforestry
- **Comprehensive Test Suite** (`tests/test_restoration_calculator.py`):
  - 20+ unit tests covering all restoration calculator methods
  - Edge case validation (negative values, invalid types, missing parameters)
  - Scenario comparison testing
- **Enhanced README**:
  - Examples for habitat restoration and species recovery
  - Restoration timeline and species recovery stages
  - Habitat type conversion factors documented

### Improved

- Added docstrings with error handling documentation
- Type hints for all new public methods
- Evidence-based conversion factors (carbon → habitat, habitat → species)
- Support for coal mining remediation workflows

### Technical Details

- Species recovery follows 10-30 year recolonization trajectory
- Carbon conversion: 0.12-0.20 ha/tCO2e (habitat type dependent)
- Tree carbon sequestration: 0.015 tCO2e/tree over 30 years
- Species density: 5.5 avg species/hectare in mature habitat

## [1.2.0] - 2026-03-10

### Added

- **Emissions Intensity Calculation**: New `calculate_emission_intensity()` method to compute tCO2e per unit production across all scopes
- **Trend Analysis**: New `calculate_trend()` method for year-over-year emissions tracking and trend analysis per operation
- **Carbon Reduction Targets**: New `calculate_carbon_reduction_target()` method to generate annual reduction targets based on current intensity
- **Comprehensive Test Suite**: 
  - 11 new tests for core tracker functionality
  - Tests for data loading, validation, preprocessing, and analysis
  - Tests for edge cases and full pipeline execution
- **Extended Sample Data**: Added `extended_emissions_data.csv` with 12 records across 4 international operations (Indonesia, Australia, Colombia)
- **Regional and Operation Type Classification**: Sample data includes region and operation type metadata for better filtering

### Changed

- Improved docstrings with detailed parameter descriptions
- Enhanced error handling for empty DataFrames
- Standardized return types and structure across methods

### Fixed

- Better handling of missing production data in intensity calculations
- Improved trend calculations with proper sorting by time period

## [1.1.0] - 2026-03-01

### Added

- CSV and Excel file loading support
- Data validation and preprocessing
- Summary statistics calculation
- DataFrame export functionality

## [1.0.0] - 2026-02-15

### Added

- Initial release
- Core emissions intensity tracking for coal operations
- Support for Scope 1, 2, and 3 emissions
- Basic analysis and reporting
