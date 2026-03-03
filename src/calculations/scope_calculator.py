"""Calculate Scope 1, 2, and 3 emissions for coal operations."""

class EmissionsCalculator:
    """Calculate greenhouse gas emissions by scope."""
    
    # Emission factors (kg CO2e)
    DIESEL_EF = 2.68  # per liter
    ELECTRICITY_EF = 0.85  # per kWh (varies by grid)
    METHANE_GWP = 28  # Global Warming Potential
    
    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.scope1 = {}
        self.scope2 = {}
        self.scope3 = {}
    
    def calculate_scope1_diesel(self, liters: float) -> float:
        """Calculate Scope 1 from diesel fuel consumption."""
        if liters < 0:
            raise ValueError("Fuel consumption cannot be negative")
        return liters * self.DIESEL_EF
    
    def calculate_scope2_electricity(self, kwh: float) -> float:
        """Calculate Scope 2 from electricity consumption."""
        if kwh < 0:
            raise ValueError("Electricity cannot be negative")
        return kwh * self.ELECTRICITY_EF
    
    def calculate_scope3_shipping(self, tons: float, 
                                 distance_km: float) -> float:
        """
        Calculate Scope 3 from coal transportation.
        Args:
            tons: Coal quantity in metric tons
            distance_km: Transport distance in kilometers
        Returns:
            CO2e emissions in kg
        """
        if tons < 0 or distance_km < 0:
            raise ValueError("Tons and distance must be non-negative")
        
        # Rough estimate: ~0.1 kg CO2e per ton-km
        return tons * distance_km * 0.1
    
    def get_total_emissions(self) -> dict:
        """Return total emissions by scope."""
        return {
            'scope1_total': sum(self.scope1.values()),
            'scope2_total': sum(self.scope2.values()),
            'scope3_total': sum(self.scope3.values())
        }
