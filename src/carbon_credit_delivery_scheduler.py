"""
Carbon Credit Delivery Scheduler
===================================
Plans and validates carbon credit issuance and delivery schedules for
coal-to-clean energy transition projects and industrial decarbonisation
commitments.

Supports:
  - Annual issuance schedule aligned to Verra VCS verification cycles
  - Forward delivery commitment contracts (buyer/vintage matching)
  - Buffer pool deduction tracking per Verra Non-Permanence Risk Tool
  - Credit retirement scheduling for compliance or voluntary claims
  - Gap analysis between committed delivery and projected issuance

Usage::

    from src.carbon_credit_delivery_scheduler import CreditDeliveryScheduler, IssuancePeriod, DeliveryCommitment

    sched = CreditDeliveryScheduler(
        project_id="VCS-99001",
        buffer_pool_pct=15.0,
    )
    sched.add_issuance(IssuancePeriod(year=2024, gross_tco2e=48000.0))
    sched.add_issuance(IssuancePeriod(year=2025, gross_tco2e=51000.0))
    sched.add_commitment(DeliveryCommitment(
        commitment_id="DEL-001",
        buyer="PT Energi Bersih",
        vintage_year=2024,
        tco2e_committed=35000.0,
        delivery_deadline="2025-06-30",
    ))
    report = sched.delivery_report()
    print(report["overall_gap_tco2e"])   # deficit if negative
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class IssuancePeriod:
    """Annual credit issuance estimate or verified issuance."""

    year: int
    gross_tco2e: float        # Gross ERs before buffer deduction
    verified: bool = False    # True = registry-verified; False = estimate
    registry_issuance_id: str = ""

    def __post_init__(self) -> None:
        if self.gross_tco2e < 0:
            raise ValueError("gross_tco2e cannot be negative")
        if self.year < 2000 or self.year > 2100:
            raise ValueError(f"year {self.year} out of expected range 2000–2100")


@dataclass
class DeliveryCommitment:
    """A forward or spot delivery commitment to a buyer."""

    commitment_id: str
    buyer: str
    vintage_year: int
    tco2e_committed: float
    delivery_deadline: str      # ISO-8601 date
    purpose: str = "voluntary"  # voluntary | compliance | CORSIA | ETS
    retired: bool = False
    retirement_date: str = ""
    retirement_serial: str = ""
    notes: str = ""

    def __post_init__(self) -> None:
        if self.tco2e_committed <= 0:
            raise ValueError("tco2e_committed must be > 0")


# ---------------------------------------------------------------------------
# Main scheduler
# ---------------------------------------------------------------------------

class CreditDeliveryScheduler:
    """
    Schedules and validates carbon credit issuance against delivery commitments.

    Methods
    -------
    add_issuance(period) — register an issuance period
    add_commitment(commitment) — register a delivery commitment
    net_issuance(year) — net credits available for year (after buffer)
    delivery_report() — full issuance vs commitment gap analysis
    retirement_schedule() — all retired commitments with vintage/serial
    unretired_commitments() — outstanding deliveries not yet retired
    """

    def __init__(self, project_id: str, buffer_pool_pct: float = 10.0) -> None:
        if buffer_pool_pct < 0 or buffer_pool_pct > 50:
            raise ValueError("buffer_pool_pct must be 0–50")
        self.project_id = project_id
        self.buffer_pool_pct = buffer_pool_pct
        self._issuances: list[IssuancePeriod] = []
        self._commitments: list[DeliveryCommitment] = []

    def add_issuance(self, period: IssuancePeriod) -> None:
        """Register an issuance period. Duplicate years are allowed (e.g., interim verifications)."""
        self._issuances.append(period)

    def add_commitment(self, commitment: DeliveryCommitment) -> None:
        if commitment.commitment_id in {c.commitment_id for c in self._commitments}:
            raise ValueError(f"Commitment '{commitment.commitment_id}' already registered.")
        self._commitments.append(commitment)

    def net_issuance(self, year: int) -> float:
        """Net tradeable credits for a given vintage year (after buffer deduction)."""
        gross = sum(p.gross_tco2e for p in self._issuances if p.year == year)
        return gross * (1.0 - self.buffer_pool_pct / 100.0)

    def total_net_issuance(self) -> float:
        """Total net credits across all issuance periods."""
        total_gross = sum(p.gross_tco2e for p in self._issuances)
        return total_gross * (1.0 - self.buffer_pool_pct / 100.0)

    def total_committed(self) -> float:
        """Total tCO₂e committed across all delivery commitments."""
        return sum(c.tco2e_committed for c in self._commitments)

    def delivery_report(self) -> dict:
        """
        Full issuance vs commitment gap analysis.

        Returns
        -------
        dict with: project_id, buffer_pool_pct, total_gross_tco2e, total_net_tco2e,
                   total_committed_tco2e, overall_gap_tco2e (positive=surplus, negative=deficit),
                   per_vintage breakdown, overcommitted_vintages
        """
        years = sorted(set(
            [p.year for p in self._issuances] + [c.vintage_year for c in self._commitments]
        ))

        per_vintage = []
        for year in years:
            net = self.net_issuance(year)
            committed = sum(c.tco2e_committed for c in self._commitments if c.vintage_year == year)
            gap = net - committed
            per_vintage.append({
                "vintage_year": year,
                "gross_tco2e": sum(p.gross_tco2e for p in self._issuances if p.year == year),
                "buffer_deducted": sum(p.gross_tco2e for p in self._issuances if p.year == year) * self.buffer_pool_pct / 100.0,
                "net_tco2e": round(net, 2),
                "committed_tco2e": round(committed, 2),
                "gap_tco2e": round(gap, 2),
                "status": "SURPLUS" if gap >= 0 else "DEFICIT",
                "verified": any(p.verified for p in self._issuances if p.year == year),
            })

        total_net = self.total_net_issuance()
        total_committed = self.total_committed()
        overall_gap = total_net - total_committed

        overcommitted = [v for v in per_vintage if v["status"] == "DEFICIT"]

        return {
            "project_id": self.project_id,
            "buffer_pool_pct": self.buffer_pool_pct,
            "total_gross_tco2e": round(sum(p.gross_tco2e for p in self._issuances), 2),
            "total_net_tco2e": round(total_net, 2),
            "total_committed_tco2e": round(total_committed, 2),
            "overall_gap_tco2e": round(overall_gap, 2),
            "overall_status": "SURPLUS" if overall_gap >= 0 else "DEFICIT",
            "per_vintage": per_vintage,
            "overcommitted_vintages": [v["vintage_year"] for v in overcommitted],
            "n_commitments": len(self._commitments),
            "n_issuance_periods": len(self._issuances),
        }

    def retirement_schedule(self) -> list[dict]:
        """Return all retired commitments with vintage, buyer, and serial number."""
        return [
            {
                "commitment_id": c.commitment_id,
                "buyer": c.buyer,
                "vintage_year": c.vintage_year,
                "tco2e": c.tco2e_committed,
                "purpose": c.purpose,
                "retirement_date": c.retirement_date,
                "retirement_serial": c.retirement_serial,
            }
            for c in self._commitments if c.retired
        ]

    def unretired_commitments(self) -> list[dict]:
        """Return outstanding delivery commitments not yet retired."""
        return [
            {
                "commitment_id": c.commitment_id,
                "buyer": c.buyer,
                "vintage_year": c.vintage_year,
                "tco2e_committed": c.tco2e_committed,
                "delivery_deadline": c.delivery_deadline,
                "purpose": c.purpose,
            }
            for c in self._commitments if not c.retired
        ]
