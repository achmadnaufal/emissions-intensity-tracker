"""
Unit tests for EmissionsIntensityTracker.
"""

import pytest
import pandas as pd
import tempfile
from pathlib import Path
from src.main import EmissionsIntensityTracker


class TestEmissionsIntensityTracker:
    """Test suite for EmissionsIntensityTracker."""
    
    @pytest.fixture
    def sample_data(self):
        """Create sample emissions data."""
        return pd.DataFrame({
            "operation_id": ["OP-001", "OP-002", "OP-001", "OP-002"],
            "year": [2024, 2024, 2025, 2025],
            "scope1_tco2e": [1000.0, 1200.0, 950.0, 1100.0],
            "scope2_tco2e": [500.0, 600.0, 480.0, 580.0],
            "scope3_tco2e": [800.0, 1000.0, 750.0, 950.0],
            "production_tonnes": [10000, 12000, 11000, 13000],
        })
    
    @pytest.fixture
    def tracker(self):
        """Create a fresh tracker instance."""
        return EmissionsIntensityTracker()
    
    def test_initialization(self, tracker):
        """Test tracker initialization."""
        assert tracker.config == {}
    
    def test_initialization_with_config(self):
        """Test tracker with custom config."""
        config = {"threshold": 0.5}
        tracker = EmissionsIntensityTracker(config=config)
        assert tracker.config["threshold"] == 0.5
    
    def test_load_csv(self, tracker, sample_data):
        """Test loading CSV file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "data.csv"
            sample_data.to_csv(filepath, index=False)
            
            df = tracker.load_data(str(filepath))
            assert len(df) == 4
            assert "operation_id" in df.columns
    
    def test_validate_empty(self, tracker):
        """Test validation of empty DataFrame."""
        with pytest.raises(ValueError, match="Input DataFrame is empty"):
            tracker.validate(pd.DataFrame())
    
    def test_validate_valid(self, tracker, sample_data):
        """Test validation of valid DataFrame."""
        assert tracker.validate(sample_data) is True
    
    def test_preprocess(self, tracker, sample_data):
        """Test preprocessing."""
        df = tracker.preprocess(sample_data)
        assert df.columns[0] == "operation_id"
        assert len(df) == 4
    
    def test_analyze(self, tracker, sample_data):
        """Test analysis."""
        result = tracker.analyze(sample_data)
        assert result["total_records"] == 4
        assert "summary_stats" in result
        assert "means" in result
    
    def test_analyze_empty(self, tracker):
        """Test analysis of empty DataFrame."""
        with pytest.raises(ValueError, match="Input DataFrame is empty"):
            tracker.analyze(pd.DataFrame())
    
    def test_run_full_pipeline(self, tracker, sample_data):
        """Test full pipeline."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "data.csv"
            sample_data.to_csv(filepath, index=False)
            
            result = tracker.run(str(filepath))
            assert result["total_records"] == 4
    
    def test_to_dataframe(self, tracker, sample_data):
        """Test conversion to DataFrame."""
        result = tracker.analyze(sample_data)
        df = tracker.to_dataframe(result)
        assert len(df) > 0
        assert "metric" in df.columns
        assert "value" in df.columns
