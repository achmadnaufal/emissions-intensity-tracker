# Changelog

All notable changes to the Emissions Intensity Tracker project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
