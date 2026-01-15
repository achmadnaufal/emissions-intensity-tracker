"""Unit tests for CarbonTaxExposureCalculator."""

import pytest
from src.carbon_tax_exposure_calculator import (
    CarbonTaxExposureCalculator,
    EmissionsProfile,
    ClimateScenario,
    CARBON_PRICE_TRAJECTORIES,
)


@pytest.fixture
def calc():
    return CarbonTaxExposureCalculator()


@pytest.fixture
def profile():
    return EmissionsProfile(
        operation_id="MINE-001",
        operation_name="Kalimantan Thermal Block",
        country="Indonesia",
        scope1_methane_tCO2e=85_000,
        scope1_combustion_tCO2e=35_000,
        scope2_tCO2e=20_000,
        scope3_coal_combustion_tCO2e=2_500_000,
        coal_production_tonnes=1_000_000,
        existing_carbon_tax_usd_per_tCO2e=5.0,
    )


class TestEmissionsProfile:
    def test_total_scope1_2(self, profile):
        assert profile.total_scope1_2_tCO2e == 140_000

    def test_net_regulated_with_offsets(self):
        p = EmissionsProfile(
            "X", "X", "X",
            scope1_methane_tCO2e=100_000,
            scope1_combustion_tCO2e=50_000,
            scope2_tCO2e=20_000,
            scope3_coal_combustion_tCO2e=0,
            current_offset_credits_tCO2e=30_000,
        )
        assert p.net_regulated_emissions == 140_000  # 170k - 30k

    def test_negative_scope1_raises(self):
        with pytest.raises(ValueError, match="scope1_methane_tCO2e"):
            EmissionsProfile("X", "X", "X", -100, 0, 0, 0)

    def test_negative_existing_tax_raises(self):
        with pytest.raises(ValueError, match="existing_carbon_tax_usd_per_tCO2e"):
            EmissionsProfile("X", "X", "X", 100, 100, 100, 0, existing_carbon_tax_usd_per_tCO2e=-5)


class TestCarbonTaxExposureCalculator:
    def test_basic_calculation(self, calc, profile):
        result = calc.calculate(profile, ClimateScenario.NZE_2050, 2030)
        assert result.scope1_2_exposure_usd > 0
        assert result.carbon_price_usd == 130.0

    def test_nze_more_expensive_than_steps(self, calc, profile):
        r_nze = calc.calculate(profile, ClimateScenario.NZE_2050, 2030)
        r_steps = calc.calculate(profile, ClimateScenario.STEPS, 2030)
        assert r_nze.total_exposure_usd > r_steps.total_exposure_usd

    def test_scope3_excluded_by_default(self, calc, profile):
        result = calc.calculate(profile, ClimateScenario.STEPS, 2030)
        assert result.scope3_exposure_usd == 0.0

    def test_scope3_included(self, profile):
        calc_s3 = CarbonTaxExposureCalculator(include_scope3=True)
        result = calc_s3.calculate(profile, ClimateScenario.STEPS, 2030)
        assert result.scope3_exposure_usd > 0

    def test_incremental_minus_existing_tax(self, calc, profile):
        result = calc.calculate(profile, ClimateScenario.NZE_2050, 2030)
        # existing paid = 140k * 5 = 700k; s1_2 exposure = 140k * 130 = 18.2M; incremental = 17.5M
        assert result.incremental_exposure_usd == pytest.approx(
            result.scope1_2_exposure_usd - result.existing_tax_already_paid_usd, rel=1e-4
        )

    def test_exposure_per_tonne_coal(self, calc, profile):
        result = calc.calculate(profile, ClimateScenario.STEPS, 2030)
        assert result.exposure_per_tonne_coal_usd is not None
        assert result.exposure_per_tonne_coal_usd > 0

    def test_no_production_none_cpu(self, calc):
        p = EmissionsProfile("X", "X", "X", 100_000, 50_000, 20_000, 0, coal_production_tonnes=0)
        result = calc.calculate(p, ClimateScenario.STEPS, 2030)
        assert result.exposure_per_tonne_coal_usd is None

    def test_year_interpolation(self, calc, profile):
        r_2025 = calc.calculate(profile, ClimateScenario.NZE_2050, 2025)
        r_2026 = calc.calculate(profile, ClimateScenario.NZE_2050, 2026)
        r_2027 = calc.calculate(profile, ClimateScenario.NZE_2050, 2027)
        # 2026 should be between 2025 and 2027
        assert r_2025.carbon_price_usd < r_2026.carbon_price_usd < r_2027.carbon_price_usd

    def test_year_out_of_range_raises(self, calc, profile):
        with pytest.raises(ValueError, match="year must be"):
            calc.calculate(profile, ClimateScenario.NZE_2050, 2070)

    def test_risk_level_set(self, calc, profile):
        result = calc.calculate(profile, ClimateScenario.NZE_2050, 2030)
        assert result.risk_level in ("low", "medium", "high", "critical")

    def test_scenario_comparison_four_results(self, calc, profile):
        results = calc.scenario_comparison(profile, 2030)
        assert len(results) == 4

    def test_multi_year_projection(self, calc, profile):
        years = [2025, 2030, 2035, 2040]
        results = calc.multi_year_projection(profile, ClimateScenario.NZE_2050, years)
        assert len(results) == 4
        # Prices should generally increase
        prices = [r.carbon_price_usd for r in results]
        assert prices == sorted(prices)

    def test_to_dict_keys(self, calc, profile):
        result = calc.calculate(profile, ClimateScenario.SDS, 2030)
        d = result.to_dict()
        assert "incremental_exposure_usd" in d
        assert "risk_level" in d
        assert "carbon_price_usd_per_tCO2e" in d

    def test_revenue_based_exposure_pct(self, profile):
        calc_rev = CarbonTaxExposureCalculator(coal_revenue_usd_per_tonne=100.0)
        result = calc_rev.calculate(profile, ClimateScenario.NZE_2050, 2030)
        assert result.exposure_as_pct_of_hypothetical_revenue is not None
        assert result.exposure_as_pct_of_hypothetical_revenue > 0

    def test_invalid_revenue_raises(self):
        with pytest.raises(ValueError, match="coal_revenue_usd_per_tonne"):
            CarbonTaxExposureCalculator(coal_revenue_usd_per_tonne=-50)

    def test_zero_scope1_zero_exposure(self, calc):
        p = EmissionsProfile("X", "X", "X", 0, 0, 0, 0)
        result = calc.calculate(p, ClimateScenario.NZE_2050, 2030)
        assert result.total_exposure_usd == 0.0
        assert result.incremental_exposure_usd == 0.0
