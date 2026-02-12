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
