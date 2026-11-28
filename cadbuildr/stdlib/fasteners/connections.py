"""One-liner fastener connections built on foundation anchors + joints.

Instead of transform math, a screwed connection is a single call::

    connect_with_screw(assembly, DIN912Screw("M4", 16), plate.anchor("mount_1"))

The screw's ``head_seat`` anchor mates onto the hole anchor, and by default a
clearance hole is drilled into the part — positioning and geometry from one
line, via the schema's ``Connection`` + ``PartModifier`` hook.

A through-bolt with a nut (and optional washers) is the same idea::

    connect_with_bolt_and_nut(
        assembly, HexBolt("M8", 40), HexNut("M8"), plate.anchor("hole"),
        grip=12, head_washer=DIN125Washer("M8"), nut_washer=DIN125Washer("M8"),
    )
"""

from __future__ import annotations

from typing import Any, Optional

from cadbuildr.foundation import (
    BoolParameter,
    Circle,
    Connection,
    Extrusion,
    PartModifier,
    RigidJoint,
    Sketch,
    anchor_plane,
)

from cadbuildr.stdlib.fasteners.base import require_fastener


def _clearance_drill(hole_anchor: Any, radius: float, depth: float) -> PartModifier:
    """A cylindrical cut of ``radius`` going ``depth`` into the anchor's part
    (against the anchor's +Z, i.e. into the face)."""
    sketch = Sketch(anchor_plane(hole_anchor))
    bore = Circle(sketch.origin, radius)
    return PartModifier(
        anchor=hole_anchor,
        operations=[Extrusion(bore, 0.0, -depth, cut=True)],
    )


def _mate(assembly: Any, parent_anchor: Any, child_anchor: Any, modifiers=()) -> None:
    """Face-to-face rigid mate (child +Z opposite parent +Z)."""
    assembly.add_connection(
        Connection(
            joint=RigidJoint(parent_anchor=parent_anchor, child_anchor=child_anchor),
            modifiers=list(modifiers),
        )
    )


def connect_with_screw(
    assembly: Any,
    screw: Any,
    hole_anchor: Any,
    clearance: float = 0.2,
    drill: bool = True,
    depth: Optional[float] = None,
    into: Optional[Any] = None,
    into_depth: Optional[float] = None,
) -> Any:
    """Fasten ``screw`` into a part at ``hole_anchor`` (+Z out of the face).

    Places the screw with its ``head_seat`` on the anchor and, when
    ``drill`` is true, cuts the clearance hole into the anchor's part
    (radius = shank + ``clearance``, ``depth`` defaults to the shank length
    plus clearance). ``screw`` must honour the
    :class:`~cadbuildr.stdlib.fasteners.base.Fastener` contract.

    ``into`` is an anchor on the part the screw threads into (its face
    under the clamped part, +Z out of it): a tap-drill hole (0.8 x the
    shank diameter) is cut there, ``into_depth`` deep (required) — e.g. a
    rail screwed down onto a base plate.
    """
    require_fastener(screw)
    modifiers = []
    if drill:
        drill_depth = depth if depth is not None else screw.body_height + clearance
        modifiers.append(
            _clearance_drill(hole_anchor, screw.body_radius + clearance, drill_depth)
        )
    if into is not None:
        if into_depth is None or float(into_depth) <= 0:
            raise ValueError(
                "connect_with_screw: into= needs a positive into_depth= "
                "(how far the shank enters that part)."
            )
        modifiers.append(
            _clearance_drill(into, 0.8 * screw.body_radius, float(into_depth))
        )
    _mate(assembly, hole_anchor, screw.anchor("head_seat"), modifiers)
    return screw


def connect_with_bolt_and_nut(
    assembly: Any,
    bolt: Any,
    nut: Any,
    hole_anchor: Any,
    *,
    grip: Optional[float] = None,
    exit_anchor: Optional[Any] = None,
    head_washer: Optional[Any] = None,
    nut_washer: Optional[Any] = None,
    clearance: float = 0.2,
    drill: bool = True,
) -> Any:
    """Through-bolt a clamped stack: bolt from ``hole_anchor``, nut on the far side.

    ``hole_anchor`` is on the bolt-head face (+Z out of it). The far face is
    either ``exit_anchor`` (+Z out of that face) or derived from ``grip`` —
    the clamped thickness, measured along the hole axis. ``head_washer`` /
    ``nut_washer`` (anything with ``bottom``/``top`` anchors and a
    ``thickness``) are stacked under the head and under the nut. When
    ``drill`` is true the clearance hole is cut through ``grip`` into the
    hole anchor's part.

    Raises ``ValueError`` if the bolt is too short to engage at least half
    the nut. Returns ``bolt``.
    """
    require_fastener(bolt)
    if exit_anchor is None:
        if grip is None:
            raise ValueError("Pass grip= (clamped thickness) or exit_anchor=.")
        exit_anchor = hole_anchor.offset(
            [0.0, 0.0, -float(grip)], name="bolt_exit"
        ).flipped(name="face")
    elif grip is None and drill:
        raise ValueError("drill=True needs grip= to size the through hole.")

    stack = (grip or 0.0) + sum(
        float(w.thickness) for w in (head_washer, nut_washer) if w is not None
    )
    nut_t = float(getattr(nut, "thickness", 0.0))
    if bolt.body_height < stack + nut_t / 2:
        raise ValueError(
            f"Bolt shank {bolt.body_height:g} mm is too short for a {stack:g} mm "
            f"stack plus a {nut_t:g} mm nut — use a longer bolt."
        )

    drill_mods = (
        [_clearance_drill(hole_anchor, bolt.body_radius + clearance, grip + clearance)]
        if drill
        else []
    )

    head_face = hole_anchor
    if head_washer is not None:
        _mate(assembly, hole_anchor, head_washer.anchor("bottom"), drill_mods)
        drill_mods = []
        head_face = head_washer.anchor("top")
    _mate(assembly, head_face, bolt.anchor("head_seat"), drill_mods)

    nut_face = exit_anchor
    if nut_washer is not None:
        _mate(assembly, exit_anchor, nut_washer.anchor("bottom"))
        nut_face = nut_washer.anchor("top")
    _mate(assembly, nut_face, nut.anchor("bottom"))
    return bolt


def connect_heat_set_insert(
    assembly: Any,
    insert: Any,
    face_anchor: Any,
    *,
    pocket: bool = True,
) -> Any:
    """Melt ``insert`` (a :class:`~cadbuildr.stdlib.fasteners.inserts.HeatSetInsert`)
    into the part at ``face_anchor`` (+Z out of the face).

    The insert's ``top`` sits flush with the face (same +Z: it is not a
    face-to-face contact), and with ``pocket`` the pocket
    (``insert.pocket_diameter`` x ``insert.pocket_depth``) is cut into the
    anchor's part. Then fasten into it with ``connect_with_screw(...,
    insert.anchor("top"), drill=False)`` or through a clamped part.
    """
    for attr in ("pocket_diameter", "pocket_depth"):
        if not hasattr(insert, attr):
            raise TypeError(
                f"{type(insert).__name__} is not a threaded insert (missing {attr})."
            )
    modifiers = (
        [
            _clearance_drill(
                face_anchor, insert.pocket_diameter / 2.0, insert.pocket_depth
            )
        ]
        if pocket
        else []
    )
    assembly.add_connection(
        Connection(
            joint=RigidJoint(
                parent_anchor=face_anchor,
                child_anchor=insert.anchor("top"),
                flip=BoolParameter(value=False),
            ),
            modifiers=modifiers,
        )
    )
    return insert
