# Contributing to Emissions Intensity Tracker

Thank you for your interest in contributing! Here's how to get started.

## Getting Started

1. **Fork the repository** and clone it locally
2. **Create a branch** for your changes: `git checkout -b feat/your-feature-name`
3. **Install dependencies:** `pip install -r requirements.txt`
4. **Run tests:** `pytest tests/ -v`

## Project Structure

```
emissions-intensity-tracker/
├── src/               # Core library code
├── demo/              # Demo scripts and sample data
├── tests/             # Unit tests (pytest)
└── data/              # Example data files
```

## How to Contribute

### Bug Reports
- Open an issue with a clear title and description
- Include sample data or a minimal reproducible example
- Specify your Python version and operating system

### New Features
- Open an issue first to discuss the feature
- Pull requests should include tests and updated documentation
- For Scope 3 emissions modules or new sector benchmarks, include academic references

### Code Style
- Follow PEP 8; 4-space indentation
- Add docstrings to all public functions and classes
- Keep functions focused — one logical unit per function

## Pull Request Process

1. Update the README.md if you add new features or change the CLI interface
2. Add or update tests covering your changes
3. Ensure `pytest tests/ -v` passes locally
4. Submit a PR with a clear description of what changed and why

## Areas to Contribute

- Additional sector benchmarks (shipping, aviation, agriculture)
- Integration with GHG Protocol Scope 3 categories
- SBTi target validation for specific jurisdictions
- EU CBAM extended coverage for indirect emissions
- Streamlit dashboard UI wrapper

---

*Built with 🌍 for the energy transition*
