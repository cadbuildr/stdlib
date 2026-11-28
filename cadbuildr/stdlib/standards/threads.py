"""Screw threads and the holes around them: metric coarse / fine, UNC / UNF.

::

    t = thread("M6")            # Thread: pitch 1.0, minor 4.917, tap drill 5.0
    t.clearance("close")        # 6.4  (ISO 273 fine series)
    thread("1/4-20").tap_drill  # 5.105 mm (#7 drill)
    counterbore("M5")           # Counterbore(diameter=10.0, depth=5.4) for ISO 4762
    countersink("M4")           # Countersink(diameter=8.96, angle=90) for ISO 10642
    screw_length("M5", grip=8)  # 16: next ISO 4762 length with 1.5 d engagement

Sources:

* basic profile ISO 68-1 / basic dimensions ISO 724: pitch diameter
  ``d2 = d - 0.6495 P``, internal minor ``D1 = d - 1.0825 P``, external
  minor ``d3 = d - 1.2269 P``;
* diameter / pitch series ISO 261 (coarse and the common fine pitches);
* tap drills ISO 2306 (``d - P`` for metric, ~75 % thread for unified);
* clearance holes ISO 273 fine / medium / coarse ("close / normal / loose");
* unified sizes ASME B1.1 (UNC / UNF major diameters and TPI); unified tap
  and clearance drills from the usual shop chart (75 % thread, close / free fit);
* counterbores for ISO 4762 heads after DIN 974-1 (row 1, no washer), depth =
  head height ``k`` + allowance so the head sits just below the face;
* countersinks: theoretical head diameter ``dk`` (the sharp-edged cone the
  real head fits inside) of ISO 10642 (socket countersunk) and ISO 7046-1
  (cross-recess countersunk; equal to the ISO 15065 countersink diameters),
  90 degrees, so every head of the standard sits flush or just below;
* screw lengths: the ISO 4762 preferred length series.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from ._common import StandardsError, UnknownSize, lookup, metric_diameter

__all__ = [
    "CLEARANCE_FITS",
    "COUNTERBORE_ISO4762",
    "COUNTERSINK_HEADS",
    "Counterbore",
    "Countersink",
    "ISO4762_LENGTHS",
    "METRIC_COARSE",
    "METRIC_FINE",
    "Thread",
    "UNIFIED",
    "clearance_diameter",
    "counterbore",
    "countersink",
    "metric_sizes",
    "screw_length",
    "tap_drill",
    "thread",
]

INCH = 25.4

# fmt: off
# ISO 261 coarse series: size -> (pitch, tap drill ISO 2306, ISO 273 close, medium, coarse).
# Sizes foundation's hole wizard (``cadbuildr.foundation.holes``) covers are
# read from it below, so TappedHole / ClearanceHole and this module cannot
# drift; the rows here are the fallback and the sizes foundation lacks.
METRIC_COARSE: Dict[str, Tuple[float, float, float, float, float]] = {
    "M1.6": (0.35, 1.25, 1.7, 1.8, 2.0),
    "M2": (0.40, 1.6, 2.2, 2.4, 2.6),
    "M2.5": (0.45, 2.05, 2.7, 2.9, 3.1),
    "M3": (0.50, 2.5, 3.2, 3.4, 3.6),
    "M4": (0.70, 3.3, 4.3, 4.5, 4.8),
    "M5": (0.80, 4.2, 5.3, 5.5, 5.8),
    "M6": (1.00, 5.0, 6.4, 6.6, 7.0),
    "M8": (1.25, 6.8, 8.4, 9.0, 10.0),
    "M10": (1.50, 8.5, 10.5, 11.0, 12.0),
    "M12": (1.75, 10.2, 13.0, 13.5, 14.5),
    "M14": (2.00, 12.0, 15.0, 15.5, 16.5),
    "M16": (2.00, 14.0, 17.0, 17.5, 18.5),
    "M18": (2.50, 15.5, 19.0, 20.0, 21.0),
    "M20": (2.50, 17.5, 21.0, 22.0, 24.0),
    "M22": (2.50, 19.5, 23.0, 24.0, 26.0),
    "M24": (3.00, 21.0, 25.0, 26.0, 28.0),
    "M27": (3.00, 24.0, 28.0, 30.0, 32.0),
    "M30": (3.50, 26.5, 31.0, 33.0, 35.0),
    "M36": (4.00, 32.0, 37.0, 39.0, 42.0),
}
# fmt: on


def _from_foundation() -> None:
    from cadbuildr.foundation.holes import ISO_METRIC_COARSE

    for d, row in ISO_METRIC_COARSE.items():
        METRIC_COARSE[f"M{d:g}"] = tuple(float(v) for v in row)
    order = sorted(METRIC_COARSE, key=lambda k: float(k[1:]))
    items = {k: METRIC_COARSE[k] for k in order}
    METRIC_COARSE.clear()
    METRIC_COARSE.update(items)


_from_foundation()

# ISO 261 common fine pitches: designation -> pitch (tap drill = d - P).
METRIC_FINE: Dict[str, float] = {
    "M3x0.35": 0.35,
    "M4x0.5": 0.5,
    "M5x0.5": 0.5,
    "M6x0.75": 0.75,
    "M8x1": 1.0,
    "M10x1": 1.0,
    "M10x1.25": 1.25,
    "M12x1.25": 1.25,
    "M12x1.5": 1.5,
    "M14x1.5": 1.5,
    "M16x1.5": 1.5,
    "M18x1.5": 1.5,
    "M20x1.5": 1.5,
    "M22x1.5": 1.5,
    "M24x2": 2.0,
}

# ASME B1.1 unified threads: designation -> (series, major in, TPI,
# tap drill (name, in), clearance close (name, in), clearance free (name, in)).
UNIFIED: Dict[
    str, Tuple[str, float, int, Tuple[str, float], Tuple[str, float], Tuple[str, float]]
] = {
    "#2-56": ("UNC", 0.086, 56, ("#50", 0.0700), ("#43", 0.0890), ("#41", 0.0960)),
    "#4-40": ("UNC", 0.112, 40, ("#43", 0.0890), ("#32", 0.1160), ("#30", 0.1285)),
    "#6-32": ("UNC", 0.138, 32, ("#36", 0.1065), ("#27", 0.1440), ("#18", 0.1695)),
    "#8-32": ("UNC", 0.164, 32, ("#29", 0.1360), ("#18", 0.1695), ("#9", 0.1960)),
    "#10-24": ("UNC", 0.190, 24, ("#25", 0.1495), ("#9", 0.1960), ("#2", 0.2210)),
    "#10-32": ("UNF", 0.190, 32, ("#21", 0.1590), ("#9", 0.1960), ("#2", 0.2210)),
    "1/4-20": ("UNC", 0.250, 20, ("#7", 0.2010), ("F", 0.2570), ("H", 0.2660)),
    "1/4-28": ("UNF", 0.250, 28, ("#3", 0.2130), ("F", 0.2570), ("H", 0.2660)),
    "5/16-18": ("UNC", 0.3125, 18, ("F", 0.2570), ("P", 0.3230), ("Q", 0.3320)),
    "5/16-24": ("UNF", 0.3125, 24, ("I", 0.2720), ("P", 0.3230), ("Q", 0.3320)),
    "3/8-16": ("UNC", 0.375, 16, ("5/16", 0.3125), ("W", 0.3860), ("X", 0.3970)),
    "3/8-24": ("UNF", 0.375, 24, ("Q", 0.3320), ("W", 0.3860), ("X", 0.3970)),
    "7/16-14": ("UNC", 0.4375, 14, ("U", 0.3680), ("29/64", 0.4531), ("15/32", 0.4688)),
    "7/16-20": (
        "UNF",
        0.4375,
        20,
        ("25/64", 0.3906),
        ("29/64", 0.4531),
        ("15/32", 0.4688),
    ),
    "1/2-13": (
        "UNC",
        0.500,
        13,
        ("27/64", 0.4219),
        ("33/64", 0.5156),
        ("17/32", 0.5312),
    ),
    "1/2-20": (
        "UNF",
        0.500,
        20,
        ("29/64", 0.4531),
        ("33/64", 0.5156),
        ("17/32", 0.5312),
    ),
    "5/8-11": (
        "UNC",
        0.625,
        11,
        ("17/32", 0.5312),
        ("41/64", 0.6406),
        ("21/32", 0.6562),
    ),
    "5/8-18": (
        "UNF",
        0.625,
        18,
        ("37/64", 0.5781),
        ("41/64", 0.6406),
        ("21/32", 0.6562),
    ),
    "3/4-10": (
        "UNC",
        0.750,
        10,
        ("21/32", 0.6562),
        ("49/64", 0.7656),
        ("25/32", 0.7812),
    ),
    "3/4-16": (
        "UNF",
        0.750,
        16,
        ("11/16", 0.6875),
        ("49/64", 0.7656),
        ("25/32", 0.7812),
    ),
}

# fmt: on
# User-facing names of the ISO 273 series.
CLEARANCE_FITS: Dict[str, str] = {
    "close": "ISO 273 fine series (accurate location, little float)",
    "normal": "ISO 273 medium series (the default for through-bolts)",
    "loose": "ISO 273 coarse series (cast / welded / printed parts, more float)",
}
_FIT_ALIASES = {
    "close": "close",
    "fine": "close",
    "normal": "normal",
    "medium": "normal",
    "free": "normal",
    "loose": "loose",
    "coarse": "loose",
}

# fmt: off
# DIN 974-1 row 1 counterbore diameters for ISO 4762 socket heads (no washer),
# plus ISO 4762 head height k (= d); depth = k + allowance.
COUNTERBORE_ISO4762: Dict[str, Tuple[float, float]] = {
    "M1.6": (3.5, 1.6),
    "M2": (4.4, 2.0),
    "M2.5": (5.5, 2.5),
    "M3": (6.5, 3.0),
    "M4": (8.0, 4.0),
    "M5": (10.0, 5.0),
    "M6": (11.0, 6.0),
    "M8": (15.0, 8.0),
    "M10": (18.0, 10.0),
    "M12": (20.0, 12.0),
    "M14": (24.0, 14.0),
    "M16": (26.0, 16.0),
    "M20": (33.0, 20.0),
    "M24": (40.0, 24.0),
    "M30": (50.0, 30.0),
}

# Theoretical maximum head diameter dk of 90 degree countersunk heads (mm).
COUNTERSINK_HEADS: Dict[str, Dict[str, float]] = {
    "ISO 10642": {  # hexagon socket countersunk head
        "M3": 6.72, "M4": 8.96, "M5": 11.20, "M6": 13.44, "M8": 17.92,
        "M10": 22.40, "M12": 26.88, "M14": 30.80, "M16": 33.60, "M20": 40.32,
    },
    "ISO 7046": {  # cross recessed countersunk head, theoretical dk (= ISO 15065)
        "M2": 4.4, "M2.5": 5.5, "M3": 6.3, "M4": 9.4, "M5": 10.4, "M6": 12.6,
        "M8": 17.3, "M10": 20.0,
    },
}

# ISO 4762 preferred nominal lengths (mm).
ISO4762_LENGTHS: Tuple[float, ...] = (
    2.5, 3, 4, 5, 6, 8, 10, 12, 16, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70,
    80, 90, 100, 110, 120, 130, 140, 150, 160, 180, 200,
)

# fmt: on


@dataclass(frozen=True)
class Thread:
    """One thread size. Lengths in mm; ``tpi`` only for unified threads."""

    designation: str
    system: str  # "metric" | "unified"
    series: str  # "coarse" | "fine" | "UNC" | "UNF"
    major: float
    pitch: float
    tap_drill: float
    clearance_close: float
    clearance_normal: float
    clearance_loose: Optional[float]
    tpi: Optional[int] = None
    tap_drill_name: Optional[str] = None

    @property
    def nominal(self) -> float:
        return self.major

    @property
    def pitch_diameter(self) -> float:
        """d2 = d - 0.6495 P (ISO 724)."""
        return round(self.major - 0.649519 * self.pitch, 4)

    @property
    def minor_internal(self) -> float:
        """D1 = d - 1.0825 P: the nut / tapped-hole minor diameter (ISO 724)."""
        return round(self.major - 1.082532 * self.pitch, 4)

    @property
    def minor_external(self) -> float:
        """d3 = d - 1.2269 P: the bolt root diameter (ISO 724)."""
        return round(self.major - 1.226869 * self.pitch, 4)

    @property
    def stress_area(self) -> float:
        """Tensile stress area As (mm²), ISO 898-1: pi/4 ((d2 + d3) / 2)²."""
        import math

        return round(
            math.pi / 4.0 * ((self.pitch_diameter + self.minor_external) / 2.0) ** 2, 3
        )

    @property
    def screw_size(self) -> str:
        """The size a ``ScrewHole`` / ``ScrewHead`` interface uses ("M6", "1/4-20")."""
        return (
            self.designation.split("x")[0]
            if self.system == "metric"
            else self.designation
        )

    def clearance(self, fit: str = "normal") -> float:
        """Clearance hole diameter for ``fit`` = close / normal / loose (ISO 273)."""
        key = _FIT_ALIASES.get(str(getattr(fit, "value", fit)).lower())
        if key is None:
            raise UnknownSize(
                f"Unknown clearance fit {fit!r}; use one of {', '.join(CLEARANCE_FITS)}"
            )
        value = {
            "close": self.clearance_close,
            "normal": self.clearance_normal,
            "loose": self.clearance_loose,
        }[key]
        if value is None:
            raise StandardsError(
                f"{self.designation}: no '{key}' clearance in the unified chart (close / normal only)"
            )
        return value


def metric_sizes() -> Tuple[str, ...]:
    """The ISO 261 coarse sizes covered, smallest first ("M1.6" .. "M36")."""
    return tuple(METRIC_COARSE)


def _coarse_key(d: float) -> str:
    return f"M{d:g}"


def thread(designation: str) -> Thread:
    """Look up ``"M6"``, ``"M10x1.25"``, ``"1/4-20"``, ``"#10-32"`` (also ``"1/4-20 UNC"``)."""
    text = str(designation).strip()
    unified_key = text.replace(" UNC", "").replace(" UNF", "").replace(" ", "")
    if unified_key in UNIFIED:
        series, major_in, tpi, tap, close, free = UNIFIED[unified_key]
        return Thread(
            designation=unified_key,
            system="unified",
            series=series,
            major=round(major_in * INCH, 4),
            pitch=round(INCH / tpi, 4),
            tap_drill=round(tap[1] * INCH, 3),
            tap_drill_name=tap[0],
            clearance_close=round(close[1] * INCH, 3),
            clearance_normal=round(free[1] * INCH, 3),
            clearance_loose=None,
            tpi=tpi,
        )
    if text and text[0] in "#0123456789" and "-" in text:
        lookup(UNIFIED, unified_key, "unified thread")  # raises with suggestions
    d, pitch = metric_diameter(
        designation if isinstance(designation, (int, float)) else text
    )
    key = _coarse_key(d)
    coarse = lookup(METRIC_COARSE, key, "metric thread size")
    p_coarse, tap, close, normal, loose = coarse
    if pitch is None or abs(pitch - p_coarse) < 1e-9:
        return Thread(key, "metric", "coarse", d, p_coarse, tap, close, normal, loose)
    fine_key = f"{key}x{pitch:g}"
    lookup(METRIC_FINE, fine_key, "metric fine thread")
    return Thread(
        fine_key, "metric", "fine", d, pitch, round(d - pitch, 3), close, normal, loose
    )


def tap_drill(designation: str) -> float:
    """Tap drill diameter (mm): ``tap_drill("M6")`` -> 5.0."""
    return thread(designation).tap_drill


def clearance_diameter(designation: str, fit: str = "normal") -> float:
    """Clearance hole diameter (mm): ``clearance_diameter("M6", "close")`` -> 6.4."""
    return thread(designation).clearance(fit)


@dataclass(frozen=True)
class Counterbore:
    """A counterbore for a cap screw head: ``diameter`` x ``depth`` over a
    ``hole`` clearance diameter (mm)."""

    size: str
    diameter: float
    depth: float
    hole: float


def counterbore(
    size: str, fit: str = "normal", *, flush_allowance: Optional[float] = None
) -> Counterbore:
    """Counterbore for an ISO 4762 / DIN 912 socket head cap screw ``size``.

    ``depth`` = head height + allowance (0.4 mm up to M6, 0.6 mm to M12, 0.8 mm
    above) so the head sits just below the face; ``hole`` = ISO 273 clearance.

    Estimated: the allowance. It reproduces the DIN 974-1 depth t for M3..M12
    (e.g. M6: 6.4, M8: 8.6) but is not read from the DIN 974-1 t column."""
    t = thread(size)
    if t.system != "metric":
        raise StandardsError(
            f"counterbore(): metric ISO 4762 sizes only (got {size!r})"
        )
    d_cb, k = lookup(COUNTERBORE_ISO4762, t.screw_size, "ISO 4762 counterbore size")
    if flush_allowance is None:
        flush_allowance = 0.4 if t.major <= 6 else (0.6 if t.major <= 12 else 0.8)
    return Counterbore(
        t.screw_size, d_cb, round(k + flush_allowance, 3), t.clearance(fit)
    )


@dataclass(frozen=True)
class Countersink:
    """A 90 degree countersink: top ``diameter`` (flush with the face) over a
    ``hole`` clearance diameter (mm)."""

    size: str
    head: str
    diameter: float
    angle: float
    hole: float


def countersink(size: str, head: str = "ISO 10642", fit: str = "normal") -> Countersink:
    """Countersink for a countersunk ``head`` ("ISO 10642" socket, "ISO 7046"
    cross recess) of ``size``: diameter = theoretical max dk, 90 degrees."""
    t = thread(size)
    heads = lookup(COUNTERSINK_HEADS, head, "countersunk head standard")
    dk = lookup(heads, t.screw_size, f"{head} size")
    return Countersink(t.screw_size, head, dk, 90.0, t.clearance(fit))


def screw_length(
    size: str,
    grip: float,
    *,
    engagement: float = 1.5,
    lengths: Tuple[float, ...] = ISO4762_LENGTHS,
) -> float:
    """Shortest standard length that clamps ``grip`` mm and still engages
    ``engagement`` x d of thread (1.0 d steel, 1.5 d cast iron / aluminium,
    2 d soft materials and plastics)."""
    t = thread(size)
    need = float(grip) + engagement * t.major
    for length in lengths:
        if length >= need - 1e-9:
            return length
    raise StandardsError(
        f"{t.screw_size}: grip {grip:g} + {engagement:g}d engagement needs {need:g} mm,"
        f" longer than the series ({lengths[-1]:g} mm)"
    )
