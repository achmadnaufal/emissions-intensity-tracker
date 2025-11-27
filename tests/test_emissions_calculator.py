import pytest
from src.calculations.scope_calculator import EmissionsCalculator

def test_scope1_diesel():
    calc = EmissionsCalculator("Mine A")
    emissions = calc.calculate_scope1_diesel(liters=10000)
    assert emissions == 10000 * 2.68

def test_scope2_electricity():
    calc = EmissionsCalculator("Mine A")
    emissions = calc.calculate_scope2_electricity(kwh=500000)
    assert emissions == 500000 * 0.85

def test_scope3_shipping():
    calc = EmissionsCalculator("Mine A")
    emissions = calc.calculate_scope3_shipping(tons=1000, distance_km=500)
    expected = 1000 * 500 * 0.1
    assert emissions == expected

def test_negative_inputs():
    calc = EmissionsCalculator("Mine A")
    with pytest.raises(ValueError):
        calc.calculate_scope1_diesel(liters=-100)
