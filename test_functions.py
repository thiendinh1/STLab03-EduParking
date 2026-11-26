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


class TestReq01:
    @pytest.mark.parametrize('plate, expected', [('59A-12345', True)], ids=['case1'])
    def test_positive_plate_format(self, plate, expected):
        assert is_valid_plate(plate) is expected

    @pytest.mark.parametrize('plate, expected', [('', False), ('59a-12345', False), ('59A12345', False), ('59A-1234', False), ('59A-123456', False)], ids=['case1', 'case2', 'case3', 'case4', 'case5'])
    def test_negative_plate_format(self, plate, expected):
        assert is_valid_plate(plate) is expected

    @pytest.mark.parametrize('plate, expected', [('00A-00000', True), ('99Z-99999', True)], ids=['case1', 'case2'])
    def test_edge_plate_format(self, plate, expected):
        assert is_valid_plate(plate) is expected

class TestReq02:
    @pytest.mark.parametrize('seconds, expected', [(1800, 1)], ids=['case1'])
    def test_positive_duration(self, seconds, expected):
        end = START + timedelta(seconds=seconds)
        assert parked_hours(START, end) == expected

    @pytest.mark.parametrize('seconds, expected', [(0, 1), (1, 1), (3599, 1), (3600, 1), (3601, 2), (7200, 2)], ids=['case1', 'case2', 'case3', 'case4', 'case5', 'case6'])
    def test_edge_duration(self, seconds, expected):
        end = START + timedelta(seconds=seconds)
        assert parked_hours(START, end) == expected

    def test_negative_reversed_time(self):
        with pytest.raises(ValueError, match=r"^INVALID_TIME$"):
            parked_hours(START, START - timedelta(seconds=1))

class TestReq03:
    @pytest.mark.parametrize('hours, expected', [(2, 5000)], ids=['case1'])
    def test_positive_fee(self, hours, expected):
        assert parking_fee("MOTORBIKE", hours) == expected

    @pytest.mark.parametrize('hours, expected', [(1, 5000), (4, 5000), (5, 7000), (16, 29000), (17, 30000)], ids=['case1', 'case2', 'case3', 'case4', 'case5'])
    def test_edge_fee(self, hours, expected):
        assert parking_fee("MOTORBIKE", hours) == expected

    @pytest.mark.parametrize('hours', [0, -1], ids=['case1', 'case2'])
    def test_negative_hours(self, hours):
        with pytest.raises(ValueError, match=r"^INVALID_HOURS$"):
            parking_fee("MOTORBIKE", hours)

class TestReq04:
    @pytest.mark.parametrize('hours, expected', [(5, 50000)], ids=['case1'])
    def test_positive_fee(self, hours, expected):
        assert parking_fee("CAR", hours) == expected

    @pytest.mark.parametrize('hours, expected', [(1, 20000), (2, 20000), (3, 30000), (19, 190000), (20, 200000), (21, 200000)], ids=['case1', 'case2', 'case3', 'case4', 'case5', 'case6'])
    def test_edge_fee(self, hours, expected):
        assert parking_fee("CAR", hours) == expected

    def test_negative_unknown_fee(self):
        with pytest.raises(ValueError, match=r"^INVALID_VEHICLE$"):
            parking_fee("TRUCK", 1)


class TestReq04Entry(LotCase):
    def test_negative_unknown_entry(self):
        before = snapshot(self.lot)
        with pytest.raises(ValueError, match=r"^INVALID_VEHICLE$"):
            self.lot.check_in(A, "TRUCK", START)
        assert snapshot(self.lot) == before

class TestReq05:
    @pytest.mark.parametrize('occupied, capacity, expected', [(1, 3, 33.333333333)], ids=['case1'])
    def test_positive_occupancy(self, occupied, capacity, expected):
        assert occupancy_rate(occupied, capacity) == pytest.approx(expected)

    @pytest.mark.parametrize('occupied, capacity, expected', [(0, 10, 0), (10, 10, 100)], ids=['case1', 'case2'])
    def test_edge_occupancy(self, occupied, capacity, expected):
        assert occupancy_rate(occupied, capacity) == pytest.approx(expected)

    @pytest.mark.parametrize('capacity', [0, -1], ids=['case1', 'case2'])
    def test_negative_capacity(self, capacity):
        with pytest.raises(ValueError, match=r"^INVALID_CAPACITY$"):
            occupancy_rate(0, capacity)

