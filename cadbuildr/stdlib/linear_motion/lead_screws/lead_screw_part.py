"""T8 lead screw and its brass nut (the Z-axis drive on most printers/CNC)."""

import math
from typing import ClassVar

from cadbuildr.foundation import Part, Sketch, Point, Circle, Extrusion, make_anchor
from cadbuildr.foundation.interfaces import Bore, PlaneFace, ScrewHole
from cadbuildr.foundation.interfaces.features import ShaftFeature
from cadbuildr.foundation.library import Num, OneOf, part
from cadbuildr.stdlib.common import (
    BRASS,
    STAINLESS,
    add_axial_anchors,
    add_trapezoidal_thread,
    require_option,
    trapezoidal_thread_geometry,
)

# T8: DIN 103 trapezoidal 30°, 8 mm major, 2 mm pitch. The printer "T8" is
# Tr8x8(P2): 4 starts, 8 mm lead; Tr8x2 is the single-start variant.
_T8_MAJOR = 8.0
_T8_PITCH = 2.0
_T8 = trapezoidal_thread_geometry(_T8_MAJOR, _T8_PITCH)
LEADS: dict[str, dict[str, int]] = {"8": {"starts": 4}, "2": {"starts": 1}}


@part(
    category="Linear Motion/Lead Screws",
    name="Lead Screw T8",
    standard="DIN 103 Tr8x8(P2) 4-start / Tr8x2",
    description="8 mm stainless trapezoidal lead screw (30°), 4-start 8 mm lead by default — the standard printer Z-axis drive screw.",
    inputs={"with_thread": {"label": "Modeled thread"}},
    configurations={
        "Tr8x8 x 300 (Prusa-style Z)": dict(length=300, lead="8"),
        "Tr8x8 x 400": dict(length=400, lead="8"),
        "Tr8x2 x 300 (fine, single start)": dict(length=300, lead="2"),
    },
    catalog_id="lead-screw-t8",
    featured=True,
    example={"length": 300},
)
class LeadScrewT8(Part):
    def __init__(
        self,
        length: Num(min=50, max=1000, step=10) = 300,
        with_thread: bool = True,
        trim: Num(min=0, max=200, step=1) = 0,
        lead: OneOf[LEADS] = "8",
    ):
        """Args:
        length: nominal length (e.g. the rail length the screw spans).
        with_thread: model the helical thread (slower to render).
        trim: cut this much off ``length`` (the screw is ``length - trim``
            long: the coupling / motor stick-out), so ``length`` can follow
            the same input as the rails.
        lead: travel per turn — ``8`` (Tr8x8, 4 starts) or ``2`` (Tr8x2, 1 start).
        """
        starts = require_option(LEADS, str(lead), what="lead", owner="LeadScrewT8")[
            "starts"
        ]
        length = float(length) - float(trim)
        if length <= 0:
            raise ValueError("LeadScrewT8: trim leaves no screw")
        self.length = length
        radius = _T8_MAJOR / 2
        # Threaded: core at the minor diameter d3 with the trapezoidal teeth
        # on it; plain: a cylinder at the major diameter.
        core_r = _T8["d3"] / 2 if with_thread else radius
        self.add_operation(
            Extrusion(Circle(Point(Sketch(self.xy()), 0, 0), core_r), length)
        )
        if with_thread:
            add_trapezoidal_thread(
                self, major_d=_T8_MAJOR, pitch=_T8_PITCH, starts=starts, length=length
            )
        # Anchors: end faces + axis. ``end_a`` mates onto a coupling's
        # ``bore_b_stop``; a LeadScrewNutT8 rides ``axis``: use ``lead`` (mm
        # per turn) for a ScrewRelation / ScrewJoint, ``pitch`` is the tooth
        # spacing.
        self.radius, self.pitch = radius, _T8_PITCH
        self.starts, self.lead = starts, _T8_PITCH * starts
        add_axial_anchors(self, length, ends=("end_a", "end_b"))
        # Interfaces: Shaft on the axis (bearings, nut), ShaftEnd at both ends.
        ShaftFeature(self, d=_T8_MAJOR, length=length)
        self.paint(STAINLESS)


@part(
    category="Linear Motion/Lead Screws",
    name="Lead Screw Nut T8 (brass)",
    standard="Tr8x8 / Tr8x2 flanged brass nut",
    description="Flanged brass nut for the T8 lead screw (trapezoidal thread, matching lead), with four flange mounting holes on a 16 mm circle.",
    inputs={"with_thread": {"label": "Modeled thread"}},
    catalog_id="lead-screw-nut-t8",
    featured=False,
    example={},
)
class LeadScrewNutT8(Part):
    FLANGE_D: ClassVar[float] = 22.0
    FLANGE_H: ClassVar[float] = 3.5
    BODY_D: ClassVar[float] = 10.2
    BODY_H: ClassVar[float] = 11.5
    HOLE_PCD: ClassVar[float] = 16.0  # pitch circle of the flange holes
    HOLE_D: ClassVar[float] = 4.2

    def __init__(self, with_thread: bool = True, lead: OneOf[LEADS] = "8"):
        """Args:
        with_thread: model the internal thread (slower to render).
        lead: the screw's lead — ``8`` (4 starts) or ``2`` (1 start).

        Estimated: flange 22 x 3.5, body 10.2 x 11.5 and hole circle 16 from
        common vendor drawings of the T8 brass nut.
        """
        starts = require_option(LEADS, str(lead), what="lead", owner="LeadScrewNutT8")[
            "starts"
        ]
        total_h = self.FLANGE_H + self.BODY_H
        # Flange + body.
        self.add_operation(
            Extrusion(
                Circle(Point(Sketch(self.xy()), 0, 0), self.FLANGE_D / 2),
                0,
                self.FLANGE_H,
            )
        )
        self.add_operation(
            Extrusion(
                Circle(Point(Sketch(self.xy()), 0, 0), self.BODY_D / 2),
                self.FLANGE_H,
                total_h,
            )
        )
        # Central bore + thread.
        self.add_operation(
            Extrusion(
                Circle(
                    Point(Sketch(self.xy()), 0, 0),
                    (_T8["D4"] if with_thread else _T8_MAJOR) / 2,
                ),
                0,
                total_h,
                cut=True,
            )
        )
        if with_thread:
            add_trapezoidal_thread(
                self,
                major_d=_T8_MAJOR,
                pitch=_T8_PITCH,
                starts=starts,
                length=total_h,
                internal=True,
            )
        self.starts, self.lead = starts, _T8_PITCH * starts
        # Four flange mounting holes.
        r = self.HOLE_PCD / 2
        for i in range(4):
            a = math.radians(45 + 90 * i)
            c = Point(Sketch(self.xy()), r * math.cos(a), r * math.sin(a))
            self.add_operation(
                Extrusion(Circle(c, self.HOLE_D / 2), 0, self.FLANGE_H, cut=True)
            )
        # Anchors: flange underside (bottom), body top (top), axis, the
        # flange shoulder the carriage plate sits on (``flange_seat``) and
        # one ``mount_hole_<i>`` per flange hole on that shoulder.
        add_axial_anchors(self, total_h)
        self.add_anchor(make_anchor("flange_seat", (0.0, 0.0, self.FLANGE_H)))
        for i in range(4):
            a = math.radians(45 + 90 * i)
            self.add_anchor(
                make_anchor(
                    f"mount_hole_{i}", (r * math.cos(a), r * math.sin(a), self.FLANGE_H)
                )
            )
        # Interfaces: the flange shoulder on a face (PlaneFace), the bore on
        # the lead screw (Bore), and one ScrewHole per flange hole on the
        # flange underside (screw heads there, group "flange").
        self.add_interface(PlaneFace(), "flange_seat")
        self.add_interface(Bore(d=_T8_MAJOR), "axis")
        for i in range(4):
            a = math.radians(45 + 90 * i)
            hole = make_anchor(
                f"flange_hole_{i}", (r * math.cos(a), r * math.sin(a), 0.0), z_down=True
            )
            self.add_interface(
                ScrewHole(size="M4", depth=self.FLANGE_H), hole, group="flange"
            )
        self.paint(BRASS)
