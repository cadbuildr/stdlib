"""ISO 286 limits and fits: tolerance grades, fundamental deviations, fits.

::

    fit("H7/g6", 10)          # Fit: hole 10.000..10.015, shaft 9.986..9.995
    fit("H7/g6", 10).kind     # "clearance"
    tolerance("k6", 8).max    # 8.010
    tolerance("H7", 22).limits  # (22.0, 22.021)

Sources: ISO 286-1:2010 Table 1 (standard tolerance grades IT1..IT16, nominal
sizes up to 500 mm), Tables 2 and 3 (fundamental deviations of shafts and
holes), and the hole rules of ISO 286-1 clause 5.3: EI = -es for A..H,
ES = -ei + Delta for K, M, N up to IT8 and P..ZC up to IT7 (Delta = IT_n -
IT_(n-1), zero up to 3 mm). Letters covered: shafts c d e f g h js k m n p r s,
holes C D E F G H JS K M N P R S. Values are in micrometres in the tables and
millimetres in the API.

Printed (FDM / SLA / SLS) parts do not follow ISO 286; :func:`printed_clearance`
gives the usual design allowances instead.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

from ._common import StandardsError, UnknownSize, lookup, range_index, row_for

__all__ = [
    "BEARING_RING_TOLERANCE_UM",
    "BEARING_SEATS",
    "FUNDAMENTAL_DEVIATION_SHAFT_UM",
    "Fit",
    "IT_GRADES_UM",
    "PREFERRED_FITS",
    "PRINTED_CLEARANCE",
    "SIZE_STEPS",
    "Tolerance",
    "bearing_fit",
    "fit",
    "it_grade",
    "printed_clearance",
    "tolerance",
]

# ISO 286-1 Table 1 nominal size steps (mm): "over a up to and including b".
SIZE_STEPS: Tuple[float, ...] = (
    0,
    3,
    6,
    10,
    18,
    30,
    50,
    80,
    120,
    180,
    250,
    315,
    400,
    500,
)

# fmt: off
# ISO 286-1 Table 1 — standard tolerance grades, micrometres, one value per size step.
IT_GRADES_UM: Dict[int, Tuple[float, ...]] = {
    1: (0.8, 1, 1, 1.2, 1.5, 1.5, 2, 2.5, 3.5, 4.5, 6, 7, 8),
    2: (1.2, 1.5, 1.5, 2, 2.5, 2.5, 3, 4, 5, 7, 8, 9, 10),
    3: (2, 2.5, 2.5, 3, 4, 4, 5, 6, 8, 10, 12, 13, 15),
    4: (3, 4, 4, 5, 6, 7, 8, 10, 12, 14, 16, 18, 20),
    5: (4, 5, 6, 8, 9, 11, 13, 15, 18, 20, 23, 25, 27),
    6: (6, 8, 9, 11, 13, 16, 19, 22, 25, 29, 32, 36, 40),
    7: (10, 12, 15, 18, 21, 25, 30, 35, 40, 46, 52, 57, 63),
    8: (14, 18, 22, 27, 33, 39, 46, 54, 63, 72, 81, 89, 97),
    9: (25, 30, 36, 43, 52, 62, 74, 87, 100, 115, 130, 140, 155),
    10: (40, 48, 58, 70, 84, 100, 120, 140, 160, 185, 210, 230, 250),
    11: (60, 75, 90, 110, 130, 160, 190, 220, 250, 290, 320, 360, 400),
    12: (100, 120, 150, 180, 210, 250, 300, 350, 400, 460, 520, 570, 630),
    13: (140, 180, 220, 270, 330, 390, 460, 540, 630, 720, 810, 890, 970),
    14: (250, 300, 360, 430, 520, 620, 740, 870, 1000, 1150, 1300, 1400, 1550),
    15: (400, 480, 580, 700, 840, 1000, 1200, 1400, 1600, 1850, 2100, 2300, 2500),
    16: (600, 750, 900, 1100, 1300, 1600, 1900, 2200, 2500, 2900, 3200, 3600, 4000),
}

# fmt: on


def _steps(values: Sequence[float]) -> List[Tuple[float, float, float]]:
    return [(SIZE_STEPS[i], SIZE_STEPS[i + 1], v) for i, v in enumerate(values)]


def _rows(*rows: Tuple[float, float, float]) -> List[Tuple[float, float, float]]:
    return list(rows)


# fmt: off
# ISO 286-1 Table 2 — fundamental deviations of shafts, micrometres.
# a..h: upper deviation es (<= 0); k..s: lower deviation ei (>= 0).
# k is the IT4..IT7 column (k is 0 for <= IT3 and > IT7).
FUNDAMENTAL_DEVIATION_SHAFT_UM: Dict[str, List[Tuple[float, float, float]]] = {
    "c": _rows(
        (0, 3, -60), (3, 6, -70), (6, 10, -80), (10, 18, -95), (18, 30, -110),
        (30, 40, -120), (40, 50, -130), (50, 65, -140), (65, 80, -150),
        (80, 100, -170), (100, 120, -180), (120, 140, -200), (140, 160, -210),
        (160, 180, -230), (180, 200, -240), (200, 225, -260), (225, 250, -280),
        (250, 280, -300), (280, 315, -330), (315, 355, -360), (355, 400, -400),
        (400, 450, -440), (450, 500, -480),
    ),
    "d": _steps((-20, -30, -40, -50, -65, -80, -100, -120, -145, -170, -190, -210, -230)),
    "e": _steps((-14, -20, -25, -32, -40, -50, -60, -72, -85, -100, -110, -125, -135)),
    "f": _steps((-6, -10, -13, -16, -20, -25, -30, -36, -43, -50, -56, -62, -68)),
    "g": _steps((-2, -4, -5, -6, -7, -9, -10, -12, -14, -15, -17, -18, -20)),
    "h": _steps((0,) * 13),
    "k": _steps((0, 1, 1, 1, 2, 2, 2, 3, 3, 4, 4, 4, 5)),
    "m": _steps((2, 4, 6, 7, 8, 9, 11, 13, 15, 17, 20, 21, 23)),
    "n": _steps((4, 8, 10, 12, 15, 17, 20, 23, 27, 31, 34, 37, 40)),
    "p": _steps((6, 12, 15, 18, 22, 26, 32, 37, 43, 50, 56, 62, 68)),
    "r": _rows(
        (0, 3, 10), (3, 6, 15), (6, 10, 19), (10, 18, 23), (18, 30, 28),
        (30, 50, 34), (50, 65, 41), (65, 80, 43), (80, 100, 51), (100, 120, 54),
        (120, 140, 63), (140, 160, 65), (160, 180, 68), (180, 200, 77),
        (200, 225, 80), (225, 250, 84), (250, 280, 94), (280, 315, 98),
        (315, 355, 108), (355, 400, 114), (400, 450, 126), (450, 500, 132),
    ),
    "s": _rows(
        (0, 3, 14), (3, 6, 19), (6, 10, 23), (10, 18, 28), (18, 30, 35),
        (30, 50, 43), (50, 65, 53), (65, 80, 59), (80, 100, 71), (100, 120, 79),
        (120, 140, 92), (140, 160, 100), (160, 180, 108), (180, 200, 122),
        (200, 225, 130), (225, 250, 140), (250, 280, 158), (280, 315, 170),
        (315, 355, 190), (355, 400, 208), (400, 450, 232), (450, 500, 252),
    ),
}

# fmt: on
_UPPER_LETTERS = ("c", "d", "e", "f", "g", "h")
_LOWER_LETTERS = ("k", "m", "n", "p", "r", "s")
SHAFT_LETTERS = _UPPER_LETTERS + ("js",) + _LOWER_LETTERS
HOLE_LETTERS = tuple(x.upper() for x in SHAFT_LETTERS)

# ISO 286-2 / ISO 1829 preferred hole-basis fits, with what they are for.
PREFERRED_FITS: Dict[str, str] = {
    "H11/c11": "loose running: wide commercial tolerances, external parts",
    "H9/d9": "free running: large temperature swings, high speeds",
    "H8/f7": "close running: accurate location at moderate speed (spindles)",
    "H7/g6": "sliding: no running, moves and turns freely, locates accurately",
    "H7/h6": "locational clearance: snug, assembled by hand, lubricated",
    "H7/js6": "locational transition: accurate location, light mallet",
    "H7/k6": "locational transition: small interference possible (bearings)",
    "H7/n6": "locational transition: more accurate, press to assemble",
    "H7/p6": "locational interference: rigid alignment, no load transfer",
    "H7/r6": "light press: steel parts, small torques",
    "H7/s6": "medium drive: ordinary steel parts, shrink fits on light sections",
}

# Rolling-bearing seats (general rotating-shaft case, normal loads):
# rotating inner ring -> transition/interference shaft, stationary outer ring
# -> housing H7/J7. Common catalogue guidance (e.g. SKF / Schaeffler general
# recommendations); check the bearing maker's table for heavy loads.
BEARING_SEATS: Dict[str, Dict[str, str]] = {
    "rotating shaft, normal load": {"shaft": "k6", "housing": "H7"},
    "rotating shaft, light load": {"shaft": "js6", "housing": "H7"},
    "rotating shaft, heavy load": {"shaft": "m6", "housing": "H7"},
    "rotating housing (wheel hub)": {"shaft": "g6", "housing": "N7"},
    "axially free (floating) bearing": {"shaft": "k6", "housing": "G7"},
}

# Diametral clearance (mm) a printed hole needs over its mating pin, by
# process and intent: typical design allowances (CNC Kitchen / Prusa / Formlabs
# / HP MJF design guides). Calibrate with a test coupon for your machine.
PRINTED_CLEARANCE: Dict[str, Dict[str, float]] = {
    "fdm": {"press": 0.0, "snug": 0.15, "sliding": 0.3, "loose": 0.5},
    "sla": {"press": 0.0, "snug": 0.1, "sliding": 0.2, "loose": 0.3},
    "sls": {"press": 0.1, "snug": 0.2, "sliding": 0.3, "loose": 0.5},
}


def it_grade(grade: int, size: float) -> float:
    """Standard tolerance ``IT<grade>`` (mm) for nominal ``size`` (mm), ISO 286-1 Table 1."""
    if int(grade) not in IT_GRADES_UM:
        raise UnknownSize(
            f"IT{grade} is not tabulated; grades IT1..IT16 are ({sorted(IT_GRADES_UM)})"
        )
    i = range_index(size, SIZE_STEPS, f"IT{grade}")
    return IT_GRADES_UM[int(grade)][i] / 1000.0


def _it_um(grade: int, size: float) -> float:
    return it_grade(grade, size) * 1000.0


def _shaft_fd_um(letter: str, size: float) -> float:
    return row_for(size, FUNDAMENTAL_DEVIATION_SHAFT_UM[letter], f"shaft {letter}")


def _js_half_um(grade: int, size: float) -> float:
    it = _it_um(grade, size)
    # ISO 286-1 5.3.1: for js7..js11 an odd IT value is rounded down to the
    # nearest even micrometre so the deviation is a whole micrometre.
    if 7 <= grade <= 11 and float(it).is_integer() and int(it) % 2 == 1:
        it -= 1
    return it / 2.0


def _shaft_deviations_um(letter: str, grade: int, size: float) -> Tuple[float, float]:
    """(es, ei) in micrometres."""
    it = _it_um(grade, size)
    if letter == "js":
        half = _js_half_um(grade, size)
        return half, -half
    if letter in _UPPER_LETTERS:
        es = _shaft_fd_um(letter, size)
        return es, es - it
    if letter == "k" and not 4 <= grade <= 7:
        ei = 0.0
    else:
        ei = _shaft_fd_um(letter, size)
    return ei + it, ei


def _delta_um(grade: int, size: float) -> float:
    if float(size) <= 3 or grade <= 1:
        return 0.0
    return _it_um(grade, size) - _it_um(grade - 1, size)


def _hole_deviations_um(letter: str, grade: int, size: float) -> Tuple[float, float]:
    """(ES, EI) in micrometres (ISO 286-1 5.3.2 general and special rules)."""
    it = _it_um(grade, size)
    low = letter.lower()
    if low == "js":
        half = _js_half_um(grade, size)
        return half, -half
    if low in _UPPER_LETTERS:  # A..H: EI = -es
        ei = -_shaft_fd_um(low, size)
        return ei + it, ei
    if low == "k":
        if grade <= 8:
            es = -_shaft_fd_um("k", size) + _delta_um(grade, size)
        else:
            es = 0.0
    elif low == "m":
        es = -_shaft_fd_um("m", size) + (_delta_um(grade, size) if grade <= 8 else 0.0)
    elif low == "n":
        if grade <= 8:
            es = -_shaft_fd_um("n", size) + _delta_um(grade, size)
        else:
            es = 0.0 if float(size) > 3 else -_shaft_fd_um("n", size)
    else:  # P..S
        es = -_shaft_fd_um(low, size) + (_delta_um(grade, size) if grade <= 7 else 0.0)
    return es, es - it


_DESIGNATION = re.compile(r"^\s*([A-Za-z]{1,2})\s*(\d{1,2})\s*$")


@dataclass(frozen=True)
class Tolerance:
    """A toleranced size: ``Tolerance("H7", 22.0, upper=0.021, lower=0.0)``.

    ``upper`` / ``lower`` are the deviations (mm) from ``nominal``; ``kind`` is
    ``"hole"`` (upper-case letter) or ``"shaft"``.
    """

    designation: str
    nominal: float
    upper: float
    lower: float
    kind: str

    @property
    def max(self) -> float:
        """Maximum size (mm)."""
        return round(self.nominal + self.upper, 6)

    @property
    def min(self) -> float:
        """Minimum size (mm)."""
        return round(self.nominal + self.lower, 6)

    @property
    def mean(self) -> float:
        """Middle of the zone (mm): the size to model for a nominal-accurate CAD."""
        return round(self.nominal + (self.upper + self.lower) / 2.0, 6)

    @property
    def limits(self) -> Tuple[float, float]:
        """``(min, max)`` in mm."""
        return self.min, self.max

    @property
    def width(self) -> float:
        """Tolerance zone width (the IT value), mm."""
        return round(self.upper - self.lower, 6)

    @property
    def mmc(self) -> float:
        """Maximum material condition: min hole / max shaft."""
        return self.min if self.kind == "hole" else self.max

    @property
    def lmc(self) -> float:
        """Least material condition: max hole / min shaft."""
        return self.max if self.kind == "hole" else self.min

    def __str__(self) -> str:
        def um(v: float) -> str:
            return "0" if abs(v) < 1e-9 else f"{v * 1000:+g}"

        return (
            f"Ø{self.nominal:g} {self.designation} ({um(self.upper)}/{um(self.lower)} µm"
            f" -> {self.min:.3f}..{self.max:.3f})"
        )


def tolerance(designation: str, size: float) -> Tolerance:
    """The ISO 286 tolerance zone ``designation`` ("H7", "g6", "js6", "K7"...) at
    nominal ``size`` mm. Upper-case letters are holes, lower-case shafts."""
    m = _DESIGNATION.match(str(designation))
    if not m:
        raise UnknownSize(
            f"Not an ISO 286 tolerance designation: {designation!r} (expected e.g. 'H7', 'g6')"
        )
    letter, grade = m.group(1), int(m.group(2))
    if letter.lower() == "js":
        letter = "JS" if letter[0].isupper() else "js"
    if letter in SHAFT_LETTERS:
        es, ei = _shaft_deviations_um(letter, grade, size)
        kind = "shaft"
        up, lo = es, ei
    elif letter in HOLE_LETTERS:
        up, lo = _hole_deviations_um(letter, grade, size)
        kind = "hole"
    else:
        raise UnknownSize(
            f"Tolerance letter {letter!r} is not covered. Holes: {', '.join(HOLE_LETTERS)};"
            f" shafts: {', '.join(SHAFT_LETTERS)}"
        )
    return Tolerance(
        designation=f"{letter}{grade}",
        nominal=float(size),
        upper=round(up / 1000.0, 6),
        lower=round(lo / 1000.0, 6),
        kind=kind,
    )


@dataclass(frozen=True)
class Fit:
    """A hole / shaft pair at one nominal size.

    ``max_clearance`` = largest hole - smallest shaft; ``min_clearance`` =
    smallest hole - largest shaft (negative: interference).
    """

    designation: str
    hole: Tolerance
    shaft: Tolerance

    @property
    def nominal(self) -> float:
        return self.hole.nominal

    @property
    def max_clearance(self) -> float:
        return round(self.hole.max - self.shaft.min, 6)

    @property
    def min_clearance(self) -> float:
        return round(self.hole.min - self.shaft.max, 6)

    @property
    def max_interference(self) -> float:
        """Largest interference (mm, >= 0 when the fit can interfere)."""
        return round(-self.min_clearance, 6)

    @property
    def kind(self) -> str:
        """``"clearance"``, ``"transition"`` or ``"interference"``."""
        if self.min_clearance >= 0:
            return "clearance"
        if self.max_clearance <= 0:
            return "interference"
        return "transition"

    @property
    def mean_clearance(self) -> float:
        return round((self.max_clearance + self.min_clearance) / 2.0, 6)

    @property
    def purpose(self) -> Optional[str]:
        """What the fit is for, when it is an ISO preferred fit."""
        return PREFERRED_FITS.get(self.designation)

    def __str__(self) -> str:
        return (
            f"Ø{self.nominal:g} {self.designation} {self.kind}: clearance"
            f" {self.min_clearance * 1000:+g}..{self.max_clearance * 1000:+g} µm"
        )


def fit(designation: str, size: float) -> Fit:
    """``fit("H7/g6", 10)`` -> :class:`Fit` with both limits and the clearance range."""
    parts = str(designation).replace(" ", "").split("/")
    if len(parts) != 2:
        raise StandardsError(
            f"A fit is written hole/shaft, e.g. 'H7/g6' (got {designation!r})"
        )
    hole, shaft = tolerance(parts[0], size), tolerance(parts[1], size)
    if hole.kind != "hole" or shaft.kind != "shaft":
        raise StandardsError(
            f"{designation!r}: write the hole first in upper case and the shaft in"
            " lower case, e.g. 'H7/g6'"
        )
    return Fit(
        designation=f"{hole.designation}/{shaft.designation}", hole=hole, shaft=shaft
    )


def printed_clearance(intent: str = "sliding", process: str = "fdm") -> float:
    """Diametral clearance (mm) to add to a printed hole for ``intent``
    (press / snug / sliding / loose) with ``process`` (fdm / sla / sls)."""
    row = lookup(PRINTED_CLEARANCE, process, "print process")
    return lookup(row, intent, f"{process} fit intent")


# ISO 492 Normal tolerance class, mean diameter deviation of rolling-bearing
# rings (µm, upper deviation 0): (over, up to and including, lower deviation).
BEARING_RING_TOLERANCE_UM: Dict[str, List[Tuple[float, float, float]]] = {
    "inner": [
        (2.5, 10, -8),
        (10, 18, -8),
        (18, 30, -10),
        (30, 50, -12),
        (50, 80, -15),
        (80, 120, -20),
    ],
    "outer": [
        (6, 18, -8),
        (18, 30, -9),
        (30, 50, -11),
        (50, 80, -13),
        (80, 120, -15),
        (120, 150, -18),
    ],
}


def _bearing_ring(ring: str, size: float) -> Tolerance:
    lower = row_for(size, BEARING_RING_TOLERANCE_UM[ring], f"ISO 492 {ring} ring")
    kind = "hole" if ring == "inner" else "shaft"
    return Tolerance("ISO 492 Normal", float(size), 0.0, lower / 1000.0, kind)


def bearing_fit(seat: str, size: float, ring: str = "inner") -> Fit:
    """Fit of a rolling-bearing ring (ISO 492 Normal class) on its seat.

    ``ring="inner"``: the bore of diameter ``size`` on a shaft toleranced
    ``seat`` ("k6"); ``ring="outer"``: the outer ring ``size`` in a housing
    ``seat`` ("H7"). The bearing bore is narrower than an H hole (0 / -8 µm),
    so k6 on a bearing is a light interference, not a transition."""
    if ring == "inner":
        shaft = tolerance(seat, size)
        if shaft.kind != "shaft":
            raise StandardsError(
                f"bearing_fit: inner ring sits on a shaft (lower case), got {seat!r}"
            )
        return Fit(f"ISO 492/{shaft.designation}", _bearing_ring("inner", size), shaft)
    if ring == "outer":
        housing = tolerance(seat, size)
        if housing.kind != "hole":
            raise StandardsError(
                f"bearing_fit: outer ring sits in a housing (upper case), got {seat!r}"
            )
        return Fit(
            f"{housing.designation}/ISO 492", housing, _bearing_ring("outer", size)
        )
    raise StandardsError(f"bearing_fit: ring must be 'inner' or 'outer', got {ring!r}")
