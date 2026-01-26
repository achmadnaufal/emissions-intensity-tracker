"""Unit tests for ScienceBasedTargetsValidator."""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from sbti_targets_validator import (
    ScienceBasedTargetsValidator,
    CompanyEmissionsProfile,
    EmissionsTarget,
    ScopeType,
    SBTiScenario,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_profile(
    scope1=500_000,
    scope2=80_000,
    scope3=0,
    targets=None,
    company_id="TEST_001",
) -> CompanyEmissionsProfile:
    return CompanyEmissionsProfile(
        company_id=company_id,
        company_name="Test Corp",
        sector="Coal Mining",
        reporting_year=2023,
        scope1_tco2e=scope1,
        scope2_market_tco2e=scope2,
        scope3_total_tco2e=scope3,
        targets=targets or [],
    )


def make_target(
    scope=ScopeType.SCOPE_1,
    base_year=2019,
    base_emissions=500_000,
    target_year=2030,
    reduction_pct=45.0,
    scenario=SBTiScenario.ONE_POINT_5C,
    methodology="ACA",
    includes_offsets=False,
) -> EmissionsTarget:
    return EmissionsTarget(
        scope=scope,
        base_year=base_year,
        base_year_emissions_tco2e=base_emissions,
        target_year=target_year,
        target_reduction_pct=reduction_pct,
        scenario=scenario,
        methodology=methodology,
        includes_offsets=includes_offsets,
    )


# ---------------------------------------------------------------------------
# Test EmissionsTarget
# ---------------------------------------------------------------------------

class TestEmissionsTarget:
    def test_horizon_years(self):
        tgt = make_target(base_year=2019, target_year=2030)
        assert tgt.horizon_years == 11

    def test_implied_annual_reduction(self):
        tgt = make_target(base_year=2019, target_year=2030, reduction_pct=77.0)
        assert abs(tgt.implied_annual_reduction_pct - 7.0) < 0.01

    def test_target_absolute_tco2e(self):
        tgt = make_target(base_emissions=1_000_000, reduction_pct=50)
        assert tgt.target_absolute_tco2e == 500_000.0

    def test_invalid_base_emissions_raises(self):
        with pytest.raises(ValueError, match="positive"):
            make_target(base_emissions=-1)

    def test_invalid_reduction_pct_raises(self):
        with pytest.raises(ValueError):
            make_target(reduction_pct=0)

    def test_target_year_before_base_raises(self):
        with pytest.raises(ValueError, match="after base_year"):
            make_target(base_year=2025, target_year=2020)

    def test_invalid_methodology_raises(self):
        with pytest.raises(ValueError, match="methodology"):
            make_target(methodology="INVALID")


# ---------------------------------------------------------------------------
# Test CompanyEmissionsProfile
# ---------------------------------------------------------------------------

class TestCompanyEmissionsProfile:
    def test_total_emissions(self):
        p = make_profile(scope1=100, scope2=50, scope3=200)
        assert p.total_emissions_tco2e == 350

    def test_scope3_materiality_pct(self):
        p = make_profile(scope1=100, scope2=50, scope3=200)
        assert abs(p.scope3_materiality_pct - 57.14) < 0.01

    def test_scope3_not_material(self):
        p = make_profile(scope1=500_000, scope2=80_000, scope3=10_000)
        assert not p.scope3_is_material

    def test_scope3_is_material(self):
        p = make_profile(scope1=100_000, scope2=50_000, scope3=500_000)
        assert p.scope3_is_material

    def test_negative_scope1_raises(self):
        with pytest.raises(ValueError):
            make_profile(scope1=-1)


# ---------------------------------------------------------------------------
# Test ScienceBasedTargetsValidator — valid cases
# ---------------------------------------------------------------------------

class TestValidatorApproved:
    def setup_method(self):
        self.validator = ScienceBasedTargetsValidator()

    def test_1_5c_aligned_target_approved(self):
        # 45% reduction over 10 years = 4.5%/yr (meets Well-Below-2C at 4.2%/yr minimum)
        tgt = make_target(reduction_pct=50, scenario=SBTiScenario.WELL_BELOW_2C)
        profile = make_profile(targets=[tgt])
        result = self.validator.validate(profile)
        assert result.near_term_aligned is True
        assert result.overall_status in ("APPROVED", "CONDITIONAL")

    def test_no_scope1_target_rejected(self):
        profile = make_profile(targets=[])
        result = self.validator.validate(profile)
        assert result.overall_status == "REJECTED"
        codes = [f.code for f in result.flags]
        assert "NO_SCOPE12_TARGET" in codes

    def test_insufficient_reduction_rate_fails(self):
        # 20% over 10 years = 2%/yr — below Well-Below-2C (4.2%/yr)
        tgt = make_target(reduction_pct=20, scenario=SBTiScenario.WELL_BELOW_2C)
        profile = make_profile(targets=[tgt])
        result = self.validator.validate(profile)
        fail_codes = [f.code for f in result.flags if f.severity == "FAIL"]
        assert "NEAR_TERM_TARGET_INSUFFICIENT" in fail_codes

    def test_scope3_material_no_target_conditional(self):
        # Scope 3 > 40% of total → target required
        tgt = make_target(reduction_pct=50, scenario=SBTiScenario.WELL_BELOW_2C)
        profile = make_profile(scope1=100_000, scope2=50_000, scope3=500_000, targets=[tgt])
        result = self.validator.validate(profile)
        assert result.scope3_coverage_ok is False
        fail_codes = [f.code for f in result.flags if f.severity == "FAIL"]
        assert "MISSING_SCOPE3_TARGET" in fail_codes

    def test_net_zero_target_90pct_passes(self):
        nz = make_target(reduction_pct=92, scenario=SBTiScenario.NET_ZERO, target_year=2050)
        s12 = make_target(reduction_pct=50, scenario=SBTiScenario.WELL_BELOW_2C)
        profile = make_profile(targets=[s12, nz])
        result = self.validator.validate(profile)
        assert result.net_zero_aligned is True
        codes = [f.code for f in result.flags]
        assert "NET_ZERO_TARGET_VALID" in codes

    def test_net_zero_below_90pct_fails(self):
        nz = make_target(reduction_pct=70, scenario=SBTiScenario.NET_ZERO, target_year=2050)
        s12 = make_target(reduction_pct=50, scenario=SBTiScenario.WELL_BELOW_2C)
        profile = make_profile(targets=[s12, nz])
        result = self.validator.validate(profile)
        codes = [f.code for f in result.flags if f.severity == "FAIL"]
        assert "NET_ZERO_TARGET_INSUFFICIENT" in codes

    def test_offset_reliance_warning(self):
        tgt = make_target(reduction_pct=50, scenario=SBTiScenario.WELL_BELOW_2C, includes_offsets=True)
        profile = make_profile(targets=[tgt])
        result = self.validator.validate(profile)
        warn_codes = [f.code for f in result.flags if f.severity == "WARNING"]
        assert "OFFSET_RELIANCE" in warn_codes

    def test_batch_validate_multiple_profiles(self):
        tgt = make_target(reduction_pct=50, scenario=SBTiScenario.WELL_BELOW_2C)
        profiles = [
            make_profile(targets=[tgt], company_id="A"),
            make_profile(targets=[], company_id="B"),
            make_profile(targets=[tgt], company_id="C"),
        ]
        results = self.validator.batch_validate(profiles)
        assert len(results) == 3
        assert results[1].overall_status == "REJECTED"

    def test_batch_empty_raises(self):
        with pytest.raises(ValueError, match="empty"):
            self.validator.batch_validate([])

    def test_summary_report(self):
        tgt = make_target(reduction_pct=50, scenario=SBTiScenario.WELL_BELOW_2C)
        profiles = [
            make_profile(targets=[tgt], company_id="A"),
            make_profile(targets=[], company_id="B"),
        ]
        results = self.validator.batch_validate(profiles)
        report = self.validator.summary_report(results)
        assert report["total_companies"] == 2
        assert report["rejected_count"] == 1

    def test_invalid_profile_type_raises(self):
        with pytest.raises(TypeError):
            self.validator.validate({"company": "bad"})

    def test_horizon_too_short_flag(self):
        tgt = make_target(base_year=2022, target_year=2024, reduction_pct=20)
        profile = make_profile(targets=[tgt])
        result = self.validator.validate(profile)
        codes = [f.code for f in result.flags if f.severity == "FAIL"]
        assert "TARGET_HORIZON_TOO_SHORT" in codes
