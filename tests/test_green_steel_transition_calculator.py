"""Tests for GreenSteelTransitionCalculator."""
import pytest
from src.green_steel_transition_calculator import (
    GreenSteelTransitionCalculator,
    TransitionScenario,
    SteelTechnology,
    TechnologyProfile,
    TECHNOLOGY_PROFILES,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def base_scenario():
    return TransitionScenario(
        plant_id="KRAKATAU-01",
        annual_capacity_Mt=3.0,
        baseline_tech=SteelTechnology.BF_BOF,
        target_tech=SteelTechnology.H_DRI_EAF,
        transition_start_year=2026,
        full_deployment_year=2035,
        electricity_carbon_intensity=0.4,
        green_h2_cost_usd_per_kg=3.0,
        carbon_price_usd_per_tCO2e=80.0,
    )


@pytest.fixture
def calc():
    return GreenSteelTransitionCalculator()


# ---------------------------------------------------------------------------
# Validation tests
# ---------------------------------------------------------------------------

class TestTransitionScenarioValidation:
    def test_zero_capacity_raises(self):
        with pytest.raises(ValueError, match="annual_capacity_Mt"):
            TransitionScenario("X", 0, SteelTechnology.BF_BOF, SteelTechnology.H_DRI_EAF, 2026, 2035)

    def test_deployment_before_start_raises(self):
        with pytest.raises(ValueError, match="full_deployment_year"):
            TransitionScenario("X", 3, SteelTechnology.BF_BOF, SteelTechnology.H_DRI_EAF, 2035, 2026)

    def test_negative_elec_intensity_raises(self):
        with pytest.raises(ValueError, match="electricity_carbon_intensity"):
            TransitionScenario("X", 3, SteelTechnology.BF_BOF, SteelTechnology.H_DRI_EAF,
                               2026, 2035, electricity_carbon_intensity=-0.1)


class TestTechnologyProfileValidation:
    def test_negative_co2e_raises(self):
        with pytest.raises(ValueError, match="co2e_intensity"):
            TechnologyProfile(SteelTechnology.BF_BOF, -1.0, 21, 380, 1000)

    def test_invalid_trl_raises(self):
        with pytest.raises(ValueError, match="trl"):
            TechnologyProfile(SteelTechnology.BF_BOF, 2.1, 21, 380, 1000, trl=10)

    def test_invalid_ccs_rate_raises(self):
        with pytest.raises(ValueError, match="ccs_capture_rate"):
            TechnologyProfile(SteelTechnology.BF_BOF_CCS, 0.5, 24, 450, 1600, ccs_capture_rate=1.5)


# ---------------------------------------------------------------------------
# Default profile tests
# ---------------------------------------------------------------------------

class TestDefaultProfiles:
    def test_h_dri_eaf_lower_co2_than_bf_bof(self):
        bf = TECHNOLOGY_PROFILES[SteelTechnology.BF_BOF]
        h_dri = TECHNOLOGY_PROFILES[SteelTechnology.H_DRI_EAF]
        assert h_dri.co2e_intensity_t_per_t < bf.co2e_intensity_t_per_t

    def test_scrap_eaf_lowest_energy(self):
        scrap = TECHNOLOGY_PROFILES[SteelTechnology.SCRAP_EAF]
        bf = TECHNOLOGY_PROFILES[SteelTechnology.BF_BOF]
        assert scrap.energy_intensity_GJ_per_t < bf.energy_intensity_GJ_per_t

    def test_h_dri_has_h2_demand(self):
        h_dri = TECHNOLOGY_PROFILES[SteelTechnology.H_DRI_EAF]
        assert h_dri.h2_demand_kg_per_t_dri > 0


# ---------------------------------------------------------------------------
# Calculation tests
# ---------------------------------------------------------------------------

class TestCalculate:
    def test_returns_result(self, calc, base_scenario):
        r = calc.calculate(base_scenario)
        assert r.plant_id == "KRAKATAU-01"

    def test_abatement_positive(self, calc, base_scenario):
        r = calc.calculate(base_scenario)
        assert r.abatement_per_t_steel > 0

    def test_green_steel_lower_co2_than_baseline(self, calc, base_scenario):
        r = calc.calculate(base_scenario)
        assert r.target_co2e_intensity < r.baseline_co2e_intensity

    def test_annual_abatement_proportional_to_capacity(self, calc):
        s1 = TransitionScenario("P1", 1.0, SteelTechnology.BF_BOF, SteelTechnology.H_DRI_EAF,
                                 2026, 2035)
        s2 = TransitionScenario("P2", 2.0, SteelTechnology.BF_BOF, SteelTechnology.H_DRI_EAF,
                                 2026, 2035)
        r1 = calc.calculate(s1)
        r2 = calc.calculate(s2)
        assert pytest.approx(r2.annual_abatement_MtCO2e, rel=0.01) == r1.annual_abatement_MtCO2e * 2

    def test_h2_demand_positive_for_h_dri(self, calc, base_scenario):
        r = calc.calculate(base_scenario)
        assert r.annual_h2_demand_kt > 0

    def test_no_h2_demand_for_bf_bof_ccs(self, calc):
        s = TransitionScenario("P1", 1.0, SteelTechnology.BF_BOF, SteelTechnology.BF_BOF_CCS,
                                2026, 2035)
        r = calc.calculate(s)
        assert r.annual_h2_demand_kt == 0.0

    def test_capex_positive(self, calc, base_scenario):
        r = calc.calculate(base_scenario)
        assert r.total_transition_capex_MUSD > 0

    def test_deployment_risk_not_empty(self, calc, base_scenario):
        r = calc.calculate(base_scenario)
        assert r.deployment_risk in ("LOW", "MEDIUM", "HIGH")

    def test_enablers_not_empty_for_h_dri(self, calc, base_scenario):
        r = calc.calculate(base_scenario)
        assert len(r.key_enablers) > 0

    def test_higher_h2_price_increases_cost_premium(self, calc):
        cheap = TransitionScenario("P1", 1.0, SteelTechnology.BF_BOF, SteelTechnology.H_DRI_EAF,
                                    2026, 2035, green_h2_cost_usd_per_kg=2.0)
        expensive = TransitionScenario("P2", 1.0, SteelTechnology.BF_BOF, SteelTechnology.H_DRI_EAF,
                                        2026, 2035, green_h2_cost_usd_per_kg=6.0)
        r_cheap = calc.calculate(cheap)
        r_expensive = calc.calculate(expensive)
        assert r_expensive.cost_premium_usd_per_t > r_cheap.cost_premium_usd_per_t

    def test_green_grid_lowers_effective_co2(self, calc):
        dirty_grid = TransitionScenario("P1", 1.0, SteelTechnology.BF_BOF,
                                         SteelTechnology.H_DRI_EAF, 2026, 2035,
                                         electricity_carbon_intensity=0.8)
        green_grid = TransitionScenario("P2", 1.0, SteelTechnology.BF_BOF,
                                         SteelTechnology.H_DRI_EAF, 2026, 2035,
                                         electricity_carbon_intensity=0.0)
        r_dirty = calc.calculate(dirty_grid)
        r_green = calc.calculate(green_grid)
        assert r_green.target_co2e_intensity < r_dirty.target_co2e_intensity


# ---------------------------------------------------------------------------
# Compare technologies tests
# ---------------------------------------------------------------------------

class TestCompareTechnologies:
    def test_returns_list(self, calc, base_scenario):
        results = calc.compare_technologies(base_scenario)
        assert isinstance(results, list)
        assert len(results) > 0

    def test_sorted_by_abatement_cost(self, calc, base_scenario):
        results = calc.compare_technologies(base_scenario)
        costs = [r.abatement_cost_usd_per_tCO2e for r in results]
        assert costs == sorted(costs)

    def test_custom_technology_list(self, calc, base_scenario):
        results = calc.compare_technologies(
            base_scenario,
            [SteelTechnology.SCRAP_EAF, SteelTechnology.BF_BOF_CCS]
        )
        assert len(results) == 2
