"""Cylindrical helical extension spring (DIN 2097 / EN 13906-2), round wire.

Close-wound body along +Z with a loop at each end. The origin is the centre
of the bottom loop (where a pin passes through it, along Y); the top loop's
centre is ``pin_distance`` above it. The body is a swept helix and each loop
is a bent wire (a riser plus a revolved ring) standing in the XZ plane.
"""

from __future__ import annotations

from typing import ClassVar, Literal

from cadbuildr.foundation import (
    Axis,
    Circle,
    Extrusion,
    Lathe,
    Line,
    Part,
    Point,
    Sketch,
    make_anchor,
)
from cadbuildr.foundation.checks import issue
from cadbuildr.foundation.interfaces import Bore, PivotHole
from cadbuildr.foundation.interference import set_part_extents
from cadbuildr.foundation.library import Num, OneOf, part
from cadbuildr.stdlib.common import require_option
from cadbuildr.stdlib.springs._design import (
    SPRING_WIRES,
    SpringError,
    extension_rate,
    helix_wire_length,
    shear_stress,
)
from cadbuildr.stdlib.springs._geometry import add_coil
from cadbuildr.stdlib.springs.compression_spring_part import END_PITCH, INDEX_RANGE
from cadbuildr.stdlib.standards.materials import material

Hook = Literal["german", "hook"]

#: Loop sweep per hook type (DIN 2097 Bild 1: "ganze deutsche Öse" is a full
#: loop over the centre; the hook ("Hakenöse") is the same loop left open).
HOOK_SWEEP = {"german": 360.0, "hook": 270.0}
#: Permissible static shear stress of an extension spring, as a share of the
#: wire tensile strength (EN 13906-2 §6.2: 0.45 Rm).
STRESS_LIMIT = 0.45


@part(
    category="Springs/Extension",
    name="Extension Spring",
    standard="DIN 2097 · EN 13906-2 (close-wound, German loops)",
    description="Close-wound helical extension spring swept from round wire, with full German loops or open hooks at both ends; rate and stress from EN 13906-2.",
    configurations={
        "d1 x D8, 20 coils": dict(wire_diameter=1.0, mean_diameter=8.0, body_coils=20, hook="german"),
        "d1.5 x D12, 16 coils": dict(wire_diameter=1.5, mean_diameter=12.0, body_coils=16, hook="german"),
        "d2 x D16, 12 coils, hooks": dict(wire_diameter=2.0, mean_diameter=16.0, body_coils=12, hook="hook"),
    },
    catalog_id="din2097-extension-spring",
    example={"wire_diameter": 1.5, "mean_diameter": 12.0, "body_coils": 16},
)  # fmt: skip
class ExtensionSpring(Part):
    """Helical extension spring of round wire with end loops.

    Body: ``nt`` close-wound coils (``n = nt`` active), body length
    ``LK = (nt + 1) d`` (EN 13906-2 eq. (15)). Loops: German loop of the
    coil diameter standing in the axial plane, inner loop height
    ``LH = Di = D - d`` (DIN 2097: 0.8..1.1 Di). Free length inside the
    loops ``L0 = LK + 2 LH``. Rate ``R = G d^4 / (8 D^3 n)`` (EN 13906-2 eq.
    (9)); force ``F = F0 + R s``; stress ``tau_k`` with the Bergmann factor
    checked against 0.45 Rm (EN 13906-2 §6.2). Moduli: EN 13906-1 Table 2.

    Estimated: coil pitch 1.02 d (the wound-in initial tension is a number,
    ``initial_tension``, not geometry); the loop is joined to the body by a
    straight riser of length R at the body's end point, not a bent
    transition; wire tensile strength from ``standards.materials``.
    """

    WIRES: ClassVar = SPRING_WIRES

    def __init__(
        self,
        wire_diameter: Num(min=0.2, max=8, step=0.05) = 1.5,
        mean_diameter: Num(min=2, max=100, step=0.5) = 12.0,
        body_coils: Num(min=2, max=80, step=1, integer=True, unit=None) = 16,
        hook: Hook = "german",
        wire: OneOf[SPRING_WIRES] = "EN 10270-1",
        initial_tension: Num(min=0, max=2000, step=0.5) = 0.0,
        extension: Num(min=0, max=500, step=0.5) = 0.0,
    ):
        """Args:
        wire_diameter: wire diameter d.
        mean_diameter: mean coil diameter D.
        body_coils: number of body coils nt (whole turns; all active).
        hook: end loop type, ``german`` (full loop) or ``hook`` (open loop).
        wire: spring wire standard (moduli from ``SPRING_WIRES``).
        initial_tension: wound-in initial tension F0 (N).
        extension: working extension s from the free length (stress check).
        """
        owner = "ExtensionSpring"
        w = require_option(SPRING_WIRES, wire, what="wire", owner=owner)
        sweep = require_option(HOOK_SWEEP, hook, what="hook", owner=owner)
        d, D, nt = float(wire_diameter), float(mean_diameter), int(body_coils)
        if nt != body_coils or nt < 1:
            raise SpringError(f"{owner}: body_coils must be a whole number >= 1.")
        if D < 3 * d:
            raise SpringError(f"{owner}: spring index D/d = {D / d:.2f} < 3 cannot be coiled.")
        R = D / 2
        pe = END_PITCH * d
        self.wire_diameter, self.mean_diameter, self.body_coils = d, D, nt
        self.active_coils, self.hook, self.wire = nt, hook, w
        self.outer_diameter, self.inner_diameter = D + d, D - d
        self.initial_tension, self.extension = float(initial_tension), float(extension)
        self.rate = extension_rate(w.G, d, D, nt)
        self.body_length = (nt + 1) * d  # EN 13906-2 eq. (15)
        self.loop_height = D - d  # LH, inside of the loop from the body end

        z_start = R  # helix start (wire centre); bottom loop centre at z=0
        add_coil(self, d=d, D=D, pitch=pe, z0=z_start, turns=nt)
        z_end = z_start + nt * pe
        self.pin_distance = z_end + R
        self.free_length = self.pin_distance + 2 * R - d  # inside the loops
        self._loop(d, R, z_from=z_start, centre=0.0, up=False, sweep=sweep)
        self._loop(d, R, z_from=z_end, centre=self.pin_distance, up=True, sweep=sweep)
        self.wire_length = (
            helix_wire_length(D, pe, nt) + 2 * R + 2 * R * 3.141592653589793 * sweep / 360.0
        )

        # Anchors: loop centres (+Z along the pin, i.e. part Y), spring axis.
        self.add_anchor(make_anchor("hook_a", (0.0, 0.0, 0.0), z_axis=(0.0, 1.0, 0.0)))
        self.add_anchor(make_anchor("hook_b", (0.0, 0.0, self.pin_distance), z_axis=(0.0, 1.0, 0.0)))
        self.add_anchor(make_anchor("axis", (0.0, 0.0, 0.0)))
        # Interfaces: a pin through each loop (revolute), guide rod in the bore.
        hole = round(self.inner_diameter, 3)
        self.add_interface(PivotHole(d=hole), "hook_a")
        self.add_interface(PivotHole(d=hole), "hook_b")
        self.add_interface(Bore(d=hole, fit="clearance"), "axis")
        De = self.outer_diameter
        set_part_extents(
            self, ((-De / 2, -d / 2 - R, -R - d / 2), (De / 2, d / 2 + R, self.pin_distance + R + d / 2))
        )
        self.paint(material(w.material).color or "#5f6368")

    def _loop(self, d, R, *, z_from, centre, up, sweep):
        """Riser from the body end (+X) to the loop centre height, then the
        loop: a ring of wire-centre radius R about the pin axis (part Y)."""
        lo, hi = sorted((z_from, centre))
        riser = Circle(Point(Sketch(self.xy()), R, 0.0), d / 2)
        self.add_operation(Extrusion(riser, start=lo, end=hi))
        s = Sketch(self.xy().get_parallel_plane(centre))
        profile = Circle(Point(s, R, 0.0), d / 2)
        # Revolve about -Y (top: +X turns to +Z, away from the body) or +Y
        # (bottom loop: +X turns to -Z).
        axis = Axis(Line(s.origin, Point(s, 0.0, -1.0 if up else 1.0)))
        if sweep >= 360.0:
            self.add_operation(Lathe(profile, axis))
        else:
            self.add_operation(Lathe(profile, axis, angle=sweep))

    @property
    def index(self) -> float:
        return self.mean_diameter / self.wire_diameter

    def force(self, extension: float) -> float:
        """Force (N) at ``extension`` mm beyond the free length, ``F0 + R s``."""
        return self.initial_tension + self.rate * float(extension)

    def stress(self, extension: float) -> float:
        """Corrected shear stress tau_k (MPa) at ``extension``."""
        return shear_stress(self.force(extension), self.wire_diameter, self.mean_diameter)

    def __checks__(self):
        out = []
        lo, hi = INDEX_RANGE
        if not lo <= self.index <= hi:
            out.append(issue(
                "warning", "spring.index",
                f"spring index D/d = {self.index:.1f} outside the recommended {lo:g}..{hi:g} (EN 13906-2).",
            ))
        rm = material(self.wire.material).uts_mpa
        tau = self.stress(self.extension)
        if rm and tau > STRESS_LIMIT * rm:
            out.append(issue(
                "warning", "spring.overstressed",
                f"shear stress {tau:.0f} MPa at {self.extension:g} mm extension exceeds "
                f"{STRESS_LIMIT:g} Rm = {STRESS_LIMIT * rm:.0f} MPa (EN 13906-2).",
                fix="reduce the extension or use a thicker wire",
            ))
        return out
