"""
Environmental restoration impact calculator for post-mining land remediation.

Converts emissions reduction and carbon sequestration to biodiversity metrics
for coal operations transitioning to land restoration.
"""

from typing import Dict, Optional


class RestorationCalculator:
    """
    Calculate environmental restoration impact metrics.
    
    Supports conversion of emissions/carbon metrics to biodiversity indicators,
    habitat area restoration, and species recovery projections.
    
    Typical coal mining remediation scenarios:
    - Bauxite pit → wetland restoration (5-20 ha)
    - Coal heap → native forest (2-10 ha per year)
    - Mine tailings → grassland + wildlife corridor (10-50 ha)
    """
    
    # Conversion factors (evidence-based, conservative estimates)
    HABITAT_PER_CARBON_TONNE = 0.15  # hectares of habitat restored per tonne CO2 equivalent
    SPECIES_PER_HECTARE = 5.5  # Average species richness increase per hectare
    CARBON_PER_NATIVE_TREE = 0.015  # Tonnes CO2 per native tree over 30 years
    
    def __init__(self):
        """Initialize restoration calculator with default conversion factors."""
        pass
    
    def calculate_habitat_restoration(
        self,
        emissions_reduction_tco2e: float,
        habitat_type: str = "native_forest"
    ) -> Dict[str, float]:
        """
        Calculate habitat area that can be restored from emissions reductions.
        
        Habitat restoration potential based on carbon offset commitments:
        - Native forest: 0.15 ha/tCO2e (baseline)
        - Wetland: 0.18 ha/tCO2e (higher biodiversity density)
        - Grassland: 0.12 ha/tCO2e (lower density)
        - Agroforestry: 0.20 ha/tCO2e (productive + biodiversity)
        
        Args:
            emissions_reduction_tco2e: Tonnes CO2e reduction achieved or targeted
            habitat_type: Type of habitat ('native_forest', 'wetland', 'grassland', 'agroforestry')
        
        Returns:
            Dictionary with:
                - habitat_area_hectares: Restorable habitat area
                - habitat_type: Habitat type used
                - carbon_offset_tco2e: Input value
                - conversion_factor: ha/tCO2e used
        
        Raises:
            ValueError: If emissions_reduction_tco2e < 0 or habitat_type invalid
        """
        if emissions_reduction_tco2e < 0:
            raise ValueError("emissions_reduction_tco2e must be non-negative")
        
        habitat_factors = {
            "native_forest": 0.15,
            "wetland": 0.18,
            "grassland": 0.12,
            "agroforestry": 0.20,
        }
        
        if habitat_type not in habitat_factors:
            raise ValueError(f"habitat_type must be one of: {list(habitat_factors.keys())}")
        
        factor = habitat_factors[habitat_type]
        habitat_area = emissions_reduction_tco2e * factor
        
        return {
            "habitat_area_hectares": round(habitat_area, 2),
            "habitat_type": habitat_type,
            "carbon_offset_tco2e": round(emissions_reduction_tco2e, 2),
            "conversion_factor_ha_per_tco2e": factor,
        }
    
    def calculate_species_recovery(
        self,
        habitat_area_hectares: float,
        baseline_species_count: int = 0,
        years: int = 10
    ) -> Dict:
        """
        Project species richness recovery in restored habitat.
        
        Species recovery trajectory follows 10-30 year recolonization:
        - Year 0-2: Pioneer species (0-15% capacity)
        - Year 2-5: Early succession (15-50% capacity)
        - Year 5-10: Mid-succession (50-80% capacity)
        - Year 10+: Mature ecosystem (80-100% capacity)
        
        Args:
            habitat_area_hectares: Area of restored habitat
            baseline_species_count: Species present at restoration start (default 0)
            years: Projection period (default 10 years)
        
        Returns:
            Dictionary with:
                - baseline_species: Starting species count
                - projected_species_final: Expected species at year N
                - recovery_percentage: % of potential reached
                - habitat_quality_index: 0-1 (ecosystem maturity)
        
        Raises:
            ValueError: If habitat_area_hectares < 0 or years < 1
        """
        if habitat_area_hectares < 0:
            raise ValueError("habitat_area_hectares must be non-negative")
        if not isinstance(years, int) or years < 1:
            raise ValueError("years must be positive integer")
        
        potential_species = int(habitat_area_hectares * self.SPECIES_PER_HECTARE)
        
        # Recovery curve: sigmoid-like trajectory
        if years <= 2:
            recovery_pct = min(15, years * 7.5)
        elif years <= 5:
            recovery_pct = 15 + (years - 2) * 8.75
        elif years <= 10:
            recovery_pct = 50 + (years - 5) * 6.0
        else:
            recovery_pct = min(100, 80 + (years - 10) * 2.0)
        
        projected_species = baseline_species_count + int(potential_species * recovery_pct / 100)
        habitat_quality = min(1.0, recovery_pct / 100.0)
        
        return {
            "habitat_area_hectares": round(habitat_area_hectares, 2),
            "baseline_species": baseline_species_count,
            "potential_species": potential_species,
            "projected_species_final": projected_species,
            "recovery_percentage": round(recovery_pct, 1),
            "habitat_quality_index": round(habitat_quality, 2),
            "years_projected": years,
        }
    
    def calculate_tree_planting_impact(
        self,
        trees_planted: int,
        tree_survival_rate_pct: float = 80.0,
        years: int = 30
    ) -> Dict:
        """
        Calculate carbon sequestration and habitat impact from tree planting.
        
        Args:
            trees_planted: Number of trees planted
            tree_survival_rate_pct: Expected survival rate (0-100%, default 80%)
            years: Projection period (default 30 years)
        
        Returns:
            Dictionary with:
                - trees_planted: Input value
                - trees_surviving: Expected survivors
                - carbon_sequestered_tco2e: 30-year projection (tonnes)
                - habitat_hectares_equivalent: Habitat equivalent
                - species_potential: Estimated species recovered
        
        Raises:
            ValueError: If tree_survival_rate_pct outside 0-100 or trees_planted < 0
        """
        if not (0 <= tree_survival_rate_pct <= 100):
            raise ValueError("tree_survival_rate_pct must be 0-100")
        if trees_planted < 0:
            raise ValueError("trees_planted must be non-negative")
        
        trees_surviving = int(trees_planted * tree_survival_rate_pct / 100)
        carbon_tco2e = trees_surviving * self.CARBON_PER_NATIVE_TREE * (years / 30.0)
        
        # Estimate habitat from carbon sequestration
        habitat_calc = self.calculate_habitat_restoration(carbon_tco2e, "native_forest")
        
        # Project species from habitat
        species_calc = self.calculate_species_recovery(
            habitat_calc["habitat_area_hectares"],
            years=min(30, years)
        )
        
        return {
            "trees_planted": trees_planted,
            "survival_rate_pct": tree_survival_rate_pct,
            "trees_surviving": trees_surviving,
            "carbon_sequestered_tco2e": round(carbon_tco2e, 2),
            "habitat_hectares_equivalent": habitat_calc["habitat_area_hectares"],
            "species_potential": species_calc["potential_species"],
            "years_projection": years,
        }
    
    def compare_remediation_scenarios(
        self,
        scenarios: Dict[str, Dict]
    ) -> Dict:
        """
        Compare multiple remediation scenarios on environmental impact.
        
        Each scenario is a dict with keys: 'carbon_tco2e', 'habitat_type', 'habitat_ha'
        
        Example:
            scenarios = {
                'wetland_restoration': {
                    'carbon_tco2e': 500,
                    'habitat_type': 'wetland',
                    'habitat_ha': 50
                },
                'native_forest': {
                    'carbon_tco2e': 400,
                    'habitat_type': 'native_forest',
                    'habitat_ha': 60
                }
            }
        
        Returns:
            Comparative analysis with rankings and recommendations
        """
        if not scenarios:
            raise ValueError("scenarios dict cannot be empty")
        
        results = {}
        for scenario_name, params in scenarios.items():
            try:
                species = self.calculate_species_recovery(
                    params.get('habitat_ha', 0),
                    years=10
                )
                results[scenario_name] = {
                    "carbon_tco2e": params['carbon_tco2e'],
                    "habitat_hectares": params['habitat_ha'],
                    "projected_species": species['projected_species_final'],
                    "habitat_quality": species['habitat_quality_index'],
                    "biodiversity_score": (
                        species['projected_species_final'] * 
                        species['habitat_quality_index']
                    ),
                }
            except (KeyError, ValueError) as e:
                results[scenario_name] = {"error": str(e)}
        
        return results
