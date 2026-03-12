"""
Carbon Market Arbitrage Analyzer
==================================
Identifies price spread opportunities and cross-market arbitrage windows
between voluntary carbon markets (VCM) and compliance carbon markets
(ETS/cap-and-trade), assisting project developers and traders in optimising
credit monetisation timing and market selection.

Supported markets:
    - EU ETS (European Union Emissions Trading System)
    - UK ETS
    - CORSIA (ICAO aviation baseline)
    - California Cap-and-Trade (WCI)
    - RGGI (Regional Greenhouse Gas Initiative, US NE)
    - VCS / Verra (voluntary)
    - Gold Standard (voluntary)
    - Article 6.2 bilateral (Paris Agreement)

References:
    - ICAP (2024). Emissions Trading Worldwide: ICAP Status Report 2024.
    - Taskforce on Scaling Voluntary Carbon Markets (2021). Final Report.
    - Refinitiv Carbon Research (2023). Carbon Market Year in Review.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class MarketType(str, Enum):
    COMPLIANCE = "compliance"
    VOLUNTARY = "voluntary"
    ARTICLE_6 = "article_6"


class CreditQuality(str, Enum):
    PREMIUM = "PREMIUM"     # High co-benefits, high additionality
    STANDARD = "STANDARD"   # Meets baseline certification requirements
    DISCOUNTED = "DISCOUNTED"  # Older vintages or low co-benefit labels


@dataclass
class CarbonMarket:
    """Snapshot of a single carbon market's pricing and characteristics."""

    market_id: str
    market_name: str
    market_type: MarketType
    current_price_usd: float          # USD per tCO2e
    price_floor_usd: Optional[float]  # regulatory price floor (if any)
    price_ceiling_usd: Optional[float]  # ceiling / cost-containment
    annual_growth_rate_pct: float     # expected YoY price growth
    liquidity_score: float            # 0–100 (100 = deepest liquidity)
    eligible_project_types: List[str]  # e.g., ["forest", "renewable"]
    transaction_cost_pct: float = 2.0  # % of transaction value

    def __post_init__(self) -> None:
        if self.current_price_usd <= 0:
            raise ValueError("current_price_usd must be positive")
        if not (0 <= self.liquidity_score <= 100):
            raise ValueError("liquidity_score must be 0–100")
        if self.annual_growth_rate_pct < -50:
            raise ValueError("annual_growth_rate_pct cannot be < -50%")


@dataclass
class CreditPosition:
    """A trader's or developer's current carbon credit holding."""

    credit_id: str
    project_type: str              # e.g., "forest", "renewable", "methane"
    vintage_year: int
    quantity_tco2e: float
    cost_basis_usd_per_tco2e: float
    certification: str             # e.g., "VCS", "Gold Standard"
    quality: CreditQuality = CreditQuality.STANDARD

    def __post_init__(self) -> None:
        if self.quantity_tco2e <= 0:
            raise ValueError("quantity_tco2e must be positive")
        if self.cost_basis_usd_per_tco2e < 0:
            raise ValueError("cost_basis_usd_per_tco2e cannot be negative")


@dataclass
class ArbitrageOpportunity:
    """A detected cross-market arbitrage or optimisation opportunity."""

    source_market: str
    target_market: str
    spread_usd: float                # price difference
    net_spread_usd: float            # after transaction costs
    annualised_return_pct: float
    recommended_action: str
    confidence: str                  # HIGH / MEDIUM / LOW
    caveats: List[str]


@dataclass
class MarketOptimisationResult:
    """Best market + timing recommendation for a credit position."""

    credit_id: str
    best_market: str
    best_price_usd: float
    net_proceeds_usd: float          # after transaction costs
    gross_profit_usd: float
    roi_pct: float
    hold_years_recommended: float
    future_price_estimate_usd: float
    arbitrage_opportunities: List[ArbitrageOpportunity]
    eligible_markets: List[str]
    reasons: List[str]


class CarbonMarketArbitrageAnalyzer:
    """
    Identifies optimal market placement and arbitrage windows for carbon
    credit portfolios across compliance and voluntary markets.

    Parameters
    ----------
    markets : list of CarbonMarket
        Snapshot of all markets to consider.
    analysis_horizon_years : int, optional
        Time horizon for forward price projections (default 5 years).

    Examples
    --------
    >>> from src.carbon_market_arbitrage import (
    ...     CarbonMarketArbitrageAnalyzer, CarbonMarket, CreditPosition,
    ...     MarketType, CreditQuality
    ... )
    >>> eu_ets = CarbonMarket(
    ...     market_id="EU_ETS",
    ...     market_name="EU ETS",
    ...     market_type=MarketType.COMPLIANCE,
    ...     current_price_usd=72,
    ...     price_floor_usd=None,
    ...     price_ceiling_usd=None,
    ...     annual_growth_rate_pct=8,
    ...     liquidity_score=95,
    ...     eligible_project_types=["industrial", "power"],
    ... )
    >>> vcs = CarbonMarket(
    ...     market_id="VCS",
    ...     market_name="Verra VCS",
    ...     market_type=MarketType.VOLUNTARY,
    ...     current_price_usd=14,
    ...     price_floor_usd=None,
    ...     price_ceiling_usd=None,
    ...     annual_growth_rate_pct=15,
    ...     liquidity_score=70,
    ...     eligible_project_types=["forest", "renewable", "methane"],
    ... )
    >>> pos = CreditPosition(
    ...     credit_id="CR-001",
    ...     project_type="forest",
    ...     vintage_year=2023,
    ...     quantity_tco2e=50000,
    ...     cost_basis_usd_per_tco2e=8,
    ...     certification="VCS",
    ... )
    >>> analyzer = CarbonMarketArbitrageAnalyzer([eu_ets, vcs])
    >>> result = analyzer.optimise_placement(pos)
    >>> print(f"Best market: {result.best_market} @ ${result.best_price_usd}/tCO2e")
    """

    # Vintage discount: credits older than this lose value at discount_rate_pct
    _VINTAGE_THRESHOLD_YEARS = 5
    _VINTAGE_DISCOUNT_PCT = 0.05  # 5% per year beyond threshold

    def __init__(
        self,
        markets: List[CarbonMarket],
        analysis_horizon_years: int = 5,
    ) -> None:
        if not markets:
            raise ValueError("At least one market is required")
        if analysis_horizon_years < 1:
            raise ValueError("analysis_horizon_years must be >= 1")
        self.markets = {m.market_id: m for m in markets}
        self.horizon = analysis_horizon_years

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _effective_price(
        self, market: CarbonMarket, position: CreditPosition, current_year: int = 2026
    ) -> float:
        """
        Compute effective price after vintage discount and quality adjustment.
        """
        base = market.current_price_usd
        # Quality adjustment
        if position.quality == CreditQuality.PREMIUM:
            base *= 1.20
        elif position.quality == CreditQuality.DISCOUNTED:
            base *= 0.75

        # Vintage discount
        age = current_year - position.vintage_year
        excess_years = max(0, age - self._VINTAGE_THRESHOLD_YEARS)
        vintage_adj = (1 - self._VINTAGE_DISCOUNT_PCT) ** excess_years

        return base * vintage_adj

    def _net_price(self, market: CarbonMarket, gross_price: float) -> float:
        """Price after transaction costs."""
        return gross_price * (1 - market.transaction_cost_pct / 100)

    def _forward_price(self, market: CarbonMarket, years: float) -> float:
        """Simple compound forward price projection."""
        return market.current_price_usd * (
            (1 + market.annual_growth_rate_pct / 100) ** years
        )

    def _eligible_markets(self, position: CreditPosition) -> List[CarbonMarket]:
        """Filter markets where the credit project type is eligible."""
        eligible = []
        for market in self.markets.values():
            if (
                position.project_type in market.eligible_project_types
                or "all" in market.eligible_project_types
            ):
                eligible.append(market)
        return eligible

    def _detect_arbitrage(
        self, position: CreditPosition, eligible: List[CarbonMarket]
    ) -> List[ArbitrageOpportunity]:
        """Compare all market pairs for spread opportunities."""
        opportunities = []

        for i, m_src in enumerate(eligible):
            for m_tgt in eligible[i + 1:]:
                src_price = self._effective_price(m_src, position)
                tgt_price = self._effective_price(m_tgt, position)

                if tgt_price > src_price:
                    # Buying in source and selling in target
                    spread = tgt_price - src_price
                    net_src = self._net_price(m_src, src_price)
                    net_tgt = self._net_price(m_tgt, tgt_price)
                    net_spread = net_tgt - net_src
                else:
                    spread = src_price - tgt_price
                    net_src = self._net_price(m_tgt, tgt_price)
                    net_tgt = self._net_price(m_src, src_price)
                    net_spread = net_tgt - net_src
                    m_src, m_tgt = m_tgt, m_src

                if net_spread <= 0:
                    continue

                annualised = (net_spread / max(net_src, 0.01)) * 100

                if annualised >= 20:
                    confidence = "HIGH"
                elif annualised >= 10:
                    confidence = "MEDIUM"
                else:
                    confidence = "LOW"

                caveats = []
                if m_tgt.market_type == MarketType.COMPLIANCE:
                    caveats.append(
                        f"Compliance market ({m_tgt.market_name}) eligibility "
                        "may require additional regulatory approval."
                    )
                if position.vintage_year < 2020:
                    caveats.append(
                        "Pre-2020 vintage may face additional scrutiny under SBTi and "
                        "VCMI integrity frameworks."
                    )
                if m_tgt.liquidity_score < 50:
                    caveats.append(
                        f"{m_tgt.market_name} has low liquidity (score {m_tgt.liquidity_score}) "
                        "— execution risk is elevated."
                    )

                opportunities.append(
                    ArbitrageOpportunity(
                        source_market=m_src.market_name,
                        target_market=m_tgt.market_name,
                        spread_usd=round(spread, 2),
                        net_spread_usd=round(net_spread, 2),
                        annualised_return_pct=round(annualised, 1),
                        recommended_action=(
                            f"Sell in {m_tgt.market_name} rather than "
                            f"{m_src.market_name} for +${net_spread:.2f}/tCO2e net gain"
                        ),
                        confidence=confidence,
                        caveats=caveats,
                    )
                )

        return sorted(opportunities, key=lambda x: x.net_spread_usd, reverse=True)

    def _optimal_hold_period(
        self, position: CreditPosition, market: CarbonMarket
    ) -> Tuple[float, float]:
        """
        Find hold period (years) that maximises NPV at 8% discount rate.
        Returns (optimal_years, forward_price).
        """
        discount_rate = 0.08
        cost = position.cost_basis_usd_per_tco2e
        best_npv = -math.inf
        best_years = 0
        best_fp = market.current_price_usd

        for y in range(0, self.horizon + 1):
            fp = self._forward_price(market, y)
            net = self._net_price(market, fp)
            npv = (net - cost) / ((1 + discount_rate) ** y)
            if npv > best_npv:
                best_npv = npv
                best_years = y
                best_fp = fp

        return float(best_years), round(best_fp, 2)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def optimise_placement(self, position: CreditPosition) -> MarketOptimisationResult:
        """
        Determine the best market and timing for a credit position.

        Parameters
        ----------
        position : CreditPosition
            The carbon credits to be analysed.

        Returns
        -------
        MarketOptimisationResult
            Best market, net proceeds, ROI, hold recommendations, and
            arbitrage opportunities.
        """
        eligible = self._eligible_markets(position)
        if not eligible:
            raise ValueError(
                f"No eligible markets for project type '{position.project_type}'"
            )

        arbitrage_opps = self._detect_arbitrage(position, eligible)

        best_market = None
        best_net = -math.inf
        best_hold = 0
        best_fp = 0.0

        for market in eligible:
            effective = self._effective_price(market, position)
            hold_years, fp = self._optimal_hold_period(position, market)
            adj_fp = self._effective_price(
                market,
                CreditPosition(
                    credit_id=position.credit_id,
                    project_type=position.project_type,
                    vintage_year=position.vintage_year,
                    quantity_tco2e=position.quantity_tco2e,
                    cost_basis_usd_per_tco2e=position.cost_basis_usd_per_tco2e,
                    certification=position.certification,
                    quality=position.quality,
                ),
            )
            net = self._net_price(market, adj_fp)
            if net > best_net:
                best_net = net
                best_market = market
                best_hold = hold_years
                best_fp = fp

        if best_market is None:
            raise RuntimeError("No suitable market found")

        gross_profit = (best_net - position.cost_basis_usd_per_tco2e) * position.quantity_tco2e
        roi_pct = (
            (best_net - position.cost_basis_usd_per_tco2e) / position.cost_basis_usd_per_tco2e
        ) * 100 if position.cost_basis_usd_per_tco2e > 0 else 0.0

        reasons = [
            f"Highest net effective price after quality/vintage adjustments "
            f"(${best_net:.2f}/tCO2e) among {len(eligible)} eligible markets",
        ]
        if best_hold > 0:
            reasons.append(
                f"Holding for {best_hold:.0f} year(s) improves NPV "
                f"(forward price: ${best_fp:.2f}/tCO2e)"
            )
        if position.quality == CreditQuality.PREMIUM:
            reasons.append(
                "PREMIUM quality label attracts 20% price premium — "
                "co-benefit narrative should be highlighted in marketing."
            )

        return MarketOptimisationResult(
            credit_id=position.credit_id,
            best_market=best_market.market_name,
            best_price_usd=round(best_net, 2),
            net_proceeds_usd=round(best_net * position.quantity_tco2e, 2),
            gross_profit_usd=round(gross_profit, 2),
            roi_pct=round(roi_pct, 2),
            hold_years_recommended=best_hold,
            future_price_estimate_usd=best_fp,
            arbitrage_opportunities=arbitrage_opps,
            eligible_markets=[m.market_name for m in eligible],
            reasons=reasons,
        )

    def market_summary(self) -> List[Dict]:
        """Return a summary table of all loaded markets."""
        rows = []
        for m in self.markets.values():
            rows.append(
                {
                    "market_id": m.market_id,
                    "market_name": m.market_name,
                    "type": m.market_type.value,
                    "current_price_usd": m.current_price_usd,
                    "5yr_forward_usd": round(self._forward_price(m, 5), 2),
                    "liquidity_score": m.liquidity_score,
                    "growth_rate_pct": m.annual_growth_rate_pct,
                }
            )
        return sorted(rows, key=lambda x: x["current_price_usd"], reverse=True)
