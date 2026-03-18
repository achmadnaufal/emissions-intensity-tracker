"""
Green Steel Transition Calculator
=====================================
Models the emissions reduction pathway from conventional blast furnace
steelmaking to green steel (hydrogen-based direct reduced iron / electric
arc furnace) for transition planning and carbon accounting.

Technology pathways modeled:
 1. BF-BOF (Blast Furnace - Basic Oxygen Furnace) — baseline
 2. BF-BOF + CCS (Carbon Capture and Storage)
 3. DRI-EAF (Direct Reduced Iron with natural gas + Electric Arc Furnace)
 4. H-DRI-EAF (Green hydrogen DRI + EAF — green steel)
 5. Electrowinning (Boston Metal process — long term)

Metrics computed:
 - CO₂e intensity (tCO₂e / t crude steel)
 - Cost premium over BF-BOF baseline (USD / t steel)
 - Green hydrogen demand (kg H₂ / t DRI)
 - Annual transition capex estimate
 - Abatement cost (USD / tCO₂e)
 - Technology readiness level (TRL) and deployment risk

References:
 - IEA (2022) "Iron and Steel Technology Roadmap"
 - HYBRIT (2021) — SSAB, LKAB, Vattenfall pilot results
 - Rocky Mountain Institute (2021) "The Steel Solution"
 - Material Economics (2021) "Industrial Transformation 2050"
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class SteelTechnology(str, Enum):
    BF_BOF = "BF_BOF"
    BF_BOF_CCS = "BF_BOF_CCS"
    DRI_EAF_NG = "DRI_EAF_NG"
    H_DRI_EAF = "H_DRI_EAF"
    ELECTROWINNING = "ELECTROWINNING"
    SCRAP_EAF = "SCRAP_EAF"


@dataclass
class TechnologyProfile:
    """
    Emission and cost profile for a steelmaking technology.

    Attributes
    ----------
    technology : SteelTechnology
    co2e_intensity_t_per_t : float  — tCO₂e per tonne crude steel
    energy_intensity_GJ_per_t : float  — total energy (GJ/t steel)
    opex_usd_per_t : float  — operating cost (USD/t steel)
    capex_usd_per_t_capacity : float  — capex (USD per tonne annual capacity)
    h2_demand_kg_per_t_dri : float  — H₂ demand for DRI process (0 if N/A)
    electricity_intensity_MWh_per_t : float  — direct electricity (MWh/t)
    trl : int  — Technology Readiness Level (1–9)
    ccs_capture_rate : float  — fraction of CO₂ captured (0 if no CCS)
    commercial_availability_year : int  — year at commercial scale
    """
    technology: SteelTechnology
    co2e_intensity_t_per_t: float
    energy_intensity_GJ_per_t: float
    opex_usd_per_t: float
    capex_usd_per_t_capacity: float
    h2_demand_kg_per_t_dri: float = 0.0
    electricity_intensity_MWh_per_t: float = 0.0
    trl: int = 9
    ccs_capture_rate: float = 0.0
    commercial_availability_year: int = 2024

    def __post_init__(self):
        if self.co2e_intensity_t_per_t < 0:
            raise ValueError("co2e_intensity_t_per_t must be >= 0")
        if self.opex_usd_per_t <= 0:
            raise ValueError("opex_usd_per_t must be positive")
        if not 1 <= self.trl <= 9:
            raise ValueError("trl must be in [1, 9]")
        if not 0 <= self.ccs_capture_rate <= 1:
            raise ValueError("ccs_capture_rate must be in [0, 1]")


@dataclass
class TransitionScenario:
    """
    Transition pathway scenario for a steel plant.

    Parameters
    ----------
    plant_id : str
    annual_capacity_Mt : float  — annual crude steel capacity (million tonnes)
    baseline_tech : SteelTechnology
    target_tech : SteelTechnology
    transition_start_year : int
    full_deployment_year : int
    electricity_carbon_intensity : float  — grid tCO₂e/MWh at plant location
    green_h2_cost_usd_per_kg : float  — assumed green H₂ price (USD/kg)
    carbon_price_usd_per_tCO2e : float  — prevailing carbon price
    """
    plant_id: str
    annual_capacity_Mt: float
    baseline_tech: SteelTechnology
    target_tech: SteelTechnology
    transition_start_year: int
    full_deployment_year: int
    electricity_carbon_intensity: float = 0.5   # tCO₂e/MWh
    green_h2_cost_usd_per_kg: float = 3.0
    carbon_price_usd_per_tCO2e: float = 50.0

    def __post_init__(self):
        if self.annual_capacity_Mt <= 0:
            raise ValueError("annual_capacity_Mt must be positive")
        if self.full_deployment_year <= self.transition_start_year:
            raise ValueError("full_deployment_year must be after transition_start_year")
        if self.electricity_carbon_intensity < 0:
            raise ValueError("electricity_carbon_intensity must be >= 0")
        if self.green_h2_cost_usd_per_kg < 0:
            raise ValueError("green_h2_cost_usd_per_kg must be >= 0")


@dataclass
class TransitionResult:
    """Output of green steel transition calculation."""
    plant_id: str
    baseline_co2e_intensity: float
    target_co2e_intensity: float
    abatement_per_t_steel: float           # tCO₂e abated per t steel
    annual_abatement_MtCO2e: float
    cost_premium_usd_per_t: float          # extra cost vs baseline
    abatement_cost_usd_per_tCO2e: float
    total_transition_capex_MUSD: float     # million USD
    annual_h2_demand_kt: float             # thousand tonnes H₂ per year
    annual_electricity_demand_TWh: float
    net_present_value_MUSD: float          # NPV at 10yr horizon, 8% discount
    deployment_risk: str                   # "LOW", "MEDIUM", "HIGH"
    key_enablers: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Default technology profiles (IEA 2022 + HYBRIT 2021 data)
# ---------------------------------------------------------------------------

TECHNOLOGY_PROFILES: Dict[SteelTechnology, TechnologyProfile] = {
    SteelTechnology.BF_BOF: TechnologyProfile(
        SteelTechnology.BF_BOF,
        co2e_intensity_t_per_t=2.1,
        energy_intensity_GJ_per_t=21.0,
        opex_usd_per_t=380,
        capex_usd_per_t_capacity=1000,
        trl=9,
        commercial_availability_year=2000,
    ),
    SteelTechnology.BF_BOF_CCS: TechnologyProfile(
        SteelTechnology.BF_BOF_CCS,
        co2e_intensity_t_per_t=0.5,
        energy_intensity_GJ_per_t=24.0,
        opex_usd_per_t=450,
        capex_usd_per_t_capacity=1600,
        trl=7,
        ccs_capture_rate=0.80,
        commercial_availability_year=2030,
    ),
    SteelTechnology.DRI_EAF_NG: TechnologyProfile(
        SteelTechnology.DRI_EAF_NG,
        co2e_intensity_t_per_t=1.4,
        energy_intensity_GJ_per_t=19.0,
        opex_usd_per_t=400,
        capex_usd_per_t_capacity=700,
        electricity_intensity_MWh_per_t=0.5,
        trl=9,
        commercial_availability_year=2000,
    ),
    SteelTechnology.H_DRI_EAF: TechnologyProfile(
        SteelTechnology.H_DRI_EAF,
        co2e_intensity_t_per_t=0.05,   # near-zero (residual scope 3)
        energy_intensity_GJ_per_t=22.0,
        opex_usd_per_t=520,
        capex_usd_per_t_capacity=1200,
        h2_demand_kg_per_t_dri=55.0,   # kg H₂ / t DRI (HYBRIT)
        electricity_intensity_MWh_per_t=3.5,
        trl=8,
        commercial_availability_year=2030,
    ),
    SteelTechnology.ELECTROWINNING: TechnologyProfile(
        SteelTechnology.ELECTROWINNING,
        co2e_intensity_t_per_t=0.02,
        energy_intensity_GJ_per_t=18.0,
        opex_usd_per_t=480,
        capex_usd_per_t_capacity=1800,
        electricity_intensity_MWh_per_t=5.0,
        trl=5,
        commercial_availability_year=2035,
    ),
    SteelTechnology.SCRAP_EAF: TechnologyProfile(
        SteelTechnology.SCRAP_EAF,
        co2e_intensity_t_per_t=0.6,
        energy_intensity_GJ_per_t=8.0,
        opex_usd_per_t=320,
        capex_usd_per_t_capacity=500,
        electricity_intensity_MWh_per_t=0.55,
        trl=9,
        commercial_availability_year=2000,
    ),
}


class GreenSteelTransitionCalculator:
    """
    Models green steel transition economics and emissions reduction.

    Examples
    --------
    >>> from emissions_intensity_tracker.src.green_steel_transition_calculator import (
    ...     GreenSteelTransitionCalculator, TransitionScenario, SteelTechnology
    ... )
    >>> scenario = TransitionScenario(
    ...     plant_id="KRAKATAU-01",
    ...     annual_capacity_Mt=3.0,
    ...     baseline_tech=SteelTechnology.BF_BOF,
    ...     target_tech=SteelTechnology.H_DRI_EAF,
    ...     transition_start_year=2026,
    ...     full_deployment_year=2035,
    ...     electricity_carbon_intensity=0.4,
    ...     green_h2_cost_usd_per_kg=3.5,
    ...     carbon_price_usd_per_tCO2e=80.0,
    ... )
    >>> calc = GreenSteelTransitionCalculator()
    >>> result = calc.calculate(scenario)
    >>> result.abatement_per_t_steel > 0
    True
    """

    def __init__(self, custom_profiles: Optional[Dict[SteelTechnology, TechnologyProfile]] = None):
        self.profiles = {**TECHNOLOGY_PROFILES, **(custom_profiles or {})}

    def _get_profile(self, tech: SteelTechnology) -> TechnologyProfile:
        p = self.profiles.get(tech)
        if p is None:
            raise ValueError(f"No profile found for technology: {tech}")
        return p

    def _effective_co2e(
        self,
        profile: TechnologyProfile,
        elec_carbon_intensity: float,
    ) -> float:
        """Adjust CO₂e intensity for local grid carbon intensity."""
        elec_co2e = profile.electricity_intensity_MWh_per_t * elec_carbon_intensity
        return profile.co2e_intensity_t_per_t + elec_co2e

    def _opex_with_h2(
        self,
        profile: TechnologyProfile,
        h2_price_usd_per_kg: float,
    ) -> float:
        """Adjust opex for green hydrogen cost."""
        if profile.h2_demand_kg_per_t_dri == 0:
            return profile.opex_usd_per_t
        # H₂ cost per t steel = h2_demand × h2_price
        h2_cost = profile.h2_demand_kg_per_t_dri * h2_price_usd_per_kg
        # Replace natural gas component of opex (~$80/t for DRI-NG gas)
        base_opex_no_gas = profile.opex_usd_per_t - 80.0
        return base_opex_no_gas + h2_cost

    def _carbon_cost_benefit(
        self,
        abatement_per_t: float,
        carbon_price: float,
    ) -> float:
        """Carbon cost benefit per tonne steel from carbon price × abatement."""
        return abatement_per_t * carbon_price

    def _npv(
        self,
        annual_benefit_usd: float,
        capex_usd: float,
        horizon_yr: int = 10,
        discount_rate: float = 0.08,
    ) -> float:
        """Simple NPV calculation at given discount rate."""
        pv = sum(
            annual_benefit_usd / (1 + discount_rate) ** t
            for t in range(1, horizon_yr + 1)
        )
        return round((pv - capex_usd) / 1e6, 1)  # MUSD

    def _deployment_risk(self, target_profile: TechnologyProfile) -> str:
        if target_profile.trl >= 8:
            return "LOW"
        elif target_profile.trl >= 6:
            return "MEDIUM"
        else:
            return "HIGH"

    def _key_enablers(self, scenario: TransitionScenario) -> List[str]:
        """Identify key enablers needed for the transition."""
        enablers = []
        target = self._get_profile(scenario.target_tech)
        if scenario.target_tech == SteelTechnology.H_DRI_EAF:
            enablers.append(f"Green hydrogen supply at scale ({scenario.green_h2_cost_usd_per_kg:.1f} USD/kg)")
            enablers.append("Renewable electricity capacity >3.5 MWh/t steel")
            enablers.append("DRI pellet supply chain (high-grade iron ore ≥67% Fe)")
        if target.trl < 8:
            enablers.append(f"Technology scale-up from TRL {target.trl} to commercial")
        if scenario.carbon_price_usd_per_tCO2e < 80:
            enablers.append(f"Carbon price above $80/tCO₂e (currently ${scenario.carbon_price_usd_per_tCO2e})")
        if scenario.target_tech == SteelTechnology.BF_BOF_CCS:
            enablers.append("CO₂ transport and storage infrastructure")
        return enablers

    def calculate(self, scenario: TransitionScenario) -> TransitionResult:
        """
        Calculate full green steel transition metrics.

        Parameters
        ----------
        scenario : TransitionScenario

        Returns
        -------
        TransitionResult
        """
        baseline = self._get_profile(scenario.baseline_tech)
        target = self._get_profile(scenario.target_tech)

        baseline_co2e = self._effective_co2e(baseline, scenario.electricity_carbon_intensity)
        target_co2e = self._effective_co2e(target, scenario.electricity_carbon_intensity)
        abatement_per_t = max(0.0, baseline_co2e - target_co2e)

        annual_capacity_t = scenario.annual_capacity_Mt * 1e6
        annual_abatement = abatement_per_t * annual_capacity_t / 1e6  # MtCO₂e

        # Cost premium
        baseline_opex = self._opex_with_h2(baseline, scenario.green_h2_cost_usd_per_kg)
        target_opex = self._opex_with_h2(target, scenario.green_h2_cost_usd_per_kg)
        carbon_benefit = self._carbon_cost_benefit(abatement_per_t, scenario.carbon_price_usd_per_tCO2e)
        cost_premium = (target_opex - baseline_opex) - carbon_benefit

        abatement_cost = (
            round(cost_premium / abatement_per_t, 1)
            if abatement_per_t > 0 else float("inf")
        )

        # Capex
        incremental_capex = max(0.0, target.capex_usd_per_t_capacity - baseline.capex_usd_per_t_capacity)
        total_capex = incremental_capex * annual_capacity_t  # USD
        total_capex_musd = total_capex / 1e6

        # H₂ and electricity demand
        annual_h2_kt = (
            target.h2_demand_kg_per_t_dri * annual_capacity_t / 1e6
            if target.h2_demand_kg_per_t_dri > 0 else 0.0
        )
        annual_elec_TWh = (
            target.electricity_intensity_MWh_per_t * annual_capacity_t / 1e6
        )

        # NPV
        annual_carbon_benefit = carbon_benefit * annual_capacity_t  # USD
        annual_net_benefit = annual_carbon_benefit - (cost_premium * annual_capacity_t)
        npv = self._npv(annual_net_benefit, total_capex)

        risk = self._deployment_risk(target)
        enablers = self._key_enablers(scenario)

        return TransitionResult(
            plant_id=scenario.plant_id,
            baseline_co2e_intensity=round(baseline_co2e, 3),
            target_co2e_intensity=round(target_co2e, 3),
            abatement_per_t_steel=round(abatement_per_t, 3),
            annual_abatement_MtCO2e=round(annual_abatement, 3),
            cost_premium_usd_per_t=round(cost_premium, 1),
            abatement_cost_usd_per_tCO2e=round(abatement_cost, 1),
            total_transition_capex_MUSD=round(total_capex_musd, 1),
            annual_h2_demand_kt=round(annual_h2_kt, 1),
            annual_electricity_demand_TWh=round(annual_elec_TWh, 2),
            net_present_value_MUSD=npv,
            deployment_risk=risk,
            key_enablers=enablers,
        )

    def compare_technologies(
        self,
        scenario_base: TransitionScenario,
        technologies: Optional[List[SteelTechnology]] = None,
    ) -> List[TransitionResult]:
        """
        Compare multiple target technologies against the same baseline.

        Returns
        -------
        List[TransitionResult] sorted by abatement_cost (ascending).
        """
        if technologies is None:
            technologies = [
                SteelTechnology.BF_BOF_CCS,
                SteelTechnology.DRI_EAF_NG,
                SteelTechnology.H_DRI_EAF,
                SteelTechnology.SCRAP_EAF,
            ]

        results = []
        for tech in technologies:
            modified_scenario = TransitionScenario(
                plant_id=scenario_base.plant_id,
                annual_capacity_Mt=scenario_base.annual_capacity_Mt,
                baseline_tech=scenario_base.baseline_tech,
                target_tech=tech,
                transition_start_year=scenario_base.transition_start_year,
                full_deployment_year=scenario_base.full_deployment_year,
                electricity_carbon_intensity=scenario_base.electricity_carbon_intensity,
                green_h2_cost_usd_per_kg=scenario_base.green_h2_cost_usd_per_kg,
                carbon_price_usd_per_tCO2e=scenario_base.carbon_price_usd_per_tCO2e,
            )
            results.append(self.calculate(modified_scenario))

        return sorted(results, key=lambda r: r.abatement_cost_usd_per_tCO2e)
