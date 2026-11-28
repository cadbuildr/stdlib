"""Shared helpers for standard-library parts.

Small, dependency-free building blocks that keep the individual part files short
and consistent: the ISO coarse-pitch table every metric fastener needs, a hex
prism sketch shared by bolt heads and nuts, and one canonical ISO/UTS thread
profile so threads look identical across screws, nuts and rods.
"""

from __future__ import annotations

import math

from cadbuildr.foundation import (
    Sketch,
    Point,
    Point3D,
    Thread,
    Extrusion,
    Axis,
    Line,
    Lathe,
    make_anchor,
)

# Material colours (hex) for consistent rendering across the catalogue.
STEEL = "#9ea4ab"
STAINLESS = "#b7bcc2"
BLACK_OXIDE = "#2b2d30"
BRASS = "#b5a642"
ALUMINIUM = "#c7ccd1"
NYLON = "#e8e4d8"
COPPER = "#b87333"


# ISO 261 coarse-thread pitch (mm) keyed by metric size designation.
ISO_COARSE_PITCH: dict[str, float] = {
    "M2": 0.4,
    "M2.5": 0.45,
    "M3": 0.5,
    "M4": 0.7,
    "M5": 0.8,
    "M6": 1.0,
    "M8": 1.25,
    "M10": 1.5,
    "M12": 1.75,
    "M14": 2.0,
    "M16": 2.0,
    "M20": 2.5,
    "M24": 3.0,
}


def nominal_diameter(size: str) -> float:
    """'M6' -> 6.0, 'M2.5' -> 2.5."""
    return float(size[1:])


def hexagon_shape(sketch: Sketch, width_across_flats: float):
    """Return a closed regular-hexagon shape centred on the sketch origin.

    ``width_across_flats`` is the wrench size (distance between opposite flats),
    which is how hex bolts and nuts are specified.
    """
    # Distance from centre to a vertex for a hexagon given its across-flats size.
    circumradius = width_across_flats / math.sqrt(3)
    for i in range(6):
        angle = math.radians(60 * i)
        x = circumradius * math.cos(angle)
        y = circumradius * math.sin(angle)
        if i == 0:
            sketch.pencil.move_to(x, y)
        else:
            sketch.pencil.line_to(x, y)
    return sketch.pencil.close()


def rectangle_shape(sketch: Sketch, width: float, length: float):
    """Closed axis-aligned rectangle centred on the sketch origin."""
    w, l = width / 2, length / 2
    sketch.pencil.move_to(-w, -l)
    sketch.pencil.line_to(w, -l)
    sketch.pencil.line_to(w, l)
    sketch.pencil.line_to(-w, l)
    return sketch.pencil.close()


def oriented_rectangle_shape(
    sketch: Sketch, cx: float, cy: float, w: float, l: float, angle: float
):
    """Closed rectangle of size ``w`` × ``l`` centred at (cx, cy) and rotated by ``angle`` rad."""
    ca, sa = math.cos(angle), math.sin(angle)
    corners = [(-w / 2, -l / 2), (w / 2, -l / 2), (w / 2, l / 2), (-w / 2, l / 2)]
    world = [(cx + px * ca - py * sa, cy + px * sa + py * ca) for px, py in corners]
    sketch.pencil.move_to(*world[0])
    for p in world[1:]:
        sketch.pencil.line_to(*p)
    return sketch.pencil.close()


def add_screwdriver_slot(
    part, *, top_z: float, across: float, width: float, depth: float
):
    """Cut a straight screwdriver slot into the top of a head (for slotted screws)."""
    slot = rectangle_shape(Sketch(part.xy()), width, across)
    part.add_operation(Extrusion(slot, top_z - depth, top_z, cut=True))


def add_hex_socket(part, *, top_z: float, width: float, depth: float):
    """Cut a hexagonal (Allen) drive socket into the top of a head."""
    socket = hexagon_shape(Sketch(part.xy()), width)
    part.add_operation(Extrusion(socket, top_z - depth, top_z, cut=True))


def lathe_revolve(part, points):
    """Revolve a 2D profile (list of (r, z) points) around the part's Z axis.

    ``points`` start and end on the axis (r == 0); the profile is closed and
    lathed, the standard way these parts build a body of revolution.
    """
    s = Sketch(part.xz())
    s.pencil.move_to(*points[0])
    for p in points[1:]:
        s.pencil.line_to(*p)
    shape = s.pencil.close()
    top = max(z for _, z in points)
    axis = Axis(Line(s.origin, Point(s, 0, top)))
    part.add_operation(Lathe(shape, axis))


def countersunk_head_profile(core_r, length, d, dk_theo, dk_actual):
    """(r, z) lathe points of a 90° countersunk screw, tip at z=0, flush head
    top at z=``length`` (ISO 10642 / ISO 2009 / ISO 7046 geometry).

    The cone runs at 45° from the shank (nominal ``d``) to the head; it
    would reach the theoretical diameter ``dk_theo`` at the top face (that is
    what the countersink is cut to, so the head sits flush). The real head
    edge is truncated: the cone stops at ``dk_actual`` and a short cylinder
    of that diameter rises to the top. Head height k = (dk_theo - d) / 2.
    """
    k = (dk_theo - d) / 2
    z_cone = length - k
    z_edge = z_cone + (dk_actual - d) / 2
    return [
        (0.0, 0.0),
        (core_r, 0.0),
        (core_r, z_cone),
        (d / 2, z_cone),
        (dk_actual / 2, z_edge),
        (dk_actual / 2, length),
        (0.0, length),
    ]


def iso_thread_profile(sketch: Sketch, pitch: float, *, external: bool = True):
    """ISO/UTS 60° thread profile on ``sketch`` (built on the part's xz plane).

    ``external`` cuts the profile for a screw/rod; the internal variant mirrors it
    for nut bores. Matches the profile the original DIN912/DIN934 parts used.
    """
    H = pitch * math.sqrt(3) / 2
    sign = 1 if external else -1
    sketch.pencil.move_to(0, -pitch / 2 + pitch / 16)
    sketch.pencil.line_to(sign * 5 / 8 * H, -pitch / 8)
    sketch.pencil.line(0, pitch / 4)
    sketch.pencil.line_to(0, pitch / 2 - pitch / 16)
    return sketch.pencil.close()


def add_external_thread(part, *, radius: float, length: float, pitch: float):
    """Add a right-hand external ISO thread of ``length`` to ``part``.

    ``radius`` is the nominal (major) radius; the helix is laid at the pitch line
    so it blends into a cylindrical shank of that radius.
    """
    H = pitch * math.sqrt(3) / 2
    thread_radius = radius - H / 4
    profile = iso_thread_profile(Sketch(part.xz()), pitch, external=True)
    part.add_operation(
        Thread(
            profile=profile,
            pitch=pitch,
            height=length - pitch,
            radius=thread_radius,
            center=Point3D(0, 0, pitch / 2),
            dir=Point3D(0, 0, 1),
        )
    )


def trapezoidal_thread_geometry(major_d: float, pitch: float) -> dict:
    """DIN 103 (ISO 2904) metric trapezoidal 30° thread dimensions.

    Returns ``d3`` (screw minor), ``d2`` (pitch), ``D1`` (nut minor), ``D4``
    (nut major), ``h3`` (screw thread depth), ``H4`` (nut depth), ``ac``
    (crest clearance). Tr8x2: d3 5.5, d2 7.0, D1 6.0, D4 8.5.
    """
    if pitch <= 1.5:
        ac = 0.15
    elif pitch <= 5:
        ac = 0.25
    elif pitch <= 12:
        ac = 0.5
    else:
        ac = 1.0
    h3 = 0.5 * pitch + ac
    return {
        "d3": major_d - 2 * h3,
        "d2": major_d - 0.5 * pitch,
        "D1": major_d - pitch,
        "D4": major_d + 2 * ac,
        "h3": h3,
        "H4": h3,
        "ac": ac,
    }


def add_trapezoidal_thread(
    part,
    *,
    major_d: float,
    pitch: float,
    starts: int,
    length: float,
    internal: bool = False,
):
    """Add a DIN 103 trapezoidal 30° thread of ``starts`` starts (lead =
    ``starts`` x ``pitch``) over ``length`` along +Z from z=0.

    External: teeth stand on the screw core of diameter ``d3`` (the caller
    builds that core). Internal: teeth hang inward from a bore of diameter
    ``D4`` (the caller cuts that bore) and sit half a pitch from the screw's
    teeth, so screw and nut built with the same arguments interleave.
    """
    from cadbuildr.foundation import Point3D, Sketch, Thread

    g = trapezoidal_thread_geometry(major_d, pitch)
    tan15 = math.tan(math.radians(15.0))
    r2 = g["d2"] / 2
    lead = pitch * starts
    if internal:
        r_root, r_crest = g["D4"] / 2, g["D1"] / 2
        z_phase = pitch / 2
    else:
        r_root, r_crest = g["d3"] / 2, major_d / 2
        z_phase = 0.0
    depth = abs(r_root - r_crest)
    # Tooth half-thickness at a radius: P/4 at the pitch line, flanks at 15°.
    sign = 1.0 if internal else -1.0

    def half(r):
        return pitch / 4 + sign * (r - r2) * tan15

    hr, hc = half(r_root), half(r_crest)
    out = -1.0 if internal else 1.0
    sink = 0.05  # overlap into the core / wall so the union is clean
    for k in range(int(starts)):
        s = Sketch(part.xz())
        s.pencil.move_to(-out * sink, -hr)
        s.pencil.line_to(out * depth, -hc)
        s.pencil.line_to(out * depth, hc)
        s.pencil.line_to(-out * sink, hr)
        profile = s.pencil.close()
        z0 = pitch / 2 + z_phase + k * pitch
        height = length - z0 - pitch / 2
        if height <= 0:
            continue
        part.add_operation(
            Thread(
                profile=profile,
                pitch=lead,
                height=height,
                radius=r_root,
                center=Point3D(0, 0, z0),
                dir=Point3D(0, 0, 1),
            )
        )
    return g


def add_internal_thread(part, *, nominal_radius: float, length: float, pitch: float):
    """Add a right-hand internal ISO thread to a bore (for nuts).

    The bore itself must already be cut at ``nominal_radius``; this lays the
    thread crests inward from the wall.
    """
    H = pitch * math.sqrt(3) / 2
    thread_radius = nominal_radius + H / 4
    profile = iso_thread_profile(Sketch(part.xz()), pitch, external=False)
    part.add_operation(
        Thread(
            profile=profile,
            pitch=pitch,
            height=length - pitch,
            radius=thread_radius,
            center=Point3D(0, 0, pitch / 2),
            dir=Point3D(0, 0, 1),
        )
    )


# --------------------------------------------------------------------------- #
# Mate anchors
#
# Convention for every stdlib part: an anchor's +Z is the OUTWARD normal of the
# face it sits on (so the default face-to-face joint, ``flip=True``, brings two
# faces into contact), or the part's own axis direction for ``axis``-style
# anchors. Rotational parts are built along +Z from z=0.
# --------------------------------------------------------------------------- #


def add_axial_anchors(part, length, *, ends=("bottom", "top"), axis="axis"):
    """Standard anchors for a body built along +Z from 0 to ``length``.

    * ``ends[0]`` — the z=0 face, outward normal -Z.
    * ``ends[1]`` — the z=``length`` face, outward normal +Z.
    * ``axis`` — at the origin, +Z along the part axis (for revolute /
      slider / cylindrical joints along the bore or shaft).

    Flat parts (nuts, washers, bearings, gears) use ``bottom``/``top``;
    long parts (rods, shafts, extrusions) use ``end_a``/``end_b`` like
    :class:`~cadbuildr.stdlib.profiles.tubes.round_tube_part.RoundTube`.
    """
    bottom, top = ends
    part.add_anchor(make_anchor(bottom, (0.0, 0.0, 0.0), z_down=True))
    part.add_anchor(make_anchor(top, (0.0, 0.0, float(length))))
    if axis:
        part.add_anchor(make_anchor(axis, (0.0, 0.0, 0.0)))


def require_option(table, value, *, what: str, owner: str):
    """Return ``table[value]`` or raise a ``ValueError`` naming the choices.

    Every catalog part looks its dimensions up in a standard's table; an
    unknown key must fail loudly with the valid options, not a bare KeyError.
    """
    if value not in table:
        choices = ", ".join(str(k) for k in table)
        raise ValueError(f"{owner}: unknown {what} {value!r} (choose from {choices}).")
    return table[value]


def require_range(value, *, lo: float, hi: float, what: str, owner: str) -> float:
    """Return ``float(value)`` or raise a ``ValueError`` when outside [lo, hi]."""
    v = float(value)
    if not lo <= v <= hi:
        raise ValueError(f"{owner}: {what} {v:g} out of range [{lo:g}, {hi:g}].")
    return v
