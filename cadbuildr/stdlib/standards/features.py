"""Standard-sized holes and bores that ship with their interface.

Each helper cuts the hole into the part that owns ``face`` (an anchor, +Z
out of the face, the hole drilled along -Z) with its size read from the
standards tables, and binds the interface a mate needs, so the hole is
immediately connectable::

    tapped_hole(block.anchor("hole_0"), "M5", depth=10)          # tap drill + ScrewHole(thread)
    clearance_hole(plate.anchor("hole_0"), "M5", depth=6)        # ISO 273 + ScrewHole
    counterbored_hole(plate.anchor("hole_0"), "M5", depth=12)    # DIN 974 + ScrewHole on the floor
    heat_set_insert_hole(case.anchor("boss_0"), "M3")            # insert hole + ScrewHole(thread)
    fitted_bore(housing.anchor("bore"), 22, "H7", depth=7)       # ISO 286 bore + Bore(d, fit)

    asm.connect_all(lambda: DIN912Screw("M5", 16), plate.group("bolts"))

The interface keeps the *nominal* size (``ScrewHole(size="M5")``,
``Bore(d=22, fit="H7")``) so mate rules match by designation; the geometry
uses the toleranced / drilled size. Pass ``group=`` to connect a whole
pattern at once with ``connect_all``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, List, Optional

import math

from cadbuildr.foundation import (
    Axis,
    CounterBoreHole,
    CounterSinkHole,
    Hole,
    Lathe,
    Line,
    Point,
)
from cadbuildr.foundation.interfaces import Bore, ScrewHole

from ._common import StandardsError, metric_diameter
from .fits import tolerance
from .inserts import heat_set_insert, self_tap_hole
from .threads import counterbore, countersink, thread

__all__ = [
    "HoleFeature",
    "clearance_hole",
    "counterbored_hole",
    "countersunk_hole",
    "fitted_bore",
    "heat_set_insert_hole",
    "self_tap_screw_hole",
    "tapped_hole",
    "tapped_holes",
]


@dataclass
class HoleFeature:
    """What a hole helper made: the cut ``operation``, the bound ``interface``
    node (None with ``interface=False``), the anchor the screw seats on and the
    table row used (``spec``)."""

    operation: Any
    interface: Any
    seat: Any
    spec: Any
    diameter: float


def _owner(face: Any) -> Any:
    # Foundation keeps the anchor -> component back-reference private; this is
    # the same lookup foundation's own features (RodHole, BearingPocket) use.
    from cadbuildr.foundation.compute_functions import _anchor_owner

    owner = _anchor_owner(face)
    if owner is None:
        raise StandardsError(
            f"anchor {face.name.value!r} is not registered on a part: add it with"
            " part.add_anchor(make_anchor(...)) before drilling"
        )
    return owner


def _bind(
    owner: Any, spec: Any, anchor: Any, group: Optional[str], interface: bool
) -> Any:
    if not interface:
        return None
    return owner.add_interface(spec, anchor, group=group)


def _check_depth(depth: float, what: str) -> float:
    d = float(depth)
    if d <= 0:
        raise StandardsError(f"{what}: depth must be > 0 mm, got {depth!r}")
    return d


DRILL_POINT_ANGLE = 118.0  # twist-drill point (DIN 1412 form A)


def axial_plane(face: Any, name: str) -> Any:
    """A sketch plane containing ``face``'s +Z axis: sketch u = the anchor's X,
    sketch v = the anchor's Z (out of the face). Revolve profiles drawn on it
    about the v axis to cut holes of any section into the face."""
    from cadbuildr.foundation.gen.models import (
        BoolParameter,
        Frame,
        Plane,
        StringParameter,
    )

    c = math.cos(math.pi / 4.0)
    return Plane(
        frame=Frame(
            top_frame=face.frame,
            name=StringParameter(value=f"{name}_frame"),
            display=BoolParameter(value=False),
            position=[0.0, 0.0, 0.0],
            quaternion=[c, c, 0.0, 0.0],  # +90 deg about X: Y -> Z
        ),
        name=StringParameter(value=name),
        display=BoolParameter(value=False),
    )


def revolve_cut(face: Any, profile: List[tuple], name: str) -> Any:
    """Cut the solid of revolution of ``profile`` ((radius, z) points, z <= 0
    into the material, first and last points on the axis) about ``face``'s +Z."""
    from cadbuildr.foundation import Sketch

    owner = _owner(face)
    sketch = Sketch(axial_plane(face, name))
    sketch.pencil.move_to(*profile[0])
    for pt in profile[1:]:
        sketch.pencil.line_to(*pt)
    shape = sketch.pencil.close()
    op = Lathe(shape, Axis(Line(sketch.origin, Point(sketch, 0.0, 1.0))), cut=True)
    owner.add_operation(op)
    return op


def drill_point_depth(diameter: float, angle: float = DRILL_POINT_ANGLE) -> float:
    """Axial length of a drill point of ``angle`` (included) on ``diameter``."""
    return diameter / 2.0 / math.tan(math.radians(angle / 2.0))


def tapped_hole(
    face: Any,
    size: str = "M5",
    depth: float = 10.0,
    *,
    drill_depth: Optional[float] = None,
    chamfer: bool = True,
    group: Optional[str] = None,
    interface: bool = True,
) -> HoleFeature:
    """A tapped blind hole: ``depth`` of full thread, drilled ``drill_depth``
    (default ``depth`` + 3 P runout) with the tap drill (ISO 2306 / unified
    chart) and a 118 degree drill point, and a 90 degree countersink at the
    mouth to 1.05 x the major diameter (``chamfer=True``).
    ``ScrewHole(size, depth, thread=True)`` on ``face``.

    The helix is not modelled: the bore is the tap-drill (minor) diameter a
    CNC program or slicer needs, as in a CAD "cosmetic" tapped hole.

    Estimated: runout 3 P (between DIN 76-1 normal and short runout for
    bottoming taps); countersink 1.05 d (common drawing practice)."""
    t = thread(size)
    depth = _check_depth(depth, f"tapped_hole({size})")
    drill = depth + 3.0 * t.pitch if drill_depth is None else float(drill_depth)
    if drill < depth:
        raise StandardsError(
            f"tapped_hole({size}): drill_depth {drill:g} is shorter than the thread depth {depth:g}"
        )
    r = t.tap_drill / 2.0
    profile = [(0.0, 0.0)]
    if chamfer:
        rc = 1.05 * t.major / 2.0
        profile += [(rc, 0.0), (r, -(rc - r))]
    else:
        profile += [(r, 0.0)]
    profile += [(r, -drill), (0.0, -drill - drill_point_depth(t.tap_drill))]
    op = revolve_cut(face, profile, f"tap_{face.name.value}")
    owner = _owner(face)
    node = _bind(
        owner,
        ScrewHole(size=t.screw_size, depth=depth, thread=True),
        face,
        group,
        interface,
    )
    return HoleFeature(op, node, face, t, t.tap_drill)


def tapped_holes(
    faces: Iterable[Any],
    size: str = "M5",
    depth: float = 10.0,
    *,
    drill_depth: Optional[float] = None,
    chamfer: bool = True,
    group: Optional[str] = None,
    interface: bool = True,
) -> List[HoleFeature]:
    """:func:`tapped_hole` at every anchor of a pattern (``anchor.linear_pattern(...)``),
    with the same options."""
    return [
        tapped_hole(
            f,
            size,
            depth,
            drill_depth=drill_depth,
            chamfer=chamfer,
            group=group,
            interface=interface,
        )
        for f in faces
    ]


def clearance_hole(
    face: Any,
    size: str = "M5",
    depth: float = 10.0,
    fit: str = "normal",
    *,
    blind: bool = False,
    group: Optional[str] = None,
    interface: bool = True,
) -> HoleFeature:
    """A clearance hole, ISO 273 close / normal / loose, ``depth`` deep, with
    ``ScrewHole(size, depth)`` on ``face`` (a screw head or washer lands on it).
    ``blind=True`` ends it in a 118 degree drill point below ``depth`` (pass
    the material thickness as ``depth`` for a through hole)."""
    t = thread(size)
    depth = _check_depth(depth, f"clearance_hole({size})")
    owner = _owner(face)
    dia = t.clearance(fit)
    if blind:
        r = dia / 2.0
        op = revolve_cut(
            face,
            [(0.0, 0.0), (r, 0.0), (r, -depth), (0.0, -depth - drill_point_depth(dia))],
            f"clear_{face.name.value}",
        )
    else:
        op = Hole(anchor=face, radius=dia / 2.0, depth=depth)
        owner.add_operation(op)
    node = _bind(
        owner,
        ScrewHole(size=t.screw_size, depth=depth, drilled=True),
        face,
        group,
        interface,
    )
    return HoleFeature(op, node, face, t, dia)


def counterbored_hole(
    face: Any,
    size: str = "M5",
    depth: float = 10.0,
    fit: str = "normal",
    *,
    blind: bool = False,
    group: Optional[str] = None,
    interface: bool = True,
) -> HoleFeature:
    """Counterbore for an ISO 4762 cap screw (DIN 974-1 diameter, depth = head
    height + allowance) over an ISO 273 clearance hole ``depth`` deep;
    ``blind=True`` ends the hole in a 118 degree drill point.

    The ``ScrewHole`` sits on the counterbore floor (anchor ``<face>_seat``),
    its ``depth`` the material left under the head, so ``connect`` seats the
    head below the face."""
    cb = counterbore(size, fit)
    depth = _check_depth(depth, f"counterbored_hole({size})")
    if cb.depth >= depth:
        raise StandardsError(
            f"counterbored_hole({size}): the {cb.depth:g} mm counterbore needs more than"
            f" {depth:g} mm of material"
        )
    owner = _owner(face)
    if blind:
        r, rc = cb.hole / 2.0, cb.diameter / 2.0
        op = revolve_cut(
            face,
            [
                (0.0, 0.0),
                (rc, 0.0),
                (rc, -cb.depth),
                (r, -cb.depth),
                (r, -depth),
                (0.0, -depth - drill_point_depth(cb.hole)),
            ],
            f"cbore_{face.name.value}",
        )
    else:
        op = CounterBoreHole(
            anchor=face,
            radius=cb.hole / 2.0,
            depth=depth,
            cbore_radius=cb.diameter / 2.0,
            cbore_depth=cb.depth,
        )
        owner.add_operation(op)
    seat = face.offset([0.0, 0.0, -cb.depth], name="seat")  # -> "<face>_seat"
    grip = round(depth - cb.depth, 4)
    node = _bind(
        owner, ScrewHole(size=cb.size, depth=grip, drilled=True), seat, group, interface
    )
    return HoleFeature(op, node, seat, cb, cb.hole)


def countersunk_hole(
    face: Any,
    size: str = "M5",
    depth: float = 10.0,
    head: str = "ISO 10642",
    fit: str = "normal",
    *,
    group: Optional[str] = None,
    interface: bool = True,
) -> HoleFeature:
    """90 degree countersink (flush with the face for ``head`` = ISO 10642 /
    ISO 7046) over an ISO 273 clearance hole, ``ScrewHole`` on ``face``."""
    cs = countersink(size, head, fit)
    depth = _check_depth(depth, f"countersunk_hole({size})")
    owner = _owner(face)
    op = CounterSinkHole(
        anchor=face,
        radius=cs.hole / 2.0,
        depth=depth,
        csink_radius=cs.diameter / 2.0,
        csink_angle_deg=cs.angle,
    )
    owner.add_operation(op)
    node = _bind(
        owner,
        ScrewHole(size=cs.size, depth=depth, drilled=True),
        face,
        group,
        interface,
    )
    return HoleFeature(op, node, face, cs, cs.hole)


def heat_set_insert_hole(
    face: Any,
    size: str = "M3",
    variant: str = "standard",
    *,
    group: Optional[str] = None,
    interface: bool = True,
) -> HoleFeature:
    """Blind hole for a heat-set insert (depth = insert length + 1 mm for the
    displaced melt) with a 45 degree lead-in chamfer of 0.3 mm that centres
    the insert, and ``ScrewHole(size, depth=insert length, thread=True)``: a
    screw connects to it like to a tapped hole.

    Estimated: the 0.3 mm lead-in (insert makers show a small chamfer, no
    size)."""
    ins = heat_set_insert(size, variant)
    owner = _owner(face)
    r, lead = ins.hole / 2.0, 0.3
    profile = [
        (0.0, 0.0),
        (r + lead, 0.0),
        (r, -lead),
        (r, -ins.depth),
        (0.0, -ins.depth),
    ]
    op = revolve_cut(face, profile, f"insert_{face.name.value}")
    node = _bind(
        owner,
        ScrewHole(size=ins.size, depth=ins.length, thread=True),
        face,
        group,
        interface,
    )
    return HoleFeature(op, node, face, ins, ins.hole)


def self_tap_screw_hole(
    face: Any,
    size: str = "M3",
    depth: Optional[float] = None,
    material: str = "PLA",
    *,
    group: Optional[str] = None,
    interface: bool = True,
) -> HoleFeature:
    """Pilot hole for a thread-forming screw into ``material`` (default depth =
    engagement 2 d + 1 mm), ``ScrewHole(thread=True)`` on ``face``."""
    d, _ = metric_diameter(size)
    spec = self_tap_hole(d, material)
    depth = _check_depth(
        depth if depth is not None else spec.engagement + 1.0, "self_tap_screw_hole"
    )
    owner = _owner(face)
    op = Hole(anchor=face, radius=spec.pilot / 2.0, depth=depth)
    owner.add_operation(op)
    node = _bind(
        owner,
        ScrewHole(size=f"M{d:g}", depth=depth, thread=True),
        face,
        group,
        interface,
    )
    return HoleFeature(op, node, face, spec, spec.pilot)


def fitted_bore(
    face: Any,
    d: float,
    fit: str = "H7",
    depth: float = 10.0,
    *,
    model: str = "mean",
    interface: bool = True,
) -> HoleFeature:
    """A bore of nominal ``d`` toleranced ``fit`` (ISO 286 hole, e.g. "H7"),
    modelled at the zone ``mean`` (or ``"min"`` / ``"max"``), with
    ``Bore(d=d, fit=fit)`` on ``face`` for a ``Shaft`` to connect."""
    tol = tolerance(fit, d)
    if tol.kind != "hole":
        raise StandardsError(
            f"fitted_bore: {fit!r} is a shaft tolerance; use an upper-case hole letter"
        )
    size = {"mean": tol.mean, "min": tol.min, "max": tol.max}.get(model)
    if size is None:
        raise StandardsError(
            f"fitted_bore: model must be mean / min / max, got {model!r}"
        )
    depth = _check_depth(depth, "fitted_bore")
    owner = _owner(face)
    op = Hole(anchor=face, radius=size / 2.0, depth=depth)
    owner.add_operation(op)
    node = _bind(owner, Bore(d=float(d), fit=tol.designation), face, None, interface)
    return HoleFeature(op, node, face, tol, size)
