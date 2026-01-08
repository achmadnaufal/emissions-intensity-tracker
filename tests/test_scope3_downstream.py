"""Unit tests for Scope3DownstreamCalculator."""
import pytest
from src.calculations.scope3_downstream import (
    CoalShipment, Scope3DownstreamCalculator
)


@pytest.fixture
def shipment_a():
    return CoalShipment(
        "SHP-001", "sub_bituminous", 50000, "Suralaya PP",
        "barge", 320, ash_pct=14.0, customer_sector="power"
    )

@pytest.fixture
def shipment_b():
    return CoalShipment(
        "SHP-002", "bituminous", 20000, "Tarahan Port",
        "bulk_vessel", 850, ash_pct=10.0, customer_sector="cement"
    )

@pytest.fixture
def calc(shipment_a, shipment_b):
    c = Scope3DownstreamCalculator("PT Test Coal", 2026)
    c.add_shipment(shipment_a)
    c.add_shipment(shipment_b)
    return c


# --- CoalShipment validation ---

def test_invalid_grade():
    with pytest.raises(ValueError, match="coal_grade"):
        CoalShipment("x", "peat", 100, "dest", "barge", 100)

def test_invalid_transport_mode():
    with pytest.raises(ValueError, match="transport_mode"):
        CoalShipment("x", "bituminous", 100, "dest", "pipeline", 100)

def test_invalid_quantity():
    with pytest.raises(ValueError, match="quantity_t"):
        CoalShipment("x", "bituminous", -1, "dest", "barge", 100)

def test_invalid_distance():
    with pytest.raises(ValueError, match="distance_km"):
        CoalShipment("x", "bituminous", 100, "dest", "barge", -10)

def test_invalid_ash_pct():
    with pytest.raises(ValueError, match="ash_pct"):
        CoalShipment("x", "bituminous", 100, "dest", "barge", 100, ash_pct=110)


# --- Calculator management ---

def test_add_shipment(calc):
    assert len(calc) == 2

def test_add_duplicate_raises(calc, shipment_a):
    with pytest.raises(ValueError, match="already registered"):
        calc.add_shipment(shipment_a)

def test_remove_shipment(calc):
    removed = calc.remove_shipment("SHP-001")
    assert removed is True
    assert len(calc) == 1

def test_remove_nonexistent(calc):
    assert calc.remove_shipment("UNKNOWN") is False

def test_repr(calc):
    assert "Scope3DownstreamCalculator" in repr(calc)


# --- Category 9 ---

def test_cat9_positive(calc):
    cat9 = calc.calculate_cat9_transport()
    assert cat9["total_tCO2e"] > 0

def test_cat9_by_shipment_keys(calc):
    cat9 = calc.calculate_cat9_transport()
    assert "SHP-001" in cat9["by_shipment"]
    assert "SHP-002" in cat9["by_shipment"]

def test_cat9_total_equals_sum(calc):
    cat9 = calc.calculate_cat9_transport()
    ship_sum = sum(cat9["by_shipment"].values())
    assert abs(cat9["total_tCO2e"] - ship_sum) < 0.01


# --- Category 11 ---

def test_cat11_sub_bituminous_factor():
    c = Scope3DownstreamCalculator()
    c.add_shipment(CoalShipment("s1", "sub_bituminous", 1000, "d", "barge", 0))
    cat11 = c.calculate_cat11_use_of_sold_products()
    assert abs(cat11["total_tCO2e"] - 1920.0) < 1.0  # 1000 * 1.92

def test_cat11_higher_grade_more_emissions():
    c = Scope3DownstreamCalculator()
    c.add_shipment(CoalShipment("s1", "anthracite", 1000, "d", "barge", 0))
    cat11_high = c.calculate_cat11_use_of_sold_products()["total_tCO2e"]
    c2 = Scope3DownstreamCalculator()
    c2.add_shipment(CoalShipment("s1", "lignite", 1000, "d", "barge", 0))
    cat11_low = c2.calculate_cat11_use_of_sold_products()["total_tCO2e"]
    assert cat11_high > cat11_low

def test_cat11_is_largest_scope3(calc):
    report = calc.generate_report()
    assert report["cat11_tCO2e"] > report["cat9_tCO2e"]
    assert report["cat11_tCO2e"] > report["cat12_tCO2e"]


# --- Category 12 ---

def test_cat12_positive(calc):
    cat12 = calc.calculate_cat12_end_of_life()
    assert cat12["total_tCO2e"] > 0

def test_cat12_scales_with_ash_pct():
    c1 = Scope3DownstreamCalculator()
    c1.add_shipment(CoalShipment("s1", "bituminous", 1000, "d", "barge", 0, ash_pct=20.0))
    c2 = Scope3DownstreamCalculator()
    c2.add_shipment(CoalShipment("s1", "bituminous", 1000, "d", "barge", 0, ash_pct=10.0))
    assert c1.calculate_cat12_end_of_life()["total_tCO2e"] > \
           c2.calculate_cat12_end_of_life()["total_tCO2e"]


# --- Full report ---

def test_report_empty():
    c = Scope3DownstreamCalculator()
    report = c.generate_report()
    assert report["total_scope3_downstream_tCO2e"] == 0.0

def test_report_keys(calc):
    report = calc.generate_report()
    for key in ["cat9_tCO2e", "cat11_tCO2e", "cat12_tCO2e",
                "total_scope3_downstream_tCO2e", "cat11_share_pct", "by_sector"]:
        assert key in report

def test_report_total_is_sum(calc):
    report = calc.generate_report()
    expected = round(report["cat9_tCO2e"] + report["cat11_tCO2e"] + report["cat12_tCO2e"], 2)
    assert abs(report["total_scope3_downstream_tCO2e"] - expected) < 0.01

def test_report_sector_breakdown(calc):
    report = calc.generate_report()
    assert "power" in report["by_sector"]
    assert "cement" in report["by_sector"]

def test_cat11_share_pct(calc):
    report = calc.generate_report()
    assert 90 < report["cat11_share_pct"] <= 100  # combustion always dominates


# --- Intensity ---

def test_intensity_empty():
    c = Scope3DownstreamCalculator()
    assert c.intensity_tCO2e_per_tonne() == 0.0

def test_intensity_reasonable_range(calc):
    intensity = calc.intensity_tCO2e_per_tonne()
    # Sub-bituminous + bituminous mix: ~1.8–2.5 tCO2e/t is expected
    assert 1.5 < intensity < 3.5
