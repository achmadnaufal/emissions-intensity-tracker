"""
Unit tests for Scope3UpstreamCalculator.
"""

import pytest
from src.calculations.scope3_upstream import Scope3UpstreamCalculator, UpstreamEmissionsResult


@pytest.fixture
def calc():
    return Scope3UpstreamCalculator("Sangatta Mine", "2025-FY")


BASE_KWARGS = dict(
    coal_production_tonnes=2_500_000,
    anfo_consumed_kg=850_000,
    diesel_upstream_liters=4_200_000,
    tyre_mass_kg=18_000,
    steel_mass_kg=95_000,
    road_freight_tonne_km=320_000,
    rail_freight_tonne_km=1_800_000,
)


class TestInit:
    def test_empty_operation_name_raises(self):
        with pytest.raises(ValueError, match="operation_name"):
            Scope3UpstreamCalculator("  ")

    def test_valid_init(self):
        c = Scope3UpstreamCalculator("Mine A", "2025")
        assert c.operation_name == "Mine A"


class TestCalculate:
    def test_returns_result_type(self, calc):
        result = calc.calculate(**BASE_KWARGS)
        assert isinstance(result, UpstreamEmissionsResult)

    def test_total_equals_sum_of_categories(self, calc):
        r = calc.calculate(**BASE_KWARGS)
        expected = (
            r.cat1_purchased_goods_tco2e
            + r.cat2_capital_goods_tco2e
            + r.cat3_fuel_energy_tco2e
            + r.cat4_upstream_transport_tco2e
        )
        assert r.total_upstream_tco2e == pytest.approx(expected, abs=0.01)

    def test_zero_inputs_zero_emissions(self, calc):
        r = calc.calculate(coal_production_tonnes=1_000_000)
        assert r.total_upstream_tco2e == 0.0

    def test_negative_coal_raises(self, calc):
        with pytest.raises(ValueError, match="coal_production_tonnes"):
            calc.calculate(coal_production_tonnes=-1)

    def test_negative_anfo_raises(self, calc):
        with pytest.raises(ValueError, match="anfo_consumed_kg"):
            calc.calculate(coal_production_tonnes=1_000_000, anfo_consumed_kg=-100)

    def test_intensity_calculation(self, calc):
        r = calc.calculate(**BASE_KWARGS)
        expected_intensity = r.total_upstream_tco2e / BASE_KWARGS["coal_production_tonnes"]
        assert r.intensity_tco2e_per_tonne_coal == pytest.approx(expected_intensity, rel=1e-4)

    def test_cat4_transport_sum(self, calc):
        r = calc.calculate(
            coal_production_tonnes=1_000_000,
            road_freight_tonne_km=1_000_000,
            rail_freight_tonne_km=1_000_000,
        )
        # road: 1_000_000 * 0.096 / 1000 = 96 tCO2e
        # rail: 1_000_000 * 0.028 / 1000 = 28 tCO2e
        assert r.cat4_upstream_transport_tco2e == pytest.approx(124.0, abs=0.1)


class TestBenchmark:
    def test_above_average_rating(self, calc):
        r = calc.calculate(**BASE_KWARGS)
        # Force a high-intensity result by using a very low coal production
        r2 = calc.calculate(
            coal_production_tonnes=10_000,
            anfo_consumed_kg=500_000,
        )
        bm = calc.benchmark(r2, industry_avg_intensity=0.015)
        assert bm["rating"] == "above_average"

    def test_below_average_rating(self, calc):
        r_low = calc.calculate(
            coal_production_tonnes=10_000_000,
            anfo_consumed_kg=100,
        )
        bm = calc.benchmark(r_low, industry_avg_intensity=0.015)
        assert bm["rating"] == "below_average"

    def test_invalid_benchmark_raises(self, calc):
        r = calc.calculate(**BASE_KWARGS)
        with pytest.raises(ValueError, match="industry_avg_intensity"):
            calc.benchmark(r, industry_avg_intensity=0)
