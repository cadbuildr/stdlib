"""Library CI generated from the interface declarations (spec 7.5).

* every migrated part (the parts the demos use) exposes interfaces;
* for each part, each of its interfaces and each mate rule that interface
  takes part in, the test connects it to a counterpart from the same pool
  (the parts of the demo layouts, at their demo sizes) and builds +
  checks + interference-checks the pair;
* the CLI surface: ``rules``, ``connect``, ``insert --connect``,
  ``eval --interfaces``.
"""

import io
import json
import warnings
from contextlib import redirect_stdout

import pytest

from cadbuildr.foundation import Assembly
from cadbuildr.foundation.dag_utils import show_dag
from cadbuildr.foundation.interfaces import candidate_pairs, find_rule, rules, spec_of
from cadbuildr.foundation.interfaces.rules import evaluate_rule
from cadbuildr.foundation.library import get_manifest
from cadbuildr.foundation.library import cli
from cadbuildr.foundation.library.evaluate import resolve_item
from cadbuildr.foundation.library.registry import call_configurable

try:  # demo_skate lives in the monorepo only; the public stdlib skips it
    from cadbuildr.demo_skate import skateboard_layout
except ImportError:  # pragma: no cover
    skateboard_layout = None
from cadbuildr.stdlib.gearbox import single_stage_layout, two_stage_layout
from cadbuildr.stdlib.motion_kits import demos

MIGRATED = {
    "SmoothRod",
    "LinearBearing",
    "RodEndPlate",
    "Carriage",
    "GantryCarriage",
    "MotorMount",
    "StepperMotor",
    "ClampCoupling",
    "LeadScrewT8",
    "LeadScrewNutT8",
    "DeepGrooveBearing",
    "GT2Pulley",
    "AluExtrusion",
    "DIN912Screw",
    "HexNut",
    "DIN125Washer",
    "TSlotNut",
    "SpurGear",
    "Shaft",
    "GearboxPlate",
    "Spacer",
    "GearStage",
}
MANIFEST = {i["cls"]: i for i in get_manifest("cadbuildr.stdlib")["items"]}


@pytest.mark.parametrize("cls", sorted(MIGRATED))
def test_migrated_parts_expose_interfaces(cls):
    """A part without interfaces cannot be connected: a library test failure."""
    item = MANIFEST[cls]
    assert item["interfaces"], cls
    for iface in item["interfaces"]:
        assert set(iface) == {"name", "type", "params", "role", "group", "required"}
        assert iface["name"] in item["anchors"]


def _pool():
    """Unique (item, inputs) of every demo layout: compatible sizes."""
    layouts = [
        demos.linear_stage_layout(),
        demos.xy_gantry_layout(),
        single_stage_layout(),
        two_stage_layout(stage2_as_assembly=True),
        *([skateboard_layout()] if skateboard_layout else []),
    ]
    seen = {}
    for layout in layouts:
        for e in layout["items"]:
            key = json.dumps([e["item"], e["inputs"]], sort_keys=True)
            seen.setdefault(key, (e["item"], e["inputs"]))
    return list(seen.values())


def _build(item_id, inputs):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return call_configurable(resolve_item(item_id), dict(inputs))


POOL = _pool()
SAMPLES = [(item_id, inputs, _build(item_id, inputs)) for item_id, inputs in POOL]


def _cases():
    cases, seen = [], set()
    for item_id, inputs, part in SAMPLES:
        for node in part.interfaces:
            for other_id, other_inputs, other in SAMPLES:
                if other is part:
                    continue
                for target in other.interfaces:
                    found = find_rule(node.type.value, target.type.value)
                    if found is None:
                        continue
                    rule, swapped = found
                    key = (item_id, node.iname, rule.name)
                    if key in seen:
                        continue
                    _, failures = evaluate_rule(
                        rule, swapped, node, target, spec_of(node), spec_of(target)
                    )
                    if failures:
                        continue
                    seen.add(key)
                    cases.append(
                        pytest.param(
                            item_id,
                            inputs,
                            node.iname,
                            other_id,
                            other_inputs,
                            target.iname,
                            id=f"{item_id.split(':')[1]}.{node.iname}-{rule.name}-{other_id.split(':')[1]}.{target.iname}",
                        )
                    )
    return cases


CASES = _cases()


def test_generated_cases_cover_every_rule_the_parts_use():
    used = {c.id.split("-")[1] for c in CASES}
    pool_types = {n.type.value for _, _, p in SAMPLES for n in p.interfaces}
    expected = {
        r.name
        for r in rules()
        if r.a.__name__ in pool_types and r.b.__name__ in pool_types
    }
    assert expected <= used, sorted(expected - used)
    assert len(CASES) >= 60


@pytest.mark.parametrize("item_id,inputs,own,other_id,other_inputs,target", CASES)
def test_connect_each_interface_to_a_counterpart(
    item_id, inputs, own, other_id, other_inputs, target
):
    base, part = _build(other_id, other_inputs), _build(item_id, inputs)
    asm = Assembly()
    asm.ground(base)
    asm.connect(part.interface(own), base.interface(target))
    assert len(asm.joints) == 1
    assert [i for i in asm.check() if i["severity"] != "info"] == []
    # between the two components (a sub-assembly's own parts are its business)
    hits = asm.check_interference(include_unknown=False)
    assert [
        i
        for i in hits
        if i.status == "overlap" and i.path_a.split("/")[0] != i.path_b.split("/")[0]
    ] == []
    dag = show_dag(asm)
    assert dag["checks"] is not None


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def _cli(argv, stdin=None, monkeypatch=None):
    if stdin is not None:
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(stdin)))
    out = io.StringIO()
    with redirect_stdout(out):
        cli.main(argv)
    return json.loads(out.getvalue())


def test_cli_rules(monkeypatch):
    doc = _cli(["rules"])
    assert doc["format"] == "cadbuildr.mate-rules/1"
    names = {r["name"] for r in doc["rules"]}
    assert {"screw_in_hole", "bearing_on_rod", "rod_in_hole"} <= names
    if skateboard_layout:  # demo_skate registers its own rules
        assert "wheel_on_axle" in names
    rule = next(r for r in doc["rules"] if r["name"] == "bearing_on_rod")
    assert (rule["a"], rule["b"], rule["joint"], rule["jointType"]) == (
        "BearingFace",
        "RodAxis",
        "slider",
        "SliderJoint",
    )
    assert doc["types"]["RodAxis"] == {
        "params": ["d"],
        "role": "male",
        "axisymmetric": True,
        "reversible": True,
        "doc": "Rod axis (+Z along the rod): linear bearings slide on it.",
    }


def test_cli_connect_resolves_the_mate(monkeypatch):
    req = {
        "a": {
            "var": "bearing_0a",
            "interface": "end_a",
            "item": "stdlib:LinearBearing",
            "inputs": {"rod": "8"},
        },
        "b": {
            "var": "rod_a",
            "interface": "axis",
            "item": "stdlib:SmoothRod",
            "inputs": {"diameter": "8", "length": 400},
        },
        "dof": {"offset": 165},
    }
    out = _cli(["connect"], req, monkeypatch)
    assert out["ok"] and out["joint"] == "slider" and out["jointType"] == "SliderJoint"
    assert out["flip"] is True and out["dof"] == {"offset": 165}
    assert (
        out["code"]
        == 'assembly.connect(bearing_0a.interface("end_a"), rod_a.interface("axis"), offset=165)'
    )
    # a component-level side lists the candidates
    req = {
        "a": {
            "var": "s",
            "item": "stdlib:DIN912Screw",
            "inputs": {"size": "M5", "length": 10},
        },
        "b": {"var": "plate", "item": "stdlib:RodEndPlate", "inputs": {}},
    }
    out = _cli(["connect"], req, monkeypatch)
    assert not out["ok"] and len(out["candidates"]) == 4
    # sizes that do not fit
    req = {
        "a": {
            "var": "s",
            "interface": "head_seat",
            "item": "stdlib:DIN912Screw",
            "inputs": {"size": "M3", "length": 10},
        },
        "b": {
            "var": "plate",
            "interface": "foot_hole_a",
            "item": "stdlib:RodEndPlate",
            "inputs": {},
        },
    }
    out = _cli(["connect"], req, monkeypatch)
    assert (
        not out["ok"] and out["candidates"] == [] and "size" in out["incompatible"][0]
    )


def test_cli_insert_with_connect():
    out = _cli(
        [
            "insert",
            "stdlib:LinearBearing",
            '{"rod": "8"}',
            "--name",
            "bearing_0a",
            "--connect",
            '{"own": "end_a", "target": ["rod_a", "axis"], "dof": {"offset": 165}}',
        ]
    )
    assert out["code"] == 'bearing_0a = LinearBearing(rod="8")'
    assert (
        out["connect"]
        == 'assembly.connect(bearing_0a.interface("end_a"), rod_a.interface("axis"), offset=165)'
    )
    assert out["lines"] == [out["code"], out["connect"]]
    ground = _cli(
        [
            "insert",
            "stdlib:RodEndPlate",
            "{}",
            "--name",
            "plate",
            "--connect",
            '{"target": null}',
        ]
    )
    assert ground["connect"] == "assembly.ground(plate)"
    plain = _cli(["insert", "stdlib:SmoothRod", "{}"])
    assert "connect" not in plain and plain["code"].startswith(
        "smooth_rod_1 = SmoothRod("
    )


def test_cli_eval_with_interfaces(monkeypatch):
    out = _cli(
        ["eval", "--interfaces"],
        {"item": "stdlib:SmoothRod", "inputs": {"diameter": "10", "length": 200}},
        monkeypatch,
    )
    assert out["ok"]
    assert [(i["name"], i["type"], i["params"]) for i in out["interfaces"]] == [
        ("end_a", "RodEnd", {"d": 10}),
        ("end_b", "RodEnd", {"d": 10}),
        ("axis", "RodAxis", {"d": 10}),
    ]
