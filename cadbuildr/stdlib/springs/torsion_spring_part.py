"""Cylindrical helical torsion spring (EN 13906-3), round wire, tangential legs.

Close-wound body along +Z from z=0, wound right-handed from +X; two straight
tangential legs, the first at the start (+X, running along -Y), the second
at the end of the last coil. ``coils`` in quarter turns sets the angle
between the legs (0, 90, 180 or 270 degrees in the free state).
"""

from __future__ import annotations

import math
from typing import ClassVar

from cadbuildr.foundation import Circle, Extrusion, Part, Point, Sketch, make_anchor
from cadbuildr.foundation.checks import issue
from cadbuildr.foundation.interfaces import Bore, PlaneFace
from cadbuildr.foundation.interference import set_part_extents
from cadbuildr.foundation.library import Num, OneOf, part
from cadbuildr.stdlib.common import add_axial_anchors, require_option
from cadbuildr.stdlib.springs._design import (
    SPRING_WIRES,
    SpringError,
    helix_wire_length,
    torsion_rate,
)
from cadbuildr.stdlib.springs._geometry import add_coil
from cadbuildr.stdlib.springs.compression_spring_part import END_PITCH, INDEX_RANGE
from cadbuildr.stdlib.standards.materials import material

#: Permissible static bending stress, share of Rm (EN 13906-3 §7: 0.7 Rm).
STRESS_LIMIT = 0.7


@part(
    category="Springs/Torsion",
    name="Torsion Spring",
    standard="EN 13906-3 (round wire, tangential legs)",
    description="Close-wound helical torsion spring swept from round wire with two straight tangential legs; angular rate and bending stress from EN 13906-3.",
    configurations={
        "d1 x D8, 5.25 coils": dict(wire_diameter=1.0, mean_diameter=8.0, coils=5.25, leg_length=20.0),
        "d1.5 x D12, 6.5 coils": dict(wire_diameter=1.5, mean_diameter=12.0, coils=6.5, leg_length=25.0),
        "d2 x D16, 8 coils": dict(wire_diameter=2.0, mean_diameter=16.0, coils=8.0, leg_length=30.0),
    },
    catalog_id="torsion-spring",
    example={"wire_diameter": 1.5, "mean_diameter": 12.0, "coils": 6.5, "leg_length": 25.0},
)  # fmt: skip
class TorsionSpring(Part):
    """Helical torsion spring, round wire, two tangential legs.

    Angular rate ``R_M = E d^4 / (3667 D n)`` in N·mm/degree with the leg
    allowance ``n = nt + (l1 + l2) / (3 pi D)`` (EN 13906-3 eq. (5), (6));
    bending stress ``sigma_q = q 32 M / (pi d^3)`` with
    ``q = (w + 0.07) / (w - 0.75)`` (EN 13906-3 eq. (8), (9)), checked
    against 0.7 Rm. Body length ``LK = (nt + 1) d`` (eq. (12)). When wound
    up by ``angle`` the inner diameter shrinks to
    ``D nt / (nt + angle / 360) - d`` (eq. (14)): it must clear the arbor.

    Estimated: coil pitch 1.02 d (a small gap so the swept solid does not
    self-touch); legs are straight cylinders (no end bends).
    """

    WIRES: ClassVar = SPRING_WIRES

    def __init__(
        self,
        wire_diameter: Num(min=0.2, max=8, step=0.05) = 1.5,
        mean_diameter: Num(min=2, max=100, step=0.5) = 12.0,
        coils: Num(min=1, max=40, step=0.25) = 6.5,
        leg_length: Num(min=2, max=200, step=0.5) = 25.0,
        wire: OneOf[SPRING_WIRES] = "EN 10270-1",
        angle: Num(min=0, max=360, step=1) = 0.0,
        arbor: Num(min=0, max=100, step=0.1) = 0.0,
    ):
        """Args:
        wire_diameter: wire diameter d.
        mean_diameter: mean coil diameter D.
        coils: body coils nt, in quarter turns (sets the leg angle).
        leg_length: length of each straight leg from the body.
        wire: spring wire standard (moduli from ``SPRING_WIRES``).
        angle: working wind-up angle in degrees (stress / arbor checks).
        arbor: diameter of the arbor the spring winds onto (0: none).
        """
        owner = "TorsionSpring"
        w = require_option(SPRING_WIRES, wire, what="wire", owner=owner)
        d, D, nt, L = float(wire_diameter), float(mean_diameter), float(coils), float(leg_length)
        quarters = nt * 4
        if abs(quarters - round(quarters)) > 1e-9 or nt < 1:
            raise SpringError(f"{owner}: coils must be >= 1 in quarter turns, got {coils!r}.")
        if D < 3 * d:
            raise SpringError(f"{owner}: spring index D/d = {D / d:.2f} < 3 cannot be coiled.")
        R, pe = D / 2, END_PITCH * d
        self.wire_diameter, self.mean_diameter, self.coils = d, D, nt
        self.leg_length, self.wire = L, w
        self.outer_diameter, self.inner_diameter = D + d, D - d
        self.angle, self.arbor = float(angle), float(arbor)
        self.effective_coils = nt + 2 * L / (3 * math.pi * D)
        self.rate = torsion_rate(w.E, d, D, self.effective_coils)  # N·mm / deg
        self.body_length = (nt + 1) * d

        z0 = d / 2
        add_coil(self, d=d, D=D, pitch=pe, z0=z0, turns=nt)
        z1 = z0 + nt * pe
        self.leg_angle = (round(quarters) % 4) * 90.0
        # Leg a: from (R, 0, z0) along -Y (xz sketch normal is -Y).
        self._leg(d, plane="xz", u=R, z=z0, length=L)
        # Leg b: tangent at the end of the last coil.
        phi = math.radians(self.leg_angle)
        q = round(quarters) % 4
        plane, u, sign = {0: ("xz", R, -1), 1: ("yz", R, -1), 2: ("xz", -R, 1), 3: ("yz", -R, 1)}[q]
        self._leg(d, plane=plane, u=u, z=z1, length=sign * L)
        self.wire_length = helix_wire_length(D, pe, nt) + 2 * L

        add_axial_anchors(self, self.body_length)
        tip_b = (R * math.cos(phi) - L * math.sin(phi), R * math.sin(phi) + L * math.cos(phi), z1)
        self.add_anchor(make_anchor("leg_a", (R, -L, z0), z_axis=(0.0, -1.0, 0.0)))
        self.add_anchor(make_anchor("leg_b", tip_b, z_axis=(-math.sin(phi), math.cos(phi), 0.0)))
        # Interfaces: the body winds on an arbor (Bore); legs bear on faces.
        self.add_interface(Bore(d=round(self.inner_diameter, 3), fit="clearance"), "axis")
        self.add_interface(PlaneFace(name="spring_leg"), "leg_a")
        self.add_interface(PlaneFace(name="spring_leg"), "leg_b")
        reach = R + L + d
        set_part_extents(self, ((-reach, -reach, 0.0), (reach, reach, self.body_length)))
        self.paint(material(w.material).color or "#5f6368")

    def _leg(self, d, *, plane, u, z, length):
        sk = Sketch(self.xz() if plane == "xz" else self.yz())
        self.add_operation(Extrusion(Circle(Point(sk, u, z), d / 2), end=length))

    @property
    def index(self) -> float:
        return self.mean_diameter / self.wire_diameter

    def moment(self, angle: float) -> float:
        """Torque (N·mm) at a wind-up of ``angle`` degrees."""
        return self.rate * float(angle)

    def stress(self, angle: float) -> float:
        """Corrected bending stress sigma_q (MPa) at ``angle`` (EN 13906-3 eq. (8))."""
        w = self.index
        q = (w + 0.07) / (w - 0.75)
        return q * 32.0 * self.moment(angle) / (math.pi * self.wire_diameter**3)

    def inner_diameter_at(self, angle: float) -> float:
        """Inner coil diameter wound up by ``angle`` degrees (EN 13906-3 eq. (14))."""
        nt = self.coils
        return self.mean_diameter * nt / (nt + float(angle) / 360.0) - self.wire_diameter

    def __checks__(self):
        out = []
        lo, hi = INDEX_RANGE
        if not lo <= self.index <= hi:
            out.append(issue(
                "warning", "spring.index",
                f"spring index D/d = {self.index:.1f} outside the recommended {lo:g}..{hi:g} (EN 13906-3).",
            ))
        rm = material(self.wire.material).uts_mpa
        sigma = self.stress(self.angle)
        if rm and sigma > STRESS_LIMIT * rm:
            out.append(issue(
                "warning", "spring.overstressed",
                f"bending stress {sigma:.0f} MPa at {self.angle:g}° exceeds "
                f"{STRESS_LIMIT:g} Rm = {STRESS_LIMIT * rm:.0f} MPa (EN 13906-3).",
                fix="reduce the angle or use a thicker wire",
            ))
        if self.arbor and self.inner_diameter_at(self.angle) < self.arbor:
            out.append(issue(
                "error", "spring.arbor_bind",
                f"wound up {self.angle:g}° the inner diameter {self.inner_diameter_at(self.angle):.2f} mm "
                f"closes onto the {self.arbor:g} mm arbor.",
                fix="use a smaller arbor (about 0.9 x the loaded inner diameter)",
            ))
        return out
