# Changelog

All notable changes to the Emissions Intensity Tracker project are documented in this file.

## [2.3.0] - 2026-04-02

### Added
- **CarbonMarketArbitrageAnalyzer** (`src/carbon_market_arbitrage.py`) — Cross-market price spread and arbitrage window detection across EU ETS VCS Gold Standard and Article 6 bilateral markets
- **Unit tests** — new comprehensive test suite in `tests/test_carbon_market_arbitrage.py`
- **CHANGELOG** updated to v2.3.0

## [2.2.0] - 2026-04-01

### Added
- **Carbon Credit Delivery Scheduler** (`src/carbon_credit_delivery_scheduler.py`) — issuance and forward delivery management for NbS and industrial decarbonisation projects
  - `IssuancePeriod` dataclass: annual gross ERs, verified/estimated flag, registry issuance ID
  - `DeliveryCommitment` dataclass: buyer, vintage year, tCO₂e committed, deadline, purpose (voluntary/compliance/CORSIA/ETS), retirement tracking (date, serial)
  - `CreditDeliveryScheduler` class: buffer pool deduction (configurable %), `net_issuance()` per vintage, `delivery_report()` with per-vintage surplus/deficit analysis
  - Gap analysis: overall SURPLUS/DEFICIT, overcommitted vintages list, buffer deduction breakdown
  - `retirement_schedule()`: registry retirement records with vintage/serial/buyer
  - `unretired_commitments()`: outstanding delivery obligations
  - Supports Verra VCS verification cycles; CORSIA/ETS purpose tracking
- **Unit tests** — 18 new tests in `tests/test_carbon_credit_delivery_scheduler.py` (all passing)

## [2.1.0] - 2026-03-31

### Added
- **Scope 3 Supply Chain Calculator** (`src/scope3_supply_chain_calculator.py`) — GHG Protocol Scope 3 upstream and downstream emissions for coal mining
  - `TransportLeg` dataclass: mode, distance, tonnage, load factor, optional custom EF
  - `CoalCombustionEndUse` dataclass: IPCC 2006 coal combustion emission factors (bituminous 2.42, subbituminous 1.85, lignite 1.32 t CO2e/t)
  - `Scope3SupplyChainCalculator` class: Categories 4, 9, and 11
  - Linear load-factor correction for empty return leg emissions
  - Cat 11 dominance detection (>90%) with customer transition recommendations
  - Road-to-rail modal shift recommendation (0.120→0.028 kg CO2e/tkm)
  - `transport_intensity_tkm_per_t()`: fleet intensity metric for GHG reporting
  - Category breakdown with `largest_category` identification
- **Unit tests** — 30 new tests in `tests/test_scope3_supply_chain_calculator.py` (all passing)

### References
- GHG Protocol (2011) Corporate Value Chain (Scope 3) Accounting Standard.
- IPCC (2006) Guidelines Vol. 2 — Energy, Chapter 2.
- IEA (2023) World Energy Statistics — Coal emission factors.

# Changelog

All notable changes to the Emissions Intensity Tracker project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-03-30

### Added
- **CBAM Cost Calculator** (`src/cbam_cost_calculator.py`) — EU Carbon Border Adjustment Mechanism liability estimation for Indonesian exporters per Regulation (EU) 2023/956
  - 6 CBAM-covered sectors: cement, aluminium, fertilisers, electricity, iron_steel, hydrogen (Annex I)
  - EU ETS benchmark intensities per sector from CBAM Implementing Regulation (EU) 2023/2390
  - `CBAMCostCalculator.estimate_annual_cost()`: total embedded emissions, taxable tCO2 above benchmark, gross/net CBAM cost in EUR
  - Domestic carbon price credit deduction (zero if no local carbon tax)
  - Supplier pass-through exposure estimate (25% default fraction for coal supply chain)
  - `portfolio_estimate()`: aggregate CBAM exposure across multiple product lines
  - `carbon_price_sensitivity()`: sensitivity table across EU ETS price scenarios
  - `total_cbam_cost_idr()`: IDR conversion helper
- **Unit tests** — 35 new tests in `tests/test_cbam_cost_calculator.py`

### References
- European Parliament (2023) Regulation (EU) 2023/956 on CBAM. OJ L 130/52.
- European Commission (2022) CBAM Impact Assessment. SWD(2022)345.

## [1.9.0] - 2026-03-30

### Added
- **NetZeroPathwayTracker** (`src/net_zero_pathway_tracker.py`)
  - `NetZeroPathwayTracker` — tracks corporate annual emissions against four science-based net zero pathways: linear, exponential, SBTi 1.5°C (4.2%/yr), SBTi well-below 2°C (2.5%/yr), IEA NZE 2050
  - `AnnualProgressRecord` — per-year snapshot with target, gap, YoY reduction %, required future rate, and cumulative budget consumed %
  - `NetZeroPathwayReport` — full report with on-track rate, overall status (on_track/lagging/critical), remaining carbon budget, and implied net zero year extrapolation
  - `record_year()` / `record_batch()` for incremental data entry; `pathway_target(year)` for target lookup
  - `total_carbon_budget()` — cumulative allowable emissions from base year to net zero
  - strict_mode: validates that custom pathway types supply reduction rates
- **Test Suite** (`tests/test_net_zero_pathway_tracker.py`) — 35 unit tests covering all pathway types, instantiation guards, on-track/off-track detection, budget tracking, and status classification

## [1.8.0] - 2026-03-26

### Added
- **ScienceBasedTargetsValidator** (`src/sbti_targets_validator.py`) — SBTi Corporate Manual v2.0 alignment checker
  - Validates Scope 1+2 near-term targets using Absolute Contraction Approach (ACA) minimum rates
  - Scope 3 materiality check: flags missing Scope 3 target when S3 > 40% of total inventory
  - Long-term net-zero alignment: verifies ≥90% absolute reduction for NET_ZERO scenario
  - Target horizon validation: 5–10 year near-term window enforcement
  - Offset-reliance warning (SBTi prioritises direct reductions)
  - Batch validation with portfolio-level summary report
  - Three temperature scenarios: `well_below_2c`, `1.5c`, `net_zero`
  - Overall status: APPROVED / CONDITIONAL / REJECTED with actionable flags
- Sample data: `data/sbti_sample_profiles.json` — 3 company profiles across coal, pharma, agri sectors
- Unit tests: 13 new tests in `tests/test_sbti_targets_validator.py`

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
