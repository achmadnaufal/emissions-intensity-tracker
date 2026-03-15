"""
Unit tests for Paris-aligned pathway and sector benchmarking.
"""
import pytest
from src.main import EmissionsIntensityTracker


@pytest.fixture
def tracker():
    return EmissionsIntensityTracker()


class TestParisAlignedPathway:

    def test_1_5c_reduces_faster_than_2c(self, tracker):
        r15 = tracker.calculate_paris_aligned_pathway(100_000, scenario="1.5c")
        r2c = tracker.calculate_paris_aligned_pathway(100_000, scenario="2c")
        assert r15["total_reduction_pct"] > r2c["total_reduction_pct"]

    def test_pathway_decreases_each_year(self, tracker):
        result = tracker.calculate_paris_aligned_pathway(50_000, scenario="1.5c")
        pathway = result["annual_pathway"]
        values = list(pathway.values())
        for i in range(len(values) - 1):
            assert values[i] >= values[i + 1], "Pathway should be non-increasing"

    def test_invalid_emissions_raises(self, tracker):
        with pytest.raises(ValueError, match="current_emissions_tco2e must be positive"):
            tracker.calculate_paris_aligned_pathway(-100)

    def test_invalid_target_year_raises(self, tracker):
        with pytest.raises(ValueError, match="target_year must be after base_year"):
            tracker.calculate_paris_aligned_pathway(50_000, base_year=2050, target_year=2040)

    def test_invalid_scenario_raises(self, tracker):
        with pytest.raises(ValueError, match="scenario must be '1.5c' or '2c'"):
            tracker.calculate_paris_aligned_pathway(50_000, scenario="3c")

    def test_returns_2030_budget(self, tracker):
        result = tracker.calculate_paris_aligned_pathway(100_000, scenario="1.5c")
        assert "budget_2030" in result
        assert result["budget_2030"] > 0
        assert result["budget_2030"] < 100_000


class TestSectorBenchmark:

    def test_best_practice_band(self, tracker):
        result = tracker.benchmark_against_sector(0.020, sector="coal_mining")
        assert result["performance_band"] == "best_practice"

    def test_above_average_band(self, tracker):
        result = tracker.benchmark_against_sector(0.032, sector="coal_mining")
        assert result["performance_band"] == "above_average"

    def test_below_average_band(self, tracker):
        result = tracker.benchmark_against_sector(0.060, sector="coal_mining")
        assert result["performance_band"] == "below_average"

    def test_invalid_sector_raises(self, tracker):
        with pytest.raises(ValueError, match="Unsupported sector"):
            tracker.benchmark_against_sector(0.040, sector="aviation")

    def test_negative_intensity_raises(self, tracker):
        with pytest.raises(ValueError, match="cannot be negative"):
            tracker.benchmark_against_sector(-0.01)

    def test_all_supported_sectors(self, tracker):
        for sector in ("coal_mining", "thermal_power", "cement", "steel"):
            result = tracker.benchmark_against_sector(
                tracker.benchmark_against_sector.__doc__ and 0.5 or 0.5,
                sector=sector,
            )
            assert "performance_band" in result
