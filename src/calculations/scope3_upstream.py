"""
Scope 3 Upstream Emissions Calculator for coal mining operations.

Covers upstream (Category 1–8) Scope 3 emission sources as defined by the
GHG Protocol Corporate Value Chain (Scope 3) Standard.

Key categories for coal mining:
  Cat 1 – Purchased goods and services (explosives, chemicals, tyres)
  Cat 2 – Capital goods (heavy equipment, conveyors)
  Cat 3 – Fuel and energy related (upstream extraction / refining of fuels used)
  Cat 4 – Upstream transportation and distribution (supplier logistics)

Reference:
    GHG Protocol Corporate Value Chain (Scope 3) Standard (2011).
    IPCC AR6 GWP100 factors (CH₄ = 29.8, N₂O = 273).

Author: github.com/achmadnaufal
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Emission factors (kg CO₂e per unit)
# ---------------------------------------------------------------------------

# Explosives (ANFO): ~0.44 kg CO₂e / kg  (EcoInvent 3.9 avg)
ANFO_EF_KG_CO2E_PER_KG = 0.44
# Diesel upstream (well-to-tank) addition: ~0.62 kg CO₂e / L
DIESEL_UPSTREAM_EF = 0.62
# Tyres (off-road): ~7.3 kg CO₂e / kg tyre  (industry estimate)
TYRE_EF_KG_CO2E_PER_KG = 7.3
# Steel (rebar/structural): ~1.85 kg CO₂e / kg  (World Steel Association)
STEEL_EF_KG_CO2E_PER_KG = 1.85
# Road freight transport: ~0.096 kg CO₂e / tonne-km  (GHG Protocol default)
ROAD_FREIGHT_EF = 0.096
# Rail freight transport: ~0.028 kg CO₂e / tonne-km
RAIL_FREIGHT_EF = 0.028


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class UpstreamEmissionsResult:
    """Scope 3 upstream emissions breakdown for a reporting period.

    Attributes:
        operation_name: Name of the mining operation.
        period: Reporting period label (e.g. '2025-Q3').
        cat1_purchased_goods_tco2e: Category 1 — explosives, chemicals, tyres.
        cat2_capital_goods_tco2e: Category 2 — heavy equipment embodied carbon.
        cat3_fuel_energy_tco2e: Category 3 — upstream fuel lifecycle emissions.
        cat4_upstream_transport_tco2e: Category 4 — inbound logistics.
        total_upstream_tco2e: Sum of all categories.
        intensity_tco2e_per_tonne_coal: Total upstream / coal production.
    """

    operation_name: str
    period: str
    cat1_purchased_goods_tco2e: float
    cat2_capital_goods_tco2e: float
    cat3_fuel_energy_tco2e: float
    cat4_upstream_transport_tco2e: float
    total_upstream_tco2e: float
    intensity_tco2e_per_tonne_coal: float


# ---------------------------------------------------------------------------
# Calculator
# ---------------------------------------------------------------------------


class Scope3UpstreamCalculator:
    """Calculate upstream Scope 3 emissions for a coal mining operation.

    Args:
        operation_name: Identifier for the mine / operation unit.
        period: Reporting period label (free text, e.g. '2025-Q3').

    Example:
        >>> calc = Scope3UpstreamCalculator("Sangatta Mine", "2025-FY")
        >>> result = calc.calculate(
        ...     coal_production_tonnes=2_500_000,
        ...     anfo_consumed_kg=850_000,
        ...     diesel_upstream_liters=4_200_000,
        ...     tyre_mass_kg=18_000,
        ...     steel_mass_kg=95_000,
        ...     road_freight_tonne_km=320_000,
        ...     rail_freight_tonne_km=1_800_000,
        ... )
        >>> print(f"Total upstream: {result.total_upstream_tco2e:.1f} tCO₂e")
        >>> print(f"Intensity: {result.intensity_tco2e_per_tonne_coal:.4f} tCO₂e/t coal")
    """

    def __init__(self, operation_name: str, period: str = ""):
        if not operation_name.strip():
            raise ValueError("operation_name cannot be empty")
        self.operation_name = operation_name
        self.period = period

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def calculate(
        self,
        coal_production_tonnes: float,
        anfo_consumed_kg: float = 0.0,
        diesel_upstream_liters: float = 0.0,
        tyre_mass_kg: float = 0.0,
        steel_mass_kg: float = 0.0,
        road_freight_tonne_km: float = 0.0,
        rail_freight_tonne_km: float = 0.0,
        custom_goods_tco2e: float = 0.0,
    ) -> UpstreamEmissionsResult:
        """Calculate upstream Scope 3 emissions.

        Args:
            coal_production_tonnes: Total coal mined in the period (tonnes).
                Must be positive.
            anfo_consumed_kg: ANFO explosive consumed (kg). Default 0.
            diesel_upstream_liters: Diesel fuel consumed (upstream only,
                i.e. well-to-tank portion) in liters. Default 0.
            tyre_mass_kg: Total mass of tyres consumed (kg). Default 0.
            steel_mass_kg: Steel in capital goods and infrastructure (kg). Default 0.
            road_freight_tonne_km: Inbound road freight (tonne-km). Default 0.
            rail_freight_tonne_km: Inbound rail freight (tonne-km). Default 0.
            custom_goods_tco2e: Any additional Cat 1 goods not covered above
                (tCO₂e). Default 0.

        Returns:
            :class:`UpstreamEmissionsResult` with category breakdown.

        Raises:
            ValueError: If ``coal_production_tonnes`` ≤ 0 or any input is negative.
        """
        if coal_production_tonnes <= 0:
            raise ValueError("coal_production_tonnes must be positive")
        for name, val in [
            ("anfo_consumed_kg", anfo_consumed_kg),
            ("diesel_upstream_liters", diesel_upstream_liters),
            ("tyre_mass_kg", tyre_mass_kg),
            ("steel_mass_kg", steel_mass_kg),
            ("road_freight_tonne_km", road_freight_tonne_km),
            ("rail_freight_tonne_km", rail_freight_tonne_km),
            ("custom_goods_tco2e", custom_goods_tco2e),
        ]:
            if val < 0:
                raise ValueError(f"{name} cannot be negative")

        # Category 1: purchased goods
        anfo_tco2e = anfo_consumed_kg * ANFO_EF_KG_CO2E_PER_KG / 1000
        tyre_tco2e = tyre_mass_kg * TYRE_EF_KG_CO2E_PER_KG / 1000
        cat1 = anfo_tco2e + tyre_tco2e + custom_goods_tco2e

        # Category 2: capital goods (steel embodied carbon)
        cat2 = steel_mass_kg * STEEL_EF_KG_CO2E_PER_KG / 1000

        # Category 3: upstream fuel lifecycle
        cat3 = diesel_upstream_liters * DIESEL_UPSTREAM_EF / 1000

        # Category 4: upstream transport
        road_tco2e = road_freight_tonne_km * ROAD_FREIGHT_EF / 1000
        rail_tco2e = rail_freight_tonne_km * RAIL_FREIGHT_EF / 1000
        cat4 = road_tco2e + rail_tco2e

        total = cat1 + cat2 + cat3 + cat4
        intensity = total / coal_production_tonnes

        return UpstreamEmissionsResult(
            operation_name=self.operation_name,
            period=self.period,
            cat1_purchased_goods_tco2e=round(cat1, 3),
            cat2_capital_goods_tco2e=round(cat2, 3),
            cat3_fuel_energy_tco2e=round(cat3, 3),
            cat4_upstream_transport_tco2e=round(cat4, 3),
            total_upstream_tco2e=round(total, 3),
            intensity_tco2e_per_tonne_coal=round(intensity, 6),
        )

    def benchmark(
        self, result: UpstreamEmissionsResult, industry_avg_intensity: float = 0.015
    ) -> Dict[str, object]:
        """Compare result against an industry benchmark intensity.

        Args:
            result: Output from :meth:`calculate`.
            industry_avg_intensity: Industry average upstream Scope 3 intensity
                in tCO₂e per tonne of coal. Default 0.015.

        Returns:
            Dict with ``'vs_industry_pct'`` (% above/below benchmark),
            ``'rating'`` ('above_average', 'average', 'below_average'), and
            ``'recommendation'`` string.
        """
        if industry_avg_intensity <= 0:
            raise ValueError("industry_avg_intensity must be positive")
        diff_pct = (
            (result.intensity_tco2e_per_tonne_coal - industry_avg_intensity)
            / industry_avg_intensity
            * 100
        )
        if diff_pct < -10:
            rating = "below_average"
            rec = "Strong upstream efficiency. Document practices for replication."
        elif diff_pct > 10:
            rating = "above_average"
            rec = "Above average upstream intensity. Review explosive usage and logistics routes."
        else:
            rating = "average"
            rec = "Within industry range. Target 5-10% reduction via ANFO optimisation."

        return {
            "vs_industry_pct": round(diff_pct, 2),
            "rating": rating,
            "recommendation": rec,
        }
