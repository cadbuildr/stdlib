"""Cylindrical helical compression spring (DIN 2095 / EN 13906-1), round wire.

Built along +Z from z=0 (bottom seat) to the free length ``L0`` (top seat).
The wire is a real helical solid: a round profile swept along helices — one
dead (closed) coil at each end, the active coils between — and, for
``ends="ground"``, both end faces ground flat (cut at z=0 and z=L0).
"""

from __future__ import annotations

import math
from typing import ClassVar, Literal

from cadbuildr.foundation import Circle, Extrusion, Part, Point, Sketch
from cadbuildr.foundation.checks import issue
from cadbuildr.foundation.interfaces import Bore, PlaneFace
from cadbuildr.foundation.interference import set_part_extents
from cadbuildr.foundation.library import Num, OneOf, part
from cadbuildr.stdlib.common import add_axial_anchors, require_option
from cadbuildr.stdlib.springs._design import (
    SPRING_WIRES,
    SpringError,
    compression_rate,
    helix_wire_length,
    min_sum_of_gaps,
    shear_stress,
    solid_length,
)
from cadbuildr.stdlib.springs._geometry import add_coil
from cadbuildr.stdlib.standards.materials import material

Ends = Literal["ground", "closed"]

#: Pitch of a closed end coil as a multiple of the wire diameter (the wire
#: touches the next coil; 2 % keeps the swept solid from self-touching).
END_PITCH = 1.02
#: Dead (inactive) coils per end of a cold-coiled spring (DIN 2095, EN 13906-1 §9.2).
DEAD_COILS = 1
#: Recommended spring index range w = D / d (EN 13906-1 §8.1).
INDEX_RANGE = (4.0, 20.0)
#: EN 13906-1 Fig. 7, both ends guided on parallel plates (nu = 0.5): above
#: this L0 / D a spring may buckle unless it runs on a rod or in a bore.
BUCKLING_SLENDERNESS = 5.24
#: Working stroke beyond this share of the travel to solid is flagged.
STROKE_LIMIT = 0.8


@part(
    category="Springs/Compression",
    name="Compression Spring",
    standard="DIN 2095 · EN 13906-1 (cold-coiled, round wire)",
    description="Helical compression spring swept from round wire: closed or ground ends, rate, solid length and a stroke check from EN 13906-1.",
    configurations={
        "d1 x D10 x L0 30": dict(wire_diameter=1.0, mean_diameter=10.0, free_length=30.0, active_coils=6, ends="ground"),
        "d1.6 x D12 x L0 40": dict(wire_diameter=1.6, mean_diameter=12.0, free_length=40.0, active_coils=7, ends="ground"),
        "d2 x D16 x L0 50 (closed)": dict(wire_diameter=2.0, mean_diameter=16.0, free_length=50.0, active_coils=8, ends="closed"),
    },
    catalog_id="din2095-compression-spring",
    featured=True,
    example={"wire_diameter": 1.6, "mean_diameter": 12.0, "free_length": 40.0, "active_coils": 7},
)  # fmt: skip
class CompressionSpring(Part):
    """Cylindrical helical compression spring of round wire.

    Dimensions: wire ``d``, mean coil diameter ``D`` (outer ``De = D + d``,
    inner ``Di = D - d``), free length ``L0``, ``n`` active coils and
    ``nt = n + 2`` total coils (one dead coil per end, DIN 2095). Rate
    ``R = G d^4 / (8 D^3 n)`` (EN 13906-1 eq. (11)); solid length
    ``Ls = nt d`` ground / ``(nt + 1.5) d`` closed (EN 13906-1 eq. (24),
    (25)); minimum sum of gaps ``Sa`` (eq. (21)); stress
    ``tau_k = k 8 D F / (pi d^3)`` with the Bergmann ``k`` (eq. (4), (6)).
    Moduli from EN 13906-1 Table 2 (``SPRING_WIRES``).

    Checks (``__checks__``): the working ``stroke`` must stay within 80 % of
    the travel to solid ``L0 - Ls`` (warning) and below it (error); the
    index ``w = D / d`` should lie in 4..20; ``L0 / D > 5.24`` may buckle.

    Estimated: closed end coils are laid at a pitch of 1.02 d (a 2 % gap so
    the swept solid does not self-intersect); the transition between dead
    and active coils is a pitch step at whole turns, not a gradual one.
    """

    WIRES: ClassVar = SPRING_WIRES

    def __init__(
        self,
        wire_diameter: Num(min=0.2, max=10, step=0.05) = 1.6,
        mean_diameter: Num(min=2, max=120, step=0.5) = 12.0,
        free_length: Num(min=4, max=400, step=0.5) = 40.0,
        active_coils: Num(min=2, max=40, step=1, integer=True, unit=None) = 7,
        ends: Ends = "ground",
        wire: OneOf[SPRING_WIRES] = "EN 10270-1",
        stroke: Num(min=0, max=300, step=0.5) = 0.0,
    ):
        """Args:
        wire_diameter: wire diameter d.
        mean_diameter: mean coil diameter D (centre line of the wire).
        free_length: unloaded length L0 between the seats.
        active_coils: number of active (working) coils n (whole turns).
        ends: ``ground`` (closed and ground flat) or ``closed`` (not ground).
        wire: spring wire standard (shear modulus from ``SPRING_WIRES``).
        stroke: working stroke from L0, used by the solid-length check.
        """
        owner = "CompressionSpring"
        w = require_option(SPRING_WIRES, wire, what="wire", owner=owner)
        if ends not in ("ground", "closed"):
            raise SpringError(f"{owner}: unknown ends {ends!r} (choose from ground, closed).")
        d, D, L0 = float(wire_diameter), float(mean_diameter), float(free_length)
        n = int(active_coils)
        if n != active_coils or n < 1:
            raise SpringError(f"{owner}: active_coils must be a whole number >= 1, got {active_coils!r}.")
        if D < 3 * d:
            raise SpringError(f"{owner}: spring index D/d = {D / d:.2f} < 3 cannot be coiled.")
        nt = n + 2 * DEAD_COILS
        pe = END_PITCH * d
        z0 = 0.0 if ends == "ground" else d / 2
        span = (L0 - 2 * z0) - 2 * DEAD_COILS * pe
        pitch = span / n
        if pitch <= END_PITCH * d:
            Lmin = 2 * z0 + 2 * DEAD_COILS * pe + n * END_PITCH * d
            raise SpringError(
                f"{owner}: free length {L0:g} mm too short for {n} active coils of "
                f"d={d:g} (needs > {Lmin:.2f} mm)."
            )
        self.wire_diameter, self.mean_diameter, self.free_length = d, D, L0
        self.outer_diameter, self.inner_diameter = D + d, D - d
        self.active_coils, self.total_coils, self.ends = n, nt, ends
        self.wire, self.G, self.stroke = w, w.G, float(stroke)
        self.pitch, self.end_pitch = pitch, pe
        self.rate = compression_rate(w.G, d, D, n)
        self.solid_length = solid_length(d, nt, ends)
        self.travel_to_solid = L0 - self.solid_length
        self.min_sum_of_gaps = min_sum_of_gaps(d, D, n)

        # Wire: dead coil, active coils, dead coil (whole turns each, so the
        # sections meet at +X).
        z = z0
        add_coil(self, d=d, D=D, pitch=pe, z0=z, turns=DEAD_COILS)
        z += DEAD_COILS * pe
        add_coil(self, d=d, D=D, pitch=pitch, z0=z, turns=n)
        z += n * pitch
        add_coil(self, d=d, D=D, pitch=pe, z0=z, turns=DEAD_COILS)
        self.wire_length = helix_wire_length(D, pe, 2 * DEAD_COILS) + helix_wire_length(D, pitch, n)
        if ends == "ground":
            # Grind both seats flat: remove everything below z=0 / above L0.
            r = D / 2 + d
            for lo, hi in ((-d, 0.0), (L0, L0 + d)):
                disc = Circle(Point(Sketch(self.xy()), 0.0, 0.0), r)
                self.add_operation(Extrusion(disc, start=lo, end=hi, cut=True))

        self.length = L0
        add_axial_anchors(self, L0)
        # Interfaces: the seats bear on flat faces; a guide rod runs in the bore.
        self.add_interface(PlaneFace(name="spring_seat"), "bottom")
        self.add_interface(PlaneFace(name="spring_seat"), "top")
        self.add_interface(Bore(d=self.inner_diameter, fit="clearance"), "axis")
        De = self.outer_diameter
        set_part_extents(self, ((-De / 2, -De / 2, 0.0), (De / 2, De / 2, L0)))
        self.paint(material(w.material).color or "#5f6368")

    # ------------------------------------------------------------------ #
    @property
    def index(self) -> float:
        """Spring index w = D / d."""
        return self.mean_diameter / self.wire_diameter

    def force(self, stroke: float) -> float:
        """Spring force (N) at ``stroke`` mm from the free length."""
        return self.rate * float(stroke)

    def stress(self, stroke: float) -> float:
        """Corrected shear stress tau_k (MPa) at ``stroke``."""
        return shear_stress(self.force(stroke), self.wire_diameter, self.mean_diameter)

    def __checks__(self):
        out = []
        sh, s = self.travel_to_solid, self.stroke
        if s > sh:
            out.append(issue(
                "error", "spring.stroke_beyond_solid",
                f"working stroke {s:g} mm exceeds the travel to solid {sh:.2f} mm "
                f"(L0 {self.free_length:g} - Ls {self.solid_length:.2f}).",
                delta={"stroke": s, "travel_to_solid": sh},
                fix="lengthen the spring or reduce the stroke",
            ))
        elif s > STROKE_LIMIT * sh:
            out.append(issue(
                "warning", "spring.stroke_over_80pct",
                f"working stroke {s:g} mm is {100 * s / sh:.0f} % of the travel to "
                f"solid {sh:.2f} mm (keep it within {100 * STROKE_LIMIT:.0f} %).",
                delta={"stroke": s, "travel_to_solid": sh, "limit": STROKE_LIMIT * sh},
                fix="use more active coils or a longer free length",
            ))
        lo, hi = INDEX_RANGE
        if not lo <= self.index <= hi:
            out.append(issue(
                "warning", "spring.index",
                f"spring index D/d = {self.index:.1f} outside the recommended {lo:g}..{hi:g} (EN 13906-1).",
            ))
        if self.free_length / self.mean_diameter > BUCKLING_SLENDERNESS:
            out.append(issue(
                "warning", "spring.buckling",
                f"L0/D = {self.free_length / self.mean_diameter:.1f} > {BUCKLING_SLENDERNESS}: "
                "the spring may buckle (EN 13906-1 Fig. 7).",
                fix="guide it on a rod or in a bore",
            ))
        return out
