"""EduParking v2: bãi giữ xe chạy trong bộ nhớ, dùng cho bài tập STLab03."""
import re
from datetime import timedelta

# loại xe: (giá gói đầu, số giờ gói đầu, giá mỗi giờ thêm, mức trần)
PRICE = {"MOTORBIKE": (5_000, 4, 2_000, 30_000), "CAR": (20_000, 2, 10_000, 200_000)}
DEBT_LIMIT = 100_000
LOST_TICKET = 50_000


# ---------- PHẦN A: hàm thuần ----------
def is_valid_plate(plate):
    return bool(re.fullmatch(r"[0-9]{2}[A-Z]-[0-9]{5}", plate))


def parked_hours(time_in, time_out):
    if time_out < time_in:
        raise ValueError("INVALID_TIME")
    elapsed = time_out - time_in
    hours, remainder = divmod(elapsed, timedelta(hours=1))
    return max(1, hours + bool(remainder))


def parking_fee(vehicle, hours):
    if vehicle not in PRICE:
        raise ValueError("INVALID_VEHICLE")
    if hours < 1:
        raise ValueError("INVALID_HOURS")
    base, base_hours, extra, cap = PRICE[vehicle]
    fee = base + max(0, hours - base_hours) * extra
    return min(fee, cap)


def occupancy_rate(occupied, capacity):
    if capacity <= 0:
        raise ValueError("INVALID_CAPACITY")
    return occupied / capacity * 100


# ---------- PHẦN B: lớp có state ----------
class ParkingLot:
    def __init__(self, capacity):
        self.capacity = capacity
        self.occupied = 0
        self.inside = {}            # biển số -> (loại xe, giờ vào)
        self.debts = {}             # biển số -> số tiền nợ
        self.blacklist = set()
        self.revenue = 0

    def can_enter(self, plate):
        return (is_valid_plate(plate)
                and plate not in self.blacklist
                and self.debts.get(plate, 0) < DEBT_LIMIT)

    def check_in(self, plate, vehicle, time_in):
        if not self.can_enter(plate):
            raise ValueError("NOT_ALLOWED")
        if vehicle not in PRICE:
            raise ValueError("INVALID_VEHICLE")
        if self.occupied >= self.capacity:
            raise ValueError("LOT_FULL")
        if plate in self.inside:
            raise ValueError("ALREADY_INSIDE")
        self.occupied += 1
        self.inside[plate] = (vehicle, time_in)

    def check_out(self, plate, time_out, lost_ticket=False):
        if plate not in self.inside:
            raise ValueError("NOT_INSIDE")
        vehicle, time_in = self.inside[plate]
        fee = parking_fee(vehicle, parked_hours(time_in, time_out))
        if lost_ticket:
            fee += LOST_TICKET
        self.revenue += fee
        del self.inside[plate]
        self.occupied -= 1
        return fee
