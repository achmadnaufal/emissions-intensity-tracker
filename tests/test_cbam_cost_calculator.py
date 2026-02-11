"""
Unit tests for CBAMCostCalculator.
"""

import pytest
from src.cbam_cost_calculator import (
    CBAMCostCalculator,
    CBAMProduct,
    CBAMEstimate,
    PortfolioEstimate,
    VALID_SECTORS,
    _EU_BENCHMARK_INTENSITY,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def standard_calc():
    return CBAMCostCalculator(
        exporter_country="Indonesia",
        eu_carbon_price_eur_tco2=65.0,
        domestic_carbon_price_eur_tco2=0.0,
    )


@pytest.fixture
def domestic_price_calc():
    return CBAMCostCalculator(
        exporter_country="Indonesia",
        eu_carbon_price_eur_tco2=65.0,
        domestic_carbon_price_eur_tco2=20.0,
    )


@pytest.fixture
def steel_product():
    return CBAMProduct(
        sector="iron_steel",
        annual_export_tonnes=500_000.0,
        embedded_emission_intensity_tco2_per_tonne=1.85,
        product_name="HRC Steel",
    )


@pytest.fixture
def clean_aluminium():
    """Aluminium with emission intensity below EU benchmark → no taxable emissions."""
    return CBAMProduct(
        sector="aluminium",
        annual_export_tonnes=10_000.0,
        embedded_emission_intensity_tco2_per_tonne=1.0,  # below benchmark 1.484
    )


# ---------------------------------------------------------------------------
# CBAMProduct validation
# ---------------------------------------------------------------------------

class TestCBAMProduct:
    def test_valid_creation(self, steel_product):
        assert steel_product.sector == "iron_steel"

    def test_invalid_sector_raises(self):
        with pytest.raises(ValueError, match="sector"):
            CBAMProduct("coal", 100_000.0, 1.5)

    def test_zero_export_raises(self):
        with pytest.raises(ValueError, match="export_tonnes"):
            CBAMProduct("cement", 0.0, 0.766)

    def test_negative_intensity_raises(self):
        with pytest.raises(ValueError, match="intensity"):
            CBAMProduct("cement", 100_000.0, -0.5)

    def test_all_valid_sectors(self):
        for s in VALID_SECTORS:
            p = CBAMProduct(s, 1000.0, 1.0)
            assert p.sector == s


# ---------------------------------------------------------------------------
# CBAMCostCalculator instantiation
# ---------------------------------------------------------------------------

class TestCalculatorInstantiation:
    def test_valid_creation(self, standard_calc):
        assert standard_calc.exporter_country == "Indonesia"

    def test_empty_country_raises(self):
        with pytest.raises(ValueError, match="exporter_country"):
            CBAMCostCalculator("", 65.0)

    def test_price_over_200_raises(self):
        with pytest.raises(ValueError, match="eu_carbon_price"):
            CBAMCostCalculator("Indonesia", 250.0)

    def test_negative_price_raises(self):
        with pytest.raises(ValueError, match="eu_carbon_price"):
            CBAMCostCalculator("Indonesia", -10.0)

    def test_negative_domestic_raises(self):
        with pytest.raises(ValueError, match="domestic_carbon_price"):
            CBAMCostCalculator("Indonesia", 65.0, -5.0)

    def test_passthrough_over_1_raises(self):
        with pytest.raises(ValueError, match="passthrough"):
            CBAMCostCalculator("Indonesia", 65.0, coal_passthrough_fraction=1.5)


# ---------------------------------------------------------------------------
# estimate_annual_cost()
# ---------------------------------------------------------------------------

class TestEstimateAnnualCost:
    def test_returns_cbam_estimate(self, standard_calc, steel_product):
        est = standard_calc.estimate_annual_cost(steel_product)
        assert isinstance(est, CBAMEstimate)

    def test_total_embedded_correct(self, standard_calc, steel_product):
        est = standard_calc.estimate_annual_cost(steel_product)
        expected = 500_000 * 1.85
        assert est.total_embedded_tco2 == pytest.approx(expected, rel=0.001)

    def test_benchmark_correct(self, standard_calc, steel_product):
        est = standard_calc.estimate_annual_cost(steel_product)
        expected = 500_000 * _EU_BENCHMARK_INTENSITY["iron_steel"]
        assert est.benchmark_tco2 == pytest.approx(expected, rel=0.001)

    def test_taxable_above_benchmark(self, standard_calc, steel_product):
        est = standard_calc.estimate_annual_cost(steel_product)
        expected = max(0.0, est.total_embedded_tco2 - est.benchmark_tco2)
        assert est.taxable_tco2 == pytest.approx(expected, rel=0.001)

    def test_total_cost_positive(self, standard_calc, steel_product):
        est = standard_calc.estimate_annual_cost(steel_product)
        assert est.total_cbam_cost_eur > 0

    def test_total_cost_floored_at_zero_for_clean_product(self, standard_calc, clean_aluminium):
        est = standard_calc.estimate_annual_cost(clean_aluminium)
        assert est.taxable_tco2 == 0.0
        assert est.total_cbam_cost_eur == 0.0

    def test_domestic_price_reduces_cost(self, standard_calc, domestic_price_calc, steel_product):
        est_no_domestic = standard_calc.estimate_annual_cost(steel_product)
        est_domestic = domestic_price_calc.estimate_annual_cost(steel_product)
        assert est_domestic.total_cbam_cost_eur < est_no_domestic.total_cbam_cost_eur

    def test_full_domestic_price_zero_liability(self, steel_product):
        # Domestic price = EU price → full offset
        calc = CBAMCostCalculator("Indonesia", 65.0, domestic_carbon_price_eur_tco2=65.0)
        est = calc.estimate_annual_cost(steel_product)
        assert est.total_cbam_cost_eur == pytest.approx(0.0, abs=0.01)

    def test_cost_per_tonne_product(self, standard_calc, steel_product):
        est = standard_calc.estimate_annual_cost(steel_product)
        expected = est.total_cbam_cost_eur / steel_product.annual_export_tonnes
        assert est.cost_per_tonne_product_eur == pytest.approx(expected, rel=0.001)

    def test_supplier_exposure_present(self, standard_calc, steel_product):
        est = standard_calc.estimate_annual_cost(steel_product)
        assert est.supplier_exposure_eur is not None
        assert est.supplier_exposure_eur < est.total_cbam_cost_eur

    def test_no_passthrough_none(self, steel_product):
        calc = CBAMCostCalculator("Indonesia", 65.0, include_supplier_passthrough=False)
        est = calc.estimate_annual_cost(steel_product)
        assert est.supplier_exposure_eur is None

    def test_to_dict_keys(self, standard_calc, steel_product):
        d = standard_calc.estimate_annual_cost(steel_product).to_dict()
        for k in ("sector", "total_cbam_cost_eur", "taxable_tco2", "cost_per_tonne_product_eur"):
            assert k in d

    def test_idr_conversion(self, standard_calc, steel_product):
        est = standard_calc.estimate_annual_cost(steel_product)
        idr = est.total_cbam_cost_idr()
        assert idr > est.total_cbam_cost_eur  # IDR >> EUR

    def test_higher_price_higher_cost(self, steel_product):
        c_low = CBAMCostCalculator("Indonesia", 30.0)
        c_high = CBAMCostCalculator("Indonesia", 100.0)
        est_low = c_low.estimate_annual_cost(steel_product)
        est_high = c_high.estimate_annual_cost(steel_product)
        assert est_high.total_cbam_cost_eur > est_low.total_cbam_cost_eur


# ---------------------------------------------------------------------------
# portfolio_estimate()
# ---------------------------------------------------------------------------

class TestPortfolioEstimate:
    def test_returns_portfolio_estimate(self, standard_calc, steel_product):
        pe = standard_calc.portfolio_estimate([steel_product])
        assert isinstance(pe, PortfolioEstimate)

    def test_empty_portfolio(self, standard_calc):
        pe = standard_calc.portfolio_estimate([])
        assert pe.total_cbam_cost_eur == 0.0

    def test_total_is_sum_of_products(self, standard_calc, steel_product):
        cement = CBAMProduct("cement", 200_000.0, 0.85)
        pe = standard_calc.portfolio_estimate([steel_product, cement])
        est1 = standard_calc.estimate_annual_cost(steel_product)
        est2 = standard_calc.estimate_annual_cost(cement)
        assert pe.total_cbam_cost_eur == pytest.approx(est1.total_cbam_cost_eur + est2.total_cbam_cost_eur, abs=1.0)

    def test_highest_exposure_sector_correct(self, standard_calc, steel_product):
        cement_small = CBAMProduct("cement", 100.0, 0.8)
        pe = standard_calc.portfolio_estimate([steel_product, cement_small])
        assert pe.highest_exposure_sector == "iron_steel"

    def test_summary_keys(self, standard_calc, steel_product):
        s = standard_calc.portfolio_estimate([steel_product]).summary()
        for k in ("total_cbam_cost_eur", "total_taxable_tco2", "highest_exposure_sector"):
            assert k in s


# ---------------------------------------------------------------------------
# carbon_price_sensitivity()
# ---------------------------------------------------------------------------

class TestCarbonPriceSensitivity:
    def test_returns_list(self, standard_calc, steel_product):
        rows = standard_calc.carbon_price_sensitivity(steel_product)
        assert isinstance(rows, list)

    def test_default_seven_prices(self, standard_calc, steel_product):
        rows = standard_calc.carbon_price_sensitivity(steel_product)
        assert len(rows) == 7

    def test_cost_increases_with_price(self, standard_calc, steel_product):
        rows = standard_calc.carbon_price_sensitivity(steel_product, prices=[30.0, 65.0, 100.0])
        costs = [r["total_cbam_cost_eur"] for r in rows]
        assert costs == sorted(costs)

    def test_custom_prices(self, standard_calc, steel_product):
        rows = standard_calc.carbon_price_sensitivity(steel_product, prices=[50.0, 100.0])
        assert len(rows) == 2


# ---------------------------------------------------------------------------
# break_even_domestic_price()
# ---------------------------------------------------------------------------

class TestBreakEven:
    def test_equals_eu_price(self, standard_calc, steel_product):
        bep = standard_calc.break_even_domestic_price(steel_product)
        assert bep == pytest.approx(standard_calc.eu_carbon_price)
