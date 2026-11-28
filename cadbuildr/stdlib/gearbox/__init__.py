"""Spur gear reducer parts: housing plates, spacers and a library gear stage.

    from cadbuildr.stdlib.gearbox import GearStage, single_stage_layout
    stage = GearStage(module=2, z_pinion=11, z_gear=33, bearing="608")

:mod:`.demos` holds the click-only reducer demo (single and two stage) as
connect sequences and builds the same assemblies in code.
"""

from cadbuildr.stdlib.gearbox.geometry import StageGeometry, stage_items, stage_loops
from cadbuildr.stdlib.gearbox.plate_part import GearboxPlate
from cadbuildr.stdlib.gearbox.spacer_part import Spacer
from cadbuildr.stdlib.gearbox.stage import GearStage
from cadbuildr.stdlib.gearbox.demos import (
    build_single_stage,
    build_two_stage,
    ratio_presets,
    single_stage_layout,
    two_stage_layout,
)

__all__ = [
    "GearStage",
    "GearboxPlate",
    "Spacer",
    "StageGeometry",
    "build_single_stage",
    "build_two_stage",
    "ratio_presets",
    "single_stage_layout",
    "stage_items",
    "stage_loops",
    "two_stage_layout",
]
