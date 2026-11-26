"""Placement tables for a click-only spur gear reducer demo (single and two stage).

Each layout is what the viewer's Library panel needs to build the reducer one
insert at a time: per item, the library ``item`` id, its ``inputs``, a
``translate`` [x, y, z] (mm) and at most ONE ``rotate`` about X, Y or Z
(``{"axis", "angle"}`` in degrees, about the part's own origin, applied
before the translation; ``None`` for none) -- the panel's position and
rotation fields. :func:`build_single_stage` / :func:`build_two_stage` build
the very same table in code (``add_component(at=translate, rot_deg=...)``).

Orientation: ``horizontal=True`` (default) lays the shafts along +Y with the
line of centres along +X (the stage frame of
:mod:`~cadbuildr.stdlib.gearbox.geometry` turned -90° about X: stage (x, y, z)
-> world (x, z, -y)); ``horizontal=False`` keeps the stage frame (shafts
along +Z).

Bindings: ``layout["bindings"]`` maps each promoted top-level input to the
``[item index, component input]`` pairs it drives, and each item carries its
own ``bindings`` ({component input: top-level input}) in the form of the
viewer's ``library`` edit command. ``layout["notes"]`` says which inputs keep
every placement valid: ``bearing`` always does (seats open on the outer
faces, holes do not depend on it, 608 <-> 688 keeps the 8 mm shafts exact);
``z_pinion`` / ``z_gear`` do when their sum is kept (same centre distance,
see :func:`ratio_presets`); ``module`` moves the output shaft, so change it
on a :class:`~cadbuildr.stdlib.gearbox.stage.GearStage` (one assembly) rather
than on a click-built stage.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

from cadbuildr.stdlib.gearbox.geometry import (
    StageGeometry,
    gear_mesh_phase_deg,
    stage_items,
)

__all__ = [
    "build_layout",
    "build_single_stage",
    "build_two_stage",
    "ratio_presets",
    "single_stage_layout",
    "two_stage_layout",
]

PROMOTED = ("module", "z_pinion", "z_gear", "bearing")
COUPLING_LENGTH = 25.0

# --------------------------------------------------------------------------- #
# Rotations (quaternions [w, x, y, z]) restricted to one principal axis
# --------------------------------------------------------------------------- #

_AXES = {"X": (1.0, 0.0, 0.0), "Y": (0.0, 1.0, 0.0), "Z": (0.0, 0.0, 1.0)}


def _quat(rotate: Optional[Dict[str, Any]]) -> List[float]:
    if not rotate or not rotate.get("angle"):
        return [1.0, 0.0, 0.0, 0.0]
    a = math.radians(float(rotate["angle"])) / 2.0
    ax = _AXES[rotate["axis"]]
    return [math.cos(a)] + [math.sin(a) * c for c in ax]


def _qmul(a: List[float], b: List[float]) -> List[float]:
    w1, x1, y1, z1 = a
    w2, x2, y2, z2 = b
    return [
        w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
        w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
        w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
        w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
    ]


def _single_axis(q: List[float]) -> Optional[Dict[str, Any]]:
    """``q`` as one rotation about X, Y or Z (None for identity); raises otherwise."""
    w, v = q[0], q[1:]
    big = [i for i, c in enumerate(v) if abs(c) > 1e-9]
    if not big:
        return None
    if len(big) > 1:
        raise ValueError(f"rotation {q} is not about a single principal axis")
    i = big[0]
    angle = math.degrees(2.0 * math.atan2(v[i], w))
    angle = (angle + 180.0) % 360.0 - 180.0
    if abs(angle + 180.0) < 1e-9:
        angle = 180.0
    angle = round(angle, 9)
    if angle == 0:
        return None
    return {"axis": "XYZ"[i], "angle": angle}


def _rotate_vec(q: List[float], p: List[float]) -> List[float]:
    w, x, y, z = q
    vx, vy, vz = p
    # v' = v + 2w (u x v) + 2 u x (u x v)
    cx, cy, cz = y * vz - z * vy, z * vx - x * vz, x * vy - y * vx
    ccx, ccy, ccz = y * cz - z * cy, z * cx - x * cz, x * cy - y * cx
    return [vx + 2 * (w * cx + ccx), vy + 2 * (w * cy + ccy), vz + 2 * (w * cz + ccz)]


def _orientation(horizontal: bool) -> Optional[Dict[str, Any]]:
    return {"axis": "X", "angle": -90.0} if horizontal else None


def _clean(v: float) -> float:
    r = round(float(v), 6)
    return 0.0 if r == 0 else r


def _place(
    entry: Dict[str, Any],
    world: Optional[Dict[str, Any]],
    offset: List[float],
    prefix: str,
) -> Dict[str, Any]:
    """Stage-frame entry -> world item (offset in the stage frame, then ``world``)."""
    qw = _quat(world)
    p = [a + b for a, b in zip(entry["translate"], offset)]
    rotate = _single_axis(_qmul(qw, _quat(entry["rotate"])))
    return {
        "name": f"{prefix}{entry['role']}",
        "item": entry["item"],
        "inputs": dict(entry["inputs"]),
        "translate": [_clean(c) for c in _rotate_vec(qw, p)],
        "rotate": rotate,
        "bindings": dict(entry.get("bind") or {}),
    }


# --------------------------------------------------------------------------- #
# Layouts
# --------------------------------------------------------------------------- #


def _geometry(module, z_pinion, z_gear, bearing) -> StageGeometry:
    return StageGeometry(
        module=float(module),
        z_pinion=int(z_pinion),
        z_gear=int(z_gear),
        bearing=bearing,
    )


def _stage(
    g: StageGeometry,
    horizontal: bool,
    offset: List[float],
    prefix: str,
    threads: bool,
    warnings: List[str],
) -> List[Dict[str, Any]]:
    world = _orientation(horizontal)
    out = []
    for entry in stage_items(g, threads=threads):
        try:
            out.append(_place(entry, world, offset, prefix))
        except ValueError:
            # The gear's mesh phase (about its own axis) cannot be combined
            # with the horizontal turn in one rotation: place it unphased.
            unphased = dict(entry, rotate=None)
            out.append(_place(unphased, world, offset, prefix))
            warnings.append(
                f"{prefix}{entry['role']}: z_gear={g.z_gear} is even, the gear needs a "
                f"{gear_mesh_phase_deg(g.z_gear):.3g} deg phase that one rotation cannot "
                "add in the horizontal layout; teeth overlap (use an odd z_gear or horizontal=False)"
            )
    return out


def _finish(
    items: List[Dict[str, Any]],
    inputs: Dict[str, Any],
    warnings: List[str],
    **extra: Any,
) -> Dict[str, Any]:
    from cadbuildr.foundation.library import item_for
    from cadbuildr.stdlib.gearbox.stage import GearStage

    bindings: Dict[str, List[List[Any]]] = {name: [] for name in inputs}
    for index, it in enumerate(items):
        for comp_input, top in it["bindings"].items():
            bindings[top].append([index, comp_input])
    stage_item = item_for(GearStage)
    widgets = {
        name: dict(stage_item.input(name)["widget"], default=value)
        for name, value in inputs.items()
    }
    part_count = sum(30 if it["item"] == "stdlib:GearStage" else 1 for it in items)
    return {
        "items": items,
        "inputs": dict(inputs),
        "widgets": widgets,
        "bindings": bindings,
        "part_count": part_count,
        "notes": {
            "placement_safe": ["bearing"],
            "placement_safe_at_constant_sum": ["z_pinion", "z_gear"],
            "moves_parts": ["module"],
        },
        "warnings": warnings,
        **extra,
    }


def single_stage_layout(
    module: float = 2,
    z_pinion: int = 11,
    z_gear: int = 33,
    bearing: str = "608",
    horizontal: bool = True,
    threads: bool = False,
) -> Dict[str, Any]:
    """One stage (30 parts): 2 plates, 4 spacers, 2 shafts, pinion + gear,
    4 bearings, 4 DIN 912 through-bolts, 8 DIN 125 washers, 4 hex nuts.

    Returns ``{"items": [...], "inputs", "widgets", "bindings", "part_count",
    "notes", "warnings", "center_distance", "ratio"}`` (see the module doc).
    """
    g = _geometry(module, z_pinion, z_gear, bearing)
    warnings: List[str] = []
    items = _stage(g, horizontal, [0.0, 0.0, 0.0], "", threads, warnings)
    inputs = dict(
        module=g.module, z_pinion=g.z_pinion, z_gear=g.z_gear, bearing=bearing
    )
    return _finish(
        items,
        inputs,
        warnings,
        center_distance=g.center_distance,
        ratio=g.ratio,
        horizontal=horizontal,
    )


def two_stage_layout(
    module: float = 2,
    z_pinion: int = 11,
    z_gear: int = 33,
    bearing: str = "608",
    horizontal: bool = True,
    threads: bool = False,
    stage2_as_assembly: bool = False,
) -> Dict[str, Any]:
    """Two identical stages in series (61 parts, ratio (z_gear / z_pinion)²).

    Stage 2 sits behind stage 1 with its input coaxial with stage 1's output;
    a clamp coupling joins the two shaft tips in the 2 x shaft-extension gap.
    ``stage2_as_assembly=True`` gives stage 2 as ONE ``stdlib:GearStage``
    item (same placement, 30 parts inside) -- the live library insert.
    """
    g = _geometry(module, z_pinion, z_gear, bearing)
    warnings: List[str] = []
    world = _orientation(horizontal)
    items = _stage(g, horizontal, [0.0, 0.0, 0.0], "s1.", threads, warnings)
    cd, h, e = g.center_distance, g.height, g.shaft_extension
    tip = h + e  # stage 1 output shaft tip (stage frame z)
    coupling = {
        "role": "coupling",
        "item": "stdlib:ClampCoupling",
        "inputs": dict(
            bore_a=g.shaft_diameter, bore_b=g.shaft_diameter, length=COUPLING_LENGTH
        ),
        "translate": [cd, 0.0, tip - COUPLING_LENGTH / 2.0],
        "rotate": None,
    }
    items.append(_place(coupling, world, [0.0, 0.0, 0.0], ""))
    offset2 = [cd, 0.0, tip + e]  # stage 2 input shaft tip meets stage 1's
    if stage2_as_assembly:
        stage2 = {
            "role": "stage",
            "item": "stdlib:GearStage",
            "inputs": dict(
                module=g.module, z_pinion=g.z_pinion, z_gear=g.z_gear, bearing=bearing
            ),
            "translate": [0.0, 0.0, 0.0],
            "rotate": None,
            "bind": {k: k for k in PROMOTED},
        }
        items.append(_place(stage2, world, offset2, "s2."))
    else:
        items += _stage(g, horizontal, offset2, "s2.", threads, warnings)
    inputs = dict(
        module=g.module, z_pinion=g.z_pinion, z_gear=g.z_gear, bearing=bearing
    )
    return _finish(
        items,
        inputs,
        warnings,
        center_distance=g.center_distance,
        ratio=g.ratio**2,
        horizontal=horizontal,
    )


def ratio_presets(module: float = 2, teeth_sum: int = 44) -> Dict[str, Dict[str, int]]:
    """Tooth pairs with the same sum (same centre distance, every placement of
    a click-built stage stays valid) and an odd gear (meshes unphased):
    ``{"3:1": {"z_pinion": 11, "z_gear": 33}, ...}``."""
    out: Dict[str, Dict[str, int]] = {}
    for z1 in range(8, teeth_sum // 2 + 1):
        z2 = teeth_sum - z1
        if z2 % 2 == 0 or z2 < z1:
            continue
        try:
            StageGeometry(module=float(module), z_pinion=z1, z_gear=z2).check()
        except ValueError:
            continue
        out[f"{z2 / z1:.2f}:1"] = {"z_pinion": z1, "z_gear": z2}
    return out


# --------------------------------------------------------------------------- #
# The same assemblies in code
# --------------------------------------------------------------------------- #


def build_layout(layout: Dict[str, Any]) -> Any:
    """An ``Assembly`` holding every layout item, built the way the viewer
    evaluates it (library item + widget inputs) and placed by ``translate`` /
    ``rotate``."""
    from cadbuildr.foundation import Assembly
    from cadbuildr.foundation.library.evaluate import resolve_item
    from cadbuildr.foundation.library.registry import call_configurable
    from cadbuildr.stdlib.gearbox.stage import rot_deg_of

    asm = Assembly()
    for it in layout["items"]:
        component = call_configurable(resolve_item(it["item"]), it["inputs"])
        asm.add_component(
            component, at=it["translate"], rot_deg=rot_deg_of(it["rotate"])
        )
    asm.layout = layout
    return asm


def build_single_stage(**kwargs: Any) -> Any:
    """:func:`single_stage_layout` (same keywords) as an ``Assembly``."""
    return build_layout(single_stage_layout(**kwargs))


def build_two_stage(**kwargs: Any) -> Any:
    """:func:`two_stage_layout` (same keywords) as an ``Assembly``."""
    return build_layout(two_stage_layout(**kwargs))


if __name__ == "__main__":  # pragma: no cover - manual viewer check
    from cadbuildr.foundation import show

    show(build_two_stage())
