"""
Carbon Border Adjustment Mechanism (CBAM) Cost Calculator
==========================================================
Estimate the CBAM compliance cost for Indonesian coal and industrial exporters
selling to European Union buyers under the EU CBAM Regulation (EU) 2023/956.

CBAM imposes a carbon price on the embedded emissions of imported goods
from non-EU countries that do not have equivalent carbon pricing.

Sectors covered (CBAM Annex I):
  - cement, aluminium, fertilisers, electricity, iron_steel, hydrogen

For coal (not directly covered as a commodity), this module calculates
the *indirect* CBAM exposure — i.e., the carbon cost that EU steel, aluminium
and cement producers will face when using Indonesian coal as a fuel/reductant,
and how that cost may be passed back to the coal supplier.

References
----------
- European Parliament (2023) Regulation (EU) 2023/956 on CBAM. OJ L 130/52.
- European Commission (2022) CBAM Impact Assessment. SWD(2022)345.
- IEA (2023) World Energy Outlook 2023. OECD/IEA, Paris.
- ESDM (2024) Indonesian Coal Export Outlook 2024.

Example
-------
>>> from src.cbam_cost_calculator import CBAMCostCalculator, CBAMProduct
>>> calc = CBAMCostCalculator(
...     exporter_country="Indonesia",
...     eu_carbon_price_eur_tco2=65.0,
...     domestic_carbon_price_eur_tco2=0.0,
... )
>>> product = CBAMProduct(
...     sector="iron_steel",
...     annual_export_tonnes=500_000.0,
...     embedded_emission_intensity_tco2_per_tonne=1.85,
... )
>>> result = calc.estimate_annual_cost(product)
>>> print(f"Annual CBAM liability: EUR {result.total_cbam_cost_eur:,.0f}")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Literal, Optional

Sector = Literal["cement", "aluminium", "fertilisers", "electricity", "iron_steel", "hydrogen"]
VALID_SECTORS = frozenset(["cement", "aluminium", "fertilisers", "electricity", "iron_steel", "hydrogen"])

# ---------------------------------------------------------------------------
# EU ETS benchmark emission intensity (tCO2/tonne product)
# Source: EU CBAM Implementing Regulation (EU) 2023/2390 Annex I
# ---------------------------------------------------------------------------
_EU_BENCHMARK_INTENSITY: dict = {
    "cement":       0.766,    # tCO2/tonne Portland cement
    "aluminium":    1.484,    # tCO2/tonne primary aluminium
    "fertilisers":  2.30,     # tCO2/tonne NH3-based fertiliser (urea equivalent)
    "electricity":  0.365,    # tCO2/MWh (use MWh as "tonne")
    "iron_steel":   1.328,    # tCO2/tonne crude steel (BF-BOF route)
    "hydrogen":     8.9,      # tCO2/tonne grey hydrogen
}

# Typical coal-sector pass-through fraction (how much CBAM cost coal suppliers absorb)
_COAL_PASSTHROUGH_FRACTION: float = 0.25   # 25% of EU buyer's CBAM is negotiated back to supplier

# IDR/EUR exchange rate (approximate 2024 mid-market)
_IDR_PER_EUR: float = 16_800.0


@dataclass
class CBAMProduct:
    """A product exported to the EU subject to CBAM."""
    sector: Sector
    annual_export_tonnes: float       # tonnes of product exported to EU per year
    embedded_emission_intensity_tco2_per_tonne: float  # actual tCO2/tonne for the specific production process
    product_name: str = ""

    def __post_init__(self):
        if self.sector not in VALID_SECTORS:
            raise ValueError(f"sector must be one of {sorted(VALID_SECTORS)}")
        if self.annual_export_tonnes <= 0:
            raise ValueError("annual_export_tonnes must be > 0")
        if self.embedded_emission_intensity_tco2_per_tonne < 0:
            raise ValueError("embedded_emission_intensity_tco2_per_tonne must be >= 0")


@dataclass
class CBAMEstimate:
    """Annual CBAM cost estimate for a product."""
    sector: str
    annual_export_tonnes: float
    embedded_intensity_tco2_per_tonne: float
    benchmark_intensity_tco2_per_tonne: float    # EU ETS free allocation benchmark
    eu_carbon_price_eur_tco2: float
    domestic_carbon_price_eur_tco2: float

    # CBAM computation
    total_embedded_tco2: float          # actual total embedded emissions
    benchmark_tco2: float               # free allocation offset
    taxable_tco2: float                 # emissions above benchmark
    gross_cbam_cost_eur: float          # taxable × EU carbon price
    domestic_credit_eur: float          # existing carbon price credit deducted
    total_cbam_cost_eur: float          # net CBAM liability (≥ 0)
    cost_per_tonne_product_eur: float   # EUR/tonne product

    # Optional: coal supplier exposure
    supplier_exposure_eur: Optional[float] = None   # estimate of supplier pass-through cost

    def to_dict(self) -> dict:
        return {
            "sector": self.sector,
            "annual_export_tonnes": self.annual_export_tonnes,
            "embedded_intensity_tco2_per_tonne": round(self.embedded_intensity_tco2_per_tonne, 4),
            "benchmark_intensity_tco2_per_tonne": round(self.benchmark_intensity_tco2_per_tonne, 4),
            "total_embedded_tco2": round(self.total_embedded_tco2, 1),
            "benchmark_tco2": round(self.benchmark_tco2, 1),
            "taxable_tco2": round(self.taxable_tco2, 1),
            "gross_cbam_cost_eur": round(self.gross_cbam_cost_eur, 0),
            "domestic_credit_eur": round(self.domestic_credit_eur, 0),
            "total_cbam_cost_eur": round(self.total_cbam_cost_eur, 0),
            "cost_per_tonne_product_eur": round(self.cost_per_tonne_product_eur, 4),
            "supplier_exposure_eur": round(self.supplier_exposure_eur, 0) if self.supplier_exposure_eur is not None else None,
        }

    def total_cbam_cost_idr(self, idr_per_eur: float = _IDR_PER_EUR) -> float:
        """Convert total CBAM cost to IDR."""
        return self.total_cbam_cost_eur * idr_per_eur


@dataclass
class PortfolioEstimate:
    """CBAM exposure across a product portfolio."""
    products: List[CBAMEstimate] = field(default_factory=list)
    total_cbam_cost_eur: float = 0.0
    total_taxable_tco2: float = 0.0
    highest_exposure_sector: str = ""

    def summary(self) -> dict:
        return {
            "n_products": len(self.products),
            "total_cbam_cost_eur": round(self.total_cbam_cost_eur, 0),
            "total_taxable_tco2": round(self.total_taxable_tco2, 1),
            "highest_exposure_sector": self.highest_exposure_sector,
        }


class CBAMCostCalculator:
    """
    Calculate CBAM compliance costs for EU-bound exports.

    Parameters
    ----------
    exporter_country : str
        Country of origin (for documentation; no tariff logic yet).
    eu_carbon_price_eur_tco2 : float
        Current EU ETS carbon price in EUR/tCO2 (0–200).
    domestic_carbon_price_eur_tco2 : float
        Effective domestic carbon price already paid (EUR/tCO2). Deducted from CBAM.
    include_supplier_passthrough : bool
        If True, estimate the fraction of CBAM cost that EU buyers pass back to suppliers.
    coal_passthrough_fraction : float
        Fraction of CBAM cost passed to coal supplier (default 0.25 = 25%).
    """

    def __init__(
        self,
        exporter_country: str,
        eu_carbon_price_eur_tco2: float,
        domestic_carbon_price_eur_tco2: float = 0.0,
        include_supplier_passthrough: bool = True,
        coal_passthrough_fraction: float = _COAL_PASSTHROUGH_FRACTION,
    ) -> None:
        if not exporter_country:
            raise ValueError("exporter_country must not be empty")
        if not (0.0 <= eu_carbon_price_eur_tco2 <= 200.0):
            raise ValueError("eu_carbon_price_eur_tco2 must be 0–200")
        if not (0.0 <= domestic_carbon_price_eur_tco2 <= 200.0):
            raise ValueError("domestic_carbon_price_eur_tco2 must be 0–200")
        if not (0.0 <= coal_passthrough_fraction <= 1.0):
            raise ValueError("coal_passthrough_fraction must be 0–1")

        self.exporter_country = exporter_country
        self.eu_carbon_price = eu_carbon_price_eur_tco2
        self.domestic_carbon_price = domestic_carbon_price_eur_tco2
        self.include_passthrough = include_supplier_passthrough
        self.passthrough = coal_passthrough_fraction

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def estimate_annual_cost(self, product: CBAMProduct) -> CBAMEstimate:
        """
        Estimate annual CBAM liability for a single product.

        CBAM liability = (embedded_tco2 - benchmark_tco2) × (EU_price - domestic_price)
        CBAM is floored at 0 (if domestic price ≥ EU ETS equivalent, no liability).

        Parameters
        ----------
        product : CBAMProduct

        Returns
        -------
        CBAMEstimate
        """
        benchmark = _EU_BENCHMARK_INTENSITY[product.sector]
        total_embedded = product.annual_export_tonnes * product.embedded_emission_intensity_tco2_per_tonne
        benchmark_tco2 = product.annual_export_tonnes * benchmark
        taxable = max(0.0, total_embedded - benchmark_tco2)

        effective_price = max(0.0, self.eu_carbon_price - self.domestic_carbon_price)
        gross = taxable * self.eu_carbon_price
        domestic_credit = taxable * self.domestic_carbon_price
        total_cost = taxable * effective_price

        cost_per_tonne = total_cost / product.annual_export_tonnes if product.annual_export_tonnes > 0 else 0.0

        supplier_exp = total_cost * self.passthrough if self.include_passthrough else None

        return CBAMEstimate(
            sector=product.sector,
            annual_export_tonnes=product.annual_export_tonnes,
            embedded_intensity_tco2_per_tonne=product.embedded_emission_intensity_tco2_per_tonne,
            benchmark_intensity_tco2_per_tonne=benchmark,
            eu_carbon_price_eur_tco2=self.eu_carbon_price,
            domestic_carbon_price_eur_tco2=self.domestic_carbon_price,
            total_embedded_tco2=round(total_embedded, 2),
            benchmark_tco2=round(benchmark_tco2, 2),
            taxable_tco2=round(taxable, 2),
            gross_cbam_cost_eur=round(gross, 2),
            domestic_credit_eur=round(domestic_credit, 2),
            total_cbam_cost_eur=round(total_cost, 2),
            cost_per_tonne_product_eur=round(cost_per_tonne, 4),
            supplier_exposure_eur=round(supplier_exp, 2) if supplier_exp is not None else None,
        )

    def portfolio_estimate(self, products: List[CBAMProduct]) -> PortfolioEstimate:
        """
        Compute aggregate CBAM exposure across a portfolio of products.

        Parameters
        ----------
        products : list of CBAMProduct

        Returns
        -------
        PortfolioEstimate
        """
        if not products:
            return PortfolioEstimate()

        estimates = [self.estimate_annual_cost(p) for p in products]
        total_cost = sum(e.total_cbam_cost_eur for e in estimates)
        total_taxable = sum(e.taxable_tco2 for e in estimates)
        top_sector = max(estimates, key=lambda e: e.total_cbam_cost_eur).sector

        return PortfolioEstimate(
            products=estimates,
            total_cbam_cost_eur=round(total_cost, 2),
            total_taxable_tco2=round(total_taxable, 2),
            highest_exposure_sector=top_sector,
        )

    def carbon_price_sensitivity(
        self,
        product: CBAMProduct,
        prices: Optional[List[float]] = None,
    ) -> List[dict]:
        """
        Sensitivity table of CBAM cost across EU carbon price scenarios.

        Parameters
        ----------
        prices : list of float, optional
            Carbon prices to test (EUR/tCO2). Default: 30, 50, 65, 80, 100, 130, 150.
        """
        if prices is None:
            prices = [30.0, 50.0, 65.0, 80.0, 100.0, 130.0, 150.0]
        rows = []
        for p in prices:
            c = CBAMCostCalculator(
                self.exporter_country, p, self.domestic_carbon_price,
                self.include_passthrough, self.passthrough,
            )
            est = c.estimate_annual_cost(product)
            rows.append({"eu_carbon_price_eur": p, "total_cbam_cost_eur": est.total_cbam_cost_eur})
        return rows

    def break_even_domestic_price(self, product: CBAMProduct) -> float:
        """
        Return the domestic carbon price (EUR/tCO2) at which CBAM liability = 0.
        This is simply equal to the EU ETS price (full offset).
        """
        return self.eu_carbon_price
