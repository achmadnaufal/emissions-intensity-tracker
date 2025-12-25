"""
Scope 1, 2, and 3 greenhouse gas emissions intensity tracking for coal operations

Author: github.com/achmadnaufal
"""
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional, Dict, Any


class EmissionsIntensityTracker:
    """Coal operations emissions intensity tracker"""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}

    def load_data(self, filepath: str) -> pd.DataFrame:
        """Load data from CSV or Excel file."""
        p = Path(filepath)
        if p.suffix in (".xlsx", ".xls"):
            return pd.read_excel(filepath)
        return pd.read_csv(filepath)

    def validate(self, df: pd.DataFrame) -> bool:
        """Basic validation of input data."""
        if df.empty:
            raise ValueError("Input DataFrame is empty")
        return True

    def preprocess(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and preprocess input data."""
        df = df.copy()
        # Drop fully empty rows
        df.dropna(how="all", inplace=True)
        # Standardize column names
        df.columns = [c.lower().strip().replace(" ", "_") for c in df.columns]
        return df

    def analyze(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Run core analysis and return summary metrics."""
        df = self.preprocess(df)
        result = {
            "total_records": len(df),
            "columns": list(df.columns),
            "missing_pct": (df.isnull().sum() / len(df) * 100).round(1).to_dict(),
        }
        numeric_df = df.select_dtypes(include="number")
        if not numeric_df.empty:
            result["summary_stats"] = numeric_df.describe().round(3).to_dict()
            result["totals"] = numeric_df.sum().round(2).to_dict()
            result["means"] = numeric_df.mean().round(3).to_dict()
        return result

    def run(self, filepath: str) -> Dict[str, Any]:
        """Full pipeline: load → validate → analyze."""
        df = self.load_data(filepath)
        self.validate(df)
        return self.analyze(df)

    def to_dataframe(self, result: Dict) -> pd.DataFrame:
        """Convert analysis result to DataFrame for export."""
        rows = []
        for k, v in result.items():
            if isinstance(v, dict):
                for kk, vv in v.items():
                    rows.append({"metric": f"{k}.{kk}", "value": vv})
            else:
                rows.append({"metric": k, "value": v})
        return pd.DataFrame(rows)
    
    def calculate_emission_intensity(
        self,
        df: pd.DataFrame,
        scope_cols: list = None,
        production_col: str = "production_tonnes"
    ) -> pd.DataFrame:
        """
        Calculate emissions intensity (tCO2e per unit production).
        
        Args:
            df: Input DataFrame with emissions and production columns
            scope_cols: List of scope columns to sum (default: all scope columns)
            production_col: Production metric column name
            
        Returns:
            DataFrame with calculated intensity metrics
        """
        df = df.copy()
        
        if scope_cols is None:
            scope_cols = [c for c in df.columns if c.startswith("scope")]
        
        # Sum all scopes
        df["total_emissions_tco2e"] = df[scope_cols].sum(axis=1)
        
        # Calculate intensity
        if production_col in df.columns:
            df["intensity_tco2e_per_unit"] = (
                df["total_emissions_tco2e"] / df[production_col]
            ).fillna(0)
        
        return df
    
    def calculate_trend(
        self,
        df: pd.DataFrame,
        group_by: str = "operation_id",
        time_col: str = "year"
    ) -> Dict[str, Any]:
        """
        Calculate year-over-year emissions trends.
        
        Args:
            df: DataFrame with operations and time periods
            group_by: Column to group by (operation_id, region, etc.)
            time_col: Time period column (year, month, etc.)
            
        Returns:
            Dictionary with trend metrics per group
        """
        df = self.calculate_emission_intensity(df)
        trends = {}
        
        for group_id, group_data in df.groupby(group_by):
            group_sorted = group_data.sort_values(time_col)
            emissions = group_sorted["total_emissions_tco2e"].tolist()
            
            if len(emissions) > 1:
                yoy_change = ((emissions[-1] - emissions[0]) / emissions[0] * 100)
                avg_change = yoy_change / (len(emissions) - 1)
            else:
                yoy_change = 0.0
                avg_change = 0.0
            
            trends[group_id] = {
                "total_yoy_change_pct": round(yoy_change, 2),
                "avg_annual_change_pct": round(avg_change, 2),
                "latest_emissions": round(emissions[-1], 2),
                "periods_tracked": len(emissions),
            }
        
        return trends
    
    def calculate_carbon_reduction_target(
        self,
        current_intensity: float,
        target_reduction_pct: float = 20,
        years_to_target: int = 5
    ) -> Dict[str, float]:
        """
        Calculate carbon reduction targets based on current intensity.
        
        Args:
            current_intensity: Current emissions intensity (tCO2e per unit)
            target_reduction_pct: Total reduction target percentage (default 20%)
            years_to_target: Years to achieve target (default 5)
            
        Returns:
            Dictionary with annual targets and final target
        """
        target_intensity = current_intensity * (1 - target_reduction_pct / 100)
        annual_reduction = (current_intensity - target_intensity) / years_to_target
        
        annual_targets = []
        for year in range(1, years_to_target + 1):
            annual_targets.append(
                round(current_intensity - (annual_reduction * year), 4)
            )
        
        return {
            "current_intensity": round(current_intensity, 4),
            "target_reduction_pct": target_reduction_pct,
            "target_intensity": round(target_intensity, 4),
            "annual_reduction_rate": round(annual_reduction, 4),
            "annual_targets": annual_targets,
            "years_to_target": years_to_target,
        }

    def calculate_paris_aligned_pathway(
        self,
        current_emissions_tco2e: float,
        base_year: int = 2025,
        target_year: int = 2050,
        scenario: str = "1.5c",
    ) -> dict:
        """
        Calculate a Paris Agreement-aligned emissions reduction pathway.

        Generates annual emissions budget following Science-Based Targets
        initiative (SBTi) reduction rates for 1.5°C or 2°C scenarios.

        Args:
            current_emissions_tco2e: Current annual emissions (tCO2e)
            base_year: Baseline year for reduction calculation, default 2025
            target_year: Target net-zero or reduction year, default 2050
            scenario: "1.5c" (4.2% annual reduction) or "2c" (2.5% annual)

        Returns:
            Dict with annual_pathway (year → budget_tco2e),
            cumulative_budget, total_reduction_pct, annual_rate_pct

        Raises:
            ValueError: If current_emissions_tco2e <= 0 or target_year <= base_year
            ValueError: If scenario is not "1.5c" or "2c"

        Example:
            >>> tracker = EmissionsIntensityTracker()
            >>> pathway = tracker.calculate_paris_aligned_pathway(
            ...     current_emissions_tco2e=50000, scenario="1.5c"
            ... )
            >>> print(f"2030 budget: {pathway['annual_pathway'][2030]:,.0f} tCO2e")
        """
        if current_emissions_tco2e <= 0:
            raise ValueError("current_emissions_tco2e must be positive")
        if target_year <= base_year:
            raise ValueError("target_year must be after base_year")
        if scenario not in ("1.5c", "2c"):
            raise ValueError("scenario must be '1.5c' or '2c'")

        # SBTi-aligned annual reduction rates (CAGR)
        annual_rates = {"1.5c": 0.042, "2c": 0.025}
        annual_rate = annual_rates[scenario]

        annual_pathway = {}
        cumulative = 0.0
        years = range(base_year, target_year + 1)

        for i, year in enumerate(years):
            budget = current_emissions_tco2e * ((1 - annual_rate) ** i)
            budget = max(0.0, budget)
            annual_pathway[year] = round(budget, 1)
            cumulative += budget

        total_reduction = (
            (current_emissions_tco2e - annual_pathway[target_year]) / current_emissions_tco2e * 100
        )

        return {
            "annual_pathway": annual_pathway,
            "cumulative_budget_tco2e": round(cumulative, 0),
            "total_reduction_pct": round(total_reduction, 1),
            "annual_rate_pct": round(annual_rate * 100, 2),
            "scenario": scenario,
            "base_year": base_year,
            "target_year": target_year,
            "budget_2030": round(annual_pathway.get(min(2030, target_year), 0), 0),
        }

    def benchmark_against_sector(
        self,
        intensity_tco2e_per_unit: float,
        sector: str = "coal_mining",
    ) -> dict:
        """
        Benchmark an operation's emissions intensity against sector averages.

        Args:
            intensity_tco2e_per_unit: Measured intensity (tCO2e/tonne or tCO2e/MWh)
            sector: Industry benchmark sector. Supported: "coal_mining",
                    "thermal_power", "cement", "steel"

        Returns:
            Dict with benchmark_value, deviation_pct, performance_band,
            and reduction_needed_to_avg

        Raises:
            ValueError: If intensity_tco2e_per_unit < 0 or sector not supported

        Example:
            >>> result = tracker.benchmark_against_sector(0.045, sector="coal_mining")
            >>> print(result["performance_band"])  # "above_average"
        """
        benchmarks = {
            "coal_mining":    {"avg": 0.040, "best_practice": 0.025, "unit": "tCO2e/tonne_coal"},
            "thermal_power":  {"avg": 0.920, "best_practice": 0.550, "unit": "tCO2e/MWh"},
            "cement":         {"avg": 0.650, "best_practice": 0.430, "unit": "tCO2e/tonne_cement"},
            "steel":          {"avg": 1.800, "best_practice": 1.200, "unit": "tCO2e/tonne_steel"},
        }
        if intensity_tco2e_per_unit < 0:
            raise ValueError("intensity_tco2e_per_unit cannot be negative")
        if sector not in benchmarks:
            raise ValueError(f"Unsupported sector '{sector}'. Choose from: {list(benchmarks)}")

        ref = benchmarks[sector]
        avg = ref["avg"]
        best = ref["best_practice"]
        deviation_pct = (intensity_tco2e_per_unit - avg) / avg * 100

        if intensity_tco2e_per_unit <= best:
            band = "best_practice"
        elif intensity_tco2e_per_unit <= avg:
            band = "above_average"
        elif intensity_tco2e_per_unit <= avg * 1.25:
            band = "average"
        else:
            band = "below_average"

        return {
            "measured_intensity": intensity_tco2e_per_unit,
            "sector_average": avg,
            "sector_best_practice": best,
            "deviation_from_avg_pct": round(deviation_pct, 1),
            "performance_band": band,
            "reduction_needed_to_avg": round(max(0, intensity_tco2e_per_unit - avg), 4),
            "reduction_needed_to_best": round(max(0, intensity_tco2e_per_unit - best), 4),
            "unit": ref["unit"],
            "sector": sector,
        }
