# Changelog

All notable changes to the Emissions Intensity Tracker project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
