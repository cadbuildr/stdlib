"""Small anchor-driven assemblies: the reference for placing stdlib parts.

No transform math anywhere — every part is placed by mating named anchors::

    from cadbuildr.foundation import show
    from cadbuildr.stdlib.examples import bolted_plate, motor_leadscrew_stack
    show(bolted_plate())
"""

from __future__ import annotations

from cadbuildr.foundation import (
    Assembly,
    BoolParameter,
    Extrusion,
    Part,
    RigidJoint,
    Sketch,
    make_anchor,
)

from cadbuildr.stdlib.common import rectangle_shape
from cadbuildr.stdlib.fasteners import (
    DIN125Washer,
    HexBolt,
    HexNut,
    connect_with_bolt_and_nut,
)
from cadbuildr.stdlib.actuators.stepper_motors.nema_stepper_part import StepperMotor
from cadbuildr.stdlib.linear_motion.lead_screws.lead_screw_part import (
    LeadScrewNutT8,
    LeadScrewT8,
)
from cadbuildr.stdlib.power_transmission.couplings.clamp_coupling_part import (
    ClampCoupling,
)
from cadbuildr.stdlib.power_transmission.gears import SpurGear, mesh_gears


def _plate(
    width: float, depth: float, thickness: float, color: str = "#4a7fb5"
) -> Part:
    plate = Part()
    plate.add_operation(
        Extrusion(rectangle_shape(Sketch(plate.xy()), width, depth), thickness)
    )
    plate.add_anchor(make_anchor("hole", (0.0, 0.0, thickness)))
    plate.add_anchor(make_anchor("bottom", (0.0, 0.0, 0.0), z_down=True))
    plate.thickness = thickness
    plate.paint(color)
    return plate


def build_bolted_plate(with_thread: bool = True) -> tuple[Assembly, dict[str, Part]]:
    """M8 hex bolt + two DIN 125 washers + hex nut through an 8 mm plate.

    Returns the assembly and its parts by role (joint placement converts the
    components, so keep the part handles to query anchors afterwards).
    """
    parts = {
        "plate": _plate(40.0, 40.0, 8.0),
        "bolt": HexBolt("M8", 30, with_thread=with_thread),
        "nut": HexNut("M8", with_thread=with_thread),
        "head_washer": DIN125Washer("M8"),
        "nut_washer": DIN125Washer("M8"),
    }
    assembly = Assembly()
    assembly.add_component(parts["plate"])
    connect_with_bolt_and_nut(
        assembly,
        parts["bolt"],
        parts["nut"],
        parts["plate"].anchor("hole"),
        grip=parts["plate"].thickness,
        head_washer=parts["head_washer"],
        nut_washer=parts["nut_washer"],
    )
    return assembly, parts


def bolted_plate(with_thread: bool = True) -> Assembly:
    """See :func:`build_bolted_plate`."""
    return build_bolted_plate(with_thread)[0]


def build_motor_leadscrew_stack(
    with_thread: bool = True,
) -> tuple[Assembly, dict[str, Part]]:
    """NEMA17 → clamp coupling (5→8 mm) → T8 lead screw, with its brass nut."""
    motor = StepperMotor("NEMA17", body_length=40, shaft_length=24)
    coupling = ClampCoupling(bore_a=5, bore_b=8, length=25)
    lead = LeadScrewT8(length=200, with_thread=with_thread)
    nut = LeadScrewNutT8(with_thread=with_thread)

    assembly = Assembly()
    assembly.add_component(motor)
    # Motor shaft tip seats against the coupling's bore-A stop...
    assembly.add_joint(
        RigidJoint(
            parent_anchor=motor.anchor("shaft_tip"),
            child_anchor=coupling.anchor("bore_a_stop"),
        )
    )
    # ...and the lead screw end butts the bore-B stop from the other side.
    assembly.add_joint(
        RigidJoint(
            parent_anchor=coupling.anchor("bore_b_stop"),
            child_anchor=lead.anchor("end_a"),
        )
    )
    # Brass nut riding the screw axis 120 mm up, same orientation as the screw.
    assembly.add_joint(
        RigidJoint(
            parent_anchor=lead.anchor("axis").offset([0.0, 0.0, 120.0], name="nut_pos"),
            child_anchor=nut.anchor("axis"),
            flip=BoolParameter(value=False),
        )
    )
    return assembly, {
        "motor": motor,
        "coupling": coupling,
        "lead_screw": lead,
        "nut": nut,
    }


def motor_leadscrew_stack(with_thread: bool = True) -> Assembly:
    """See :func:`build_motor_leadscrew_stack`."""
    return build_motor_leadscrew_stack(with_thread)[0]


def build_gear_pair() -> tuple[Assembly, dict[str, Part]]:
    """A 12-tooth pinion meshing a 30-tooth wheel (module 1)."""
    pinion = SpurGear(module=1, teeth=12, face_width=6, bore=5)
    wheel = SpurGear(module=1, teeth=30, face_width=6, bore=8)
    assembly = Assembly()
    assembly.add_component(pinion)
    mesh_gears(assembly, pinion, wheel)
    return assembly, {"pinion": pinion, "wheel": wheel}


def gear_pair() -> Assembly:
    """See :func:`build_gear_pair`."""
    return build_gear_pair()[0]


if __name__ == "__main__":  # pragma: no cover - manual viewer check
    from cadbuildr.foundation import show

    show(bolted_plate())
