"""Operating elements and machine feet: DIN 319 ball knobs, DIN 39 fixed
handles and levelling feet.

Built along +Z. Thread sizes, pitches and diameters come from
:mod:`cadbuildr.stdlib.standards`; tapped holes carry ``ScrewHole``, male
studs ``ScrewHead`` / ``ScrewTip`` like the screws, so they connect to the
holes and nuts of the rest of the library.
"""

from __future__ import annotations

import math
from typing import ClassVar, Literal

from cadbuildr.foundation import Circle, Extrusion, Part, Point, Sketch, Sphere, make_anchor
from cadbuildr.foundation.interfaces import PlaneFace, ScrewHead, ScrewHole, ScrewTip
from cadbuildr.foundation.library import Num, OneOf, part
from cadbuildr.stdlib.common import (
    STEEL,
    add_axial_anchors,
    add_internal_thread,
    hexagon_shape,
    lathe_revolve,
    require_option,
    require_range,
)
from cadbuildr.stdlib.fasteners.threaded_rods.studs_part import add_thread_section
from cadbuildr.stdlib.standards import thread

__all__ = ["BallKnob", "FixedHandle", "LevellingFoot"]

_THREAD_LABEL = {"with_thread": {"label": "Modeled thread"}}
PHENOLIC = "#1e1f21"


def _arc(zc: float, R: float, r_from: float, n: int = 10):
    """(r, z) points on the upper sphere of radius R centred (0, zc), from
    radius ``r_from`` (below the equator) over the equator to the apex."""
    start = math.atan2(-math.sqrt(max(R**2 - r_from**2, 0.0)), r_from)
    pts = []
    for i in range(n + 1):
        t = start + (math.pi / 2 - start) * i / n
        pts.append((R * math.cos(t), zc + R * math.sin(t)))
    pts[-1] = (0.0, zc + R)
    return pts


Form = Literal["C", "E"]


@part(
    category="Hardware/Knobs",
    name="Ball Knob",
    standard="DIN 319 (form C tapped / form E threaded bush)",
    description="Plastic ball knob for levers and spindles, with a blind tapped hole (C) or a threaded bush (E).",
    inputs=_THREAD_LABEL,
    configurations={"16 M4": dict(d1="16"), "25 M6": dict(d1="25"), "40 M10": dict(d1="40")},
    catalog_id="din319-ball-knob",
    example={"d1": "25"},
)
class BallKnob(Part):
    """DIN 319 ball knob: ball d1, thread d2, overall height h1 and thread
    depth t (form C tapped, form E bush) from DIN 319:2020 Table 1 as listed
    at https://www.fasteners.eu/standards/DIN/319/ (25: M6, h1 22.5, t 11 /
    9). The ball is cut flat at the base to height h1. ``bottom`` (z=0, -Z)
    carries ``ScrewHole(d2, thread=True)``: a lever's stud connects to it.

    Estimated: that page's column headers are garbled — h1 is read from
    the d6 column and t from the h / t2 columns (consistent with Elesa+Ganter
    thread lengths, e.g. 32-M8-C 14.5); no base boss or shoulder recess."""

    # d1: (thread, h1, t form C, t form E)
    TABLE: ClassVar[dict[str, tuple[str, float, float, float]]] = {
        "16": ("M4", 15.0, 7.0, 6.0), "20": ("M5", 18.0, 9.0, 7.5),
        "25": ("M6", 22.5, 11.0, 9.0), "32": ("M8", 29.0, 14.5, 12.0),
        "40": ("M10", 37.0, 18.0, 15.0), "50": ("M12", 46.0, 21.0, 18.0),
    }  # fmt: skip

    def __init__(self, d1: OneOf[TABLE] = "25", form: Form = "C", with_thread: bool = True):
        """Args:
        d1: ball diameter (``TABLE`` key).
        form: ``C`` tapped hole or ``E`` threaded bush.
        with_thread: model the internal thread (slower to render).
        """
        owner = "BallKnob"
        size, h1, tc, te = require_option(self.TABLE, str(d1), what="d1", owner=owner)
        if form not in ("C", "E"):
            raise ValueError(f"{owner}: unknown form {form!r} (choose from C, E).")
        R = float(d1) / 2
        zc = h1 - R
        self.add_operation(Sphere(Point(Sketch(self.xz()), 0.0, zc), R))
        cut = Circle(Point(Sketch(self.xy()), 0.0, 0.0), R + 1)
        self.add_operation(Extrusion(cut, start=zc - R - 1, end=0.0, cut=True))
        th = thread(size)
        t = tc if form == "C" else te
        self.add_operation(Extrusion(Circle(Point(Sketch(self.xy()), 0, 0), th.major / 2), end=t, cut=True))
        if with_thread:
            add_internal_thread(self, nominal_radius=th.major / 2, length=t, pitch=th.pitch)
        self.diameter, self.height, self.size, self.form = float(d1), h1, size, form
        self.thread_depth = t
        self.base_diameter = 2 * math.sqrt(R**2 - zc**2)
        add_axial_anchors(self, h1)
        self.add_interface(ScrewHole(size=size, depth=t, thread=True), "bottom")
        self.paint(PHENOLIC)


@part(
    category="Hardware/Handles",
    name="Fixed Handle",
    standard="DIN 39 form E (threaded pin)",
    description="Turned steel fixed handle (ball grip) with a collar and a threaded pin, screwed into a lever or hand wheel.",
    inputs=_THREAD_LABEL,
    configurations={"16 M6": dict(d1="16"), "25 M10": dict(d1="25"), "32 M12": dict(d1="32")},
    catalog_id="din39-fixed-handle",
    example={"d1": "20"},
)
class FixedHandle(Part):
    """DIN 39 fixed handle, form E: grip ball d1, threaded pin d3 of length
    l2, collar d4 (h13) of length l3 and overall length l1 above the collar
    face from DIN 39 as tabulated by Elesa+Ganter
    (https://www.elesa.com/siteassets/PDF/PDF_US/DIN%2039.pdf; 16: M6, d4 10,
    l1 50, l2 11, l3 7; 45 g). ``head_seat`` (z=0, -Z) is the collar face
    with ``ScrewHead(d3, l2)``; the pin runs down to ``tip``.

    Estimated: the grip is a cone from the collar to 0.8 d1 on the ball (the
    standard's curved flank is straightened; the catalogue mass is matched
    within ~10 %); l3 is read as the collar length."""

    # d1: (thread, d4, l1, l2, l3, mass g)
    TABLE: ClassVar[dict[str, tuple[str, float, float, float, float, float]]] = {
        "16": ("M6", 10.0, 50.0, 11.0, 7.0, 45.0), "20": ("M8", 13.0, 64.0, 13.0, 8.0, 91.0),
        "25": ("M10", 16.0, 80.0, 14.0, 10.0, 177.0), "32": ("M12", 20.0, 100.0, 21.0, 13.0, 360.0),
        "36": ("M16", 22.0, 112.0, 26.0, 14.0, 526.0),
    }  # fmt: skip
    NECK: ClassVar[float] = 0.4  # neck radius at the ball, x d1

    def __init__(self, d1: OneOf[TABLE] = "20", with_thread: bool = True):
        """Args:
        d1: grip ball diameter (``TABLE`` key).
        with_thread: model the pin thread (slower to render).
        """
        size, d4, l1, l2, l3, mass = require_option(self.TABLE, str(d1), what="d1", owner="FixedHandle")
        R = float(d1) / 2
        zc = l1 - R
        rn = self.NECK * float(d1)
        profile = [(0.0, 0.0), (d4 / 2, 0.0), (d4 / 2, l3)] + _arc(zc, R, rn)
        lathe_revolve(self, profile)
        th = thread(size)
        pin = [(0.0, -l2), (th.major / 2 - 0.5 * th.pitch, -l2), (th.major / 2, -l2 + 0.5 * th.pitch),
               (th.major / 2, 0.0), (0.0, 0.0)]  # fmt: skip
        lathe_revolve(self, pin)
        if with_thread:
            add_thread_section(self, d=th.major, pitch=th.pitch, z0=-l2, z1=0.0)
        self.diameter, self.size, self.length = float(d1), size, l1
        self.pin_length, self.collar_diameter, self.catalogue_mass_g = l2, d4, mass
        self.body_height = 0.0
        self.add_anchor(make_anchor("head_seat", (0.0, 0.0, 0.0), z_down=True))
        self.add_anchor(make_anchor("tip", (0.0, 0.0, -l2), z_down=True))
        self.add_anchor(make_anchor("top", (0.0, 0.0, l1)))
        self.add_anchor(make_anchor("axis", (0.0, 0.0, 0.0)))
        self.add_interface(ScrewHead(size=size, length=l2), "head_seat")
        self.add_interface(ScrewTip(size=size), "tip")
        self.paint(STEEL)


@part(
    category="Hardware/Feet",
    name="Levelling Foot",
    standard="Ganter GN 343.1 base (steel) + threaded spindle",
    description="Levelling foot: a steel base with a hex for the spanner and a threaded spindle that screws into the machine frame.",
    inputs=_THREAD_LABEL,
    configurations={
        "32 M10 x 50": dict(base="32-M10", stud_length=50),
        "50 M12 x 80": dict(base="50-M12", stud_length=80),
        "60 M16 x 100": dict(base="60-M16", stud_length=100),
    },
    catalog_id="levelling-foot",
    example={"base": "40-M12", "stud_length": 60},
)
class LevellingFoot(Part):
    """Levelling foot: base d1 with pad thickness l4, overall base height
    l2, hex A/F and female thread depth t from the Ganter GN 343.1 datasheet
    (7/2018; 32-M10: l2 23, l4 5, A/F 15, t 10.5; 60-M16: l2 36, l4 8.5,
    A/F 24, t 16 — https://www.ganternorm.com, GN 343.1), with a threaded
    spindle screwed t deep into it and ``stud_length`` above the base.
    ``bottom`` (z=0) stands on the floor (``PlaneFace``); ``stud_tip``
    carries ``ScrewTip`` for the frame's tapped hole or a nut.

    Estimated: l4 for the 40 / 50 bases (not in the excerpt); the hex
    occupies the top 40 % of l2 above a conical neck; the base is rigid
    (the GN 343.1 ball joint and swivel are not modeled)."""

    # key: (d1, thread, l2, l4, A/F, t)
    TABLE: ClassVar[dict[str, tuple[float, str, float, float, float, float]]] = {
        "32-M10": (32.0, "M10", 23.0, 5.0, 15.0, 10.5),
        "40-M12": (40.0, "M12", 26.0, 6.0, 17.0, 11.5),
        "50-M12": (50.0, "M12", 28.0, 6.5, 17.0, 11.5),
        "60-M16": (60.0, "M16", 36.0, 8.5, 24.0, 16.0),
    }

    def __init__(
        self,
        base: OneOf[TABLE] = "40-M12",
        stud_length: Num(min=20, max=200, step=5) = 60,
        with_thread: bool = True,
    ):
        """Args:
        base: base size ``<d1>-<thread>`` (``TABLE`` key).
        stud_length: spindle length above the base.
        with_thread: model the spindle thread (slower to render).
        """
        owner = "LevellingFoot"
        d1, size, l2, l4, af, t = require_option(self.TABLE, base, what="base", owner=owner)
        Ls = require_range(stud_length, lo=20, hi=200, what="stud_length", owner=owner)
        th = thread(size)
        hex_h = 0.4 * l2
        z_hex = l2 - hex_h
        rn = af / 2 * 0.95
        c = 0.15 * l4
        lathe_revolve(
            self,
            [(0.0, 0.0), (d1 / 2, 0.0), (d1 / 2, l4 - c), (d1 / 2 - c, l4), (rn, z_hex), (0.0, z_hex)],
        )
        self.add_operation(Extrusion(hexagon_shape(Sketch(self.xy()), af), start=z_hex, end=l2))
        top = l2 + Ls
        r = th.major / 2
        lathe_revolve(
            self,
            [(0.0, l2 - t), (r, l2 - t), (r, top - 0.6 * th.pitch), (r - 0.6 * th.pitch, top), (0.0, top)],
        )
        if with_thread:
            add_thread_section(self, d=th.major, pitch=th.pitch, z0=l2, z1=top)
        self.base, self.size, self.base_diameter, self.base_height = base, size, d1, l2
        self.stud_length, self.width_across_flats = Ls, af
        self.add_anchor(make_anchor("bottom", (0.0, 0.0, 0.0), z_down=True))
        self.add_anchor(make_anchor("stud_tip", (0.0, 0.0, top)))
        self.add_anchor(make_anchor("axis", (0.0, 0.0, 0.0)))
        self.add_interface(PlaneFace(name="floor"), "bottom")
        self.add_interface(ScrewTip(size=size), "stud_tip")
        self.paint(STEEL)
