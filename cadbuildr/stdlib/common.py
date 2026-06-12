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


def oriented_rectangle_shape(sketch: Sketch, cx: float, cy: float, w: float, l: float, angle: float):
    """Closed rectangle of size ``w`` × ``l`` centred at (cx, cy) and rotated by ``angle`` rad."""
    ca, sa = math.cos(angle), math.sin(angle)
    corners = [(-w / 2, -l / 2), (w / 2, -l / 2), (w / 2, l / 2), (-w / 2, l / 2)]
    world = [(cx + px * ca - py * sa, cy + px * sa + py * ca) for px, py in corners]
    sketch.pencil.move_to(*world[0])
    for p in world[1:]:
        sketch.pencil.line_to(*p)
    return sketch.pencil.close()


def add_screwdriver_slot(part, *, top_z: float, across: float, width: float, depth: float):
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
