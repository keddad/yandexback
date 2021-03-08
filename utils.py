import itertools
from datetime import datetime
from typing import List

from sqlalchemy.ext.declarative import api

from models import WorkHours


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


def hours_to_datetime(h: List[str]) -> List[datetime]:
    times = []

    for rng in h:
        for el in rng.split("-"):
            times.append(datetime.strptime(el, "%H:%M"))

    return times


def grouper(iterable, n, fillvalue=None):
    "Collect data into fixed-length chunks or blocks"
    # grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx"
    args = [iter(iterable)] * n
    return itertools.zip_longest(*args, fillvalue=fillvalue)

def db_time_to_api(l: List[WorkHours]) -> List[str]:
    answ = []

    for a, b in grouper(sorted(list(map(lambda x: x.hours.strftime("%H:%M"), l))), 2):
        answ.append(f"{a}-{b}")
        
    return answ
