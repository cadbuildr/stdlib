"""Surface finish (roughness) and ISO 2768 general tolerances.

::

    ra_grade(1.6)                     # "N7"
    processes_for_ra(0.8)             # ["grinding", "reaming", "turning", ...]
    RA_FOR["bearing seat (shaft)"]    # 0.8 µm
    general_tolerance(45, "m")        # ±0.3 mm (ISO 2768-1 medium)
    general_angle_tolerance(30, "m")  # ±0.5 degree
    flatness_tolerance(200, "K")      # 0.4 mm (ISO 2768-2 K)

Sources: ISO 1302 (Ra in µm and the N1..N12 roughness grades), typical
achievable Ra per process (Machinery's Handbook surface-texture chart, average
production ranges), recommended Ra per function (bearing-maker / Parker
O-ring handbook guidance), ISO 2768-1 (linear, radius / chamfer and angular
general tolerances, classes f m c v) and ISO 2768-2 (straightness / flatness
classes H K L).
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from ._common import OutOfRange, StandardsError, lookup, row_for

__all__ = [
    "N_GRADES",
    "PROCESS_RA",
    "RA_FOR",
    "flatness_tolerance",
    "general_angle_tolerance",
    "general_tolerance",
    "processes_for_ra",
    "ra_grade",
    "radius_tolerance",
]

# fmt: off
# ISO 1302 roughness grade -> Ra (µm).
N_GRADES: Dict[str, float] = {
    "N1": 0.025, "N2": 0.05, "N3": 0.1, "N4": 0.2, "N5": 0.4, "N6": 0.8,
    "N7": 1.6, "N8": 3.2, "N9": 6.3, "N10": 12.5, "N11": 25.0, "N12": 50.0,
}

# Typical production Ra range (µm, best .. roughest).
PROCESS_RA: Dict[str, Tuple[float, float]] = {
    "lapping / polishing": (0.05, 0.4),
    "grinding": (0.1, 1.6),
    "honing": (0.1, 0.8),
    "reaming": (0.4, 3.2),
    "turning": (0.4, 6.3),
    "milling": (0.8, 6.3),
    "drilling": (1.6, 6.3),
    "edm (wire)": (0.8, 3.2),
    "die casting": (0.8, 3.2),
    "laser cutting": (3.2, 12.5),
    "waterjet": (3.2, 12.5),
    "sand casting": (12.5, 50.0),
    "sla print": (0.4, 3.2),
    "sls / mjf print": (6.3, 12.5),
    "fdm print": (6.3, 25.0),
}

# Recommended Ra (µm) by function.
RA_FOR: Dict[str, float] = {
    "bearing seat (shaft)": 0.8,
    "bearing seat (housing)": 1.6,
    "o-ring gland, static": 1.6,
    "o-ring gland, dynamic": 0.4,
    "sliding fit (bushing)": 0.8,
    "press fit": 1.6,
    "general machined face": 3.2,
    "non-functional face": 6.3,
}

_LINEAR_STEPS = (0.5, 3, 6, 30, 120, 400, 1000, 2000, 4000)
# ISO 2768-1 linear: class -> ± per step (None = not specified).
_LINEAR: Dict[str, Tuple] = {
    "f": (0.05, 0.05, 0.1, 0.15, 0.2, 0.3, 0.5, None),
    "m": (0.1, 0.1, 0.2, 0.3, 0.5, 0.8, 1.2, 2.0),
    "c": (0.2, 0.3, 0.5, 0.8, 1.2, 2.0, 3.0, 4.0),
    "v": (None, 0.5, 1.0, 1.5, 2.5, 4.0, 6.0, 8.0),
}
# ISO 2768-1 external radii and chamfer heights.
_RADIUS: Dict[str, Tuple[float, float, float]] = {
    "f": (0.2, 0.5, 1.0), "m": (0.2, 0.5, 1.0), "c": (0.4, 1.0, 2.0), "v": (0.4, 1.0, 2.0),
}
# ISO 2768-1 angular, by shorter leg length (mm): degrees.
_ANGLE_ROWS = [(0, 10), (10, 50), (50, 120), (120, 400), (400, float("inf"))]
_ANGLE: Dict[str, Tuple[float, ...]] = {
    "f": (1.0, 0.5, 20 / 60, 10 / 60, 5 / 60),
    "m": (1.0, 0.5, 20 / 60, 10 / 60, 5 / 60),
    "c": (1.5, 1.0, 0.5, 15 / 60, 10 / 60),
    "v": (3.0, 2.0, 1.0, 0.5, 20 / 60),
}
# ISO 2768-2 straightness and flatness (mm) by nominal length.
_FLAT_ROWS = [(0, 10), (10, 30), (30, 100), (100, 300), (300, 1000), (1000, 3000)]
_FLAT: Dict[str, Tuple[float, ...]] = {
    "H": (0.02, 0.05, 0.1, 0.2, 0.3, 0.4),
    "K": (0.05, 0.1, 0.2, 0.4, 0.6, 0.8),
    "L": (0.1, 0.2, 0.4, 0.8, 1.2, 1.6),
}

# fmt: on


def ra_grade(ra_um: float) -> str:
    """ISO 1302 N grade for Ra (µm): the finest grade whose Ra >= ``ra_um``."""
    for grade, value in N_GRADES.items():
        if value >= float(ra_um) - 1e-12:
            return grade
    raise OutOfRange(f"Ra {ra_um:g} µm is rougher than N12 (50 µm)")


def processes_for_ra(ra_um: float) -> List[str]:
    """Processes that typically reach ``ra_um`` (µm) or better, finest first."""
    return [
        p
        for p, (best, _rough) in sorted(PROCESS_RA.items(), key=lambda kv: kv[1])
        if best <= float(ra_um)
    ]


def _cls(cls: str, table: Dict, what: str):
    return lookup(table, str(cls).strip(), what)


def general_tolerance(length: float, cls: str = "m") -> float:
    """ISO 2768-1 permissible deviation ± (mm) for a linear size ``length``."""
    values = _cls(cls.lower(), _LINEAR, "ISO 2768-1 tolerance class")
    rows = [(_LINEAR_STEPS[i], _LINEAR_STEPS[i + 1], v) for i, v in enumerate(values)]
    v = float(length)
    if v < _LINEAR_STEPS[0]:
        raise OutOfRange(
            "ISO 2768-1 linear tolerances start at 0.5 mm; tolerance smaller sizes explicitly"
        )
    value = (
        values[0] if v <= _LINEAR_STEPS[1] else row_for(v, rows, "ISO 2768-1 linear")
    )
    if value is None:
        raise StandardsError(
            f"ISO 2768-{cls}: no general tolerance specified for {v:g} mm"
        )
    return value


def radius_tolerance(size: float, cls: str = "m") -> float:
    """ISO 2768-1 ± (mm) for an external radius or chamfer height ``size``."""
    a, b, c = _cls(cls.lower(), _RADIUS, "ISO 2768-1 tolerance class")
    v = float(size)
    if v < 0.5:
        raise OutOfRange("ISO 2768-1 radii / chamfers start at 0.5 mm")
    return a if v <= 3 else (b if v <= 6 else c)


def general_angle_tolerance(shorter_leg: float, cls: str = "m") -> float:
    """ISO 2768-1 angular ± (degrees) for an angle whose shorter leg is ``shorter_leg`` mm."""
    values = _cls(cls.lower(), _ANGLE, "ISO 2768-1 tolerance class")
    rows = [(lo, hi, values[i]) for i, (lo, hi) in enumerate(_ANGLE_ROWS)]
    return row_for(shorter_leg, rows, "ISO 2768-1 angular")


def flatness_tolerance(length: float, cls: str = "K") -> float:
    """ISO 2768-2 straightness / flatness (mm) over nominal ``length``."""
    values = _cls(cls.upper(), _FLAT, "ISO 2768-2 tolerance class")
    rows = [(lo, hi, values[i]) for i, (lo, hi) in enumerate(_FLAT_ROWS)]
    return row_for(length, rows, "ISO 2768-2 flatness")
