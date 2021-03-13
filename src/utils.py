import itertools
from datetime import time, datetime
from typing import List

from sqlalchemy.ext.declarative import api

from .models import Order, WorkHours, Courier


def type_to_weight(type: str) -> int:
    d = {
        "foot": 10,
        "bike": 15,
        "car": 50
    }

    return d[type]


def weight_to_type(weight: int) -> str:
    d = {
        10: "foot",
        15: "bike",
        50: "car"
    }

    return d[weight]


def hours_to_time(h: List[str]) -> List[time]:
    times = []

    for rng in h:
        for el in rng.split("-"):
            times.append(datetime.strptime(el, "%H:%M").time())

    return times


def grouper(iterable, n, fillvalue=None):
    "Collect data into fixed-length chunks or blocks"
    # grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx"
    args = [iter(iterable)] * n
    return itertools.zip_longest(*args, fillvalue=fillvalue)


def time_to_hours(l: List[WorkHours]) -> List[str]:
    answ = []

    for a, b in grouper(sorted(list(map(lambda x: x.hours.strftime("%H:%M"), l))), 2):
        answ.append(f"{a}-{b}")

    return answ


def match_times(a: List[time], b: list[time]):
    for a_s, a_e in grouper(a, 2):
        for b_s, b_e in grouper(b, 2):
            if a_s <= b_s <= a_e or a_s <= b_e <= a_e or (b_s <= a_s and a_e <= b_e):
                return True
    return False


def filter_time_orders(courier: Courier, orders: List[Order]) -> List[Order]:
    out = []

    for o in orders:
        if match_times(sorted([x.hours for x in courier.hours]), sorted([x.hours for x in o.hours])):
            out.append(o)

    return out
