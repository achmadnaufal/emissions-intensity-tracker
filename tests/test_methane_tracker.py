"""
Unit tests for methane_tracker.py — IPCC Tier 2 CH₄ accounting for coal mining.
"""

import pytest
from src.methane_tracker import (
    MethaneEmissionsCalculator,
    AbatementOption,
    CH4_GWP,
    METHANE_DENSITY_T_PER_M3,
    M3_CH4_TO_TCO2E,
    DEFAULT_EF_UNDERGROUND,
    DEFAULT_EF_SURFACE,
)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def calc():
    return MethaneEmissionsCalculator()


@pytest.fixture
def high_gas_calc():
    return MethaneEmissionsCalculator(
        default_underground_ef=25.0,
        default_surface_ef=1.0,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test: Underground mining emissions
# ─────────────────────────────────────────────────────────────────────────────

class TestUndergroundMiningEmissions:
    """IPCC Tier 2 underground mining calculations."""

    def test_basic_underground_emissions(self, calc):
        """Standard underground mine with known production and methane content."""
        result = calc.calculate_mining_emissions(
            mine_type="underground",
            production_t=500_000,
            methane_content_m3_t=12.5,
            emission_factor=1.0,
        )
        # CH₄ (m³) = 500,000 × 12.5 = 6,250,000 m³
        # tCO₂e = 6,250,000 × 0.000715 × 28 = 125,125 tCO₂e
        expected = 500_000 * 12.5 * M3_CH4_TO_TCO2E
        assert result == pytest.approx(expected, rel=1e-9)

    def test_underground_emissions_with_default_ef(self, calc):
        """Uses default underground EF when no methane_content provided."""
        result = calc.calculate_mining_emissions(
            mine_type="underground",
            production_t=100_000,
            emission_factor=1.0,
        )
        expected = 100_000 * DEFAULT_EF_UNDERGROUND * M3_CH4_TO_TCO2E
        assert result == pytest.approx(expected, rel=1e-9)

    def test_underground_emissions_with_both_content_and_ef(self, calc):
        """When both methane_content and emission_factor are given, content wins."""
        result = calc.calculate_mining_emissions(
            mine_type="underground",
            production_t=200_000,
            methane_content_m3_t=5.0,
            emission_factor=0.8,
        )
        # Uses methane_content_m3_t, not emission_factor, as the MC value
        expected = 200_000 * 5.0 * M3_CH4_TO_TCO2E
        assert result == pytest.approx(expected, rel=1e-9)

    def test_underground_emissions_partial_emission_factor(self, calc):
        """Emission factor < 1 reduces effective emissions."""
        result_full = calc.calculate_mining_emissions(
            mine_type="underground",
            production_t=100_000,
            methane_content_m3_t=10.0,
            emission_factor=1.0,
        )
        result_half = calc.calculate_mining_emissions(
            mine_type="underground",
            production_t=100_000,
            methane_content_m3_t=5.0,  # content halved
            emission_factor=1.0,
        )
        assert result_half == pytest.approx(result_full * 0.5, rel=1e-9)

    def test_underground_emissions_high_gas_mine(self, high_gas_calc):
        """High-gas mine (25 m³/t) should have higher emissions."""
        result = high_gas_calc.calculate_mining_emissions(
            mine_type="underground",
            production_t=1_000_000,
            methane_content_m3_t=25.0,
        )
        expected = 1_000_000 * 25.0 * M3_CH4_TO_TCO2E
        assert result == pytest.approx(expected, rel=1e-9)


# ─────────────────────────────────────────────────────────────────────────────
# Test: Surface mining emissions
# ─────────────────────────────────────────────────────────────────────────────

class TestSurfaceMiningEmissions:
    """IPCC Tier 2 surface mining calculations."""

    def test_surface_emissions_lower_than_underground(self, calc):
        """Surface mining has much lower methane content per tonne."""
        ug_result = calc.calculate_mining_emissions(
            mine_type="underground",
            production_t=500_000,
            methane_content_m3_t=12.5,
        )
        surf_result = calc.calculate_mining_emissions(
            mine_type="surface",
            production_t=500_000,
            methane_content_m3_t=0.5,
        )
        assert surf_result < ug_result
        ratio = surf_result / ug_result
        assert ratio == pytest.approx(0.5 / 12.5, rel=1e-6)

    def test_surface_emissions_default_ef(self, calc):
        """Surface mining uses default surface EF."""
        result = calc.calculate_mining_emissions(
            mine_type="surface",
            production_t=1_000_000,
        )
        expected = 1_000_000 * DEFAULT_EF_SURFACE * M3_CH4_TO_TCO2E
        assert result == pytest.approx(expected, rel=1e-9)


# ─────────────────────────────────────────────────────────────────────────────
# Test: Mining emissions edge cases
# ─────────────────────────────────────────────────────────────────────────────

class TestMiningEmissionsEdgeCases:
    """Zero, negative, and invalid inputs."""

    def test_zero_production(self, calc):
        """Zero production should yield zero emissions."""
        result = calc.calculate_mining_emissions(
            mine_type="underground",
            production_t=0,
            methane_content_m3_t=12.5,
        )
        assert result == 0.0

    def test_zero_methane_content(self, calc):
        """Zero methane content = zero emissions."""
        result = calc.calculate_mining_emissions(
            mine_type="underground",
            production_t=500_000,
            methane_content_m3_t=0.0,
        )
        assert result == 0.0

    def test_negative_production_raises(self, calc):
        with pytest.raises(ValueError, match="cannot be negative"):
            calc.calculate_mining_emissions(
                mine_type="underground",
                production_t=-100,
                methane_content_m3_t=10.0,
            )

    def test_negative_methane_content_raises(self, calc):
        with pytest.raises(ValueError, match="cannot be negative"):
            calc.calculate_mining_emissions(
                mine_type="underground",
                production_t=500_000,
                methane_content_m3_t=-5.0,
            )

    def test_negative_emission_factor_raises(self, calc):
        with pytest.raises(ValueError, match="must be 0"):
            calc.calculate_mining_emissions(
                mine_type="underground",
                production_t=500_000,
                emission_factor=-0.1,
            )

    def test_emission_factor_over_1_raises(self, calc):
        with pytest.raises(ValueError, match="must be 0"):
            calc.calculate_mining_emissions(
                mine_type="underground",
                production_t=500_000,
                emission_factor=1.5,
            )

    def test_invalid_mine_type_raises(self, calc):
        with pytest.raises(ValueError, match="must be 'underground' or 'surface'"):
            calc.calculate_mining_emissions(
                mine_type="opencast",
                production_t=500_000,
                methane_content_m3_t=5.0,
            )


# ─────────────────────────────────────────────────────────────────────────────
# Test: Drainage emissions
# ─────────────────────────────────────────────────────────────────────────────

class TestDrainageEmissions:
    """Post-mining gas drainage + oxidation credit."""

    def test_drainage_100_percent(self, calc):
        """100% drainage with 0% oxidation = all CH₄ drained."""
        result = calc.calculate_drainage_emissions(
            production_t=100_000,
            drainage_pct=100.0,
            methane_content_m3_t=10.0,
            oxidation_efficiency_pct=0.0,
        )
        # All CH₄ drained, none emitted
        assert result["direct_ch4_tco2e"] == 0.0
        assert result["net_tco2e"] == 0.0

    def test_drainage_0_percent(self, calc):
        """0% drainage = all CH₄ released directly."""
        result = calc.calculate_drainage_emissions(
            production_t=100_000,
            drainage_pct=0.0,
            methane_content_m3_t=10.0,
        )
        total_ch4_m3 = 100_000 * 10.0
        expected_tco2e = total_ch4_m3 * M3_CH4_TO_TCO2E
        assert result["direct_ch4_tco2e"] == pytest.approx(expected_tco2e, rel=1e-9)
        assert result["net_tco2e"] == pytest.approx(expected_tco2e, rel=1e-9)

    def test_drainage_with_oxidation_credit(self, calc):
        """Drained CH₄ oxidized → lower net than undrained."""
        no_ox = calc.calculate_drainage_emissions(
            production_t=100_000,
            drainage_pct=50.0,
            methane_content_m3_t=10.0,
            oxidation_efficiency_pct=0.0,
        )
        with_ox = calc.calculate_drainage_emissions(
            production_t=100_000,
            drainage_pct=50.0,
            methane_content_m3_t=10.0,
            oxidation_efficiency_pct=100.0,
        )
        # Oxidation converts CH₄ → CO₂, which has lower GWP
        # So net_tco2e with oxidation < net without
        assert with_ox["net_tco2e"] < no_ox["net_tco2e"]

    def test_drainage_invalid_pct_raises(self, calc):
        with pytest.raises(ValueError, match="drainage_pct"):
            calc.calculate_drainage_emissions(
                production_t=100_000,
                drainage_pct=150.0,
                methane_content_m3_t=10.0,
            )


# ─────────────────────────────────────────────────────────────────────────────
# Test: VAM emissions
# ─────────────────────────────────────────────────────────────────────────────

class TestVAMEmissions:
    """Ventilation Air Methane calculations."""

    def test_vam_basic_calculation(self, calc):
        """VAM with 50 m³/s air flow, 2500 ppm CH₄."""
        result = calc.calculate_vam_emissions(
            air_flow_m3s=50.0,
            ch4_ppm=2500,
            operating_hours=8760,
        )
        # CH₄ fraction = 2500 / 1e6 = 0.0025
        # Annual air = 50 × 8760 × 3600 = 1,576,800,000 m³
        # CH₄ volume = 1,576,800,000 × 0.0025 = 3,942,000 m³
        annual_air = 50 * 8760 * 3600
        expected_m3 = annual_air * (2500 / 1_000_000)
        expected_tco2e = expected_m3 * M3_CH4_TO_TCO2E
        assert result["raw_vam_m3"] == pytest.approx(expected_m3, rel=1e-9)
        assert result["raw_vam_tco2e"] == pytest.approx(expected_tco2e, rel=1e-9)

    def test_vam_zero_ppm(self, calc):
        """Zero CH₄ concentration = zero emissions."""
        result = calc.calculate_vam_emissions(
            air_flow_m3s=50.0,
            ch4_ppm=0.0,
        )
        assert result["raw_vam_m3"] == 0.0
        assert result["raw_vam_tco2e"] == 0.0
        assert result["net_tco2e"] == 0.0

    def test_vam_with_capture(self, calc):
        """Capture system reduces net emissions."""
        no_capture = calc.calculate_vam_emissions(
            air_flow_m3s=100.0,
            ch4_ppm=5000,
        )
        with_capture = calc.calculate_vam_emissions(
            air_flow_m3s=100.0,
            ch4_ppm=5000,
            capture_efficiency_pct=90.0,
        )
        assert with_capture["net_tco2e"] < no_capture["net_tco2e"]

    def test_vam_zero_airflow(self, calc):
        """Zero airflow = zero emissions regardless of CH₄."""
        result = calc.calculate_vam_emissions(
            air_flow_m3s=0.0,
            ch4_ppm=5000,
        )
        assert result["raw_vam_m3"] == 0.0
        assert result["net_tco2e"] == 0.0

    def test_vam_invalid_capture_raises(self, calc):
        with pytest.raises(ValueError, match="capture_efficiency"):
            calc.calculate_vam_emissions(
                air_flow_m3s=50.0,
                ch4_ppm=2500,
                capture_efficiency_pct=120.0,
            )


# ─────────────────────────────────────────────────────────────────────────────
# Test: Cumulative emissions profile
# ─────────────────────────────────────────────────────────────────────────────

class TestCumulativeProfile:
    """Multi-year mine lifetime emissions."""

    def test_profile_length(self, calc):
        """Profile returns one entry per mine_age_years."""
        profile = calc.cumulative_emissions_profile(
            mine_type="underground",
            annual_production_t=[500_000],
            methane_content_m3_t=[12.5],
            mine_age_years=10,
        )
        assert len(profile) == 10

    def test_profile_uses_last_value_for_short_list(self, calc):
        """Short production list is extended with last value."""
        profile = calc.cumulative_emissions_profile(
            mine_type="underground",
            annual_production_t=[100_000, 200_000],  # only 2 years given
            methane_content_m3_t=[5.0],
            mine_age_years=4,
        )
        assert profile[0]["production_t"] == 100_000
        assert profile[1]["production_t"] == 200_000
        assert profile[2]["production_t"] == 200_000  # repeated
        assert profile[3]["production_t"] == 200_000  # repeated

    def test_profile_ramp_up(self, calc):
        """Profile captures production ramp-up."""
        profile = calc.cumulative_emissions_profile(
            mine_type="underground",
            annual_production_t=[100_000, 200_000, 300_000, 400_000, 500_000],
            methane_content_m3_t=[10.0],
            mine_age_years=5,
        )
        tco2e_vals = [p["tco2e"] for p in profile]
        assert tco2e_vals == sorted(tco2e_vals)  # strictly increasing

    def test_total_lifetime_emissions(self, calc):
        """total_lifetime_emissions = sum of profile."""
        profile = calc.cumulative_emissions_profile(
            mine_type="surface",
            annual_production_t=[1_000_000] * 20,
            methane_content_m3_t=[0.5],
            mine_age_years=20,
        )
        total = calc.total_lifetime_emissions(
            mine_type="surface",
            annual_production_t=[1_000_000] * 20,
            methane_content_m3_t=[0.5],
            mine_age_years=20,
        )
        assert total == pytest.approx(sum(p["tco2e"] for p in profile), rel=1e-9)

    def test_invalid_mine_age_raises(self, calc):
        with pytest.raises(ValueError, match="positive"):
            calc.cumulative_emissions_profile(
                mine_type="underground",
                annual_production_t=[100_000],
                methane_content_m3_t=[10.0],
                mine_age_years=0,
            )


# ─────────────────────────────────────────────────────────────────────────────
# Test: Abatement cost curve
# ─────────────────────────────────────────────────────────────────────────────

class TestAbatementCostCurve:
    """Abatement options and net emissions calculations."""

    def test_cost_curve_returns_options(self, calc):
        """ abatement_cost_curve returns a list of AbatementOption objects."""
        curve = calc.abatement_cost_curve()
        assert len(curve) >= 3
        assert all(isinstance(o, AbatementOption) for o in curve)

    def test_cost_curve_sorted_by_total_cost(self, calc):
        """Options should be sorted by levelised cost (lowest first)."""
        curve = calc.abatement_cost_curve()
        costs = [o.total_cost_usd_per_tco2e for o in curve]
        assert costs == sorted(costs)

    def test_abate_option_capture_efficiency(self, calc):
        """Each option has capture_efficiency between 0 and 100."""
        curve = calc.abatement_cost_curve()
        for opt in curve:
            assert 0 <= opt.capture_efficiency_pct <= 100

    def test_vam_oxidation_highest_capture(self, calc):
        """VAM oxidation should be one of the highest capture options."""
        curve = calc.abatement_cost_curve()
        vam = next(o for o in curve if "VAM" in o.name)
        assert vam.capture_efficiency_pct == 90.0


# ─────────────────────────────────────────────────────────────────────────────
# Test: Net emissions after abatement
# ─────────────────────────────────────────────────────────────────────────────

class TestNetEmissionsAfterAbatement:
    """Abatement efficiency applied to gross emissions."""

    def test_0_percent_abatement(self, calc):
        """0% abatement = gross emissions unchanged."""
        net = calc.net_emissions_after_abatement(1000.0, 0.0)
        assert net == 1000.0

    def test_50_percent_abatement(self, calc):
        """50% abatement halves net emissions."""
        net = calc.net_emissions_after_abatement(1000.0, 50.0)
        assert net == 500.0

    def test_100_percent_abatement(self, calc):
        """100% abatement = zero net."""
        net = calc.net_emissions_after_abatement(1000.0, 100.0)
        assert net == 0.0

    def test_abatement_over_100_capped(self, calc):
        """Abatement > 100% is capped at 100%."""
        net = calc.net_emissions_after_abatement(1000.0, 150.0)
        assert net == 0.0

    def test_negative_abatement_raises(self, calc):
        """Negative abatement efficiency raises ValueError."""
        with pytest.raises(ValueError, match="cannot be negative"):
            calc.net_emissions_after_abatement(1000.0, -10.0)

    def test_abatement_combined_with_underground(self, calc):
        """Full workflow: underground emissions → abatement."""
        gross = calc.calculate_mining_emissions(
            mine_type="underground",
            production_t=500_000,
            methane_content_m3_t=12.5,
        )
        # 60% abatement efficiency (e.g., drainage + VAM combined)
        net = calc.net_emissions_after_abatement(gross, 60.0)
        assert net == pytest.approx(gross * 0.4, rel=1e-9)


# ─────────────────────────────────────────────────────────────────────────────
# Test: Constants and utility methods
# ─────────────────────────────────────────────────────────────────────────────

class TestConstants:
    """Verify GWP and conversion constants."""

    def test_ch4_gwp_is_28(self):
        assert CH4_GWP == 28

    def test_m3_ch4_to_tco2e_calculation(self):
        # 1 m³ CH₄ × 0.000715 t/m³ × 28 GWP = 0.02002 tCO₂e
        expected = 1.0 * METHANE_DENSITY_T_PER_M3 * CH4_GWP
        assert M3_CH4_TO_TCO2E == pytest.approx(expected, rel=1e-9)

    def test_extend_list_exact_length(self, calc):
        result = calc._extend_list([1.0, 2.0, 3.0], 3)
        assert result == [1.0, 2.0, 3.0]

    def test_extend_list_shorter(self, calc):
        result = calc._extend_list([1.0, 2.0], 4)
        assert result == [1.0, 2.0, 2.0, 2.0]

    def test_extend_list_longer_truncates(self, calc):
        result = calc._extend_list([1.0, 2.0, 3.0, 4.0, 5.0], 3)
        assert result == [1.0, 2.0, 3.0]

    def test_extend_list_empty_raises(self, calc):
        with pytest.raises(ValueError, match="cannot be empty"):
            calc._extend_list([], 5)
