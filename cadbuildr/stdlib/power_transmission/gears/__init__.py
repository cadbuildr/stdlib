"""Spur gears and the joint helper that meshes them."""

from cadbuildr.stdlib.power_transmission.gears.connections import (
    center_distance,
    mesh_gears,
    mesh_phase,
)
from cadbuildr.stdlib.power_transmission.gears.spur_gear_part import SpurGear

__all__ = ["SpurGear", "center_distance", "mesh_gears", "mesh_phase"]
