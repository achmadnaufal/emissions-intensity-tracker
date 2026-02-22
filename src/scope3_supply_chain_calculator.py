"""Scope 3 supply chain emissions calculator for coal mining operations.

Implements GHG Protocol Corporate Value Chain (Scope 3) Standard categories
relevant to upstream and downstream coal mining emissions: purchased goods,
transportation (Categories 4 & 9), processing of sold products (Category 10),
use of sold products (Category 11 — coal combustion), and end-of-life (Category 12).

References:
    GHG Protocol (2011) Corporate Value Chain (Scope 3) Accounting and Reporting Standard.
    IPCC (2006) Guidelines for National GHG Inventories Vol. 2 — Energy, Chapter 2.
    IEA (2023) World Energy Statistics — Coal emission factors.
    ISO 14064-1:2018 — Greenhouse gas inventories for organisations.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class Scope3Category(Enum):
    """GHG Protocol Scope 3 categories relevant to coal mining."""
    CAT1_PURCHASED_GOODS = "Category 1 — Purchased goods and services"
    CAT4_UPSTREAM_TRANSPORT = "Category 4 — Upstream transportation and distribution"
    CAT5_WASTE = "Category 5 — Waste generated in operations"
    CAT9_DOWNSTREAM_TRANSPORT = "Category 9 — Downstream transportation and distribution"
    CAT10_PROCESSING = "Category 10 — Processing of sold products"
    CAT11_USE_OF_SOLD = "Category 11 — Use of sold products (coal combustion)"
    CAT12_END_OF_LIFE = "Category 12 — End-of-life treatment of sold products"


class TransportMode(Enum):
    """Transport mode with default emission factors (kg CO2e per tonne-km)."""
    RAIL = "rail"
    ROAD_HGV = "road_hgv"
    BARGE_INLAND = "barge_inland"
    BULK_CARRIER_SMALL = "bulk_carrier_small"    # <10,000 DWT
    BULK_CARRIER_LARGE = "bulk_carrier_large"    # >50,000 DWT (Panamax/Capesize)


# GHG Protocol / GLEC Framework emission factors (kg CO2e per tonne-km)
TRANSPORT_EF: Dict[TransportMode, float] = {
    TransportMode.RAIL: 0.028,
    TransportMode.ROAD_HGV: 0.120,
    TransportMode.BARGE_INLAND: 0.031,
    TransportMode.BULK_CARRIER_SMALL: 0.019,
    TransportMode.BULK_CARRIER_LARGE: 0.008,
}

# IPCC 2006 coal combustion emission factors (t CO2e per TJ, net calorific value)
# Power generation assumed 33% efficiency (IPCC Tier 1)
COAL_COMBUSTION_EF_T_CO2E_PER_T: Dict[str, float] = {
    "anthracite": 2.65,
    "bituminous": 2.42,
    "subbituminous": 1.85,
    "lignite": 1.32,
    "coking_coal": 2.55,
}


@dataclass
class TransportLeg:
    """A single transport segment in the supply chain.

    Args:
        leg_id: Identifier for this transport leg.
        mode: Transport mode.
        distance_km: One-way haul distance in km.
        annual_tonnage_kt: Annual tonnage transported (thousand tonnes).
        load_factor: Fraction of capacity actually loaded (0.5–1.0). Default 0.85.
        custom_ef_kg_co2e_tkm: Override default EF (kg CO2e/tonne-km) if available.
    """
    leg_id: str
    mode: TransportMode
    distance_km: float
    annual_tonnage_kt: float
    load_factor: float = 0.85
    custom_ef_kg_co2e_tkm: Optional[float] = None

    def __post_init__(self) -> None:
        if self.distance_km <= 0:
            raise ValueError("distance_km must be positive")
        if self.annual_tonnage_kt <= 0:
            raise ValueError("annual_tonnage_kt must be positive")
        if not 0.3 <= self.load_factor <= 1.0:
            raise ValueError("load_factor must be 0.3–1.0")
        if self.custom_ef_kg_co2e_tkm is not None and self.custom_ef_kg_co2e_tkm < 0:
            raise ValueError("custom_ef_kg_co2e_tkm must be non-negative")

    @property
    def emission_factor(self) -> float:
        """Effective emission factor (kg CO2e/tonne-km), adjusted for load factor."""
        base_ef = (
            self.custom_ef_kg_co2e_tkm
            if self.custom_ef_kg_co2e_tkm is not None
            else TRANSPORT_EF[self.mode]
        )
        # Empty return leg correction: total emissions / loaded tonnage
        return base_ef / self.load_factor

    @property
    def annual_emissions_t_co2e(self) -> float:
        """Annual GHG emissions for this transport leg (t CO2e)."""
        return self.emission_factor * self.distance_km * self.annual_tonnage_kt * 1000 / 1000
        # kg CO2e/tkm × km × kt × 1000 t/kt / 1000 (kg→t) = t CO2e


@dataclass
class CoalCombustionEndUse:
    """Coal sold for combustion at end-user facilities (Cat 11).

    Args:
        end_use_id: Identifier for this end use (e.g. "India-power-plants").
        coal_type: Coal type key from COAL_COMBUSTION_EF_T_CO2E_PER_T.
        annual_sales_kt: Annual coal sales to this end user (kt).
        combustion_efficiency_pct: End-user thermal efficiency (20–50% for power, 55–90% for industry).
        custom_ef_t_co2e_per_t: Override default combustion EF if measured data available.
    """
    end_use_id: str
    coal_type: str
    annual_sales_kt: float
    combustion_efficiency_pct: float = 33.0
    custom_ef_t_co2e_per_t: Optional[float] = None

    def __post_init__(self) -> None:
        if self.annual_sales_kt <= 0:
            raise ValueError("annual_sales_kt must be positive")
        if self.coal_type not in COAL_COMBUSTION_EF_T_CO2E_PER_T and self.custom_ef_t_co2e_per_t is None:
            valid = list(COAL_COMBUSTION_EF_T_CO2E_PER_T.keys())
            raise ValueError(f"coal_type must be one of {valid} or supply custom_ef_t_co2e_per_t")
        if not 15 <= self.combustion_efficiency_pct <= 95:
            raise ValueError("combustion_efficiency_pct must be 15–95%")

    @property
    def emission_factor(self) -> float:
        if self.custom_ef_t_co2e_per_t is not None:
            return self.custom_ef_t_co2e_per_t
        return COAL_COMBUSTION_EF_T_CO2E_PER_T[self.coal_type]

    @property
    def annual_emissions_t_co2e(self) -> float:
        return self.emission_factor * self.annual_sales_kt * 1000


@dataclass
class Scope3Result:
    """Annual Scope 3 emissions breakdown by GHG Protocol category."""
    company_id: str
    reporting_year: int
    cat4_upstream_transport_t_co2e: float
    cat9_downstream_transport_t_co2e: float
    cat11_coal_combustion_t_co2e: float
    total_scope3_t_co2e: float
    intensity_t_co2e_per_t_coal: float
    category_breakdown: Dict[str, float]
    largest_category: str
    reduction_opportunities: List[str]


class Scope3SupplyChainCalculator:
    """Calculate Scope 3 emissions for coal mining supply chain.

    Supports GHG Protocol Categories 4, 9, and 11 with transport leg
    modelling and coal combustion end-use accounting.

    Example::

        calc = Scope3SupplyChainCalculator("Berau Coal", 2024)
        calc.add_upstream_leg(TransportLeg("mine-to-port", TransportMode.RAIL, 120, 8000))
        calc.add_downstream_leg(TransportLeg("port-to-India", TransportMode.BULK_CARRIER_LARGE, 3800, 6000))
        calc.add_end_use(CoalCombustionEndUse("India-power", "subbituminous", 6000))
        result = calc.calculate()
        print(f"Total Scope 3: {result.total_scope3_t_co2e / 1e6:.1f} Mt CO2e")
    """

    def __init__(self, company_id: str, reporting_year: int) -> None:
        """Initialise calculator.

        Args:
            company_id: Company or business unit name.
            reporting_year: Fiscal/calendar year for reporting.
        """
        self.company_id = company_id
        self.reporting_year = reporting_year
        self._upstream_legs: List[TransportLeg] = []
        self._downstream_legs: List[TransportLeg] = []
        self._end_uses: List[CoalCombustionEndUse] = []

    def add_upstream_leg(self, leg: TransportLeg) -> None:
        """Register an upstream transport leg (Category 4).

        Args:
            leg: TransportLeg for mine-to-port or mine-to-plant movement.
        """
        if not isinstance(leg, TransportLeg):
            raise TypeError("leg must be a TransportLeg")
        self._upstream_legs.append(leg)

    def add_downstream_leg(self, leg: TransportLeg) -> None:
        """Register a downstream transport leg (Category 9).

        Args:
            leg: TransportLeg for port-to-customer or export movement.
        """
        if not isinstance(leg, TransportLeg):
            raise TypeError("leg must be a TransportLeg")
        self._downstream_legs.append(leg)

    def add_end_use(self, end_use: CoalCombustionEndUse) -> None:
        """Register a coal combustion end use (Category 11).

        Args:
            end_use: CoalCombustionEndUse for each customer/destination.
        """
        if not isinstance(end_use, CoalCombustionEndUse):
            raise TypeError("end_use must be a CoalCombustionEndUse")
        self._end_uses.append(end_use)

    def _total_production_kt(self) -> float:
        """Estimate total coal production as sum of downstream sales tonnage."""
        if self._end_uses:
            return sum(e.annual_sales_kt for e in self._end_uses)
        elif self._downstream_legs:
            return sum(l.annual_tonnage_kt for l in self._downstream_legs)
        elif self._upstream_legs:
            return sum(l.annual_tonnage_kt for l in self._upstream_legs)
        return 1.0  # avoid division by zero

    def _reduction_opportunities(
        self, cat4: float, cat9: float, cat11: float
    ) -> List[str]:
        opps = []
        if cat11 > 0 and cat11 / (cat4 + cat9 + cat11) > 0.9:
            opps.append(
                "Category 11 (coal combustion) represents >90% of Scope 3 emissions."
                " Transition customers to higher-efficiency power plants (USC/AUSC) or"
                " renewable alternatives to materially reduce this category."
            )
        for leg in self._upstream_legs:
            if leg.mode == TransportMode.ROAD_HGV and leg.distance_km > 50:
                opps.append(
                    f"Upstream leg '{leg.leg_id}': Road HGV haul {leg.distance_km:.0f} km."
                    " Consider rail conversion — EF 0.028 vs 0.120 kg CO2e/tkm (>75% reduction)."
                )
        for leg in self._downstream_legs:
            if leg.mode == TransportMode.BULK_CARRIER_SMALL:
                opps.append(
                    f"Downstream leg '{leg.leg_id}': Small bulk carrier used."
                    " Larger Panamax/Capesize vessels have EF 0.008 vs 0.019 kg CO2e/tkm."
                )
        if cat4 > 0 and sum(l.load_factor for l in self._upstream_legs) / max(len(self._upstream_legs), 1) < 0.8:
            opps.append(
                "Average upstream load factor <80%. Improve backhaul utilisation to reduce"
                " empty return leg emissions."
            )
        if not opps:
            opps.append(
                "Supply chain transport emissions are well-optimised. Engage key customers on"
                " coal-to-renewables transition roadmaps to address Category 11."
            )
        return opps

    def calculate(self) -> Scope3Result:
        """Calculate total Scope 3 emissions.

        Returns:
            Scope3Result with category breakdown and reduction opportunities.

        Raises:
            ValueError: If no inputs have been registered.
        """
        if not self._upstream_legs and not self._downstream_legs and not self._end_uses:
            raise ValueError("No transport legs or end uses registered.")

        cat4 = sum(l.annual_emissions_t_co2e for l in self._upstream_legs)
        cat9 = sum(l.annual_emissions_t_co2e for l in self._downstream_legs)
        cat11 = sum(e.annual_emissions_t_co2e for e in self._end_uses)
        total = cat4 + cat9 + cat11

        production_kt = self._total_production_kt()
        intensity = total / (production_kt * 1000) if production_kt > 0 else 0.0

        breakdown = {
            "cat4_upstream_transport": round(cat4, 1),
            "cat9_downstream_transport": round(cat9, 1),
            "cat11_coal_combustion": round(cat11, 1),
        }
        largest = max(breakdown, key=lambda k: breakdown[k])

        opps = self._reduction_opportunities(cat4, cat9, cat11)

        return Scope3Result(
            company_id=self.company_id,
            reporting_year=self.reporting_year,
            cat4_upstream_transport_t_co2e=round(cat4, 1),
            cat9_downstream_transport_t_co2e=round(cat9, 1),
            cat11_coal_combustion_t_co2e=round(cat11, 1),
            total_scope3_t_co2e=round(total, 1),
            intensity_t_co2e_per_t_coal=round(intensity, 4),
            category_breakdown=breakdown,
            largest_category=largest,
            reduction_opportunities=opps,
        )

    def transport_intensity_tkm_per_t(self) -> Dict[str, float]:
        """Compute total transport intensity (tonne-km per tonne of coal sold)."""
        production_t = self._total_production_kt() * 1000
        result = {}
        for cat, legs in [("upstream", self._upstream_legs), ("downstream", self._downstream_legs)]:
            tkm = sum(l.distance_km * l.annual_tonnage_kt * 1000 for l in legs)
            result[cat] = round(tkm / production_t, 2) if production_t > 0 else 0.0
        return result
