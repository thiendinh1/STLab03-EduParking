from datetime import datetime, timedelta

import pytest

from parking_app import ParkingLot, is_valid_plate, parked_hours, parking_fee, occupancy_rate

START = datetime(2026, 11, 1, 8)
A = "59A-12345"
B = "59B-12345"


def snapshot(lot):
    return (lot.occupied, lot.inside.copy(), lot.debts.copy(), lot.blacklist.copy(), lot.revenue)


class LotCase:
    def setup_method(self):
        self.lot = ParkingLot(2)


class TestReq06(LotCase):
    @pytest.mark.parametrize('debt, expected', [(0, True)], ids=['case1'])
    def test_positive_debt(self, debt, expected):
        self.lot.debts[A] = debt
        assert self.lot.can_enter(A) is expected

    @pytest.mark.parametrize('debt, expected', [(99999, True), (100000, False), (100001, False)], ids=['case1', 'case2', 'case3'])
    def test_edge_debt(self, debt, expected):
        self.lot.debts[A] = debt
        assert self.lot.can_enter(A) is expected

    def test_negative_bad_plate(self):
        before = snapshot(self.lot)
        with pytest.raises(ValueError, match=r"^NOT_ALLOWED$"):
            self.lot.check_in("bad", "CAR", START)
        assert snapshot(self.lot) == before

    def test_negative_can_enter_bad_plate(self):
        assert self.lot.can_enter("bad") is False

    def test_negative_blacklist(self):
        self.lot.blacklist.add(A)
        before = snapshot(self.lot)
        with pytest.raises(ValueError, match=r"^NOT_ALLOWED$"):
            self.lot.check_in(A, "CAR", START)
        assert snapshot(self.lot) == before

    def test_negative_can_enter_blacklist(self):
        self.lot.blacklist.add(A)
        assert self.lot.can_enter(A) is False

    def test_negative_debt_limit(self):
        self.lot.debts[A] = 100000
        before = snapshot(self.lot)
        with pytest.raises(ValueError, match=r"^NOT_ALLOWED$"):
            self.lot.check_in(A, "CAR", START)
        assert snapshot(self.lot) == before

    def test_negative_eligibility_before_vehicle(self):
        before = snapshot(self.lot)
        with pytest.raises(ValueError, match=r"^NOT_ALLOWED$"):
            self.lot.check_in("bad", "TRUCK", START)
        assert snapshot(self.lot) == before

class TestReq07(LotCase):
    def test_positive_first_entry(self):
        self.lot.check_in(A, "CAR", START)
        assert self.lot.occupied == 1
        assert self.lot.inside[A] == ("CAR", START)

    def test_edge_last_space(self):
        self.lot.check_in(B, "MOTORBIKE", START)
        self.lot.check_in(A, "CAR", START)
        assert self.lot.occupied == 2
        assert self.lot.inside[A] == ("CAR", START)

    def test_positive_recorded_vehicle(self):
        self.lot.check_in(A, "CAR", START)
        assert self.lot.occupied == 1
        assert self.lot.inside[A] == ("CAR", START)

class TestReq08(LotCase):
    def test_negative_full(self):
        self.lot.check_in(A, "CAR", START)
        self.lot.check_in(B, "MOTORBIKE", START)
        before = snapshot(self.lot)
        with pytest.raises(ValueError, match=r"^LOT_FULL$"):
            self.lot.check_in("59C-12345", "CAR", START)
        assert snapshot(self.lot) == before

    def test_edge_full_before_duplicate(self):
        self.lot.check_in(A, "CAR", START)
        self.lot.check_in(B, "MOTORBIKE", START)
        before = snapshot(self.lot)
        with pytest.raises(ValueError, match=r"^LOT_FULL$"):
            self.lot.check_in(A, "CAR", START)
        assert snapshot(self.lot) == before

    def test_negative_vehicle_before_full(self):
        self.lot.check_in(A, "CAR", START)
        self.lot.check_in(B, "MOTORBIKE", START)
        before = snapshot(self.lot)
        with pytest.raises(ValueError, match=r"^INVALID_VEHICLE$"):
            self.lot.check_in(A, "TRUCK", START)
        assert snapshot(self.lot) == before

class TestReq09(LotCase):
    def test_negative_duplicate_error(self):
        self.lot.check_in(A, "CAR", START)
        with pytest.raises(ValueError, match=r"^ALREADY_INSIDE$"):
            self.lot.check_in(A, "CAR", START)

    def test_edge_duplicate_preserves_state(self):
        self.lot.check_in(A, "CAR", START)
        before = snapshot(self.lot)
        with pytest.raises(ValueError, match=r"^ALREADY_INSIDE$"):
            self.lot.check_in(A, "MOTORBIKE", START + timedelta(minutes=2))
        assert snapshot(self.lot) == before

class TestReq10(LotCase):
    def test_positive_removes_car(self):
        self.lot.check_in(A, "CAR", START)
        self.lot.revenue = 7000
        fee = self.lot.check_out(A, START + timedelta(minutes=30))
        assert fee == 20000
        assert self.lot.revenue == 27000
        assert self.lot.inside == {}
        assert self.lot.occupied == 0

    def test_positive_keeps_other(self):
        self.lot.check_in(B, "MOTORBIKE", START)
        self.lot.check_in(A, "CAR", START)
        self.lot.revenue = 7000
        fee = self.lot.check_out(A, START + timedelta(minutes=30))
        assert fee == 20000
        assert self.lot.revenue == 27000
        assert self.lot.inside == {B: ("MOTORBIKE", START)}
        assert self.lot.occupied == 1

    def test_negative_clock_reversed(self):
        self.lot.check_in(A, "CAR", START)
        before = snapshot(self.lot)
        with pytest.raises(ValueError, match=r"^INVALID_TIME$"):
            self.lot.check_out(A, START - timedelta(seconds=1))
        assert snapshot(self.lot) == before

class TestReq11(LotCase):
    def test_negative_absent(self):
        before = snapshot(self.lot)
        with pytest.raises(ValueError, match=r"^NOT_INSIDE$"):
            self.lot.check_out(A, START)
        assert snapshot(self.lot) == before

    def test_edge_other_car(self):
        self.lot.check_in(B, "MOTORBIKE", START)
        before = snapshot(self.lot)
        with pytest.raises(ValueError, match=r"^NOT_INSIDE$"):
            self.lot.check_out(A, START)
        assert snapshot(self.lot) == before

class TestReq12(LotCase):
    @pytest.mark.parametrize('minutes, lost, expected', [(30, False, 20000), (30, True, 70000)], ids=['case1', 'case2'])
    def test_positive_ticket(self, minutes, lost, expected):
        self.lot.check_in(A, "CAR", START)
        self.lot.revenue = 7000
        fee = self.lot.check_out(A, START + timedelta(minutes=minutes), lost_ticket=lost)
        assert fee == expected
        assert self.lot.revenue == 7000 + expected
        assert self.lot.occupied == 0
        assert self.lot.inside == {}

    @pytest.mark.parametrize('minutes, lost, expected', [(1300, True, 250000)], ids=['case1'])
    def test_edge_ticket_above_cap(self, minutes, lost, expected):
        self.lot.check_in(A, "CAR", START)
        self.lot.revenue = 7000
        fee = self.lot.check_out(A, START + timedelta(minutes=minutes), lost_ticket=lost)
        assert fee == expected
        assert self.lot.revenue == 7000 + expected
        assert self.lot.occupied == 0
        assert self.lot.inside == {}

