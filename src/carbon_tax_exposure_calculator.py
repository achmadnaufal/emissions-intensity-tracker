"""
Carbon Tax Exposure Calculator for coal mining operations.

Estimates financial exposure to current and future carbon pricing mechanisms,
including:
  - Existing carbon taxes (where applicable)
  - EU Carbon Border Adjustment Mechanism (CBAM) for export markets
  - Voluntary carbon credit offset costs
  - Stranded cost scenarios under IEA 1.5°C/2°C/NDC pathways

Carbon price trajectories are based on:
  - World Bank Carbon Pricing Dashboard (2024)
  - IEA Net Zero by 2050 carbon price scenarios
  - Taskforce on Scaling Voluntary Carbon Markets (TSVCM)

Use this module for ESG financial risk disclosure (TCFD alignment),
coal asset valuation under transition risk, and budget planning for
carbon price exposure.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple


class ClimateScenario(str, Enum):
    """IEA-aligned carbon price trajectory scenarios."""
    NZE_2050 = "nze_2050"       # Net Zero by 2050 — most aggressive
    SDS = "sds"                  # Sustainable Development Scenario (1.8°C)
    STEPS = "steps"              # Stated Policies Scenario (2.5°C)
    ANNOUNCED = "announced"      # Announced Pledges Scenario (NDCs, 2.1°C)


# Carbon price trajectories (USD/tCO2e) by scenario and year
# Source: IEA World Energy Outlook 2023, IAMC data
CARBON_PRICE_TRAJECTORIES: Dict[ClimateScenario, Dict[int, float]] = {
    ClimateScenario.NZE_2050: {
        2025: 50,  2027: 80,  2030: 130, 2035: 200, 2040: 250, 2050: 250,
    },
    ClimateScenario.SDS: {
        2025: 30,  2027: 45,  2030: 75,  2035: 120, 2040: 160, 2050: 200,
    },
    ClimateScenario.ANNOUNCED: {
        2025: 20,  2027: 28,  2030: 45,  2035: 70,  2040: 100, 2050: 140,
    },
    ClimateScenario.STEPS: {
        2025: 10,  2027: 13,  2030: 18,  2035: 25,  2040: 35,  2050: 50,
    },
}


@dataclass
class EmissionsProfile:
    """Annual GHG emissions profile for a coal mining operation."""
    operation_id: str
    operation_name: str
    country: str

    # Scope 1: Direct emissions (tCO2e/year)
    scope1_methane_tCO2e: float     # Fugitive methane from coal seams
    scope1_combustion_tCO2e: float  # Diesel, explosives

    # Scope 2: Indirect from electricity (tCO2e/year)
    scope2_tCO2e: float

    # Scope 3 (relevant for carbon tax exposure)
    scope3_coal_combustion_tCO2e: float  # Cat 11: End-use combustion of sold coal

    # Current mitigation
    current_offset_credits_tCO2e: float = 0.0  # Purchased VCUs or compliance credits
    existing_carbon_tax_usd_per_tCO2e: float = 0.0  # Already-paying jurisdictional price

    # Production data
    coal_production_tonnes: float = 0.0

    def __post_init__(self):
        for attr in [
            "scope1_methane_tCO2e", "scope1_combustion_tCO2e", "scope2_tCO2e",
            "scope3_coal_combustion_tCO2e", "current_offset_credits_tCO2e",
        ]:
            if getattr(self, attr) < 0:
                raise ValueError(f"{attr} must be non-negative ({self.operation_id})")
        if self.existing_carbon_tax_usd_per_tCO2e < 0:
            raise ValueError(f"existing_carbon_tax_usd_per_tCO2e must be non-negative ({self.operation_id})")

    @property
    def total_scope1_2_tCO2e(self) -> float:
        return self.scope1_methane_tCO2e + self.scope1_combustion_tCO2e + self.scope2_tCO2e

    @property
    def net_regulated_emissions(self) -> float:
        """Scope 1+2 after subtracting existing offsets."""
        return max(self.total_scope1_2_tCO2e - self.current_offset_credits_tCO2e, 0.0)


@dataclass
class CarbonTaxExposureResult:
    """Carbon tax financial exposure estimate for a single operation and scenario."""
    operation_id: str
    operation_name: str
    scenario: ClimateScenario
    assessment_year: int
    carbon_price_usd: float

    # Exposure by scope
    scope1_2_exposure_usd: float       # Direct operational exposure
    scope3_exposure_usd: float         # Downstream product exposure
    total_exposure_usd: float

    # Cost intensity
    exposure_per_tonne_coal_usd: Optional[float]  # USD per tonne of coal produced
    existing_tax_already_paid_usd: float

    # Net incremental exposure (above current payments)
    incremental_exposure_usd: float

    # Risk classification
    exposure_as_pct_of_hypothetical_revenue: Optional[float]
    risk_level: str   # low / medium / high / critical

    def to_dict(self) -> dict:
        return {
            "operation_id": self.operation_id,
            "operation_name": self.operation_name,
            "scenario": self.scenario.value,
            "assessment_year": self.assessment_year,
            "carbon_price_usd_per_tCO2e": round(self.carbon_price_usd, 2),
            "scope1_2_exposure_usd": round(self.scope1_2_exposure_usd, 0),
            "scope3_exposure_usd": round(self.scope3_exposure_usd, 0),
            "total_exposure_usd": round(self.total_exposure_usd, 0),
            "incremental_exposure_usd": round(self.incremental_exposure_usd, 0),
            "exposure_per_tonne_coal_usd": (
                round(self.exposure_per_tonne_coal_usd, 2)
                if self.exposure_per_tonne_coal_usd is not None else None
            ),
            "risk_level": self.risk_level,
        }


class CarbonTaxExposureCalculator:
    """
    Calculate financial exposure to carbon pricing for coal mining operations.

    Supports both regulatory carbon tax scenarios and scope 3 downstream
    coal combustion exposure (relevant for CBAM-style mechanisms or
    voluntary offset cost estimation).

    Parameters
    ----------
    include_scope3 : bool
        Whether to include Scope 3 downstream coal combustion in exposure (default False).
        Set True for full value-chain exposure analysis (TCFD MSCI-style).
    coal_revenue_usd_per_tonne : float, optional
        Average realized coal price (USD/tonne) for revenue-based risk ratio.
        If provided, enables exposure-as-% of revenue calculation.

    Examples
    --------
    >>> calc = CarbonTaxExposureCalculator()
    >>> profile = EmissionsProfile(
    ...     operation_id="MINE-001",
    ...     operation_name="Kalimantan Thermal Block",
    ...     country="Indonesia",
    ...     scope1_methane_tCO2e=85_000,
    ...     scope1_combustion_tCO2e=35_000,
    ...     scope2_tCO2e=20_000,
    ...     scope3_coal_combustion_tCO2e=2_500_000,
    ...     coal_production_tonnes=1_000_000,
    ... )
    >>> result = calc.calculate(profile, ClimateScenario.NZE_2050, year=2030)
    >>> print(f"Incremental exposure: USD {result.incremental_exposure_usd:,.0f}")
    """

    _RISK_THRESHOLDS = [
        (500_000, "low"),
        (5_000_000, "medium"),
        (20_000_000, "high"),
        (float("inf"), "critical"),
    ]

    def __init__(
        self,
        include_scope3: bool = False,
        coal_revenue_usd_per_tonne: Optional[float] = None,
    ) -> None:
        if coal_revenue_usd_per_tonne is not None and coal_revenue_usd_per_tonne <= 0:
            raise ValueError("coal_revenue_usd_per_tonne must be positive if provided.")
        self.include_scope3 = include_scope3
        self.coal_revenue_usd_per_tonne = coal_revenue_usd_per_tonne

    def _get_carbon_price(self, scenario: ClimateScenario, year: int) -> float:
        """Interpolate or look up carbon price for a scenario/year."""
        trajectory = CARBON_PRICE_TRAJECTORIES[scenario]
        sorted_years = sorted(trajectory.keys())

        if year <= sorted_years[0]:
            return trajectory[sorted_years[0]]
        if year >= sorted_years[-1]:
            return trajectory[sorted_years[-1]]

        # Linear interpolation between nearest years
        for i in range(len(sorted_years) - 1):
            y1, y2 = sorted_years[i], sorted_years[i + 1]
            if y1 <= year <= y2:
                t = (year - y1) / (y2 - y1)
                return trajectory[y1] + t * (trajectory[y2] - trajectory[y1])
        return trajectory[sorted_years[-1]]

    def _risk_level(self, exposure: float) -> str:
        for threshold, level in self._RISK_THRESHOLDS:
            if exposure < threshold:
                return level
        return "critical"

    def calculate(
        self,
        profile: EmissionsProfile,
        scenario: ClimateScenario,
        year: int,
    ) -> CarbonTaxExposureResult:
        """
        Calculate carbon tax exposure for a specific scenario and year.

        Parameters
        ----------
        profile : EmissionsProfile
        scenario : ClimateScenario
        year : int
            Assessment year (2025–2050).

        Returns
        -------
        CarbonTaxExposureResult
        """
        if year < 2020 or year > 2060:
            raise ValueError(f"year must be 2020–2060, got {year}")

        carbon_price = self._get_carbon_price(scenario, year)

        # Existing tax already paid
        existing_paid = profile.net_regulated_emissions * profile.existing_carbon_tax_usd_per_tCO2e

        # Scope 1+2 gross exposure at scenario price
        s1_2_exposure = profile.net_regulated_emissions * carbon_price

        # Scope 3 exposure (optional)
        s3_exposure = (
            profile.scope3_coal_combustion_tCO2e * carbon_price
            if self.include_scope3 else 0.0
        )

        total_exposure = s1_2_exposure + s3_exposure
        incremental = max(total_exposure - existing_paid, 0.0)

        # Cost per tonne of coal
        cpu = (
            incremental / profile.coal_production_tonnes
            if profile.coal_production_tonnes > 0 else None
        )

        # Exposure as % of revenue
        if self.coal_revenue_usd_per_tonne and profile.coal_production_tonnes > 0:
            hypothetical_revenue = self.coal_revenue_usd_per_tonne * profile.coal_production_tonnes
            exp_pct = incremental / hypothetical_revenue * 100
        else:
            exp_pct = None

        risk = self._risk_level(incremental)

        return CarbonTaxExposureResult(
            operation_id=profile.operation_id,
            operation_name=profile.operation_name,
            scenario=scenario,
            assessment_year=year,
            carbon_price_usd=carbon_price,
            scope1_2_exposure_usd=s1_2_exposure,
            scope3_exposure_usd=s3_exposure,
            total_exposure_usd=total_exposure,
            existing_tax_already_paid_usd=existing_paid,
            incremental_exposure_usd=incremental,
            exposure_per_tonne_coal_usd=cpu,
            exposure_as_pct_of_hypothetical_revenue=exp_pct,
            risk_level=risk,
        )

    def scenario_comparison(
        self,
        profile: EmissionsProfile,
        year: int,
    ) -> List[CarbonTaxExposureResult]:
        """Compare exposure across all four IEA scenarios for a given year."""
        return [
            self.calculate(profile, scenario, year)
            for scenario in ClimateScenario
        ]

    def multi_year_projection(
        self,
        profile: EmissionsProfile,
        scenario: ClimateScenario,
        years: List[int],
    ) -> List[CarbonTaxExposureResult]:
        """Project carbon tax exposure across multiple years under one scenario."""
        return [self.calculate(profile, scenario, y) for y in years]
