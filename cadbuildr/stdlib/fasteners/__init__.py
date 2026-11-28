"""Fasteners: screws, bolts, nuts, washers, inserts, pins, rivets, studs,
standoffs, and the connection helpers that drive them.

Deep-module paths stay canonical; these re-exports are the ergonomic
surface agents reach for first.
"""

from cadbuildr.stdlib.fasteners.base import Fastener, ScrewLike, is_fastener
from cadbuildr.stdlib.fasteners.connections import (
    connect_heat_set_insert,
    connect_with_bolt_and_nut,
    connect_with_screw,
)
from cadbuildr.stdlib.fasteners.inserts import (
    HeatSetInsert,
    WireThreadInsert,
    wire_thread_insert_hole,
)
from cadbuildr.stdlib.fasteners.nuts.iso_nuts_part import (
    CapNut,
    FlangeNut,
    ISO4032Nut,
    ISO4035Nut,
    NylonInsertNut,
)
from cadbuildr.stdlib.fasteners.nuts.hex_din934_part import HexNut
from cadbuildr.stdlib.fasteners.nuts.nut_variants_part import (
    NylonLockNut,
    SquareNut,
    ThinNut,
    WingNut,
)
from cadbuildr.stdlib.fasteners.nuts.t_slot_nut_part import TSlotNut
from cadbuildr.stdlib.fasteners.pins import (
    ClevisPin,
    CoiledPin,
    CotterPin,
    DowelPin,
    ParallelPin,
    RClip,
    SpringPin,
    pin_hole,
)
from cadbuildr.stdlib.fasteners.rivets import BlindRivet, SolidRivet, rivet_hole
from cadbuildr.stdlib.fasteners.screws_and_bolts.hex_bolt_part import HexBolt
from cadbuildr.stdlib.fasteners.washers.din125_part import DIN125Washer
from cadbuildr.stdlib.fasteners.washers.iso_washers_part import (
    DIN433Washer,
    ISO7090Washer,
    ToothLockWasher,
)
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
from cadbuildr.stdlib.fasteners.threaded_rods.studs_part import DIN976Rod, StudBolt

__all__ = [
    "BlindRivet",
    "ButtonHeadSocketScrew",
    "CapNut",
    "CheeseHeadSlottedScrew",
    "ClevisPin",
    "CoiledPin",
    "CotterPin",
    "CountersunkSlottedScrew",
    "CountersunkSocketScrew",
    "DIN125Washer",
    "DIN433Washer",
    "DIN912Screw",
    "DIN976Rod",
    "DowelPin",
    "Fastener",
    "FenderWasher",
    "FlangeNut",
    "HeatSetInsert",
    "HexBolt",
    "HexNut",
    "HexStandoff",
    "ISO4032Nut",
    "ISO4035Nut",
    "ISO7090Washer",
    "MetricThreadedRod",
    "NylonInsertNut",
    "NylonLockNut",
    "PanHeadScrew",
    "ParallelPin",
    "RClip",
    "ScrewLike",
    "SetScrew",
    "SolidRivet",
    "SplitLockWasher",
    "SpringPin",
    "SquareNut",
    "StudBolt",
    "TSlotNut",
    "ThinNut",
    "ThreadedRod",
    "ToothLockWasher",
    "WingNut",
    "WireThreadInsert",
    "WoodScrew",
    "connect_heat_set_insert",
    "connect_with_bolt_and_nut",
    "connect_with_screw",
    "is_fastener",
    "pin_hole",
    "rivet_hole",
    "wire_thread_insert_hole",
]
