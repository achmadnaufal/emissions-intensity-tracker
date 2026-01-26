"""
Science-Based Targets initiative (SBTi) Validator for corporate GHG reduction commitments.

Validates whether a company's emissions reduction targets align with SBTi criteria
under different temperature warming scenarios (1.5°C, Well Below 2°C, 2°C).

Key methodologies supported:
  - Absolute Contraction Approach (ACA): linear annual reduction from base year
  - Sectoral Decarbonization Approach (SDA): sector-specific intensity pathways
  - Economic Intensity Contraction (EIC): revenue-intensity-based reduction

Validation covers:
  - Scope 1 + 2 near-term targets (5–10 year horizon)
  - Scope 3 near-term targets (>=67% of Scope 3 must be covered for high-S3 companies)
  - Long-term net-zero alignment by 2050

References:
  - SBTi Corporate Manual v2.0 (2023)
  - SBTi Net-Zero Standard v1.1 (2023)
  - GHG Protocol Corporate Standard

Author: github.com/achmadnaufal
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class SBTiScenario(str, Enum):
    """SBTi-aligned temperature warming scenarios."""
    WELL_BELOW_2C = "well_below_2c"   # Requires >=4.2% linear annual reduction
    ONE_POINT_5C = "1.5c"             # Requires >=7.6% linear annual reduction (ACA)
    NET_ZERO = "net_zero"             # Requires >=90% absolute reduction by 2050 vs base year


class ScopeType(str, Enum):
    """GHG Protocol scope categories."""
    SCOPE_1 = "scope_1"
    SCOPE_2 = "scope_2"
    SCOPE_3 = "scope_3"


# Minimum required annual linear reduction rates by scenario (ACA method)
# Source: SBTi Corporate Manual v2.0
ACA_MIN_ANNUAL_REDUCTION: Dict[SBTiScenario, float] = {
    SBTiScenario.WELL_BELOW_2C: 4.2,   # % per year
    SBTiScenario.ONE_POINT_5C: 7.6,    # % per year (1.5°C aligned)
    SBTiScenario.NET_ZERO: 7.6,        # same near-term; long-term 90%+ absolute
}

# Scope 3 materiality threshold
SCOPE3_MATERIALITY_THRESHOLD_PCT = 40.0  # If Scope 3 > 40% of total, target required


@dataclass
class EmissionsTarget:
    """A single GHG reduction target declaration.

    Attributes:
        scope: GHG scope(s) covered by this target.
        base_year: Reference year for baseline emissions.
        base_year_emissions_tco2e: Absolute GHG in base year (tCO2e).
        target_year: Year by which the target must be achieved.
        target_reduction_pct: Committed % reduction vs base year.
        methodology: Approach used: 'ACA', 'SDA', or 'EIC'.
        scenario: Temperature scenario this target is designed to meet.
        includes_offsets: Whether target relies on offsets to close the gap.
        description: Optional free-text description.
    """

    scope: ScopeType
    base_year: int
    base_year_emissions_tco2e: float
    target_year: int
    target_reduction_pct: float
    methodology: str = "ACA"
    scenario: SBTiScenario = SBTiScenario.WELL_BELOW_2C
    includes_offsets: bool = False
    description: str = ""

    def __post_init__(self) -> None:
        if self.base_year_emissions_tco2e <= 0:
            raise ValueError("base_year_emissions_tco2e must be positive")
        if not (0 < self.target_reduction_pct <= 100):
            raise ValueError("target_reduction_pct must be between 0 and 100")
        if self.target_year <= self.base_year:
            raise ValueError("target_year must be after base_year")
        if self.methodology not in ("ACA", "SDA", "EIC"):
            raise ValueError(f"Unknown methodology '{self.methodology}'. Use ACA, SDA, or EIC.")

    @property
    def horizon_years(self) -> int:
        """Number of years from base year to target year."""
        return self.target_year - self.base_year

    @property
    def implied_annual_reduction_pct(self) -> float:
        """Implied average annual linear reduction rate (%)."""
        return self.target_reduction_pct / self.horizon_years

    @property
    def target_absolute_tco2e(self) -> float:
        """Absolute emissions level at target year (tCO2e)."""
        return self.base_year_emissions_tco2e * (1 - self.target_reduction_pct / 100)


@dataclass
class CompanyEmissionsProfile:
    """Full emissions inventory and target declarations for a company.

    Attributes:
        company_id: Unique company identifier.
        company_name: Display name.
        sector: Business sector (e.g., 'Coal Mining', 'Pharmaceuticals').
        reporting_year: Most recent inventory year.
        scope1_tco2e: Scope 1 absolute emissions (tCO2e).
        scope2_market_tco2e: Scope 2 market-based emissions (tCO2e).
        scope3_total_tco2e: Total Scope 3 emissions across all categories (tCO2e).
        targets: List of declared reduction targets.
    """

    company_id: str
    company_name: str
    sector: str
    reporting_year: int
    scope1_tco2e: float
    scope2_market_tco2e: float
    scope3_total_tco2e: float = 0.0
    targets: List[EmissionsTarget] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.scope1_tco2e < 0:
            raise ValueError("scope1_tco2e cannot be negative")
        if self.scope2_market_tco2e < 0:
            raise ValueError("scope2_market_tco2e cannot be negative")
        if self.scope3_total_tco2e < 0:
            raise ValueError("scope3_total_tco2e cannot be negative")

    @property
    def total_emissions_tco2e(self) -> float:
        """Total Scope 1 + 2 + 3 GHG inventory (tCO2e)."""
        return self.scope1_tco2e + self.scope2_market_tco2e + self.scope3_total_tco2e

    @property
    def scope3_materiality_pct(self) -> float:
        """Scope 3 share of total emissions (%)."""
        if self.total_emissions_tco2e == 0:
            return 0.0
        return (self.scope3_total_tco2e / self.total_emissions_tco2e) * 100

    @property
    def scope3_is_material(self) -> bool:
        """True if Scope 3 exceeds materiality threshold (>40% of total)."""
        return self.scope3_materiality_pct > SCOPE3_MATERIALITY_THRESHOLD_PCT


@dataclass
class ValidationFlag:
    """A single validation finding (pass/warning/fail)."""
    code: str
    severity: str          # 'PASS', 'WARNING', 'FAIL'
    scope: Optional[str]
    message: str
    recommendation: Optional[str] = None


@dataclass
class SBTiValidationResult:
    """Full SBTi validation report for a company.

    Attributes:
        company_id: Validated company identifier.
        company_name: Display name.
        overall_status: 'APPROVED', 'CONDITIONAL', or 'REJECTED'.
        flags: List of individual validation findings.
        near_term_aligned: Whether near-term targets are SBTi-aligned.
        net_zero_aligned: Whether long-term net-zero target exists and is valid.
        scope3_coverage_ok: Whether Scope 3 target requirement is satisfied.
        highest_scenario: Best scenario met across all targets.
        summary: Human-readable summary string.
    """

    company_id: str
    company_name: str
    overall_status: str
    flags: List[ValidationFlag]
    near_term_aligned: bool
    net_zero_aligned: bool
    scope3_coverage_ok: bool
    highest_scenario: Optional[str]
    summary: str


class ScienceBasedTargetsValidator:
    """Validates corporate GHG targets against SBTi criteria.

    Checks Scope 1+2 and Scope 3 near-term targets, validates minimum
    annual reduction rates per the Absolute Contraction Approach, and
    assesses long-term net-zero alignment.

    Example:
        >>> validator = ScienceBasedTargetsValidator()
        >>> target = EmissionsTarget(
        ...     scope=ScopeType.SCOPE_1,
        ...     base_year=2019,
        ...     base_year_emissions_tco2e=500_000,
        ...     target_year=2030,
        ...     target_reduction_pct=45,
        ...     scenario=SBTiScenario.ONE_POINT_5C,
        ... )
        >>> profile = CompanyEmissionsProfile(
        ...     company_id="COAL_001",
        ...     company_name="Kaltim Resources",
        ...     sector="Coal Mining",
        ...     reporting_year=2023,
        ...     scope1_tco2e=500_000,
        ...     scope2_market_tco2e=80_000,
        ...     scope3_total_tco2e=2_100_000,
        ...     targets=[target],
        ... )
        >>> result = validator.validate(profile)
        >>> print(result.overall_status)
    """

    def __init__(
        self,
        require_scope3_target: bool = True,
        min_near_term_horizon_years: int = 5,
        max_near_term_horizon_years: int = 10,
    ) -> None:
        """Initialise the validator.

        Args:
            require_scope3_target: If True and Scope 3 is material, a Scope 3 target
                is mandatory for SBTi approval.
            min_near_term_horizon_years: Minimum allowed target horizon (default 5).
            max_near_term_horizon_years: Maximum near-term horizon (default 10).
        """
        self.require_scope3_target = require_scope3_target
        self.min_near_term_horizon_years = min_near_term_horizon_years
        self.max_near_term_horizon_years = max_near_term_horizon_years

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def validate(self, profile: CompanyEmissionsProfile) -> SBTiValidationResult:
        """Run full SBTi validation for a company emissions profile.

        Args:
            profile: Company emissions inventory and target declarations.

        Returns:
            SBTiValidationResult with overall status, flags, and summary.
        """
        if not isinstance(profile, CompanyEmissionsProfile):
            raise TypeError("profile must be a CompanyEmissionsProfile instance")

        flags: List[ValidationFlag] = []
        near_term_scope12_ok = False
        net_zero_ok = False
        scope3_ok = True
        scenario_met: Optional[str] = None

        # --- Check Scope 1+2 near-term targets ---
        scope12_targets = [
            t for t in profile.targets
            if t.scope in (ScopeType.SCOPE_1, ScopeType.SCOPE_2)
        ]

        if not scope12_targets:
            flags.append(ValidationFlag(
                code="NO_SCOPE12_TARGET",
                severity="FAIL",
                scope="Scope 1+2",
                message="No near-term Scope 1 or Scope 2 reduction target declared.",
                recommendation="Declare a Scope 1+2 target with ≥4.2% annual reduction for Well-Below 2°C.",
            ))
        else:
            for tgt in scope12_targets:
                flag, ok = self._validate_near_term_target(tgt)
                flags.append(flag)
                if ok:
                    near_term_scope12_ok = True
                    if scenario_met is None or self._scenario_rank(tgt.scenario) > self._scenario_rank(
                        SBTiScenario(scenario_met)
                    ):
                        scenario_met = tgt.scenario.value

        # --- Check target horizon validity ---
        for tgt in profile.targets:
            if tgt.scope != ScopeType.SCOPE_3:
                horizon = tgt.horizon_years
                if horizon < self.min_near_term_horizon_years:
                    flags.append(ValidationFlag(
                        code="TARGET_HORIZON_TOO_SHORT",
                        severity="FAIL",
                        scope=tgt.scope.value,
                        message=f"Target horizon of {horizon} years is below minimum {self.min_near_term_horizon_years} years.",
                        recommendation="Extend target year to at least 5 years from base year.",
                    ))
                elif horizon > self.max_near_term_horizon_years:
                    flags.append(ValidationFlag(
                        code="TARGET_HORIZON_TOO_LONG",
                        severity="WARNING",
                        scope=tgt.scope.value,
                        message=f"Target horizon of {horizon} years exceeds near-term maximum of {self.max_near_term_horizon_years}.",
                        recommendation="Targets beyond 10 years are considered long-term; a separate net-zero target is required.",
                    ))

        # --- Check Scope 3 ---
        if profile.scope3_is_material:
            scope3_targets = [t for t in profile.targets if t.scope == ScopeType.SCOPE_3]
            if not scope3_targets and self.require_scope3_target:
                scope3_ok = False
                flags.append(ValidationFlag(
                    code="MISSING_SCOPE3_TARGET",
                    severity="FAIL",
                    scope="Scope 3",
                    message=(
                        f"Scope 3 is material ({profile.scope3_materiality_pct:.1f}% of total) "
                        "but no Scope 3 target declared."
                    ),
                    recommendation="Declare a Scope 3 target covering ≥67% of total Scope 3 emissions.",
                ))
            elif scope3_targets:
                flags.append(ValidationFlag(
                    code="SCOPE3_TARGET_PRESENT",
                    severity="PASS",
                    scope="Scope 3",
                    message=f"Scope 3 near-term target declared (materiality: {profile.scope3_materiality_pct:.1f}%).",
                ))

        # --- Check net-zero (long-term) alignment ---
        net_zero_targets = [t for t in profile.targets if t.scenario == SBTiScenario.NET_ZERO]
        if net_zero_targets:
            nz_tgt = net_zero_targets[0]
            if nz_tgt.target_reduction_pct >= 90:
                net_zero_ok = True
                flags.append(ValidationFlag(
                    code="NET_ZERO_TARGET_VALID",
                    severity="PASS",
                    scope=nz_tgt.scope.value,
                    message=(
                        f"Net-zero target meets ≥90% absolute reduction "
                        f"({nz_tgt.target_reduction_pct:.0f}% by {nz_tgt.target_year})."
                    ),
                ))
            else:
                flags.append(ValidationFlag(
                    code="NET_ZERO_TARGET_INSUFFICIENT",
                    severity="FAIL",
                    scope=nz_tgt.scope.value,
                    message=(
                        f"Net-zero target reduction of {nz_tgt.target_reduction_pct:.0f}% "
                        "is below SBTi minimum of 90%."
                    ),
                    recommendation="Increase absolute reduction commitment to ≥90% for net-zero alignment.",
                ))
        else:
            flags.append(ValidationFlag(
                code="NO_NET_ZERO_TARGET",
                severity="WARNING",
                scope=None,
                message="No long-term net-zero target declared.",
                recommendation="Declare a net-zero target with ≥90% absolute reduction by 2050.",
            ))

        # --- Check offset reliance ---
        for tgt in profile.targets:
            if tgt.includes_offsets:
                flags.append(ValidationFlag(
                    code="OFFSET_RELIANCE",
                    severity="WARNING",
                    scope=tgt.scope.value,
                    message=f"Target for {tgt.scope.value} relies on offsets. SBTi prioritises direct reductions.",
                    recommendation="Offsets should supplement, not replace, direct emission reductions.",
                ))

        # --- Determine overall status ---
        fail_flags = [f for f in flags if f.severity == "FAIL"]
        warn_flags = [f for f in flags if f.severity == "WARNING"]

        if not fail_flags:
            overall_status = "APPROVED"
        elif len(fail_flags) == 1 and not scope3_ok and near_term_scope12_ok:
            overall_status = "CONDITIONAL"
        else:
            overall_status = "REJECTED"

        summary = self._build_summary(profile, overall_status, fail_flags, warn_flags, scenario_met)

        return SBTiValidationResult(
            company_id=profile.company_id,
            company_name=profile.company_name,
            overall_status=overall_status,
            flags=flags,
            near_term_aligned=near_term_scope12_ok,
            net_zero_aligned=net_zero_ok,
            scope3_coverage_ok=scope3_ok,
            highest_scenario=scenario_met,
            summary=summary,
        )

    def batch_validate(
        self, profiles: List[CompanyEmissionsProfile]
    ) -> List[SBTiValidationResult]:
        """Validate a list of company profiles in batch.

        Args:
            profiles: List of CompanyEmissionsProfile instances.

        Returns:
            List of SBTiValidationResult in same order as input.

        Raises:
            ValueError: If profiles list is empty.
        """
        if not profiles:
            raise ValueError("profiles list cannot be empty")
        return [self.validate(p) for p in profiles]

    def summary_report(self, results: List[SBTiValidationResult]) -> Dict:
        """Generate portfolio-level summary of SBTi validation results.

        Args:
            results: List of SBTiValidationResult from batch_validate().

        Returns:
            Dict with counts, rates, and per-status breakdowns.
        """
        if not results:
            return {}

        approved = [r for r in results if r.overall_status == "APPROVED"]
        conditional = [r for r in results if r.overall_status == "CONDITIONAL"]
        rejected = [r for r in results if r.overall_status == "REJECTED"]

        return {
            "total_companies": len(results),
            "approved_count": len(approved),
            "conditional_count": len(conditional),
            "rejected_count": len(rejected),
            "approval_rate_pct": round(len(approved) / len(results) * 100, 1),
            "net_zero_aligned_count": sum(1 for r in results if r.net_zero_aligned),
            "scope3_coverage_ok_count": sum(1 for r in results if r.scope3_coverage_ok),
            "companies_by_status": {
                "APPROVED": [r.company_name for r in approved],
                "CONDITIONAL": [r.company_name for r in conditional],
                "REJECTED": [r.company_name for r in rejected],
            },
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _validate_near_term_target(
        self, target: EmissionsTarget
    ) -> Tuple[ValidationFlag, bool]:
        """Check a single near-term target against ACA minimum reduction rates.

        Returns:
            Tuple of (ValidationFlag, is_valid).
        """
        required_rate = ACA_MIN_ANNUAL_REDUCTION.get(target.scenario, 4.2)
        actual_rate = target.implied_annual_reduction_pct

        if actual_rate >= required_rate:
            return ValidationFlag(
                code="NEAR_TERM_TARGET_VALID",
                severity="PASS",
                scope=target.scope.value,
                message=(
                    f"Target meets {target.scenario.value} ACA requirement: "
                    f"{actual_rate:.1f}%/yr ≥ {required_rate:.1f}%/yr required."
                ),
            ), True
        else:
            return ValidationFlag(
                code="NEAR_TERM_TARGET_INSUFFICIENT",
                severity="FAIL",
                scope=target.scope.value,
                message=(
                    f"Target falls short of {target.scenario.value}: "
                    f"{actual_rate:.1f}%/yr < {required_rate:.1f}%/yr required (ACA)."
                ),
                recommendation=(
                    f"Increase target reduction from {target.target_reduction_pct:.0f}% to at least "
                    f"{required_rate * target.horizon_years:.0f}% over {target.horizon_years} years."
                ),
            ), False

    @staticmethod
    def _scenario_rank(scenario: SBTiScenario) -> int:
        """Return numeric rank for scenario stringency comparison."""
        ranking = {
            SBTiScenario.WELL_BELOW_2C: 1,
            SBTiScenario.ONE_POINT_5C: 2,
            SBTiScenario.NET_ZERO: 3,
        }
        return ranking.get(scenario, 0)

    @staticmethod
    def _build_summary(
        profile: CompanyEmissionsProfile,
        status: str,
        fails: List[ValidationFlag],
        warnings: List[ValidationFlag],
        scenario: Optional[str],
    ) -> str:
        scenario_str = f" | Highest scenario: {scenario}" if scenario else ""
        fail_str = f" | {len(fails)} FAIL(s)" if fails else ""
        warn_str = f" | {len(warnings)} WARNING(s)" if warnings else ""
        return (
            f"{profile.company_name} [{profile.company_id}] — {status}"
            f"{scenario_str}{fail_str}{warn_str}"
        )
