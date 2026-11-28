"""Lead-screw and pipe threads: metric trapezoidal (Tr), BSP (G / R) and NPT.

::

    trapezoidal("Tr8x2")        # TrapezoidalThread(d=8, P=2, d3=5.5, D1=6, ...)
    trapezoidal("Tr8x8(P2)")    # 4-start 3D-printer lead screw: lead 8, pitch 2
    pipe_thread("G1/4")         # PipeThread(major=13.157 mm, 19 TPI, tap drill 11.8, parallel)
    pipe_thread("1/4 NPT")      # major 13.716 mm, 18 TPI, tap drill 7/16 in, taper 1:16

Sources: ISO 2904 (trapezoidal basic profile: d2 = d - 0.5 P, D1 = d - P,
d3 = d - (P + 2 ac), D4 = d + 2 ac with crest clearance ac 0.15 / 0.25 / 0.5 mm
for P 1.5 / 2-5 / 6-12) and ISO 2901-2903 size series; ISO 228-1 (G, parallel)
and ISO 7-1 (R / Rp / Rc, 1:16 taper) share the BSP diameters and TPI; ASME
B1.20.1 NPT (outside pipe diameter, TPI, 1:16 taper) with the usual tap drills.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from ._common import StandardsError, UnknownSize, lookup

__all__ = [
    "BSP",
    "NPT",
    "PipeThread",
    "TRAPEZOIDAL",
    "TrapezoidalThread",
    "pipe_thread",
    "trapezoidal",
]

INCH = 25.4

# ISO 2904 trapezoidal sizes: designation -> (d, P) for the preferred pitches.
# fmt: off
TRAPEZOIDAL: Dict[str, Tuple[float, float]] = {
    "Tr8x1.5": (8, 1.5), "Tr8x2": (8, 2), "Tr10x2": (10, 2), "Tr10x3": (10, 3),
    "Tr12x3": (12, 3), "Tr14x3": (14, 3), "Tr14x4": (14, 4), "Tr16x4": (16, 4),
    "Tr18x4": (18, 4), "Tr20x4": (20, 4), "Tr22x5": (22, 5), "Tr24x5": (24, 5),
    "Tr26x5": (26, 5), "Tr28x5": (28, 5), "Tr30x6": (30, 6), "Tr32x6": (32, 6),
    "Tr36x6": (36, 6), "Tr40x7": (40, 7),
}

# BSP (ISO 228-1 / ISO 7-1): size -> (major diameter mm, TPI, parallel tap drill mm).
BSP: Dict[str, Tuple[float, int, float]] = {
    "1/16": (7.723, 28, 6.8), "1/8": (9.728, 28, 8.8), "1/4": (13.157, 19, 11.8),
    "3/8": (16.662, 19, 15.25), "1/2": (20.955, 14, 19.0), "3/4": (26.441, 14, 24.5),
    "1": (33.249, 11, 30.5), "1-1/4": (41.910, 11, 39.0), "1-1/2": (47.803, 11, 45.0),
    "2": (59.614, 11, 57.0),
}

# NPT (ASME B1.20.1): size -> (pipe OD in, TPI, tap drill (name, in)).
NPT: Dict[str, Tuple[float, float, Tuple[str, float]]] = {
    "1/16": (0.3125, 27, ("C", 0.2420)), "1/8": (0.405, 27, ("R", 0.3390)),
    "1/4": (0.540, 18, ("7/16", 0.4375)), "3/8": (0.675, 18, ("37/64", 0.5781)),
    "1/2": (0.840, 14, ("23/32", 0.7188)), "3/4": (1.050, 14, ("59/64", 0.9219)),
    "1": (1.315, 11.5, ("1-5/32", 1.1563)), "1-1/4": (1.660, 11.5, ("1-1/2", 1.5000)),
    "1-1/2": (1.900, 11.5, ("1-47/64", 1.7344)), "2": (2.375, 11.5, ("2-7/32", 2.2188)),
}
# fmt: on


def _crest_clearance(pitch: float) -> float:
    if pitch <= 1.5:
        return 0.15
    if pitch <= 5:
        return 0.25
    if pitch <= 12:
        return 0.5
    return 1.0


@dataclass(frozen=True)
class TrapezoidalThread:
    """An ISO 2904 trapezoidal (30 degree) thread; ``lead`` = ``pitch`` x ``starts``."""

    designation: str
    d: float
    pitch: float
    starts: int = 1

    @property
    def lead(self) -> float:
        return self.pitch * self.starts

    @property
    def ac(self) -> float:
        """Crest clearance (mm)."""
        return _crest_clearance(self.pitch)

    @property
    def pitch_diameter(self) -> float:
        """d2 = D2 = d - 0.5 P."""
        return round(self.d - 0.5 * self.pitch, 4)

    @property
    def minor_external(self) -> float:
        """Screw root d3 = d - (P + 2 ac)."""
        return round(self.d - (self.pitch + 2 * self.ac), 4)

    @property
    def minor_internal(self) -> float:
        """Nut minor D1 = d - P (also the nut's core drill)."""
        return round(self.d - self.pitch, 4)

    @property
    def major_internal(self) -> float:
        """Nut major D4 = d + 2 ac."""
        return round(self.d + 2 * self.ac, 4)

    @property
    def tap_drill(self) -> float:
        return self.minor_internal

    @property
    def clearance(self) -> float:
        """Bore that clears the screw (D4 + 0.5 mm) for a pass-through."""
        return round(self.major_internal + 0.5, 3)


_TR = re.compile(
    r"^\s*Tr\s*(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)\s*(?:\(\s*P\s*(\d+(?:\.\d+)?)\s*\))?\s*$"
)


def trapezoidal(designation: str) -> TrapezoidalThread:
    """``"Tr8x2"``, or multi-start ``"Tr8x8(P2)"`` (lead 8, pitch 2 -> 4 starts)."""
    m = _TR.match(str(designation))
    if not m:
        raise UnknownSize(
            f"Not a trapezoidal designation: {designation!r} (expected 'Tr8x2' or 'Tr8x8(P2)')"
        )
    d, first, pitch = float(m.group(1)), float(m.group(2)), m.group(3)
    if pitch is None:
        key = f"Tr{d:g}x{first:g}"
        lookup(TRAPEZOIDAL, key, "trapezoidal size")
        return TrapezoidalThread(key, d, first, 1)
    lead, p = first, float(pitch)
    starts = lead / p
    if abs(starts - round(starts)) > 1e-9 or starts < 1:
        raise StandardsError(
            f"{designation}: lead {lead:g} is not a multiple of pitch {p:g}"
        )
    if not any(abs(dd - d) < 1e-9 for dd, _ in TRAPEZOIDAL.values()):
        raise UnknownSize(f"{designation}: Tr{d:g} is not a tabulated diameter")
    if p not in {pp for _, pp in TRAPEZOIDAL.values()}:
        raise UnknownSize(f"{designation}: pitch {p:g} is not an ISO 2904 pitch")
    return TrapezoidalThread(f"Tr{d:g}x{lead:g}(P{p:g})", d, p, int(round(starts)))


@dataclass(frozen=True)
class PipeThread:
    """A pipe thread (55 degree BSP or 60 degree NPT); lengths in mm.

    BSP ``tap_drill`` is the parallel (G / Rp) drill; a tapered Rc port is
    drilled the same and then taper-reamed. NPT ``tap_drill`` is for tapping
    without reaming."""

    designation: str
    standard: str  # "BSP" | "NPT"
    major: float
    tpi: float
    tap_drill: float
    tapered: bool
    tap_drill_name: Optional[str] = None

    @property
    def pitch(self) -> float:
        return round(INCH / self.tpi, 4)

    @property
    def taper(self) -> Optional[str]:
        """1:16 on diameter for R / Rc / NPT, None for parallel G / Rp."""
        return "1:16" if self.tapered else None


_PIPE = re.compile(
    r"^\s*(G|R|Rp|Rc|BSPP|BSPT)?\s*([\d\-/]+)\s*(NPT|BSPP|BSPT|BSP)?\s*$", re.I
)


def pipe_thread(designation: str) -> PipeThread:
    """``"G1/4"`` (BSP parallel), ``"R1/2"`` / ``"Rc1/2"`` (BSP taper), ``"Rp3/8"``,
    ``"1/4 NPT"``. Sizes are nominal pipe sizes (inch fractions)."""
    m = _PIPE.match(str(designation))
    if not m or not (m.group(1) or m.group(3)):
        raise UnknownSize(
            f"Not a pipe thread designation: {designation!r} (expected 'G1/4', 'R1/2' or '1/4 NPT')"
        )
    prefix = (m.group(1) or "").upper()
    suffix = (m.group(3) or "").upper()
    size = m.group(2)
    if suffix == "NPT":
        od_in, tpi, (name, drill_in) = lookup(NPT, size, "NPT size")
        return PipeThread(
            f"{size} NPT",
            "NPT",
            round(od_in * INCH, 3),
            tpi,
            round(drill_in * INCH, 3),
            True,
            name,
        )
    major, tpi, drill = lookup(BSP, size, "BSP size")
    tapered = prefix in ("R", "RC", "BSPT") or suffix == "BSPT"
    label = {"": "G", "BSPP": "G", "BSPT": "R"}.get(prefix, m.group(1))
    if suffix == "BSPT":
        label = "R"
    return PipeThread(f"{label}{size}", "BSP", major, tpi, drill, tapered)
