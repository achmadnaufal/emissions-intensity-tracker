"""
Unit tests for environmental restoration impact calculator.

Tests habitat restoration calculations, species recovery projections,
and tree planting impact assessments.
"""

import pytest
from src.restoration_calculator import RestorationCalculator


class TestHabitatRestoration:
    """Test suite for habitat restoration calculations."""
    
    @pytest.fixture
    def calc(self):
        """Fixture: Initialize RestorationCalculator."""
        return RestorationCalculator()
    
    def test_habitat_native_forest(self, calc):
        """Test habitat area calculation for native forest."""
        result = calc.calculate_habitat_restoration(
            emissions_reduction_tco2e=500,
            habitat_type="native_forest"
        )
        
        assert result["habitat_area_hectares"] == 75.0  # 500 * 0.15
        assert result["habitat_type"] == "native_forest"
        assert result["conversion_factor_ha_per_tco2e"] == 0.15
    
    def test_habitat_wetland(self, calc):
        """Test habitat area calculation for wetland restoration."""
        result = calc.calculate_habitat_restoration(
            emissions_reduction_tco2e=400,
            habitat_type="wetland"
        )
        
        assert result["habitat_area_hectares"] == 72.0  # 400 * 0.18
        assert result["habitat_type"] == "wetland"
    
    def test_habitat_agroforestry(self, calc):
        """Test habitat area calculation for agroforestry."""
        result = calc.calculate_habitat_restoration(
            emissions_reduction_tco2e=300,
            habitat_type="agroforestry"
        )
        
        assert result["habitat_area_hectares"] == 60.0  # 300 * 0.20
    
    def test_habitat_invalid_type(self, calc):
        """Test that invalid habitat type raises ValueError."""
        with pytest.raises(ValueError):
            calc.calculate_habitat_restoration(100, habitat_type="invalid_type")
    
    def test_habitat_negative_carbon(self, calc):
        """Test that negative carbon reduction raises ValueError."""
        with pytest.raises(ValueError):
            calc.calculate_habitat_restoration(-50, habitat_type="native_forest")
    
    def test_habitat_zero_carbon(self, calc):
        """Test habitat calculation with zero carbon reduction."""
        result = calc.calculate_habitat_restoration(0, habitat_type="native_forest")
        assert result["habitat_area_hectares"] == 0.0


class TestSpeciesRecovery:
    """Test suite for species recovery projections."""
    
    @pytest.fixture
    def calc(self):
        return RestorationCalculator()
    
    def test_species_recovery_10_years(self, calc):
        """Test species recovery at 10-year mark."""
        result = calc.calculate_species_recovery(
            habitat_area_hectares=50,
            baseline_species_count=0,
            years=10
        )
        
        assert result["projected_species_final"] > result["baseline_species"]
        assert 50 <= result["recovery_percentage"] <= 100
        assert 0 <= result["habitat_quality_index"] <= 1.0
    
    def test_species_recovery_early_stage(self, calc):
        """Test species recovery in early stage (< 2 years)."""
        result = calc.calculate_species_recovery(
            habitat_area_hectares=50,
            years=1
        )
        
        assert result["recovery_percentage"] <= 15
        assert result["habitat_quality_index"] <= 0.15
    
    def test_species_recovery_with_baseline(self, calc):
        """Test species recovery starting from non-zero baseline."""
        result = calc.calculate_species_recovery(
            habitat_area_hectares=50,
            baseline_species_count=10,
            years=10
        )
        
        assert result["projected_species_final"] >= result["baseline_species"]
    
    def test_species_recovery_invalid_habitat(self, calc):
        """Test that negative habitat area raises ValueError."""
        with pytest.raises(ValueError):
            calc.calculate_species_recovery(-10, years=10)
    
    def test_species_recovery_invalid_years(self, calc):
        """Test that invalid years parameter raises ValueError."""
        with pytest.raises(ValueError):
            calc.calculate_species_recovery(50, years=-5)
        
        with pytest.raises(ValueError):
            calc.calculate_species_recovery(50, years=0)


class TestTreePlanting:
    """Test suite for tree planting impact calculations."""
    
    @pytest.fixture
    def calc(self):
        return RestorationCalculator()
    
    def test_tree_impact_baseline(self, calc):
        """Test tree planting impact with default survival rate."""
        result = calc.calculate_tree_planting_impact(
            trees_planted=1000,
            tree_survival_rate_pct=80.0,
            years=30
        )
        
        assert result["trees_surviving"] == 800
        assert result["carbon_sequestered_tco2e"] > 0
        assert result["habitat_hectares_equivalent"] > 0
        assert result["species_potential"] > 0
    
    def test_tree_impact_high_survival(self, calc):
        """Test tree impact with high survival rate."""
        result_high = calc.calculate_tree_planting_impact(
            trees_planted=1000,
            tree_survival_rate_pct=95.0
        )
        
        result_low = calc.calculate_tree_planting_impact(
            trees_planted=1000,
            tree_survival_rate_pct=60.0
        )
        
        assert result_high["trees_surviving"] > result_low["trees_surviving"]
        assert result_high["carbon_sequestered_tco2e"] > result_low["carbon_sequestered_tco2e"]
    
    def test_tree_impact_invalid_survival_rate(self, calc):
        """Test that invalid survival rate raises ValueError."""
        with pytest.raises(ValueError):
            calc.calculate_tree_planting_impact(1000, tree_survival_rate_pct=150)
        
        with pytest.raises(ValueError):
            calc.calculate_tree_planting_impact(1000, tree_survival_rate_pct=-10)
    
    def test_tree_impact_negative_count(self, calc):
        """Test that negative tree count raises ValueError."""
        with pytest.raises(ValueError):
            calc.calculate_tree_planting_impact(-500)
    
    def test_tree_impact_zero_trees(self, calc):
        """Test tree impact with zero trees planted."""
        result = calc.calculate_tree_planting_impact(0)
        assert result["trees_surviving"] == 0
        assert result["carbon_sequestered_tco2e"] == 0.0


class TestScenarioComparison:
    """Test suite for remediation scenario comparisons."""
    
    @pytest.fixture
    def calc(self):
        return RestorationCalculator()
    
    def test_scenario_comparison_valid(self, calc):
        """Test comparison of multiple remediation scenarios."""
        scenarios = {
            "wetland": {
                "carbon_tco2e": 500,
                "habitat_type": "wetland",
                "habitat_ha": 90
            },
            "forest": {
                "carbon_tco2e": 400,
                "habitat_type": "native_forest",
                "habitat_ha": 60
            }
        }
        
        result = calc.compare_remediation_scenarios(scenarios)
        
        assert "wetland" in result
        assert "forest" in result
        assert result["wetland"]["biodiversity_score"] > 0
        assert result["forest"]["biodiversity_score"] > 0
    
    def test_scenario_comparison_empty(self, calc):
        """Test that empty scenarios dict raises ValueError."""
        with pytest.raises(ValueError):
            calc.compare_remediation_scenarios({})
    
    def test_scenario_comparison_missing_keys(self, calc):
        """Test scenario comparison with incomplete scenario data."""
        scenarios = {
            "incomplete": {
                "carbon_tco2e": 500
                # Missing habitat_ha
            }
        }
        
        result = calc.compare_remediation_scenarios(scenarios)
        # Should handle gracefully, may have error key
        assert "incomplete" in result
