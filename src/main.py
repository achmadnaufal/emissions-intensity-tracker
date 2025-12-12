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
