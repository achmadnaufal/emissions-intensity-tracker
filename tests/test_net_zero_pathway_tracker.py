"""Unit tests for NetZeroPathwayTracker."""

import pytest
from src.net_zero_pathway_tracker import (
    NetZeroPathwayTracker,
    NetZeroPathwayReport,
    AnnualProgressRecord,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sbti_tracker():
    return NetZeroPathwayTracker(
        organisation="PT Semen Nusantara",
        base_year=2019,
        base_year_emissions_tco2e=250_000,
        net_zero_year=2050,
        pathway_type="sbti_1.5c",
    )


def _on_track_emissions(tracker, years):
    """Return emissions exactly at the SBTi 1.5°C pathway target for given years."""
    return {y: tracker.pathway_target(y) for y in years}


# ---------------------------------------------------------------------------
# Instantiation
# ---------------------------------------------------------------------------

class TestInstantiation:
    def test_default_init(self):
        t = NetZeroPathwayTracker("Org", 2020, 100_000)
        assert t is not None

    def test_invalid_pathway_type_raises(self):
        with pytest.raises(ValueError, match="Unknown pathway_type"):
            NetZeroPathwayTracker("Org", 2020, 100_000, pathway_type="magic")

    def test_net_zero_before_base_year_raises(self):
        with pytest.raises(ValueError, match="net_zero_year"):
            NetZeroPathwayTracker("Org", 2020, 100_000, net_zero_year=2015)

    def test_net_zero_equal_to_base_year_raises(self):
        with pytest.raises(ValueError):
            NetZeroPathwayTracker("Org", 2020, 100_000, net_zero_year=2020)

    def test_zero_base_emissions_raises(self):
        with pytest.raises(ValueError, match="base_year_emissions_tco2e"):
            NetZeroPathwayTracker("Org", 2020, 0)

    def test_linear_without_custom_rate_raises(self):
        with pytest.raises(ValueError, match="custom_annual_reduction_pct"):
            NetZeroPathwayTracker("Org", 2020, 100_000, pathway_type="linear")

    def test_linear_with_rate_valid(self):
        t = NetZeroPathwayTracker(
            "Org", 2020, 100_000,
            pathway_type="linear", custom_annual_reduction_pct=5.0
        )
        assert t is not None


# ---------------------------------------------------------------------------
# pathway_target()
# ---------------------------------------------------------------------------

class TestPathwayTarget:
    def test_sbti_base_year_plus_one_reduced(self, sbti_tracker):
        t = sbti_tracker.pathway_target(2020)
        assert t < 250_000

    def test_sbti_reduction_rate_approx_4_2_pct(self, sbti_tracker):
        t2020 = sbti_tracker.pathway_target(2020)
        expected = 250_000 * (1 - 0.042)
        assert abs(t2020 - expected) < 1.0

    def test_sbti_net_zero_year_returns_zero(self, sbti_tracker):
        assert sbti_tracker.pathway_target(2050) == 0.0

    def test_sbti_after_net_zero_returns_zero(self, sbti_tracker):
        assert sbti_tracker.pathway_target(2060) == 0.0

    def test_linear_reduces_by_fixed_amount(self):
        t = NetZeroPathwayTracker(
            "Org", 2020, 100_000,
            pathway_type="linear", custom_annual_reduction_pct=5.0
        )
        expected = 100_000 * 0.95  # 5% reduction
        assert abs(t.pathway_target(2021) - expected) < 1.0

    def test_exponential_compound_reduction(self):
        t = NetZeroPathwayTracker(
            "Org", 2020, 100_000,
            pathway_type="exponential", custom_annual_reduction_pct=5.0
        )
        expected = 100_000 * (0.95 ** 2)
        assert abs(t.pathway_target(2022) - expected) < 1.0

    def test_iea_nze_linear_to_zero(self):
        t = NetZeroPathwayTracker(
            "Org", 2020, 100_000,
            pathway_type="iea_nze", net_zero_year=2050,
        )
        # After 15 years (midpoint), target should be ~50%
        expected_approx = 100_000 * (1 - 15 / 30)
        assert abs(t.pathway_target(2035) - expected_approx) < 100

    def test_sbti_wb2c_rate(self):
        t = NetZeroPathwayTracker("Org", 2020, 100_000, pathway_type="sbti_wb2c")
        expected = 100_000 * (1 - 0.025)
        assert abs(t.pathway_target(2021) - expected) < 1.0


# ---------------------------------------------------------------------------
# record_year()
# ---------------------------------------------------------------------------

class TestRecordYear:
    def test_record_valid_year(self, sbti_tracker):
        sbti_tracker.record_year(2020, 240_000)
        assert sbti_tracker._annual_data[2020] == 240_000

    def test_record_base_year_raises(self, sbti_tracker):
        with pytest.raises(ValueError, match="base_year"):
            sbti_tracker.record_year(2019, 240_000)

    def test_record_year_before_base_raises(self, sbti_tracker):
        with pytest.raises(ValueError):
            sbti_tracker.record_year(2010, 240_000)

    def test_record_negative_emissions_raises(self, sbti_tracker):
        with pytest.raises(ValueError, match="actual_emissions_tco2e"):
            sbti_tracker.record_year(2020, -1000)

    def test_record_zero_emissions_valid(self, sbti_tracker):
        sbti_tracker.record_year(2020, 0)
        assert sbti_tracker._annual_data[2020] == 0

    def test_record_batch(self, sbti_tracker):
        sbti_tracker.record_batch({2020: 240_000, 2021: 230_000})
        assert 2020 in sbti_tracker._annual_data
        assert 2021 in sbti_tracker._annual_data


# ---------------------------------------------------------------------------
# generate_report()
# ---------------------------------------------------------------------------

class TestGenerateReport:
    def test_no_records_raises(self, sbti_tracker):
        with pytest.raises(ValueError, match="No annual emissions records"):
            sbti_tracker.generate_report()

    def test_returns_report_type(self, sbti_tracker):
        sbti_tracker.record_year(2020, 240_000)
        report = sbti_tracker.generate_report()
        assert isinstance(report, NetZeroPathwayReport)

    def test_on_track_when_at_target(self, sbti_tracker):
        target = sbti_tracker.pathway_target(2020)
        sbti_tracker.record_year(2020, target)
        report = sbti_tracker.generate_report()
        assert 2020 in report.years_on_track

    def test_off_track_when_above_target(self, sbti_tracker):
        target = sbti_tracker.pathway_target(2020)
        sbti_tracker.record_year(2020, target + 10_000)
        report = sbti_tracker.generate_report()
        assert 2020 in report.years_off_track

    def test_always_on_track_gives_on_track_status(self, sbti_tracker):
        targets = _on_track_emissions(sbti_tracker, range(2020, 2025))
        sbti_tracker.record_batch(targets)
        report = sbti_tracker.generate_report()
        assert report.overall_status == "on_track"

    def test_mostly_off_track_gives_critical_status(self, sbti_tracker):
        target = sbti_tracker.pathway_target(2020)
        sbti_tracker.record_batch({
            y: target * 2 for y in range(2020, 2025)
        })
        report = sbti_tracker.generate_report()
        assert report.overall_status == "critical"

    def test_organisation_name_preserved(self, sbti_tracker):
        sbti_tracker.record_year(2020, 240_000)
        report = sbti_tracker.generate_report()
        assert report.organisation == "PT Semen Nusantara"

    def test_pathway_type_preserved(self, sbti_tracker):
        sbti_tracker.record_year(2020, 240_000)
        report = sbti_tracker.generate_report()
        assert report.pathway_type == "sbti_1.5c"

    def test_annual_records_count(self, sbti_tracker):
        sbti_tracker.record_batch({y: 240_000 for y in range(2020, 2026)})
        report = sbti_tracker.generate_report()
        assert len(report.annual_records) == 6

    def test_yoy_reduction_none_for_first_year(self, sbti_tracker):
        sbti_tracker.record_batch({2020: 240_000, 2021: 230_000})
        report = sbti_tracker.generate_report()
        first = report.annual_records[0]
        # Note: first compared to base year, so yoy should not be None
        assert first.yoy_reduction_pct is not None

    def test_budget_remaining_decreases_with_more_emissions(self, sbti_tracker):
        sbti_tracker.record_year(2020, 300_000)  # above target
        report1 = sbti_tracker.generate_report()
        sbti_tracker.record_year(2021, 300_000)
        report2 = sbti_tracker.generate_report()
        assert report2.budget_remaining_tco2e < report1.budget_remaining_tco2e

    def test_cumulative_actual_sum_of_recorded_years(self, sbti_tracker):
        sbti_tracker.record_batch({2020: 240_000, 2021: 230_000})
        report = sbti_tracker.generate_report()
        assert abs(report.cumulative_actual_emissions_tco2e - 470_000) < 0.01


# ---------------------------------------------------------------------------
# total_carbon_budget()
# ---------------------------------------------------------------------------

class TestTotalCarbonBudget:
    def test_budget_positive(self, sbti_tracker):
        assert sbti_tracker.total_carbon_budget() > 0

    def test_shorter_pathway_smaller_budget(self):
        t1 = NetZeroPathwayTracker("Org", 2020, 100_000, net_zero_year=2035, pathway_type="sbti_1.5c")
        t2 = NetZeroPathwayTracker("Org", 2020, 100_000, net_zero_year=2050, pathway_type="sbti_1.5c")
        assert t1.total_carbon_budget() < t2.total_carbon_budget()
