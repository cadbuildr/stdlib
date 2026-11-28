"""Fasteners: screws, bolts, nuts, washers, inserts, pins, standoffs, and the
connection helpers that drive them.

Deep-module paths stay canonical; these re-exports are the ergonomic
surface agents reach for first.
"""

from cadbuildr.stdlib.fasteners.base import Fastener, ScrewLike, is_fastener
from cadbuildr.stdlib.fasteners.connections import (
    connect_heat_set_insert,
    connect_with_bolt_and_nut,
    connect_with_screw,
)
from cadbuildr.stdlib.fasteners.inserts import HeatSetInsert
from cadbuildr.stdlib.fasteners.nuts.hex_din934_part import HexNut
from cadbuildr.stdlib.fasteners.nuts.nut_variants_part import (
    NylonLockNut,
    SquareNut,
    ThinNut,
    WingNut,
)
from cadbuildr.stdlib.fasteners.nuts.t_slot_nut_part import TSlotNut
from cadbuildr.stdlib.fasteners.pins import DowelPin
from cadbuildr.stdlib.fasteners.screws_and_bolts.hex_bolt_part import HexBolt
from cadbuildr.stdlib.fasteners.washers.din125_part import DIN125Washer
from cadbuildr.stdlib.fasteners.washers.washer_variants_part import (
    FenderWasher,
    SplitLockWasher,
)
from cadbuildr.stdlib.fasteners.screws_and_bolts.din912_part import DIN912Screw
from cadbuildr.stdlib.fasteners.screws_and_bolts.pan_head_screws_part import (
    PanHeadScrew,
)
from cadbuildr.stdlib.fasteners.screws_and_bolts.set_screws_part import SetScrew
from cadbuildr.stdlib.fasteners.screws_and_bolts.slotted_screws_part import (
    CheeseHeadSlottedScrew,
    CountersunkSlottedScrew,
)
from cadbuildr.stdlib.fasteners.screws_and_bolts.socket_head_screws_part import (
    ButtonHeadSocketScrew,
    CountersunkSocketScrew,
)
from cadbuildr.stdlib.fasteners.screws_and_bolts.wood_screws_part import WoodScrew
from cadbuildr.stdlib.fasteners.standoffs import HexStandoff
from cadbuildr.stdlib.fasteners.threaded_rods.base_part import ThreadedRod
from cadbuildr.stdlib.fasteners.threaded_rods.metric_part import MetricThreadedRod

__all__ = [
    "ButtonHeadSocketScrew",
    "CheeseHeadSlottedScrew",
    "CountersunkSlottedScrew",
    "CountersunkSocketScrew",
    "DIN125Washer",
    "DIN912Screw",
    "DowelPin",
    "Fastener",
    "FenderWasher",
    "HeatSetInsert",
    "HexBolt",
    "HexNut",
    "HexStandoff",
    "MetricThreadedRod",
    "NylonLockNut",
    "PanHeadScrew",
    "ScrewLike",
    "SetScrew",
    "SplitLockWasher",
    "SquareNut",
    "TSlotNut",
    "ThinNut",
    "ThreadedRod",
    "WingNut",
    "WoodScrew",
    "connect_heat_set_insert",
    "connect_with_bolt_and_nut",
    "connect_with_screw",
    "is_fastener",
]
