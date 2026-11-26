"""T8 lead screw and its brass nut (the Z-axis drive on most printers/CNC)."""

import math
from typing import ClassVar

from cadbuildr.foundation import Part, Sketch, Point, Circle, Extrusion, make_anchor
from cadbuildr.foundation.interfaces import Bore, PlaneFace, ScrewHole
from cadbuildr.foundation.interfaces.features import ShaftFeature
from cadbuildr.foundation.library import Num, part
from cadbuildr.stdlib.common import (
    BRASS,
    STAINLESS,
    add_external_thread,
    add_internal_thread,
    add_axial_anchors,
)

# T8 trapezoidal screw: 8 mm major, 2 mm pitch (modeled as a coarse helical thread).
_T8_MAJOR = 8.0
_T8_PITCH = 2.0


@part(
    category="Linear Motion/Lead Screws",
    name="Lead Screw T8",
    standard="Tr8x8(P2) trapezoidal",
    description="8 mm stainless lead screw with a coarse helical thread — the standard Z-axis drive screw.",
    inputs={"with_thread": {"label": "Modeled thread"}},
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
    ):
        """Args:
        length: nominal length (e.g. the rail length the screw spans).
        with_thread: model the helical thread (slower to render).
        trim: cut this much off ``length`` (the screw is ``length - trim``
            long: the coupling / motor stick-out), so ``length`` can follow
            the same input as the rails.
        """
        length = float(length) - float(trim)
        if length <= 0:
            raise ValueError("trim leaves no screw")
        self.length = length
        radius = _T8_MAJOR / 2
        H = _T8_PITCH * math.sqrt(3) / 2
        core_r = radius - (H / 4 + 0.01 if with_thread else 0.0)
        self.add_operation(
            Extrusion(Circle(Point(Sketch(self.xy()), 0, 0), core_r), length)
        )
        if with_thread:
            add_external_thread(self, radius=radius, length=length, pitch=_T8_PITCH)
        # Anchors: end faces + axis. ``end_a`` mates onto a coupling's
        # ``bore_b_stop``; a LeadScrewNutT8 rides ``axis`` (ScrewJoint, pitch 2).
        self.radius, self.pitch = radius, _T8_PITCH
        add_axial_anchors(self, length, ends=("end_a", "end_b"))
        # Interfaces: Shaft on the axis (bearings, nut), ShaftEnd at both ends.
        ShaftFeature(self, d=_T8_MAJOR, length=length)
        self.paint(STAINLESS)


@part(
    category="Linear Motion/Lead Screws",
    name="Lead Screw Nut T8 (brass)",
    standard="T8 flanged brass nut",
    description="Flanged brass nut for the T8 lead screw, with four M4 flange mounting holes.",
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

    def __init__(self, with_thread: bool = True):
        """Args:
        with_thread: model the internal thread (slower to render).
        """
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
                Circle(Point(Sketch(self.xy()), 0, 0), _T8_MAJOR / 2),
                0,
                total_h,
                cut=True,
            )
        )
        if with_thread:
            add_internal_thread(
                self, nominal_radius=_T8_MAJOR / 2, length=total_h, pitch=_T8_PITCH
            )
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
