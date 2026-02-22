"""Unit tests for scope3_supply_chain_calculator module."""

import pytest
from src.scope3_supply_chain_calculator import (
    CoalCombustionEndUse,
    Scope3Result,
    Scope3SupplyChainCalculator,
    TransportLeg,
    TransportMode,
)


def _rail_leg(tonnage=8000, distance=120, load=0.85):
    return TransportLeg("mine-to-port", TransportMode.RAIL, distance, tonnage, load)


def _vessel_leg(tonnage=6000, distance=3800):
    return TransportLeg("port-to-India", TransportMode.BULK_CARRIER_LARGE, distance, tonnage)


def _coal_end_use(kt=6000, coal_type="subbituminous"):
    return CoalCombustionEndUse("India-power", coal_type, kt)


def _make_calc():
    return Scope3SupplyChainCalculator("Berau Coal", 2024)


class TestTransportLeg:
    def test_valid(self):
        leg = _rail_leg()
        assert leg.mode == TransportMode.RAIL

    def test_invalid_distance(self):
        with pytest.raises(ValueError):
            TransportLeg("x", TransportMode.RAIL, 0, 1000)

    def test_invalid_tonnage(self):
        with pytest.raises(ValueError):
            TransportLeg("x", TransportMode.RAIL, 100, -1)

    def test_invalid_load_factor(self):
        with pytest.raises(ValueError):
            TransportLeg("x", TransportMode.RAIL, 100, 1000, load_factor=0.1)

    def test_negative_custom_ef_raises(self):
        with pytest.raises(ValueError):
            TransportLeg("x", TransportMode.RAIL, 100, 1000, custom_ef_kg_co2e_tkm=-0.1)

    def test_emission_factor_adjusted_for_load(self):
        leg = TransportLeg("x", TransportMode.RAIL, 100, 1000, load_factor=0.5)
        # EF should be doubled at 50% load
        assert abs(leg.emission_factor - 0.028 / 0.5) < 0.001

    def test_annual_emissions_positive(self):
        leg = _rail_leg()
        assert leg.annual_emissions_t_co2e > 0

    def test_annual_emissions_custom_ef(self):
        leg = TransportLeg("x", TransportMode.RAIL, 100, 1000, custom_ef_kg_co2e_tkm=0.050)
        # kg CO2e/tkm × km × kt × 1000/1000 = t CO2e
        expected = 0.050 / 0.85 * 100 * 1000 * 1000 / 1000
        assert abs(leg.annual_emissions_t_co2e - expected) < 1


class TestCoalCombustionEndUse:
    def test_valid(self):
        e = _coal_end_use()
        assert e.coal_type == "subbituminous"

    def test_invalid_coal_type(self):
        with pytest.raises(ValueError):
            CoalCombustionEndUse("x", "peat", 1000)

    def test_invalid_tonnage(self):
        with pytest.raises(ValueError):
            CoalCombustionEndUse("x", "bituminous", 0)

    def test_invalid_efficiency(self):
        with pytest.raises(ValueError):
            CoalCombustionEndUse("x", "bituminous", 1000, combustion_efficiency_pct=10)

    def test_custom_ef_overrides_default(self):
        e = CoalCombustionEndUse("x", "bituminous", 1000, custom_ef_t_co2e_per_t=3.0)
        assert e.emission_factor == 3.0

    def test_annual_emissions_calculated(self):
        e = _coal_end_use(kt=1000, coal_type="bituminous")
        # 1000 kt × 2.42 t CO2e/t = 2,420,000 t CO2e
        assert abs(e.annual_emissions_t_co2e - 2_420_000) < 1000


class TestScope3SupplyChainCalculator:
    def test_raises_if_no_inputs(self):
        calc = _make_calc()
        with pytest.raises(ValueError):
            calc.calculate()

    def test_add_invalid_upstream_leg(self):
        calc = _make_calc()
        with pytest.raises(TypeError):
            calc.add_upstream_leg("not a leg")

    def test_add_invalid_downstream_leg(self):
        calc = _make_calc()
        with pytest.raises(TypeError):
            calc.add_downstream_leg(42)

    def test_add_invalid_end_use(self):
        calc = _make_calc()
        with pytest.raises(TypeError):
            calc.add_end_use({"coal": "bituminous"})

    def test_cat4_computed(self):
        calc = _make_calc()
        calc.add_upstream_leg(_rail_leg())
        result = calc.calculate()
        assert result.cat4_upstream_transport_t_co2e > 0

    def test_cat9_computed(self):
        calc = _make_calc()
        calc.add_downstream_leg(_vessel_leg())
        result = calc.calculate()
        assert result.cat9_downstream_transport_t_co2e > 0

    def test_cat11_computed(self):
        calc = _make_calc()
        calc.add_end_use(_coal_end_use())
        result = calc.calculate()
        assert result.cat11_coal_combustion_t_co2e > 0

    def test_total_is_sum_of_categories(self):
        calc = _make_calc()
        calc.add_upstream_leg(_rail_leg())
        calc.add_downstream_leg(_vessel_leg())
        calc.add_end_use(_coal_end_use())
        result = calc.calculate()
        expected = (
            result.cat4_upstream_transport_t_co2e
            + result.cat9_downstream_transport_t_co2e
            + result.cat11_coal_combustion_t_co2e
        )
        assert abs(result.total_scope3_t_co2e - expected) < 1

    def test_cat11_dominates(self):
        calc = _make_calc()
        calc.add_upstream_leg(_rail_leg(tonnage=500, distance=100))
        calc.add_downstream_leg(_vessel_leg(tonnage=500, distance=100))
        calc.add_end_use(_coal_end_use(kt=5000))
        result = calc.calculate()
        assert result.largest_category == "cat11_coal_combustion"

    def test_intensity_computed(self):
        calc = _make_calc()
        calc.add_end_use(_coal_end_use(kt=1000))
        result = calc.calculate()
        assert result.intensity_t_co2e_per_t_coal > 0

    def test_reduction_opportunities_listed(self):
        calc = _make_calc()
        calc.add_end_use(_coal_end_use(kt=5000))
        result = calc.calculate()
        assert len(result.reduction_opportunities) > 0

    def test_road_hgv_triggers_rail_recommendation(self):
        calc = _make_calc()
        calc.add_upstream_leg(TransportLeg("truck", TransportMode.ROAD_HGV, 100, 500))
        result = calc.calculate()
        recs = " ".join(result.reduction_opportunities)
        assert "rail" in recs.lower() or "Rail" in recs

    def test_multiple_end_uses_summed(self):
        calc = _make_calc()
        calc.add_end_use(_coal_end_use(kt=3000, coal_type="bituminous"))
        calc.add_end_use(_coal_end_use(kt=2000, coal_type="subbituminous"))
        result = calc.calculate()
        expected_cat11 = 3000 * 1000 * 2.42 + 2000 * 1000 * 1.85
        assert abs(result.cat11_coal_combustion_t_co2e - expected_cat11) < 100

    def test_transport_intensity_computed(self):
        calc = _make_calc()
        calc.add_upstream_leg(_rail_leg())
        calc.add_end_use(_coal_end_use(kt=8000))
        intensity = calc.transport_intensity_tkm_per_t()
        assert "upstream" in intensity
        assert "downstream" in intensity
        assert intensity["upstream"] > 0

    def test_result_type(self):
        calc = _make_calc()
        calc.add_end_use(_coal_end_use())
        result = calc.calculate()
        assert isinstance(result, Scope3Result)

    def test_company_id_and_year_in_result(self):
        calc = Scope3SupplyChainCalculator("TestCorp", 2025)
        calc.add_end_use(_coal_end_use())
        result = calc.calculate()
        assert result.company_id == "TestCorp"
        assert result.reporting_year == 2025
