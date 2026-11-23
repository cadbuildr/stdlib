"""Fasteners: screws, bolts, and the connection helpers that drive them.

Deep-module paths stay canonical; these re-exports are the ergonomic
surface agents reach for first.
"""

from cadbuildr.stdlib.fasteners.base import Fastener, ScrewLike, is_fastener
from cadbuildr.stdlib.fasteners.connections import (
    connect_with_bolt_and_nut,
    connect_with_screw,
)
from cadbuildr.stdlib.fasteners.nuts.hex_din934_part import HexNut
from cadbuildr.stdlib.fasteners.screws_and_bolts.hex_bolt_part import HexBolt
from cadbuildr.stdlib.fasteners.washers.din125_part import DIN125Washer
from cadbuildr.stdlib.fasteners.screws_and_bolts.din912_part import DIN912Screw
from cadbuildr.stdlib.fasteners.screws_and_bolts.slotted_screws_part import (
    CheeseHeadSlottedScrew,
    CountersunkSlottedScrew,
)
from cadbuildr.stdlib.fasteners.screws_and_bolts.socket_head_screws_part import (
    ButtonHeadSocketScrew,
    CountersunkSocketScrew,
)
from cadbuildr.stdlib.fasteners.screws_and_bolts.wood_screws_part import WoodScrew

__all__ = [
    "ButtonHeadSocketScrew",
    "CheeseHeadSlottedScrew",
    "CountersunkSlottedScrew",
    "CountersunkSocketScrew",
    "DIN125Washer",
    "DIN912Screw",
    "Fastener",
    "HexBolt",
    "HexNut",
    "ScrewLike",
    "WoodScrew",
    "connect_with_bolt_and_nut",
    "is_fastener",
    "connect_with_screw",
]
