# Emissions Intensity Tracker

![Python](https://img.shields.io/badge/python-3.9%2B-blue?logo=python)
![License](https://img.shields.io/badge/license-MIT-green)
![Last Commit](https://img.shields.io/github/last-commit/achmadnaufal/emissions-intensity-tracker)

Scope 1, 2, and 3 greenhouse gas emissions intensity tracking for coal and heavy-industry operations — with Paris-aligned pathway modelling, SBTi benchmarking, CBAM/carbon-tax exposure, and green-steel transition economics.

## Features

- **Emissions intensity calculation** (`EmissionsIntensityTracker`) — tCO2e per tonne of production across Scope 1/2/3
- **Year-over-year trend analysis** — per-operation CAGR tracking
- **Paris 1.5°C / 2°C pathway** — SBTi-aligned annual reduction budgets
- **Sector benchmarking** — compare against coal_mining, thermal_power, cement, steel
- **Carbon reduction roadmaps** — annual targets to a user-defined % reduction
- **Methane (CH₄) tracker** (`MethaneEmissionsCalculator`) — IPCC Tier 2 underground/surface mining emissions with VAM, gas drainage, and abatement cost curves
- **Scope 3 supply chain calculator** (`Scope3SupplyChainCalculator`) — GHG Protocol Cat 4/9/11 for coal mining (upstream/downstream transport + end-use combustion)
- **Scope 3 upstream / downstream modules** (`Scope3UpstreamCalculator`, `Scope3DownstreamCalculator`) — transport leg emissions and coal-shipment accounting
- **SBTi target validator** (`ScienceBasedTargetsValidator`) — SBTi ACA / SDA alignment checks
- **Net-zero pathway tracker** (`NetZeroPathwayTracker`) — IEA/SBTi/linear/exponential scenarios with annual progress records
- **EU CBAM cost calculator** (`CBAMCostCalculator`) — EU Regulation 2023/956 liability estimation per product / portfolio
- **Carbon tax exposure calculator** (`CarbonTaxExposureCalculator`) — multi-jurisdiction climate-scenario tax liability
- **Carbon market arbitrage analyzer** (`CarbonMarketArbitrageAnalyzer`) — EU ETS vs VCS DiD pricing, arbitrage windows, ROPI
- **Carbon credit delivery scheduler** (`CreditDeliveryScheduler`) — issuance gap analysis and retirement tracking
- **Green steel transition calculator** (`GreenSteelTransitionCalculator`) — BF-BOF / CCS / DRI-EAF / H-DRI-EAF / electrowinning cost premium, abatement cost, capex, H2 demand, NPV, deployment risk
- **Mine restoration calculator** (`RestorationCalculator`) — post-closure rehabilitation accounting
- Supports CSV and Excel input formats

## Quick Start

**Clone the repository:**
```bash
git clone https://github.com/achmadnaufal/emissions-intensity-tracker.git
cd emissions-intensity-tracker
```

**Install dependencies:**
```bash
pip install -r requirements.txt
```

**Run the demo:**
```bash
python3 demo/run_demo.py
```

## Usage

**Run with sample data:**
```bash
python3 demo/run_demo.py
```

Live demo output:

```
============================================================
  Emissions Intensity Tracker — Demo
============================================================

✓ Loaded 12 records from extended_emissions_data.csv
  Operations: 4 | Years: [2023, 2024, 2025]

✓ Calculated Scope 1+2+3 emission intensities
  Avg intensity: 0.3338 tCO2e/tonne
  Best performer: OP-AUSTRALIA-001 (0.2845 tCO2e/t)

✓ Year-over-year trend analysis (4 operations):
  Operation                   YoY Change    Avg Annual   Latest (tCO2e)
  -----------------------------------------------------------------
  OP-AUSTRALIA-001          ↓       9.3%        -4.64%         31,300.0
  OP-COLOMBIA-001           ↓       6.8%        -3.38%         19,300.0
  OP-KALIMANTAN-001         ↓       8.1%        -4.03%         25,100.0
  OP-SUMATRA-001            ↓       8.2%        -4.10%         17,900.0

✓ Paris 1.5°C Pathway (from 50,000 tCO2e baseline):
  Annual reduction rate : 4.2% CAGR (SBTi ACA)
  2030 budget           : 40,346 tCO2e
  2050 budget           : 17,104 tCO2e
  Total reduction       : 65.8% vs baseline

✓ Sector benchmark (coal_mining):
  Measured intensity    : 0.038 tCO2e/tonne
  Sector average        : 0.04 tCO2e/tonne
  Deviation from avg    : -5.0%
  Performance band      : ABOVE_AVERAGE
  Reduction to avg      : 0.0000 tCO2e/t

✓ Carbon reduction roadmap (25% in 5 years):
  Current intensity     : 0.038 tCO2e/unit
  Target intensity      : 0.0285 tCO2e/unit
  Year 1               : 0.0361 tCO2e/unit
  Year 2               : 0.0342 tCO2e/unit
  Year 3               : 0.0323 tCO2e/unit
  Year 4               : 0.0304 tCO2e/unit
  Year 5               : 0.0285 tCO2e/unit

============================================================
  ✅ Demo complete
============================================================
```

**Use in your own code:**
```python
from src.main import EmissionsIntensityTracker

tracker = EmissionsIntensityTracker()
df = tracker.load_data("data/extended_emissions_data.csv")

df = tracker.calculate_emission_intensity(
    df,
    scope_cols=["scope1_tco2e", "scope2_tco2e", "scope3_tco2e"],
    production_col="production_tonnes",
)

pathway = tracker.calculate_paris_aligned_pathway(50000, scenario="1.5c")
bench = tracker.benchmark_against_sector(0.038, sector="coal_mining")
```

**Methane (CH₄) emissions accounting:**
```python
from src.methane_tracker import MethaneEmissionsCalculator

calc = MethaneEmissionsCalculator()
emissions = calc.calculate_mining_emissions(
    mine_type="underground",
    production_t=500000,
    methane_content_m3_t=12.5,
    emission_factor=0.5,
)
vam = calc.calculate_vam_emissions(air_flow_m3s=50, ch4_ppm=2500, operating_hours=8760)
curve = calc.abatement_cost_curve()
net = calc.net_emissions_after_abatement(gross_emissions_tco2e=12500, abatement_pct=60)
```

**Export results:**
```python
tracker.to_dataframe(result).to_csv("output.csv", index=False)
```

## Architecture

```mermaid
flowchart TD
    IN[("sample_data/ · data/*.csv · *.xlsx")] --> LOAD[EmissionsIntensityTracker.load_data]
    LOAD --> VAL[Input Validators<br/>schema · scope cols · production col]
    VAL --> CORE[Core Intensity + Trend<br/>Scope 1+2+3 / production · YoY CAGR]
    VAL --> SCOPE3[Scope 3 Modules<br/>supply chain · upstream · downstream]
    VAL --> CH4[MethaneEmissionsCalculator<br/>IPCC Tier 2 · VAM · abatement]
    VAL --> STEEL[GreenSteelTransitionCalculator<br/>BF-BOF → H-DRI-EAF · NPV]
    VAL --> REST[RestorationCalculator]

    CORE --> PATH[Net-Zero / Paris Pathways<br/>NetZeroPathwayTracker · SBTi ACA/SDA]
    CORE --> BENCH[Sector Benchmark<br/>coal_mining · power · cement · steel]
    PATH --> SBTI[ScienceBasedTargetsValidator]

    CORE --> CBAM[CBAMCostCalculator<br/>EU Reg 2023/956]
    CORE --> TAX[CarbonTaxExposureCalculator<br/>multi-jurisdiction scenarios]
    CBAM --> ARB[CarbonMarketArbitrageAnalyzer<br/>EU ETS vs VCS · ROPI]
    TAX --> ARB
    ARB --> SCHED[CreditDeliveryScheduler<br/>issuance gap · retirement]

    SBTI --> OUT[(Metrics · Reports · CSV exports)]
    BENCH --> OUT
    CH4 --> OUT
    STEEL --> OUT
    SCOPE3 --> OUT
    SCHED --> OUT
    REST --> OUT
```

## Tech Stack

| Tool | Purpose |
|---|---|
| **Python 3.9+** | Core language |
| **pandas / numpy** | Data manipulation |
| **matplotlib** | Plotting / charts |
| **openpyxl** | Excel I/O |
| **rich** | CLI rendering |
| **pytest** | Unit testing |

## Testing

```bash
pytest tests/ -v
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines. PRs welcome — especially additional sector benchmarks, SBTi validation modules, and EU CBAM coverage extensions.

---

> Built by [Achmad Naufal](https://github.com/achmadnaufal) | Lead Data Analyst | Power BI · SQL · Python · GIS
