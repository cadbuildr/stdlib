"""Parts and a demo built from the shaft / seal / nut cuts (:mod:`.cuts`).

* :class:`ParallelKey` — DIN 6885-1 form A key for a shaft diameter.
* :class:`ORingSeal` — an AS568 O-ring (torus).
* :class:`KeyedShaft` — a stepped-free plain shaft with a DIN 6885 keyway,
  two DIN 471 circlip grooves and an optional D-flat end.
* :class:`CaptiveNutBlock` / :class:`CaptiveNutDemo` — a printed block with
  hex nut pockets underneath and clearance holes on top; stdlib ``HexNut`` s
  connect into the pockets and ``DIN912Screw`` s into the holes.

Declared as library items only by :func:`.demos.register` (like the other
Standards demo items).
"""

from __future__ import annotations

from cadbuildr.foundation import (
    Assembly,
    Axis,
    Circle,
    Extrusion,
    Lathe,
    Line,
    Part,
    Point,
    Rectangle,
    Sketch,
    make_anchor,
)
from cadbuildr.foundation.interfaces.features import ShaftFeature
from cadbuildr.foundation.library import Num, OneOf

from cadbuildr.stdlib.fasteners.nuts.hex_din934_part import HexNut
from cadbuildr.stdlib.fasteners.screws_and_bolts.din912_part import DIN912Screw

from ._common import StandardsError
from .cuts import (
    captive_nut_pocket,
    circlip_groove,
    d_flat,
    shaft_end_chamfer,
    shaft_keyway,
)
from .demos import _declare
from .features import clearance_hole
from .seals import AS568, oring
from .shaft_features import key_length as din_key_length
from .shaft_features import keyway
from .threads import screw_length

__all__ = [
    "CaptiveNutBlock",
    "CaptiveNutDemo",
    "KeyedShaft",
    "ORingSeal",
    "ParallelKey",
]

KEY_SHAFTS = [8.0, 10.0, 12.0, 16.0, 20.0, 25.0, 30.0, 40.0, 50.0]
STEEL = "#9ea4ab"
NUT_SIZES = ["M3", "M4", "M5", "M6"]


@_declare(
    "part",
    category="Standards/Shafts",
    name="Parallel key",
    standard="DIN 6885-1 form A",
    description="Square-ended parallel key sized for a shaft diameter (b x h), length from the DIN 6885 series.",
    configurations={
        "20 mm shaft, 28 long": dict(shaft_d=20.0, length=28),
        "8 mm shaft, 12 long": dict(shaft_d=8.0, length=12),
    },
)
class ParallelKey(Part):
    """A DIN 6885-1 form A (round-ended) parallel key along +Z: bottom face
    (the one in the shaft keyway) at x = 0, height h along +X, width b along
    Y, ends rounded with radius b / 2.

    Estimated: none; the edge chamfers s (0.16..0.8 mm) are not modelled.

    Args:
        shaft_d: shaft diameter the key is for (b x h from DIN 6885-1).
        length: wanted length, rounded up to the DIN 6885 series.
    """

    def __init__(
        self,
        shaft_d: OneOf[KEY_SHAFTS] = 20.0,
        length: Num(min=6, max=200, step=1) = 28,
    ):
        k = keyway(float(shaft_d))
        L = din_key_length(float(shaft_d), float(length))
        half = k.b / 2.0
        sketch = Sketch(self.yz())  # u = Y, v = Z, extruded along +X (height)
        body = Rectangle.from_center_and_sides(
            Point(sketch, 0.0, L / 2.0), k.b, L - k.b
        )
        self.add_operation(Extrusion(body, start=0.0, end=k.h))
        for zc in (half, L - half):
            ends = Sketch(self.yz())
            self.add_operation(
                Extrusion(Circle(Point(ends, 0.0, zc), half), start=0.0, end=k.h)
            )
        self.add_anchor(make_anchor("bottom", (0.0, 0.0, 0.0), z_axis=(-1, 0, 0)))
        self.add_anchor(make_anchor("end_a", (k.h / 2.0, 0.0, 0.0), z_down=True))
        self.add_anchor(make_anchor("end_b", (k.h / 2.0, 0.0, L)))
        self.key, self.length = k, L
        self.paint(STEEL)


@_declare(
    "part",
    category="Standards/Seals",
    name="O-ring (AS568)",
    standard="AS568",
    description="An AS568 O-ring modelled as a torus (inside diameter x cross-section).",
    configurations={
        "AS568-010": dict(size="AS568-010"),
        "AS568-214": dict(size="AS568-214"),
    },
)
class ORingSeal(Part):
    """An O-ring in the XY plane, centred on the origin (``axis`` anchor).

    Args:
        size: AS568 dash number.
    """

    def __init__(self, size: OneOf[list(AS568)] = "AS568-017"):
        ring = oring(size)
        s = Sketch(self.xz())
        rc = ring.id / 2.0 + ring.cs / 2.0
        shape = Circle(Point(s, rc, 0.0), ring.cs / 2.0)
        self.add_operation(Lathe(shape, Axis(Line(s.origin, Point(s, 0.0, 1.0)))))
        self.add_anchor(make_anchor("axis", (0.0, 0.0, 0.0)))
        self.ring = ring
        self.paint("#202124")


@_declare(
    "part",
    category="Standards/Shafts",
    name="Keyed shaft",
    standard="DIN 6885-1 / DIN 471",
    description="Plain shaft with a DIN 6885 keyway, two DIN 471 circlip grooves and an optional D-flat end.",
    configurations={
        "20 mm, keyed": dict(d=20.0, length=120, key_length=28, d_flat_end=False),
        "8 mm, D-flat end": dict(d=8.0, length=60, key_length=12, d_flat_end=True),
    },
)
class KeyedShaft(Part):
    """A shaft along +Z (``axis``, ``end_a``, ``end_b``): DIN 6885 form A
    keyway centred, DIN 471 circlip grooves 5 mm in from each end, D-flat
    over the last 15 mm, 45 degree end chamfers.

    Estimated: the groove positions (5 mm from the ends) and the chamfer
    sizes (0.5 mm up to d = 10, 1 mm above) are layout choices, not standard.

    Args:
        d: shaft diameter.
        length: shaft length.
        key_length: keyway length (rounded up to the DIN 6885 series).
        d_flat_end: cut a D-flat on the end_b side (motor / pulley shafts).
    """

    def __init__(
        self,
        d: OneOf[[8.0, 10.0, 12.0, 16.0, 20.0, 25.0]] = 20.0,
        length: Num(min=30, max=400, step=1) = 120,
        key_length: Num(min=6, max=100, step=1) = 28,
        d_flat_end: bool = False,
    ):
        d, length = float(d), float(length)
        sketch = Sketch(self.xy())
        self.add_operation(Extrusion(Circle(Point(sketch, 0.0, 0.0), d / 2.0), length))
        kl = din_key_length(d, float(key_length))
        if kl > length - 20.0:
            raise StandardsError(
                f"KeyedShaft: a {kl:g} mm keyway does not fit a {length:g} mm shaft with its grooves"
            )
        self.key = shaft_keyway(self, d, (length - kl) / 2.0, kl)
        self.rings = [circlip_groove(self, d, z) for z in (5.0, length - 5.0 - 1.5)]
        self.flat = d_flat(self, d, length - 15.0, 15.0) if d_flat_end else None
        # Estimated: 45 deg end chamfers 0.5 mm up to 10 mm, 1 mm above.
        self.chamfer = 0.5 if d <= 10 else 1.0
        shaft_end_chamfer(self, d, length, self.chamfer, "top")
        shaft_end_chamfer(self, d, 0.0, self.chamfer, "bottom")
        ShaftFeature(self, d=d, length=length)
        self.d, self.length, self.key_length = d, length, kl
        self.paint(STEEL)


@_declare(
    "part",
    category="Standards/Threads",
    name="Captive nut block",
    standard="ISO 4032 / ISO 273",
    description="Printed block with hex nut pockets underneath and clearance holes on top (ScrewHole groups).",
    configurations={
        "2 x M3": dict(size="M3", n=2, height=12),
        "3 x M5": dict(size="M5", n=3, height=16),
    },
)
class CaptiveNutBlock(Part):
    """A block with ``n`` holes along X: ISO 273 clearance from the top face
    (group ``bolts``) down to an ISO 4032 nut pocket in the bottom face
    (group ``nuts``, ScrewHole on the pocket floor).

    Args:
        size: screw / nut size.
        n: number of holes.
        height: block height.
    """

    def __init__(
        self,
        size: OneOf[NUT_SIZES] = "M3",
        n: Num(min=1, max=6, step=1, integer=True, unit=None) = 2,
        height: Num(min=6, max=40, step=0.5) = 12,
    ):
        d = float(size[1:])
        n, height = int(n), float(height)
        pitch = 4 * d + 8.0
        length, width = pitch * n, 4 * d + 10.0
        sketch = Sketch(self.xy())
        self.add_operation(
            Extrusion(
                Rectangle.from_center_and_sides(sketch.origin, length, width), height
            )
        )
        top = self.add_anchor(make_anchor("top", (0.0, 0.0, height)))
        bottom = self.add_anchor(make_anchor("bottom", (0.0, 0.0, 0.0), z_down=True))
        x0 = -(n - 1) * pitch / 2.0
        self.pockets = []
        for i, a in enumerate(
            top.offset([x0, 0.0, 0.0], name="hole").linear_pattern(
                n, pitch, direction=(1, 0, 0)
            )
        ):
            self.add_anchor(a)
            clearance_hole(a, size, height, group="bolts")
        # Bottom anchor: +Z points down, so its X runs along -X of the part.
        for a in bottom.offset([-x0, 0.0, 0.0], name="pocket").linear_pattern(
            n, pitch, direction=(-1, 0, 0)
        ):
            self.add_anchor(a)
            self.pockets.append(
                captive_nut_pocket(a, size, group="nuts", interface=True)
            )
        if self.pockets[0].depth >= height - 2.0:
            raise StandardsError(
                f"CaptiveNutBlock: {height:g} mm is too low for {size} nut pockets"
            )
        self.size, self.height = size, height
        self.paint("#e0e0e0")


@_declare(
    "assembly",
    category="Standards/Threads",
    name="Captive nut demo",
    standard="ISO 4032 / ISO 4762",
    description="Hex nuts connected into a printed block's pockets, DIN 912 screws through its clearance holes.",
    configurations={
        "2 x M3": dict(size="M3", n=2, height=12),
        "3 x M5": dict(size="M5", n=3, height=16),
    },
)
class CaptiveNutDemo(Assembly):
    """:class:`CaptiveNutBlock` + one ``HexNut`` per pocket + one ``DIN912Screw``
    per hole, the screw length from :func:`screw_length` so it passes the nut.

    Args:
        size: screw / nut size.
        n: number of screws.
        height: block height.
    """

    def __init__(
        self,
        size: OneOf[NUT_SIZES] = "M3",
        n: Num(min=1, max=6, step=1, integer=True, unit=None) = 2,
        height: Num(min=6, max=40, step=0.5) = 12,
    ):
        block = CaptiveNutBlock(size=size, n=n, height=height)
        self.ground(block)
        self.nuts = self.connect_all(
            lambda: HexNut(size=size, with_thread=False), block.group("nuts")
        )
        grip = float(height) - block.pockets[0].depth
        length = screw_length(
            size,
            grip,
            engagement=HexNut.dimension_table[size]["thickness"] / float(size[1:]),
        )
        self.screws = self.connect_all(
            lambda: DIN912Screw(size=size, length=length, with_thread=False),
            block.group("bolts"),
        )
        self.add_anchor(make_anchor("origin", (0.0, 0.0, 0.0)))
        self.block, self.screw_length = block, length
