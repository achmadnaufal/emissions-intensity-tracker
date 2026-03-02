"""Unit tests for CreditDeliveryScheduler."""
import pytest
from src.carbon_credit_delivery_scheduler import (
    CreditDeliveryScheduler, IssuancePeriod, DeliveryCommitment
)


def _sched(**kwargs) -> CreditDeliveryScheduler:
    return CreditDeliveryScheduler(project_id=kwargs.get("project_id", "VCS-001"),
                                    buffer_pool_pct=kwargs.get("buffer_pool_pct", 15.0))

def _period(year=2024, gross=50000.0, verified=False) -> IssuancePeriod:
    return IssuancePeriod(year=year, gross_tco2e=gross, verified=verified)

def _commitment(cid="DEL-001", vintage=2024, tco2e=30000.0, buyer="Buyer A") -> DeliveryCommitment:
    return DeliveryCommitment(commitment_id=cid, buyer=buyer, vintage_year=vintage,
                               tco2e_committed=tco2e, delivery_deadline="2025-06-30")


class TestIssuancePeriod:
    def test_valid_period(self):
        p = _period()
        assert p.gross_tco2e == 50000.0

    def test_negative_gross_raises(self):
        with pytest.raises(ValueError):
            IssuancePeriod(year=2024, gross_tco2e=-100.0)

    def test_invalid_year_raises(self):
        with pytest.raises(ValueError):
            IssuancePeriod(year=1990, gross_tco2e=1000.0)


class TestDeliveryCommitment:
    def test_valid_commitment(self):
        c = _commitment()
        assert c.tco2e_committed == 30000.0

    def test_zero_tco2e_raises(self):
        with pytest.raises(ValueError):
            _commitment(tco2e=0.0)


class TestSchedulerBasics:
    def test_buffer_out_of_range_raises(self):
        with pytest.raises(ValueError):
            CreditDeliveryScheduler("P", buffer_pool_pct=60.0)

    def test_net_issuance_computed(self):
        s = _sched(buffer_pool_pct=15.0)
        s.add_issuance(_period(year=2024, gross=50000.0))
        net = s.net_issuance(2024)
        assert net == pytest.approx(50000.0 * 0.85)

    def test_no_issuance_returns_zero(self):
        s = _sched()
        assert s.net_issuance(2030) == 0.0

    def test_duplicate_commitment_raises(self):
        s = _sched()
        s.add_commitment(_commitment())
        with pytest.raises(ValueError, match="already registered"):
            s.add_commitment(_commitment())


class TestDeliveryReport:
    def setup_method(self):
        self.s = _sched(buffer_pool_pct=15.0)
        self.s.add_issuance(_period(2024, gross=50000.0))
        self.s.add_issuance(_period(2025, gross=52000.0))
        self.s.add_commitment(_commitment("DEL-001", vintage=2024, tco2e=30000.0))
        self.s.add_commitment(_commitment("DEL-002", vintage=2025, tco2e=45000.0))

    def test_report_has_required_keys(self):
        r = self.s.delivery_report()
        for key in ("overall_status", "overall_gap_tco2e", "per_vintage", "total_net_tco2e"):
            assert key in r

    def test_surplus_vintage(self):
        r = self.s.delivery_report()
        v2024 = next(v for v in r["per_vintage"] if v["vintage_year"] == 2024)
        # net 2024 = 50000*0.85 = 42500; committed 30000 → surplus
        assert v2024["status"] == "SURPLUS"
        assert v2024["gap_tco2e"] > 0

    def test_deficit_vintage(self):
        r = self.s.delivery_report()
        v2025 = next(v for v in r["per_vintage"] if v["vintage_year"] == 2025)
        # net 2025 = 52000*0.85 = 44200; committed 45000 → deficit
        assert v2025["status"] == "DEFICIT"

    def test_overall_gap_computed(self):
        r = self.s.delivery_report()
        total_net = 50000*0.85 + 52000*0.85
        total_committed = 30000 + 45000
        assert r["overall_gap_tco2e"] == pytest.approx(total_net - total_committed, abs=1.0)

    def test_overcommitted_vintages_listed(self):
        r = self.s.delivery_report()
        assert 2025 in r["overcommitted_vintages"]

    def test_total_committed(self):
        assert self.s.total_committed() == pytest.approx(75000.0)


class TestRetirementAndUnretired:
    def test_retirement_schedule_empty(self):
        s = _sched()
        s.add_commitment(_commitment())
        assert s.retirement_schedule() == []

    def test_unretired_returns_open(self):
        s = _sched()
        s.add_commitment(_commitment())
        unretired = s.unretired_commitments()
        assert len(unretired) == 1

    def test_retired_excluded_from_unretired(self):
        s = _sched()
        c = DeliveryCommitment(commitment_id="RET-001", buyer="B", vintage_year=2024,
                                tco2e_committed=1000.0, delivery_deadline="2025-01-01",
                                retired=True, retirement_date="2025-01-15", retirement_serial="SN-001")
        s.add_commitment(c)
        assert len(s.unretired_commitments()) == 0
        assert len(s.retirement_schedule()) == 1
