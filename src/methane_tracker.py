"""
Methane (CH₄) emissions accounting for coal mining operations.
Implements IPCC Tier 2 methodology for underground and surface mining.

References:
    - IPCC (2006) Volume 2 Energy, Chapter 4: Underground and Surface Mining
    - IEA (2023) Methane Emissions from Coal Mining — abatement technology costs
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


# Global Warming Potentials (AR5 100-year)
CH4_GWP = 28  # CH₄ → CO₂e
CO2_GWP = 1   # reference

# Default emission factors (m³ CH₄ per tonne of coal produced)
# IPCC Tier 2 defaults by mining type
DEFAULT_EF_UNDERGROUND = 18.0   # m³ CH₄ / tonne (gassy mines)
DEFAULT_EF_SURFACE = 0.5         # m³ CH₄ / tonne (surface mines)

# Methane density at standard conditions (m³ → t CH₄)
# At 0°C and 1 atm: 1 m³ CH₄ ≈ 0.715 kg
METHANE_DENSITY_T_PER_M3 = 0.000715

# Default operating hours per year
DEFAULT_OPERATING_HOURS = 8760

# Conversion: m³ CH₄ → tCO₂e
# m³ × density (t/m³) × GWP × (CO2_GWP/CH4_GWP) — simplified to m³ × density × GWP
M3_CH4_TO_TCO2E = METHANE_DENSITY_T_PER_M3 * CH4_GWP


@dataclass
class AbatementOption:
    """Represents a methane abatement technology option."""
    name: str
    capture_efficiency_pct: float   # % of CH₄ captured/destroyed
    operating_cost_usd_per_tco2e: float  # USD per tCO₂e avoided
    capital_cost_usd_per_tco2e: float    # USD capital per tCO₂e capacity
    description: str = ""

    @property
    def total_cost_usd_per_tco2e(self) -> float:
        """Levelised cost (placeholder for detailed LCOE calc)."""
        return self.operating_cost_usd_per_tco2e + self.capital_cost_usd_per_tco2e * 0.1


class MethaneEmissionsCalculator:
    """
    Calculates methane (CH₄) emissions from coal mining using IPCC Tier 2.

    Supports:
        - Underground and surface mining emissions
        - Ventilation Air Methane (VAM)
        - Gas drainage and post-mining emissions
        - Cumulative lifetime emissions profiles
        - Abatement cost curves
    """

    def __init__(
        self,
        default_underground_ef: float = DEFAULT_EF_UNDERGROUND,
        default_surface_ef: float = DEFAULT_EF_SURFACE,
    ):
        """
        Initialize the calculator.

        Args:
            default_underground_ef: Default emission factor for underground mining (m³ CH₄/t).
            default_surface_ef: Default emission factor for surface mining (m³ CH₄/t).
        """
        self.default_underground_ef = default_underground_ef
        self.default_surface_ef = default_surface_ef

    # ─────────────────────────────────────────────────────────────────────────
    # Core emissions calculation
    # ─────────────────────────────────────────────────────────────────────────

    def calculate_mining_emissions(
        self,
        mine_type: str,
        production_t: float,
        methane_content_m3_t: Optional[float] = None,
        emission_factor: Optional[float] = None,
    ) -> float:
        """
        Calculate CH₄ emissions from coal mining using IPCC Tier 2.

        Emissions (m³ CH₄) = coal_production_t × emission_factor × methane_content_m3/t

        Args:
            mine_type: "underground" or "surface"
            production_t: Annual coal production in tonnes
            methane_content_m3_t: Measured methane content (m³ CH₄ per tonne).
                                  If None, uses default emission factor.
            emission_factor: Proportion of CH₄ emitted (0–1). If None, uses
                             type-specific default (underground=1.0, surface=1.0).

        Returns:
            CH₄ emissions in tCO₂e.

        Raises:
            ValueError: If mine_type is invalid, production is negative,
                        or factors are out of valid range.
        """
        if mine_type not in ("underground", "surface"):
            raise ValueError(
                f"mine_type must be 'underground' or 'surface', got '{mine_type}'"
            )
        if production_t < 0:
            raise ValueError(f"production_t cannot be negative, got {production_t}")

        # Determine effective emission factor
        if emission_factor is not None:
            if not (0 <= emission_factor <= 1):
                raise ValueError(
                    f"emission_factor must be 0–1, got {emission_factor}"
                )
            ef = emission_factor
        else:
            ef = 1.0  # default: all methane is emitted

        # Determine methane content
        if methane_content_m3_t is not None:
            if methane_content_m3_t < 0:
                raise ValueError(
                    f"methane_content_m3_t cannot be negative, got {methane_content_m3_t}"
                )
            mc = methane_content_m3_t
        else:
            # Fallback: use the type-specific default as the methane content
            mc = (
                self.default_underground_ef
                if mine_type == "underground"
                else self.default_surface_ef
            )

        # Calculate CH₄ volume (m³)
        ch4_volume_m3 = production_t * mc

        # Convert to tCO₂e
        tco2e = ch4_volume_m3 * M3_CH4_TO_TCO2E

        return round(tco2e, 4)

    def calculate_drainage_emissions(
        self,
        production_t: float,
        drainage_pct: float,
        methane_content_m3_t: float,
        oxidation_efficiency_pct: float = 0.0,
    ) -> dict[str, float]:
        """
        Calculate emissions from post-mining gas drainage.

        Gas drainage captures CH₄ before it enters the atmosphere.
        If the captured gas is oxidized (e.g., in a thermal oxidiser),
        the resulting CO₂ is less harmful than direct CH₄ release.

        Args:
            production_t: Annual coal production (tonnes)
            drainage_pct: Percentage of CH₄ drained (0–100)
            methane_content_m3_t: Methane content (m³ CH₄/t)
            oxidation_efficiency_pct: % of drained CH₄ that is oxidized to CO₂ (0–100).
                                      Oxidation converts CH₄ → CO₂ (GWP credit).

        Returns:
            dict with keys:
                - raw_drainage_m3: raw CH₄ drained (m³)
                - oxidized_tco2e: CO₂e from oxidized portion
                - direct_ch4_tco2e: CH₄e that would be released untreated
                - net_tco2e: net emissions (positive = source, negative = credit)
        """
        if not (0 <= drainage_pct <= 100):
            raise ValueError(f"drainage_pct must be 0–100, got {drainage_pct}")
        if not (0 <= oxidation_efficiency_pct <= 100):
            raise ValueError(
                f"oxidation_efficiency_pct must be 0–100, got {oxidation_efficiency_pct}"
            )

        total_ch4_m3 = production_t * methane_content_m3_t
        drained_m3 = total_ch4_m3 * (drainage_pct / 100)
        undrained_m3 = total_ch4_m3 - drained_m3

        # Untreated CH₄ emissions (what would have been released)
        direct_ch4_tco2e = undrained_m3 * M3_CH4_TO_TCO2E

        # Oxidized portion: CH₄ → CO₂ (GWP drops from 28 to 1)
        # Carbon is conserved: 1 m³ CH₄ (0.715 kg) → 1 m³ CO₂ (1.963 kg) at STP
        # CO₂ per m³ CH₄ = (44/16) × density_CH₄ = 2.74 kg CO₂ / m³ CH₄
        oxidized_m3 = drained_m3 * (oxidation_efficiency_pct / 100)
        CO2_PER_CH4_M3 = 2.74  # kg CO₂ produced per m³ CH₄ oxidized
        oxidized_tco2e = oxidized_m3 * (CO2_PER_CH4_M3 / 1000)  # CO₂ in tCO₂e (GWP=1)
        # Net: undrained CH₄e minus CO₂ credit from oxidation
        net_tco2e = direct_ch4_tco2e - oxidized_tco2e

        return {
            "raw_drainage_m3": round(drained_m3, 4),
            "oxidized_tco2e": round(oxidized_tco2e, 4),
            "direct_ch4_tco2e": round(direct_ch4_tco2e, 4),
            "net_tco2e": round(net_tco2e, 4),
        }

    def calculate_vam_emissions(
        self,
        air_flow_m3s: float,
        ch4_ppm: float,
        operating_hours: float = DEFAULT_OPERATING_HOURS,
        capture_efficiency_pct: float = 0.0,
    ) -> dict[str, float]:
        """
        Calculate Ventilation Air Methane (VAM) emissions.

        VAM is low-concentration CH₄ (0.1–1% or 1,000–10,000 ppm) in mine
        ventilation air streams. Cannot be economically combusted at <1% CH₄,
        but VAM oxidation systems can destroy the CH₄ thermally.

        Args:
            air_flow_m3s: Ventilation air flow rate (m³/s)
            ch4_ppm: CH₄ concentration in ventilation air (ppm by volume)
            operating_hours: Operating hours per year (default 8,760)
            capture_efficiency_pct: % of VAM CH₄ captured by oxidation system (0–100)

        Returns:
            dict with:
                - raw_vam_m3: raw CH₄ volume in ventilation air (m³/year)
                - raw_vam_tco2e: GWP impact of raw CH₄ release
                - captured_tco2e: avoided emissions from oxidation (credit)
                - net_tco2e: net emissions after capture
        """
        if air_flow_m3s < 0:
            raise ValueError(f"air_flow_m3s cannot be negative, got {air_flow_m3s}")
        if ch4_ppm < 0:
            raise ValueError(f"ch4_ppm cannot be negative, got {ch4_ppm}")
        if not (0 <= capture_efficiency_pct <= 100):
            raise ValueError(
                f"capture_efficiency_pct must be 0–100, got {capture_efficiency_pct}"
            )

        # Convert ppm to volume fraction
        ch4_fraction = ch4_ppm / 1_000_000

        # Total CH₄ volume per year (m³)
        annual_air_m3 = air_flow_m3s * operating_hours * 3600
        raw_vam_m3 = annual_air_m3 * ch4_fraction
        raw_vam_tco2e = raw_vam_m3 * M3_CH4_TO_TCO2E

        # Captured/oxidized portion
        captured_m3 = raw_vam_m3 * (capture_efficiency_pct / 100)
        captured_tco2e = captured_m3 * M3_CH4_TO_TCO2E

        # Net: raw minus credit
        net_tco2e = raw_vam_tco2e - captured_tco2e

        return {
            "raw_vam_m3": round(raw_vam_m3, 4),
            "raw_vam_tco2e": round(raw_vam_tco2e, 4),
            "captured_tco2e": round(captured_tco2e, 4),
            "net_tco2e": round(net_tco2e, 4),
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Lifetime / profile methods
    # ─────────────────────────────────────────────────────────────────────────

    def cumulative_emissions_profile(
        self,
        mine_type: str,
        annual_production_t: list[float],
        methane_content_m3_t: list[float],
        mine_age_years: int,
    ) -> list[dict[str, float]]:
        """
        Calculate annual CH₄ emissions profile over the mine lifetime.

        Args:
            mine_type: "underground" or "surface"
            annual_production_t: List of annual production values (tonnes).
                                 If len < mine_age_years, last value is repeated.
            methane_content_m3_t: List of annual methane content values.
                                  If len < mine_age_years, last value is repeated.
            mine_age_years: Number of years in the mine lifetime.

        Returns:
            List of dicts, one per year, with keys: year, production_t,
            methane_content, ch4_volume_m3, tco2e.
        """
        if mine_age_years <= 0:
            raise ValueError(f"mine_age_years must be positive, got {mine_age_years}")

        # Extend production and content lists to cover all years
        prod_ext = self._extend_list(annual_production_t, mine_age_years)
        mc_ext = self._extend_list(methane_content_m3_t, mine_age_years)

        profile = []
        for i in range(mine_age_years):
            ch4_m3 = prod_ext[i] * mc_ext[i]
            tco2e = ch4_m3 * M3_CH4_TO_TCO2E
            profile.append({
                "year": i + 1,
                "production_t": prod_ext[i],
                "methane_content_m3_t": mc_ext[i],
                "ch4_volume_m3": round(ch4_m3, 4),
                "tco2e": round(tco2e, 4),
            })

        return profile

    def total_lifetime_emissions(
        self,
        mine_type: str,
        annual_production_t: list[float],
        methane_content_m3_t: list[float],
        mine_age_years: int,
    ) -> float:
        """
        Sum total lifetime CH₄ emissions in tCO₂e.

        Args:
            mine_type: "underground" or "surface"
            annual_production_t: Annual production list
            methane_content_m3_t: Annual methane content list
            mine_age_years: Mine lifetime in years

        Returns:
            Total tCO₂e over mine lifetime.
        """
        profile = self.cumulative_emissions_profile(
            mine_type, annual_production_t, methane_content_m3_t, mine_age_years
        )
        return round(sum(year["tco2e"] for year in profile), 4)

    # ─────────────────────────────────────────────────────────────────────────
    # Abatement
    # ─────────────────────────────────────────────────────────────────────────

    def abatement_cost_curve(self) -> list[AbatementOption]:
        """
        Return a cost curve of methane abatement options.

        Based on IEA (2023) Methane Emissions from Coal Mining and
        IPCC (2006) Tier 2 guidance. Costs are indicative levelised costs.

        Returns:
            List of AbatementOption objects sorted by cost (lowest first).
        """
        options = [
            AbatementOption(
                name="VAM Oxidation (Thermal)",
                capture_efficiency_pct=90.0,
                operating_cost_usd_per_tco2e=8.0,
                capital_cost_usd_per_tco2e=25.0,
                description=(
                    "Ventilation Air Methane oxidation. Destroys low-concentration "
                    "CH₄ (0.1–1%) from mine ventilation air streams."
                ),
            ),
            AbatementOption(
                name="Gas Drainage + Flaring",
                capture_efficiency_pct=75.0,
                operating_cost_usd_per_tco2e=5.0,
                capital_cost_usd_per_tco2e=15.0,
                description=(
                    "Pre-mining gas drainage captures CH₄ before mining. "
                    "Captured gas is flared (CH₄ → CO₂), reducing GWP by ~28×."
                ),
            ),
            AbatementOption(
                name="Gas Drainage + Utilisation (CHP)",
                capture_efficiency_pct=70.0,
                operating_cost_usd_per_tco2e=3.0,
                capital_cost_usd_per_tco2e=20.0,
                description=(
                    "Captured CH4 used for power generation (CHP). "
                    "Displaces grid electricity; additional revenue possible."
                ),
            ),
            AbatementOption(
                name="Enhanced Drainage (Goaf / Cross-measure)",
                capture_efficiency_pct=55.0,
                operating_cost_usd_per_tco2e=10.0,
                capital_cost_usd_per_tco2e=30.0,
                description=(
                    "Enhanced drainage for difficult seams. "
                    "Higher cost; applicable to high-emission underground mines."
                ),
            ),
            AbatementOption(
                name="Coal Seam Methane (CGM) Extraction",
                capture_efficiency_pct=65.0,
                operating_cost_usd_per_tco2e=6.0,
                capital_cost_usd_per_tco2e=22.0,
                description=(
                    "Dedicated CGM wells extracted before, during, and after mining. "
                    "Long-term revenue from gas sales."
                ),
            ),
        ]

        return sorted(options, key=lambda x: x.total_cost_usd_per_tco2e)

    def net_emissions_after_abatement(
        self,
        gross_emissions_tco2e: float,
        abatement_pct: float,
    ) -> float:
        """
        Apply abatement efficiency to gross emissions to get net tCO₂e.

        Args:
            gross_emissions_tco2e: Gross (unabated) CH₄ emissions in tCO₂e
            abatement_pct: Total abatement efficiency across all measures (0–100).
                           Values > 100 are capped at 100.

        Returns:
            Net emissions in tCO₂e (gross × (1 – abatement%))

        Raises:
            ValueError: If abatement_pct is negative.
        """
        if abatement_pct < 0:
            raise ValueError(f"abatement_pct cannot be negative, got {abatement_pct}")

        effective_pct = min(abatement_pct, 100.0)
        net = gross_emissions_tco2e * (1 - effective_pct / 100)
        return round(net, 4)

    # ─────────────────────────────────────────────────────────────────────────
    # Utility
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _extend_list(values: list[float], target_length: int) -> list[float]:
        """Repeat the last value to fill a list to target_length."""
        if not values:
            raise ValueError("values list cannot be empty")
        if len(values) >= target_length:
            return values[:target_length]
        return values + [values[-1]] * (target_length - len(values))
