"""Shaft / hub features: parallel keys (DIN 6885-1) and retaining rings (DIN 471 / 472).

::

    keyway(20)             # Key(b=6, h=6, t1=3.5, t2=2.8) for shafts over 17 up to 22 mm
    key_length(20, 28)     # 28: next DIN 6885 length
    circlip_shaft(8)       # RetainingRing(groove=7.6, width=0.9, thickness=0.8)
    circlip_bore(22)       # 608 bearing in a 22 mm bore: groove 23.0 x 1.1

Sources: DIN 6885-1 (form A parallel keys, shaft diameter ranges, keyway depth
in the shaft t1 and in the hub t2); DIN 471 (external rings for shafts) and
DIN 472 (internal rings for bores): groove diameter d2, groove width m (H13),
ring thickness s.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from ._common import StandardsError, lookup, row_for

__all__ = [
    "DIN471",
    "DIN472",
    "DIN6885_KEYS",
    "DIN6885_LENGTHS",
    "Key",
    "RetainingRing",
    "circlip_bore",
    "circlip_shaft",
    "key_length",
    "keyway",
]

# fmt: off
# (over, up to and including, (b, h, t1 shaft, t2 hub)), mm.
DIN6885_KEYS: List[Tuple[float, float, Tuple[float, float, float, float]]] = [
    (6, 8, (2, 2, 1.2, 1.0)),
    (8, 10, (3, 3, 1.8, 1.4)),
    (10, 12, (4, 4, 2.5, 1.8)),
    (12, 17, (5, 5, 3.0, 2.3)),
    (17, 22, (6, 6, 3.5, 2.8)),
    (22, 30, (8, 7, 4.0, 3.3)),
    (30, 38, (10, 8, 5.0, 3.3)),
    (38, 44, (12, 8, 5.0, 3.3)),
    (44, 50, (14, 9, 5.5, 3.8)),
    (50, 58, (16, 10, 6.0, 4.3)),
    (58, 65, (18, 11, 7.0, 4.4)),
    (65, 75, (20, 12, 7.5, 4.9)),
    (75, 85, (22, 14, 9.0, 5.4)),
    (85, 95, (25, 14, 9.0, 5.4)),
    (95, 110, (28, 16, 10.0, 6.4)),
    (110, 130, (32, 18, 11.0, 7.4)),
]

DIN6885_LENGTHS: Tuple[float, ...] = (
    6, 8, 10, 12, 14, 16, 18, 20, 22, 25, 28, 32, 36, 40, 45, 50, 56, 63, 70,
    80, 90, 100, 110, 125, 140, 160, 180, 200,
)

# DIN 471, shaft d1 -> (groove d2, groove width m, ring thickness s), mm.
DIN471: Dict[str, Tuple[float, float, float]] = {
    "3": (2.8, 0.5, 0.4), "4": (3.8, 0.5, 0.4), "5": (4.8, 0.7, 0.6),
    "6": (5.7, 0.8, 0.7), "7": (6.7, 0.9, 0.8), "8": (7.6, 0.9, 0.8),
    "9": (8.6, 1.1, 1.0), "10": (9.6, 1.1, 1.0), "11": (10.5, 1.1, 1.0), "12": (11.5, 1.1, 1.0),
    "13": (12.4, 1.1, 1.0),
    "14": (13.4, 1.1, 1.0), "15": (14.3, 1.1, 1.0), "16": (15.2, 1.1, 1.0),
    "17": (16.2, 1.1, 1.0), "18": (17.0, 1.3, 1.2), "19": (18.0, 1.3, 1.2),
    "20": (19.0, 1.3, 1.2),
    "22": (21.0, 1.3, 1.2), "25": (23.9, 1.3, 1.2), "28": (26.6, 1.6, 1.5),
    "30": (28.6, 1.6, 1.5), "32": (30.3, 1.6, 1.5), "35": (33.0, 1.6, 1.5),
    "40": (37.5, 1.85, 1.75), "45": (42.5, 1.85, 1.75), "50": (47.0, 2.15, 2.0),
}

# DIN 472, bore d1 -> (groove d2, groove width m, ring thickness s), mm.
DIN472: Dict[str, Tuple[float, float, float]] = {
    "8": (8.4, 0.9, 0.8), "9": (9.4, 0.9, 0.8), "10": (10.4, 1.1, 1.0),
    "12": (12.5, 1.1, 1.0), "13": (13.6, 1.1, 1.0), "14": (14.6, 1.1, 1.0),
    "15": (15.7, 1.1, 1.0), "16": (16.8, 1.1, 1.0), "17": (17.8, 1.1, 1.0), "18": (19.0, 1.1, 1.0),
    "19": (20.0, 1.1, 1.0), "20": (21.0, 1.1, 1.0), "22": (23.0, 1.1, 1.0),
    "24": (25.2, 1.3, 1.2), "25": (26.2, 1.3, 1.2), "26": (27.2, 1.3, 1.2),
    "28": (29.4, 1.3, 1.2), "30": (31.4, 1.3, 1.2), "32": (33.7, 1.3, 1.2),
    "35": (37.0, 1.6, 1.5), "37": (39.0, 1.6, 1.5), "40": (42.5, 1.85, 1.75),
    "42": (44.5, 1.85, 1.75), "47": (49.5, 1.85, 1.75), "52": (55.0, 2.15, 2.0),
}

# fmt: on


@dataclass(frozen=True)
class Key:
    """A DIN 6885-1 parallel key section for one shaft diameter (mm)."""

    shaft: float
    b: float
    h: float
    t1: float
    t2: float

    @property
    def shaft_depth(self) -> float:
        """Keyway depth into the shaft (t1)."""
        return self.t1

    @property
    def hub_depth(self) -> float:
        """Keyway depth into the hub (t2), measured from the bore."""
        return self.t2

    @property
    def designation(self) -> str:
        return f"DIN 6885 A {self.b:g} x {self.h:g}"


def keyway(shaft_d: float) -> Key:
    """The DIN 6885-1 key for a shaft of diameter ``shaft_d`` (over 6 up to 130 mm)."""
    b, h, t1, t2 = row_for(shaft_d, DIN6885_KEYS, "DIN 6885 keyway")
    return Key(float(shaft_d), b, h, t1, t2)


def key_length(shaft_d: float, length: float) -> float:
    """Shortest DIN 6885 key length >= ``length`` (raises past 200 mm)."""
    keyway(shaft_d)  # validates the shaft range
    for value in DIN6885_LENGTHS:
        if value >= float(length) - 1e-9:
            return value
    raise StandardsError(
        f"key length {length:g} mm exceeds the DIN 6885 series (200 mm)"
    )


@dataclass(frozen=True)
class RetainingRing:
    """A retaining ring (circlip) groove (mm). ``groove`` is the groove-bottom
    diameter, ``width`` the groove width (H13), ``thickness`` the ring's."""

    standard: str
    nominal: float
    groove: float
    width: float
    thickness: float

    @property
    def groove_depth(self) -> float:
        return round(abs(self.nominal - self.groove) / 2.0, 4)


def _key(d: float) -> str:
    return f"{float(d):g}"


def circlip_shaft(shaft_d: float) -> RetainingRing:
    """DIN 471 external ring groove for a shaft of diameter ``shaft_d``."""
    groove, m, s = lookup(DIN471, _key(shaft_d), "DIN 471 shaft diameter")
    return RetainingRing("DIN 471", float(shaft_d), groove, m, s)


def circlip_bore(bore_d: float) -> RetainingRing:
    """DIN 472 internal ring groove for a bore of diameter ``bore_d``."""
    groove, m, s = lookup(DIN472, _key(bore_d), "DIN 472 bore diameter")
    return RetainingRing("DIN 472", float(bore_d), groove, m, s)
