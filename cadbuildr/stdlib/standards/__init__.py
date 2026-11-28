"""Engineering standards data for every CADbuildr manufacturing library.

Typed, cited tables and small functions — the numbers a part needs to be
made, bought and assembled, in one place instead of hard-coded per library::

    from cadbuildr.stdlib.standards import fit, thread, material, tapped_hole

    fit("H7/g6", 10).min_clearance      # 0.005 mm (ISO 286)
    thread("M6").tap_drill              # 5.0 mm (ISO 2306)
    thread("M6").clearance("close")     # 6.4 mm (ISO 273)
    material("6061-T6").mass_kg(1e5)    # 0.27 kg
    tapped_hole(block.anchor("hole_0"), "M5", depth=10)   # hole + ScrewHole

Modules: :mod:`.fits` (ISO 286 limits and fits, bearing seats, printed
clearances), :mod:`.threads` (metric / unified threads, ISO 273 clearance,
counterbores, countersinks, screw lengths), :mod:`.inserts` (heat-set inserts,
self-tapping into plastic), :mod:`.shaft_features` (DIN 6885 keys, DIN 471 /
472 circlips), :mod:`.seals` (AS568 / ISO 3601 O-rings, gland design),
:mod:`.preferred` (Renard / E series, sheet gauges, stock sizes),
:mod:`.materials` (density, E, yield, cost, process flags), :mod:`.surface`
(Ra / N grades, ISO 2768 general tolerances), :mod:`.special_threads`
(Tr lead screws, BSP / NPT pipe threads), :mod:`.wood` (pilot holes),
:mod:`.features` (holes and bores that ship with their interface) and
:mod:`.cuts` (D-flats, keyways, circlip / O-ring grooves, captive-nut pockets). Lengths are mm; every lookup raises a
:class:`StandardsError` naming the table and the known keys.
"""

from ._common import OutOfRange, StandardsError, UnknownSize
from .features import (
    HoleFeature,
    clearance_hole,
    counterbored_hole,
    countersunk_hole,
    fitted_bore,
    heat_set_insert_hole,
    self_tap_screw_hole,
    tapped_hole,
    tapped_holes,
)
from .cuts import (
    NutPocket,
    captive_nut_pocket,
    circlip_groove,
    d_flat,
    d_flat_size,
    hub_keyway,
    oring_groove,
    shaft_keyway,
)
from .fits import (
    BEARING_SEATS,
    PREFERRED_FITS,
    Fit,
    Tolerance,
    bearing_fit,
    fit,
    it_grade,
    printed_clearance,
    tolerance,
)
from .inserts import HeatSetInsert, SelfTapHole, heat_set_insert, self_tap_hole
from .materials import MATERIALS, Material, material, materials_for
from .preferred import preferred, sheet_gauge, stock_size
from .seals import Gland, ORing, gland, oring, piston_groove
from .shaft_features import (
    Key,
    RetainingRing,
    circlip_bore,
    circlip_shaft,
    key_length,
    keyway,
)
from .special_threads import PipeThread, TrapezoidalThread, pipe_thread, trapezoidal
from .surface import (
    flatness_tolerance,
    general_angle_tolerance,
    general_tolerance,
    processes_for_ra,
    ra_grade,
    radius_tolerance,
)
from .wood import WoodPilot, wood_pilot
from .threads import (
    Counterbore,
    Countersink,
    Thread,
    clearance_diameter,
    counterbore,
    countersink,
    metric_sizes,
    screw_length,
    tap_drill,
    thread,
)

__all__ = [
    "NutPocket",
    "captive_nut_pocket",
    "circlip_groove",
    "d_flat",
    "d_flat_size",
    "hub_keyway",
    "oring_groove",
    "shaft_keyway",
    "PipeThread",
    "TrapezoidalThread",
    "pipe_thread",
    "trapezoidal",
    "WoodPilot",
    "wood_pilot",
    "BEARING_SEATS",
    "Counterbore",
    "Countersink",
    "Fit",
    "Gland",
    "HeatSetInsert",
    "HoleFeature",
    "Key",
    "MATERIALS",
    "Material",
    "ORing",
    "OutOfRange",
    "PREFERRED_FITS",
    "RetainingRing",
    "SelfTapHole",
    "StandardsError",
    "Thread",
    "Tolerance",
    "UnknownSize",
    "bearing_fit",
    "circlip_bore",
    "circlip_shaft",
    "clearance_diameter",
    "clearance_hole",
    "counterbore",
    "counterbored_hole",
    "countersink",
    "countersunk_hole",
    "fit",
    "fitted_bore",
    "flatness_tolerance",
    "general_angle_tolerance",
    "general_tolerance",
    "gland",
    "heat_set_insert",
    "heat_set_insert_hole",
    "it_grade",
    "key_length",
    "keyway",
    "material",
    "materials_for",
    "metric_sizes",
    "oring",
    "piston_groove",
    "preferred",
    "printed_clearance",
    "processes_for_ra",
    "ra_grade",
    "radius_tolerance",
    "screw_length",
    "self_tap_hole",
    "self_tap_screw_hole",
    "sheet_gauge",
    "stock_size",
    "tap_drill",
    "tapped_hole",
    "tapped_holes",
    "thread",
    "tolerance",
]
