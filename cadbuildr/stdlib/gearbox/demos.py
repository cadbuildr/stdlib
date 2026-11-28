"""Click-only spur gear reducer demo (single and two stage) as connect sequences.

Each layout is what the viewer's Library panel records when the reducer is
built one *insert & connect* at a time: per item, the library ``item`` id,
its ``inputs`` and the ``connect`` that places it (``{own, target: [item,
interface], dof}``; the first item is grounded). There are no positions:
the joints place every part, so changing ``module`` moves the output shaft,
``bearing`` resizes seats / bearings, and the tooth counts re-space the
plates through the chain. ``loops`` are the redundant contacts (plate B on
the other spacers, shafts in plate B's bearings, nuts on their bolts),
checked on build. See :func:`cadbuildr.foundation.library.layout.build_layout`.

``bindings`` maps each promoted top-level input to the ``[item, component
input]`` pairs that take its value as is (equal values only); shaft and gear
bore diameters follow the bearing bore and are derived by re-running the
layout.
"""

from __future__ import annotations

from typing import Any, Dict, List

from cadbuildr.foundation.library.layout import build_layout, derive_bindings
from cadbuildr.stdlib.gearbox.geometry import StageGeometry, stage_items, stage_loops

__all__ = [
    "build_single_stage",
    "build_two_stage",
    "ratio_presets",
    "single_stage_layout",
    "two_stage_layout",
]

PROMOTED = ("module", "z_pinion", "z_gear", "bearing")
COUPLING_LENGTH = 25.0


def _geometry(module, z_pinion, z_gear, bearing) -> StageGeometry:
    return StageGeometry(
        module=float(module),
        z_pinion=int(z_pinion),
        z_gear=int(z_gear),
        bearing=bearing,
    )


def _named(entries: List[Dict[str, Any]], prefix: str) -> List[Dict[str, Any]]:
    out = []
    for e in entries:
        link = e["connect"]
        if link is not None:
            target = list(link["target"])
            if not target[0].startswith(("s1.", "s2.", "coupling")) or not prefix:
                target[0] = f"{prefix}{target[0]}" if target[0] in _ROLES else target[0]
            link = dict(link, target=target)
        out.append(
            {
                "name": f"{prefix}{e['role']}",
                "item": e["item"],
                "inputs": dict(e["inputs"]),
                "connect": link,
            }
        )
    return out


_ROLES = {e["role"] for e in stage_items(_geometry(2, 11, 33, "608"))}


def _bindings_of(
    entries: List[Dict[str, Any]], prefix: str, acc: Dict[str, List[List[str]]]
) -> None:
    for e in entries:
        for comp_input, top in (e.get("bind") or {}).items():
            acc.setdefault(top, []).append([f"{prefix}{e['role']}", comp_input])


def _finish(items, loops, inputs, bindings, **extra) -> Dict[str, Any]:
    from cadbuildr.foundation.library import item_for
    from cadbuildr.stdlib.gearbox.stage import GearStage

    stage_item = item_for(GearStage)
    widgets = {
        name: dict(stage_item.input(name)["widget"], default=value)
        for name, value in inputs.items()
    }
    part_count = sum(30 if it["item"] == "stdlib:GearStage" else 1 for it in items)
    return {
        "inputs": {k: {"widget": widgets[k], "default": v} for k, v in inputs.items()},
        "bindings": {k: bindings.get(k, []) for k in inputs},
        "items": items,
        "loops": loops,
        "part_count": part_count,
        **extra,
    }


def single_stage_layout(
    module: float = 2,
    z_pinion: int = 11,
    z_gear: int = 33,
    bearing: str = "608",
    threads: bool = False,
) -> Dict[str, Any]:
    """One stage (30 parts): 2 plates, 4 spacers, 2 shafts, pinion + gear,
    4 bearings, 4 DIN 912 through-bolts, 8 DIN 125 washers, 4 hex nuts.

    Returns ``{"inputs", "bindings", "items", "loops", "part_count",
    "center_distance", "ratio"}``; plate A is grounded (shafts along +Z)."""
    g = _geometry(module, z_pinion, z_gear, bearing)
    entries = stage_items(g, threads=threads)
    bindings: Dict[str, List[List[str]]] = {}
    _bindings_of(entries, "", bindings)
    inputs = dict(
        module=g.module, z_pinion=g.z_pinion, z_gear=g.z_gear, bearing=bearing
    )
    return _finish(
        _named(entries, ""),
        stage_loops(""),
        inputs,
        bindings,
        center_distance=g.center_distance,
        ratio=g.ratio,
    )


def two_stage_layout(
    module: float = 2,
    z_pinion: int = 11,
    z_gear: int = 33,
    bearing: str = "608",
    threads: bool = False,
    stage2_as_assembly: bool = False,
) -> Dict[str, Any]:
    """Two identical stages in series (61 parts, ratio (z_gear / z_pinion)^2).

    A clamp coupling sits on stage 1's output shaft tip; stage 2's input
    shaft tip goes in its other bore (the stage hangs from it).
    ``stage2_as_assembly=True`` makes stage 2 ONE ``stdlib:GearStage`` item
    connected by its exposed ``input`` -- the live library insert."""
    g = _geometry(module, z_pinion, z_gear, bearing)
    bindings: Dict[str, List[List[str]]] = {}
    s1 = stage_items(g, threads=threads)
    _bindings_of(s1, "s1.", bindings)
    items = _named(s1, "s1.")
    loops = stage_loops("s1.")
    d = g.shaft_diameter
    items.append(
        {
            "name": "coupling",
            "item": "stdlib:ClampCoupling",
            "inputs": dict(bore_a=d, bore_b=d, length=COUPLING_LENGTH),
            "connect": {
                "own": "bore_a_stop",
                "target": ["s1.shaft_out", "end_b"],
                "dof": {},
            },
        }
    )
    if stage2_as_assembly:
        items.append(
            {
                "name": "s2.stage",
                "item": "stdlib:GearStage",
                "inputs": dict(
                    module=g.module,
                    z_pinion=g.z_pinion,
                    z_gear=g.z_gear,
                    bearing=bearing,
                ),
                "connect": {
                    "own": "input",
                    "target": ["coupling", "bore_b_stop"],
                    "dof": {},
                },
            }
        )
        for k in PROMOTED:
            bindings.setdefault(k, []).append(["s2.stage", k])
    else:
        s2 = stage_items(
            g, threads=threads, root="input", entry=["coupling", "bore_b_stop"]
        )
        _bindings_of(s2, "s2.", bindings)
        items += _named(s2, "s2.")
        loops += stage_loops("s2.")
    inputs = dict(
        module=g.module, z_pinion=g.z_pinion, z_gear=g.z_gear, bearing=bearing
    )
    return _finish(
        items,
        loops,
        inputs,
        bindings,
        center_distance=g.center_distance,
        ratio=g.ratio**2,
    )


def ratio_presets(module: float = 2, teeth_sum: int = 44) -> Dict[str, Dict[str, int]]:
    """Tooth pairs with the same sum (same centre distance) and an odd gear
    (meshes unphased): ``{"3.00:1": {"z_pinion": 11, "z_gear": 33}, ...}``."""
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


def build_single_stage(**kwargs: Any) -> Any:
    """:func:`single_stage_layout` (same keywords) built with ground / connect."""
    return build_layout(single_stage_layout(**kwargs))


def build_two_stage(**kwargs: Any) -> Any:
    """:func:`two_stage_layout` (same keywords) built with ground / connect."""
    return build_layout(two_stage_layout(**kwargs))


def check_bindings(layout_fn, values: Dict[str, Any], probes: Dict[str, List[Any]]):
    """The equal-value bindings re-derived by re-running ``layout_fn``."""
    return derive_bindings(layout_fn, values, probes)


if __name__ == "__main__":  # pragma: no cover - manual viewer check
    from cadbuildr.foundation import show

    show(build_two_stage(stage2_as_assembly=True))
