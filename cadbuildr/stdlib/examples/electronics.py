"""Worked example: a PCB on standoffs over a 3D-printed base.

The everyday electronics-enclosure stack, all placed by anchors::

    base (printed) <- 4 x HeatSetInsert M3   (connect_heat_set_insert cuts the pockets)
         insert top <- HexStandoff M3 x 10 male-female, stud down into the insert
     standoff (up)  <- PCB 70 x 50 x 1.6, one corner on each standoff
          PCB top   <- 4 x PanHeadScrew M3 x 6 (connect_with_screw drills the PCB)

Change ``standoff_length`` and the PCB and screws follow.
"""

from __future__ import annotations

from cadbuildr.foundation import (
    Assembly,
    Extrusion,
    Part,
    RigidJoint,
    Sketch,
    make_anchor,
)

from cadbuildr.stdlib.common import rectangle_shape
from cadbuildr.stdlib.fasteners import (
    HeatSetInsert,
    HexStandoff,
    PanHeadScrew,
    connect_heat_set_insert,
    connect_with_screw,
)

PCB_GREEN = "#1f6f43"
PRINT_GREY = "#d4d0c8"


def _board(width, depth, thickness, inset, color) -> Part:
    """A plate with ``corner_<i>_top`` / ``corner_<i>_bottom`` anchors at the
    four hole positions ``inset`` from the edges."""
    board = Part()
    board.add_operation(
        Extrusion(rectangle_shape(Sketch(board.xy()), width, depth), thickness)
    )
    i = 0
    for sx in (-1, 1):
        for sy in (-1, 1):
            xy = (sx * (width / 2 - inset), sy * (depth / 2 - inset))
            board.add_anchor(make_anchor(f"corner_{i}_top", (*xy, thickness)))
            board.add_anchor(make_anchor(f"corner_{i}_bottom", (*xy, 0.0), z_down=True))
            i += 1
    board.thickness = thickness
    board.paint(color)
    return board


def build_pcb_on_standoffs(standoff_length: float = 10.0, size: str = "M3"):
    """Returns ``(assembly, parts)``; ``parts`` has ``base``, ``pcb`` and the
    lists ``inserts``, ``standoffs``, ``screws``."""
    base = _board(90.0, 70.0, 8.0, inset=10.0, color=PRINT_GREY)
    pcb = _board(80.0, 60.0, 1.6, inset=5.0, color=PCB_GREEN)
    # Corners of the PCB sit over the base corners: same hole pattern.
    pcb_holes = (80.0 / 2 - 5.0, 60.0 / 2 - 5.0)
    base_holes = (90.0 / 2 - 10.0, 70.0 / 2 - 10.0)
    if pcb_holes != base_holes:
        raise ValueError("pcb and base hole patterns must match")

    assembly = Assembly()
    assembly.add_component(base)
    inserts, standoffs, screws = [], [], []
    for i in range(4):
        insert = HeatSetInsert(size)
        connect_heat_set_insert(assembly, insert, base.anchor(f"corner_{i}_top"))
        standoff = HexStandoff(size, standoff_length, "male-female")
        # Shoulder face (``top``, around the stud) on the insert, stud down.
        assembly.add_joint(
            RigidJoint(
                parent_anchor=insert.anchor("top"),
                child_anchor=standoff.anchor("top"),
            )
        )
        inserts.append(insert)
        standoffs.append(standoff)
    # The PCB is placed once, by its first corner on the first standoff's
    # free (female) end; the other three corners land on the others.
    assembly.add_joint(
        RigidJoint(
            parent_anchor=standoffs[0].anchor("bottom"),
            child_anchor=pcb.anchor("corner_0_bottom"),
        )
    )
    for i in range(4):
        screw = PanHeadScrew(size, 6, with_thread=False)
        connect_with_screw(
            assembly, screw, pcb.anchor(f"corner_{i}_top"), depth=pcb.thickness + 0.2
        )
        screws.append(screw)
    return assembly, {
        "base": base,
        "pcb": pcb,
        "inserts": inserts,
        "standoffs": standoffs,
        "screws": screws,
    }


def pcb_on_standoffs(standoff_length: float = 10.0) -> Assembly:
    """See :func:`build_pcb_on_standoffs`."""
    return build_pcb_on_standoffs(standoff_length)[0]
