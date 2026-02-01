"""
Net Zero Pathway Tracker.

Tracks an organisation's annual emissions against a science-based net zero
pathway and quantifies annual progress, cumulative carbon budget consumption,
required reduction rate, and remaining carbon budget.

Supported pathway types:
- **Linear**: Constant absolute reduction per year.
- **Exponential**: Constant percentage reduction per year (compound).
- **SBTi 1.5°C**: Science Based Targets initiative 1.5°C well-below pathway
  using a 4.2% year-on-year absolute reduction (SBTi Corporate Net-Zero
  Standard, 2021).
- **IEA NZE**: IEA Net Zero Emissions by 2050 Scenario; linear reduction
  from base year to net zero in 2050.

References:
- SBTi Corporate Net-Zero Standard v1.1 (2021)
- IEA World Energy Outlook 2023 — Net Zero Emissions Scenario
- GHG Protocol — Corporate Standard (Revised 2015)
- IPCC AR6 Carbon Budget Assessment (2021)

Author: github.com/achmadnaufal
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SBTI_1_5C_ANNUAL_REDUCTION_RATE = 0.042      # 4.2% per year (absolute)
_SBTI_WELL_BELOW_2C_ANNUAL_REDUCTION_RATE = 0.025  # 2.5% per year

_PATHWAY_TYPES = {"linear", "exponential", "sbti_1.5c", "sbti_wb2c", "iea_nze"}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class AnnualProgressRecord:
    """Emissions progress snapshot for a single reporting year.

    Attributes:
        year: Reporting year (YYYY).
        actual_emissions_tco2e: Reported gross emissions in tCO2e.
        pathway_target_tco2e: Pathway budget for this year in tCO2e.
        gap_tco2e: Actual minus target (positive = overrun, negative = ahead).
        on_track: True when actual ≤ pathway target.
        yoy_reduction_pct: Year-on-year emissions reduction % (None for base year).
        required_reduction_rate_pct: Constant % reduction needed each remaining
            year to reach net zero from current emissions.
        cumulative_budget_consumed_pct: % of total carbon budget used to date.
    """

    year: int
    actual_emissions_tco2e: float
    pathway_target_tco2e: float
    gap_tco2e: float
    on_track: bool
    yoy_reduction_pct: Optional[float]
    required_reduction_rate_pct: float
    cumulative_budget_consumed_pct: float


@dataclass
class NetZeroPathwayReport:
    """Full net zero pathway tracking report.

    Attributes:
        organisation: Organisation name.
        base_year: Emissions baseline year.
        net_zero_year: Target year for net zero.
        pathway_type: Pathway methodology applied.
        base_year_emissions_tco2e: Baseline gross emissions in tCO2e.
        total_carbon_budget_tco2e: Total allowable cumulative emissions
            from base year to net zero year.
        cumulative_actual_emissions_tco2e: Total reported emissions to date.
        years_on_track: List of years where actual ≤ target.
        years_off_track: List of years where actual > target.
        on_track_rate_pct: % of reported years that met the pathway target.
        annual_records: Per-year progress detail.
        overall_status: 'on_track', 'lagging', or 'critical'.
        budget_remaining_tco2e: Remaining carbon budget.
        implied_net_zero_year: Projected net zero year at current pace
            (extrapolated from last reported year).
    """

    organisation: str
    base_year: int
    net_zero_year: int
    pathway_type: str
    base_year_emissions_tco2e: float
    total_carbon_budget_tco2e: float
    cumulative_actual_emissions_tco2e: float
    years_on_track: List[int]
    years_off_track: List[int]
    on_track_rate_pct: float
    annual_records: List[AnnualProgressRecord]
    overall_status: str
    budget_remaining_tco2e: float
    implied_net_zero_year: Optional[int]


class NetZeroPathwayTracker:
    """Tracks corporate emissions against a net zero reduction pathway.

    Args:
        organisation: Name of the organisation being tracked.
        base_year: Baseline year for emissions (e.g. 2020).
        base_year_emissions_tco2e: Baseline gross emissions in tCO2e.
        net_zero_year: Target year for net zero achievement. Default 2050.
        pathway_type: One of 'linear', 'exponential', 'sbti_1.5c',
            'sbti_wb2c', 'iea_nze'. Default 'sbti_1.5c'.
        custom_annual_reduction_pct: Required only for 'linear' and
            'exponential' pathway types; ignored for SBTi/IEA pathways.

    Raises:
        ValueError: On invalid pathway type, net zero year before base year,
            or missing custom reduction rate for custom pathway types.

    Example::

        tracker = NetZeroPathwayTracker(
            organisation="PT Semen Nusantara",
            base_year=2019,
            base_year_emissions_tco2e=250_000,
            net_zero_year=2050,
            pathway_type="sbti_1.5c",
        )
        tracker.record_year(2020, 245_000)
        tracker.record_year(2021, 238_000)
        tracker.record_year(2022, 229_000)
        report = tracker.generate_report()
        print(report.overall_status)       # 'on_track' / 'lagging' / 'critical'
        print(report.on_track_rate_pct)    # % of years meeting target
    """

    def __init__(
        self,
        organisation: str,
        base_year: int,
        base_year_emissions_tco2e: float,
        net_zero_year: int = 2050,
        pathway_type: str = "sbti_1.5c",
        custom_annual_reduction_pct: Optional[float] = None,
    ) -> None:
        if pathway_type not in _PATHWAY_TYPES:
            raise ValueError(
                f"Unknown pathway_type '{pathway_type}'. "
                f"Valid options: {sorted(_PATHWAY_TYPES)}"
            )
        if net_zero_year <= base_year:
            raise ValueError(
                f"net_zero_year ({net_zero_year}) must be after base_year ({base_year})."
            )
        if base_year_emissions_tco2e <= 0:
            raise ValueError(
                f"base_year_emissions_tco2e must be > 0, got {base_year_emissions_tco2e}."
            )
        if pathway_type in ("linear", "exponential") and custom_annual_reduction_pct is None:
            raise ValueError(
                f"custom_annual_reduction_pct is required for pathway_type='{pathway_type}'."
            )

        self.organisation = organisation
        self.base_year = base_year
        self.base_year_emissions_tco2e = base_year_emissions_tco2e
        self.net_zero_year = net_zero_year
        self.pathway_type = pathway_type
        self._custom_rate = custom_annual_reduction_pct
        self._annual_data: Dict[int, float] = {}  # year → actual tCO2e

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record_year(self, year: int, actual_emissions_tco2e: float) -> None:
        """Record actual emissions for a reporting year.

        Args:
            year: Reporting year (must be > base_year).
            actual_emissions_tco2e: Gross annual emissions in tCO2e.

        Raises:
            ValueError: If year ≤ base_year or emissions < 0.
        """
        if year <= self.base_year:
            raise ValueError(
                f"Reporting year {year} must be after base_year {self.base_year}."
            )
        if actual_emissions_tco2e < 0:
            raise ValueError(f"actual_emissions_tco2e must be ≥ 0, got {actual_emissions_tco2e}.")
        self._annual_data[year] = actual_emissions_tco2e

    def record_batch(self, records: Dict[int, float]) -> None:
        """Record multiple years at once.

        Args:
            records: Dict mapping year → actual tCO2e.
        """
        for year, emissions in records.items():
            self.record_year(year, emissions)

    def pathway_target(self, year: int) -> float:
        """Return the pathway emissions target for a given year.

        Args:
            year: Year to calculate target for.

        Returns:
            Target emissions in tCO2e. Returns 0 if year ≥ net_zero_year.
        """
        if year >= self.net_zero_year:
            return 0.0

        elapsed = year - self.base_year
        base = self.base_year_emissions_tco2e

        if self.pathway_type == "linear":
            rate = self._custom_rate / 100
            return max(0.0, base * (1 - rate * elapsed))

        elif self.pathway_type == "exponential":
            rate = self._custom_rate / 100
            return max(0.0, base * ((1 - rate) ** elapsed))

        elif self.pathway_type == "sbti_1.5c":
            return max(0.0, base * ((1 - _SBTI_1_5C_ANNUAL_REDUCTION_RATE) ** elapsed))

        elif self.pathway_type == "sbti_wb2c":
            return max(0.0, base * ((1 - _SBTI_WELL_BELOW_2C_ANNUAL_REDUCTION_RATE) ** elapsed))

        elif self.pathway_type == "iea_nze":
            # Linear reduction to zero by 2050
            total_years = self.net_zero_year - self.base_year
            annual_reduction = base / total_years
            return max(0.0, base - annual_reduction * elapsed)

        return base  # fallback

    def total_carbon_budget(self) -> float:
        """Calculate total allowable carbon budget from base year to net zero.

        Sums annual pathway targets across all years from base_year+1 to
        net_zero_year (inclusive of net zero year with target=0).

        Returns:
            Total carbon budget in tCO2e.
        """
        return sum(
            self.pathway_target(y)
            for y in range(self.base_year + 1, self.net_zero_year + 1)
        )

    def generate_report(self) -> NetZeroPathwayReport:
        """Generate a full net zero pathway tracking report.

        Returns:
            NetZeroPathwayReport with per-year records and aggregate statistics.

        Raises:
            ValueError: If no annual records have been added yet.
        """
        if not self._annual_data:
            raise ValueError(
                "No annual emissions records found. Call record_year() before generate_report()."
            )

        sorted_years = sorted(self._annual_data.keys())
        total_budget = self.total_carbon_budget()
        cumulative_actual = 0.0
        annual_records: List[AnnualProgressRecord] = []

        prev_emissions = self.base_year_emissions_tco2e

        for year in sorted_years:
            actual = self._annual_data[year]
            target = self.pathway_target(year)
            gap = round(actual - target, 2)
            on_track = actual <= target

            # YoY reduction %
            if prev_emissions and prev_emissions > 0:
                yoy = round((prev_emissions - actual) / prev_emissions * 100, 2)
            else:
                yoy = None

            cumulative_actual += actual
            budget_consumed_pct = round(
                cumulative_actual / total_budget * 100, 2
            ) if total_budget > 0 else 0.0

            # Required annual reduction rate to reach zero from current emissions
            remaining_years = self.net_zero_year - year
            if remaining_years > 0 and actual > 0:
                # r such that actual * (1-r)^remaining_years = 0 is impossible exactly;
                # use 95% reduction as practical proxy for "net zero"
                import math
                req_rate = round((1 - (0.05 ** (1 / remaining_years))) * 100, 2)
            else:
                req_rate = 0.0

            annual_records.append(AnnualProgressRecord(
                year=year,
                actual_emissions_tco2e=actual,
                pathway_target_tco2e=round(target, 2),
                gap_tco2e=gap,
                on_track=on_track,
                yoy_reduction_pct=yoy,
                required_reduction_rate_pct=req_rate,
                cumulative_budget_consumed_pct=budget_consumed_pct,
            ))

            prev_emissions = actual

        on_track_years = [r.year for r in annual_records if r.on_track]
        off_track_years = [r.year for r in annual_records if not r.on_track]
        on_track_rate = round(len(on_track_years) / len(annual_records) * 100, 1)

        budget_remaining = max(0.0, total_budget - cumulative_actual)

        # Implied net zero year from last reported year
        last_record = annual_records[-1]
        implied_nz = self._extrapolate_net_zero_year(last_record)

        # Overall status
        if on_track_rate >= 80:
            overall_status = "on_track"
        elif on_track_rate >= 50:
            overall_status = "lagging"
        else:
            overall_status = "critical"

        return NetZeroPathwayReport(
            organisation=self.organisation,
            base_year=self.base_year,
            net_zero_year=self.net_zero_year,
            pathway_type=self.pathway_type,
            base_year_emissions_tco2e=self.base_year_emissions_tco2e,
            total_carbon_budget_tco2e=round(total_budget, 2),
            cumulative_actual_emissions_tco2e=round(cumulative_actual, 2),
            years_on_track=on_track_years,
            years_off_track=off_track_years,
            on_track_rate_pct=on_track_rate,
            annual_records=annual_records,
            overall_status=overall_status,
            budget_remaining_tco2e=round(budget_remaining, 2),
            implied_net_zero_year=implied_nz,
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _extrapolate_net_zero_year(self, last: AnnualProgressRecord) -> Optional[int]:
        """Extrapolate net zero year from last reporting year's YoY rate."""
        if last.yoy_reduction_pct is None or last.yoy_reduction_pct <= 0:
            return None  # no positive reduction trend
        import math
        rate = last.yoy_reduction_pct / 100
        # Solve: actual * (1-rate)^n < 1000 tCO2e (practical net zero threshold)
        if last.actual_emissions_tco2e <= 0:
            return last.year
        try:
            n = math.ceil(
                math.log(1000 / last.actual_emissions_tco2e) / math.log(1 - rate)
            )
            return last.year + n
        except (ValueError, ZeroDivisionError):
            return None
