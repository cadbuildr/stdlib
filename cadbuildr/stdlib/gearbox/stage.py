"""One spur gear reduction stage as a library assembly."""

from __future__ import annotations

from typing import Any, Dict

from cadbuildr.foundation import Assembly, make_anchor
from cadbuildr.foundation.library import Num, OneOf, assembly
from cadbuildr.stdlib.bearings.ball_bearings.deep_groove_part import (
    DeepGrooveBearing,
)
from cadbuildr.stdlib.fasteners.nuts.hex_din934_part import HexNut
from cadbuildr.stdlib.fasteners.screws_and_bolts.din912_part import DIN912Screw
from cadbuildr.stdlib.fasteners.washers.din125_part import DIN125Washer
from cadbuildr.stdlib.gearbox.geometry import StageGeometry, stage_items
from cadbuildr.stdlib.gearbox.plate_part import GearboxPlate
from cadbuildr.stdlib.gearbox.spacer_part import Spacer
from cadbuildr.stdlib.power_transmission.gears.spur_gear_part import SpurGear
from cadbuildr.stdlib.power_transmission.shafts.base_part import Shaft

BEARINGS: dict = DeepGrooveBearing.TABLE


def rot_deg_of(rotate: Any) -> Any:
    """A placement's ``{"axis", "angle"}`` as ``add_component(rot_deg=...)``."""
    if not rotate or not rotate.get("angle"):
        return None
    angle = float(rotate["angle"])
    return {
        "X": (angle, 0.0, 0.0),
        "Y": (0.0, angle, 0.0),
        "Z": (0.0, 0.0, angle),
    }[rotate["axis"]]


@assembly(
    category="Gearbox/Stages",
    name="Spur Gear Stage",
    description="Self-contained spur gear reduction stage: pinion and gear on two shafts in four deep groove bearings, between two plates held by four spacers and DIN 912 through-bolts with washers and nuts (30 parts).",
    example={"module": 2, "z_pinion": 11, "z_gear": 33, "bearing": "608"},
)
class GearStage(Assembly):
    """Spur gear stage (shafts along +Z; input on the origin, output at
    ``x = module * (z_pinion + z_gear) / 2``; plate A outer face on z=0).

    The gear is phased half a tooth for an even ``z_gear`` so the teeth mesh.
    Anchors: ``input`` / ``output`` shaft tips (outward along the shaft),
    ``input_axis`` / ``output_axis`` (+Z along each shaft on plate A's outer
    face), ``face_a`` / ``face_b`` (outer plate faces, outward normals).

    Args:
        module: gear module (drives both gears and the plates' centre distance).
        z_pinion: input pinion tooth count.
        z_gear: output gear tooth count (ratio = z_gear / z_pinion).
        bearing: deep groove bearing of all four shaft supports (plate seats follow; shaft diameter = bearing bore).
    """

    def __init__(
        self,
        module: Num(min=0.5, max=3, step=0.5) = 2,
        z_pinion: Num(min=8, max=60, step=1, integer=True, unit=None) = 11,
        z_gear: Num(min=8, max=120, step=1, integer=True, unit=None) = 33,
        bearing: OneOf[BEARINGS] = "608",
    ):
        g = StageGeometry(
            module=float(module),
            z_pinion=int(z_pinion),
            z_gear=int(z_gear),
            bearing=bearing,
        )
        items = stage_items(g)
        by_role = {it["role"]: it for it in items}
        d, fw = g.shaft_diameter, g.face_width
        parts: Dict[str, Any] = {}
        # Written with the stage's own input names, so every component
        # records its binding to them (library_ref ``bindings``).
        parts["plate_a"] = GearboxPlate(
            module=module, z_pinion=z_pinion, z_gear=z_gear, bearing=bearing
        )
        parts["plate_b"] = GearboxPlate(
            module=module, z_pinion=z_pinion, z_gear=z_gear, bearing=bearing
        )
        parts["shaft_in"] = Shaft(diameter=d, length=g.input_shaft_length)
        parts["shaft_out"] = Shaft(diameter=d, length=g.output_shaft_length)
        parts["pinion"] = SpurGear(module=module, teeth=z_pinion, face_width=fw, bore=d)
        parts["gear"] = SpurGear(module=module, teeth=z_gear, face_width=fw, bore=d)
        for role in ("bearing_in_a", "bearing_in_b", "bearing_out_a", "bearing_out_b"):
            parts[role] = DeepGrooveBearing(model=bearing)
        for i in range(1, 5):
            parts[f"spacer_{i}"] = Spacer(
                screw=g.screw, length=g.bay, outer_diameter=g.spacer_od
            )
            parts[f"screw_{i}"] = DIN912Screw(
                size=g.screw, length=g.screw_length, with_thread=False
            )
            parts[f"washer_head_{i}"] = DIN125Washer(size=g.screw)
            parts[f"washer_nut_{i}"] = DIN125Washer(size=g.screw)
            parts[f"nut_{i}"] = HexNut(size=g.screw, with_thread=False)
        assert set(parts) == set(by_role), set(parts) ^ set(by_role)

        for it in items:
            self.add_component(
                parts[it["role"]], at=it["translate"], rot_deg=rot_deg_of(it["rotate"])
            )

        self.geometry = g
        self.stage_parts = parts
        self.module, self.z_pinion, self.z_gear, self.bearing = (
            g.module,
            g.z_pinion,
            g.z_gear,
            bearing,
        )
        self.center_distance = g.center_distance
        self.ratio = g.ratio
        cd, h, e = g.center_distance, g.height, g.shaft_extension
        self.add_anchor(make_anchor("input", (0.0, 0.0, -e), z_down=True))
        self.add_anchor(make_anchor("output", (cd, 0.0, h + e)))
        self.add_anchor(make_anchor("input_axis", (0.0, 0.0, 0.0)))
        self.add_anchor(make_anchor("output_axis", (cd, 0.0, 0.0)))
        self.add_anchor(make_anchor("face_a", (0.0, 0.0, 0.0), z_down=True))
        self.add_anchor(make_anchor("face_b", (0.0, 0.0, h)))
