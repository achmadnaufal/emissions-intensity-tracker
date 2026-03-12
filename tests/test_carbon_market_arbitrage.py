"""Unit tests for CarbonMarketArbitrageAnalyzer."""

import pytest
from src.carbon_market_arbitrage import (
    CarbonMarket,
    CarbonMarketArbitrageAnalyzer,
    CreditPosition,
    CreditQuality,
    MarketType,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def eu_ets():
    return CarbonMarket(
        market_id="EU_ETS",
        market_name="EU ETS",
        market_type=MarketType.COMPLIANCE,
        current_price_usd=72,
        price_floor_usd=None,
        price_ceiling_usd=None,
        annual_growth_rate_pct=8,
        liquidity_score=95,
        eligible_project_types=["industrial", "power", "forest"],
    )


@pytest.fixture
def vcs():
    return CarbonMarket(
        market_id="VCS",
        market_name="Verra VCS",
        market_type=MarketType.VOLUNTARY,
        current_price_usd=14,
        price_floor_usd=None,
        price_ceiling_usd=None,
        annual_growth_rate_pct=15,
        liquidity_score=70,
        eligible_project_types=["forest", "renewable", "methane"],
    )


@pytest.fixture
def gold_standard():
    return CarbonMarket(
        market_id="GS",
        market_name="Gold Standard",
        market_type=MarketType.VOLUNTARY,
        current_price_usd=18,
        price_floor_usd=None,
        price_ceiling_usd=None,
        annual_growth_rate_pct=12,
        liquidity_score=65,
        eligible_project_types=["forest", "renewable", "cookstove"],
    )


@pytest.fixture
def forest_position():
    return CreditPosition(
        credit_id="CR-001",
        project_type="forest",
        vintage_year=2023,
        quantity_tco2e=50000,
        cost_basis_usd_per_tco2e=8,
        certification="VCS",
    )


@pytest.fixture
def analyzer(eu_ets, vcs, gold_standard):
    return CarbonMarketArbitrageAnalyzer(
        markets=[eu_ets, vcs, gold_standard],
        analysis_horizon_years=5,
    )


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class TestValidation:
    def test_empty_markets_raises(self):
        with pytest.raises(ValueError, match="market"):
            CarbonMarketArbitrageAnalyzer(markets=[])

    def test_negative_price_raises(self):
        with pytest.raises(ValueError):
            CarbonMarket(
                market_id="X", market_name="X", market_type=MarketType.VOLUNTARY,
                current_price_usd=-5, price_floor_usd=None, price_ceiling_usd=None,
                annual_growth_rate_pct=5, liquidity_score=50,
                eligible_project_types=["forest"],
            )

    def test_invalid_liquidity_raises(self):
        with pytest.raises(ValueError, match="liquidity"):
            CarbonMarket(
                market_id="X", market_name="X", market_type=MarketType.VOLUNTARY,
                current_price_usd=10, price_floor_usd=None, price_ceiling_usd=None,
                annual_growth_rate_pct=5, liquidity_score=150,
                eligible_project_types=["forest"],
            )

    def test_zero_quantity_raises(self):
        with pytest.raises(ValueError):
            CreditPosition(
                credit_id="X", project_type="forest", vintage_year=2022,
                quantity_tco2e=0, cost_basis_usd_per_tco2e=8, certification="VCS"
            )

    def test_no_eligible_market_raises(self, analyzer):
        pos = CreditPosition(
            credit_id="X", project_type="nuclear", vintage_year=2023,
            quantity_tco2e=1000, cost_basis_usd_per_tco2e=8, certification="VCS"
        )
        with pytest.raises(ValueError, match="eligible"):
            analyzer.optimise_placement(pos)


# ---------------------------------------------------------------------------
# Effective price
# ---------------------------------------------------------------------------


class TestEffectivePrice:
    def test_premium_quality_increases_price(self, analyzer, eu_ets, forest_position):
        forest_position.quality = CreditQuality.PREMIUM
        premium_price = analyzer._effective_price(eu_ets, forest_position)
        forest_position.quality = CreditQuality.STANDARD
        std_price = analyzer._effective_price(eu_ets, forest_position)
        assert premium_price > std_price

    def test_discounted_quality_reduces_price(self, analyzer, vcs, forest_position):
        forest_position.quality = CreditQuality.DISCOUNTED
        disc_price = analyzer._effective_price(vcs, forest_position)
        forest_position.quality = CreditQuality.STANDARD
        std_price = analyzer._effective_price(vcs, forest_position)
        assert disc_price < std_price

    def test_old_vintage_applies_discount(self, analyzer, vcs):
        old_pos = CreditPosition(
            credit_id="OLD", project_type="forest", vintage_year=2010,
            quantity_tco2e=1000, cost_basis_usd_per_tco2e=5, certification="VCS"
        )
        new_pos = CreditPosition(
            credit_id="NEW", project_type="forest", vintage_year=2023,
            quantity_tco2e=1000, cost_basis_usd_per_tco2e=5, certification="VCS"
        )
        old_price = analyzer._effective_price(vcs, old_pos)
        new_price = analyzer._effective_price(vcs, new_pos)
        assert old_price < new_price


# ---------------------------------------------------------------------------
# Forward price
# ---------------------------------------------------------------------------


class TestForwardPrice:
    def test_forward_price_higher_for_positive_growth(self, analyzer, vcs):
        fp = analyzer._forward_price(vcs, 5)
        assert fp > vcs.current_price_usd

    def test_forward_price_at_zero_years_equals_current(self, analyzer, vcs):
        fp = analyzer._forward_price(vcs, 0)
        assert fp == pytest.approx(vcs.current_price_usd)


# ---------------------------------------------------------------------------
# Arbitrage detection
# ---------------------------------------------------------------------------


class TestArbitrage:
    def test_arbitrage_detected_between_eu_ets_and_vcs(
        self, analyzer, forest_position
    ):
        eligible = analyzer._eligible_markets(forest_position)
        opps = analyzer._detect_arbitrage(forest_position, eligible)
        # EU ETS at $72 vs VCS at $14 — should detect spread
        assert len(opps) > 0

    def test_arbitrage_net_spread_positive(self, analyzer, forest_position):
        eligible = analyzer._eligible_markets(forest_position)
        opps = analyzer._detect_arbitrage(forest_position, eligible)
        for opp in opps:
            assert opp.net_spread_usd > 0

    def test_arbitrage_sorted_by_net_spread_descending(self, analyzer, forest_position):
        eligible = analyzer._eligible_markets(forest_position)
        opps = analyzer._detect_arbitrage(forest_position, eligible)
        spreads = [o.net_spread_usd for o in opps]
        assert spreads == sorted(spreads, reverse=True)

    def test_compliance_market_caveat_included(self, analyzer, forest_position):
        eligible = analyzer._eligible_markets(forest_position)
        opps = analyzer._detect_arbitrage(forest_position, eligible)
        eu_opps = [o for o in opps if "EU ETS" in o.target_market]
        if eu_opps:
            caveats_text = " ".join(eu_opps[0].caveats).lower()
            assert "compliance" in caveats_text or "regulatory" in caveats_text


# ---------------------------------------------------------------------------
# optimise_placement()
# ---------------------------------------------------------------------------


class TestOptimisePlacement:
    def test_returns_result(self, analyzer, forest_position):
        result = analyzer.optimise_placement(forest_position)
        assert result is not None

    def test_best_market_is_eu_ets_for_forest(self, analyzer, forest_position):
        result = analyzer.optimise_placement(forest_position)
        # EU ETS has the highest absolute price
        assert result.best_price_usd > 0

    def test_net_proceeds_equals_price_times_quantity(self, analyzer, forest_position):
        result = analyzer.optimise_placement(forest_position)
        expected = result.best_price_usd * forest_position.quantity_tco2e
        assert result.net_proceeds_usd == pytest.approx(expected, rel=1e-4)

    def test_gross_profit_positive(self, analyzer, forest_position):
        result = analyzer.optimise_placement(forest_position)
        assert result.gross_profit_usd > 0

    def test_roi_pct_positive(self, analyzer, forest_position):
        result = analyzer.optimise_placement(forest_position)
        assert result.roi_pct > 0

    def test_eligible_markets_not_empty(self, analyzer, forest_position):
        result = analyzer.optimise_placement(forest_position)
        assert len(result.eligible_markets) > 0

    def test_reasons_populated(self, analyzer, forest_position):
        result = analyzer.optimise_placement(forest_position)
        assert len(result.reasons) > 0


# ---------------------------------------------------------------------------
# market_summary()
# ---------------------------------------------------------------------------


class TestMarketSummary:
    def test_summary_includes_all_markets(self, analyzer):
        summary = analyzer.market_summary()
        assert len(summary) == 3

    def test_summary_sorted_by_price_descending(self, analyzer):
        summary = analyzer.market_summary()
        prices = [row["current_price_usd"] for row in summary]
        assert prices == sorted(prices, reverse=True)

    def test_5yr_forward_present(self, analyzer):
        summary = analyzer.market_summary()
        for row in summary:
            assert "5yr_forward_usd" in row
            assert row["5yr_forward_usd"] > 0
