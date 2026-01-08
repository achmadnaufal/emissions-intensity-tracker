"""
Scope 3 Downstream Emissions Calculator for Coal Operations.

Covers GHG Protocol Corporate Value Chain (Scope 3) Standard Categories:
  - Category 11: Use of Sold Products
  - Category 12: End-of-Life Treatment of Sold Products
  - Category 9: Downstream Transportation and Distribution

Category 11 (use of sold products) is typically the largest Scope 3 category
for coal producers — accounting for combustion emissions at power plants and
industrial facilities that purchase the coal.

References:
    - GHG Protocol Corporate Value Chain (Scope 3) Accounting and Reporting Standard
    - IPCC AR5 GWP-100 values
    - IEA Coal Information 2023

Author: github.com/achmadnaufal
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Combustion emission factors (tCO2e/tonne coal) — GHG Protocol Scope 3 defaults
# ---------------------------------------------------------------------------

COAL_COMBUSTION_FACTORS: Dict[str, float] = {
    # Grade → tCO2e per tonne coal combusted (higher CV = more CO2)
    "anthracite": 2.86,
    "bituminous": 2.42,
    "sub_bituminous": 1.92,
    "lignite": 1.54,
    "thermal_general": 2.20,  # fallback for unknown grade
}

# CO2 emission factor from coal fly ash landfill per tonne ash (tCO2e/t)
ASH_LANDFILL_FACTOR = 0.034  # Category 12

# Shipping emission factors (tCO2e/tonne/km)
SHIPPING_MODE_FACTORS: Dict[str, float] = {
    "bulk_vessel": 0.0000113,   # Capesize/Panamax
    "barge": 0.0000197,
    "rail": 0.0000280,
    "truck": 0.0000960,
}


@dataclass
class CoalShipment:
    """
    Represents a single coal shipment for downstream emissions tracking.

    Attributes:
        shipment_id: Unique identifier.
        coal_grade: Coal grade (``anthracite``, ``bituminous``, ``sub_bituminous``,
            ``lignite``, ``thermal_general``).
        quantity_t: Shipment quantity in metric tonnes.
        destination: Destination name or code.
        transport_mode: Transport mode (``bulk_vessel``, ``barge``, ``rail``, ``truck``).
        distance_km: Transport distance in kilometres.
        ash_pct: Ash content as % of coal mass (used for Cat 12 calculation).
        customer_sector: End-use sector (e.g., ``power``, ``cement``, ``steel``).
    """

    shipment_id: str
    coal_grade: str
    quantity_t: float
    destination: str
    transport_mode: str
    distance_km: float
    ash_pct: float = 15.0
    customer_sector: str = "power"

    VALID_GRADES = set(COAL_COMBUSTION_FACTORS.keys())
    VALID_MODES = set(SHIPPING_MODE_FACTORS.keys())

    def __post_init__(self) -> None:
        if self.coal_grade not in self.VALID_GRADES:
            raise ValueError(
                f"coal_grade '{self.coal_grade}' invalid. Choose from {self.VALID_GRADES}"
            )
        if self.transport_mode not in self.VALID_MODES:
            raise ValueError(
                f"transport_mode '{self.transport_mode}' invalid. Choose from {self.VALID_MODES}"
            )
        if self.quantity_t <= 0:
            raise ValueError("quantity_t must be positive.")
        if self.distance_km < 0:
            raise ValueError("distance_km cannot be negative.")
        if not (0 <= self.ash_pct <= 100):
            raise ValueError("ash_pct must be between 0 and 100.")


class Scope3DownstreamCalculator:
    """
    Calculates GHG Protocol Scope 3 downstream emissions for coal operations.

    Covers three downstream categories:

    - **Category 9** — Downstream transportation and distribution
    - **Category 11** — Use of sold products (coal combustion at customer sites)
    - **Category 12** — End-of-life treatment (fly ash landfill)

    Attributes:
        company_name (str): Name of the reporting company.
        reporting_year (int): Reporting year.
        shipments (list): Registered shipments.

    Example::

        calc = Scope3DownstreamCalculator("PT Nusantara Coal", 2026)
        calc.add_shipment(CoalShipment(
            shipment_id="SHP-001",
            coal_grade="sub_bituminous",
            quantity_t=50_000,
            destination="Suralaya Power Plant",
            transport_mode="barge",
            distance_km=320,
            ash_pct=14.0,
            customer_sector="power",
        ))
        report = calc.generate_report()
        print(f"Category 11 (use of sold products): {report['cat11_tCO2e']:,.0f} tCO2e")
    """

    def __init__(self, company_name: str = "Coal Co.", reporting_year: int = 2026) -> None:
        """
        Initialize the calculator.

        Args:
            company_name: Reporting entity name (used in reports).
            reporting_year: Financial/reporting year (informational).
        """
        self.company_name = company_name
        self.reporting_year = reporting_year
        self.shipments: List[CoalShipment] = []

    # ------------------------------------------------------------------
    # Shipment management
    # ------------------------------------------------------------------

    def add_shipment(self, shipment: CoalShipment) -> None:
        """
        Register a coal shipment.

        Args:
            shipment: A :class:`CoalShipment` instance.

        Raises:
            ValueError: If a shipment with the same ID already exists.
        """
        if any(s.shipment_id == shipment.shipment_id for s in self.shipments):
            raise ValueError(f"Shipment '{shipment.shipment_id}' already registered.")
        self.shipments.append(shipment)

    def remove_shipment(self, shipment_id: str) -> bool:
        """
        Remove a shipment by ID.

        Returns:
            ``True`` if removed, ``False`` if not found.
        """
        before = len(self.shipments)
        self.shipments = [s for s in self.shipments if s.shipment_id != shipment_id]
        return len(self.shipments) < before

    # ------------------------------------------------------------------
    # Category calculations
    # ------------------------------------------------------------------

    def calculate_cat9_transport(self) -> Dict[str, float]:
        """
        Category 9: Downstream transportation emissions.

        Returns:
            dict with per-shipment and total tCO2e from downstream shipping.
        """
        results: Dict[str, float] = {}
        for s in self.shipments:
            factor = SHIPPING_MODE_FACTORS[s.transport_mode]
            tco2e = s.quantity_t * s.distance_km * factor
            results[s.shipment_id] = round(tco2e, 3)
        return {
            "by_shipment": results,
            "total_tCO2e": round(sum(results.values()), 3),
        }

    def calculate_cat11_use_of_sold_products(self) -> Dict[str, float]:
        """
        Category 11: Emissions from combustion of sold coal at customer sites.

        This is typically the largest downstream Scope 3 category for coal producers.

        Returns:
            dict with per-shipment and total tCO2e from coal combustion.
        """
        results: Dict[str, float] = {}
        for s in self.shipments:
            factor = COAL_COMBUSTION_FACTORS[s.coal_grade]
            tco2e = s.quantity_t * factor
            results[s.shipment_id] = round(tco2e, 2)
        return {
            "by_shipment": results,
            "total_tCO2e": round(sum(results.values()), 2),
        }

    def calculate_cat12_end_of_life(self) -> Dict[str, float]:
        """
        Category 12: End-of-life emissions from coal ash landfilling.

        Assumes all ash from combustion is sent to landfill (conservative).

        Returns:
            dict with per-shipment and total tCO2e from ash disposal.
        """
        results: Dict[str, float] = {}
        for s in self.shipments:
            ash_tonnes = s.quantity_t * (s.ash_pct / 100.0)
            tco2e = ash_tonnes * ASH_LANDFILL_FACTOR
            results[s.shipment_id] = round(tco2e, 3)
        return {
            "by_shipment": results,
            "total_tCO2e": round(sum(results.values()), 3),
        }

    # ------------------------------------------------------------------
    # Aggregated reporting
    # ------------------------------------------------------------------

    def generate_report(self) -> Dict:
        """
        Generate a full Scope 3 downstream emissions report.

        Returns:
            dict with:

            - ``company`` – reporting entity name
            - ``year`` – reporting year
            - ``total_coal_sold_t`` – total coal sold in tonnes
            - ``cat9_tCO2e`` – Category 9 transport emissions
            - ``cat11_tCO2e`` – Category 11 use-of-sold-products emissions
            - ``cat12_tCO2e`` – Category 12 end-of-life emissions
            - ``total_scope3_downstream_tCO2e`` – sum of all three categories
            - ``cat11_share_pct`` – Category 11 as % of total downstream Scope 3
            - ``by_sector`` – tCO2e breakdown by customer sector
            - ``by_grade`` – tCO2e breakdown by coal grade
        """
        if not self.shipments:
            return {
                "company": self.company_name,
                "year": self.reporting_year,
                "total_coal_sold_t": 0.0,
                "cat9_tCO2e": 0.0,
                "cat11_tCO2e": 0.0,
                "cat12_tCO2e": 0.0,
                "total_scope3_downstream_tCO2e": 0.0,
            }

        cat9 = self.calculate_cat9_transport()["total_tCO2e"]
        cat11 = self.calculate_cat11_use_of_sold_products()["total_tCO2e"]
        cat12 = self.calculate_cat12_end_of_life()["total_tCO2e"]
        total = round(cat9 + cat11 + cat12, 2)
        total_coal = round(sum(s.quantity_t for s in self.shipments), 2)

        # Sector breakdown (Cat 11 only — most material)
        sector_tco2e: Dict[str, float] = {}
        grade_tco2e: Dict[str, float] = {}
        for s in self.shipments:
            factor = COAL_COMBUSTION_FACTORS[s.coal_grade]
            tco2e = round(s.quantity_t * factor, 2)
            sector_tco2e[s.customer_sector] = round(
                sector_tco2e.get(s.customer_sector, 0.0) + tco2e, 2
            )
            grade_tco2e[s.coal_grade] = round(
                grade_tco2e.get(s.coal_grade, 0.0) + tco2e, 2
            )

        return {
            "company": self.company_name,
            "year": self.reporting_year,
            "n_shipments": len(self.shipments),
            "total_coal_sold_t": total_coal,
            "cat9_tCO2e": cat9,
            "cat11_tCO2e": cat11,
            "cat12_tCO2e": cat12,
            "total_scope3_downstream_tCO2e": total,
            "cat11_share_pct": round(cat11 / total * 100, 1) if total > 0 else 0.0,
            "by_sector": sector_tco2e,
            "by_grade": grade_tco2e,
        }

    def intensity_tCO2e_per_tonne(self) -> float:
        """
        Return total downstream Scope 3 intensity (tCO2e per tonne sold).

        Returns:
            Scope 3 downstream intensity. Returns 0.0 if no shipments registered.
        """
        total_coal = sum(s.quantity_t for s in self.shipments)
        if total_coal == 0:
            return 0.0
        report = self.generate_report()
        return round(report["total_scope3_downstream_tCO2e"] / total_coal, 4)

    def __len__(self) -> int:
        return len(self.shipments)

    def __repr__(self) -> str:
        return (
            f"Scope3DownstreamCalculator(company={self.company_name!r}, "
            f"year={self.reporting_year}, shipments={len(self.shipments)})"
        )
