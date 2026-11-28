"""Library-practice guards: every stdlib item follows the Nov-27 conventions.

* declared with ``@part`` / ``@assembly`` (no deprecated ``catalog_part``);
* every input typed (enum / number with bounds / bool) and every part offers
  at least one named configuration when it has a non-bool input;
* every part carries at least one typed interface (``assembly.connect``);
* every declared preset builds a DAG;
* an unknown table key fails loudly with the valid choices.
"""

from __future__ import annotations

import pathlib

import pytest

from cadbuildr.foundation.dag_utils import show_dag
from cadbuildr.foundation.library import get_manifest, items
from cadbuildr.stdlib.catalog import get_catalog_entries

PKG = pathlib.Path(__file__).resolve().parents[1] / "cadbuildr" / "stdlib"
get_catalog_entries()  # discovery: import every module once
MANIFEST = get_manifest("cadbuildr.stdlib")
ITEMS = {i["cls"]: i for i in MANIFEST["items"]}
LIB_ITEMS = [i for i in items("cadbuildr.stdlib") if i.kind in ("part", "assembly")]


def test_no_module_uses_the_deprecated_catalog_part():
    offenders = [
        str(p.relative_to(PKG))
        for p in PKG.rglob("*.py")
        if p.name != "catalog.py" and "@catalog_part" in p.read_text()
    ]
    assert not offenders, offenders


def test_manifest_has_no_errors_and_one_section_per_top_category():
    assert "errors" not in MANIFEST
    sections = [s["label"] for s in MANIFEST["toolbar"]["sections"]]
    tops = {i["category"].split("/")[0] for i in MANIFEST["items"]}
    assert set(sections) == tops


@pytest.mark.parametrize("item", MANIFEST["items"], ids=lambda i: i["id"])
def test_inputs_are_typed_and_bounded(item):
    for inp in item["inputs"]:
        w = inp["widget"]
        if inp["name"] == "color":  # free-form paint colour
            continue
        assert w["kind"] in ("enum", "number", "bool"), (item["id"], inp)
        if w["kind"] == "number":
            assert w.get("min") is not None and w.get("max") is not None, (
                item["id"],
                inp["name"],
            )


@pytest.mark.parametrize("item", MANIFEST["items"], ids=lambda i: i["id"])
def test_configurable_items_offer_named_configurations(item):
    non_bool = [i for i in item["inputs"] if i["widget"]["kind"] != "bool"]
    if non_bool:
        assert item["configurations"], item["id"]


@pytest.mark.parametrize(
    "item",
    [i for i in MANIFEST["items"] if i["kind"] == "part"],
    ids=lambda i: i["id"],
)
def test_every_part_has_an_interface(item):
    assert item.get("interfaces"), f"{item['id']} declares no typed interface"


def _preset_cases():
    for item in LIB_ITEMS:
        for name, values in item.presets.items():
            yield pytest.param(item, values, id=f"{item.cls}:{name}")


@pytest.mark.parametrize("item,values", list(_preset_cases()))
def test_every_declared_preset_builds(item, values):
    cls = item.load()
    kwargs = dict(values)
    params = {p.name for p in item.parameters()}
    if "with_thread" in params:
        kwargs.setdefault("with_thread", False)  # geometry, not thread meshing
    dag = show_dag(cls(**kwargs))
    assert dag["DAG"]


@pytest.mark.parametrize(
    "cls,kwargs",
    [
        ("ThinNut", {"size": "M2"}),  # DIN 439 table starts at M3
        ("SquareNut", {"size": "M3"}),
        ("WingNut", {"size": "M12"}),
        ("HexBolt", {"size": "M24", "length": 40}),
        ("CountersunkSocketScrew", {"size": "M7", "length": 20}),
        ("MetricThreadedRod", {"size": "M9", "length": 50}),
        ("SplitLockWasher", {"size": "M1"}),
    ],
)
def test_unknown_size_names_the_choices(cls, kwargs):
    item = next(i for i in LIB_ITEMS if i.cls == cls)
    with pytest.raises(ValueError, match="choose from"):
        item.load()(**kwargs)


def test_nut_variants_offer_only_their_own_sizes():
    from cadbuildr.stdlib.fasteners.nuts.nut_variants_part import (
        NylonLockNut,
        ThinNut,
    )

    for cls in (ThinNut, NylonLockNut):
        widget = ITEMS[cls.__name__]["inputs"][0]["widget"]
        assert widget["options"] == list(cls.dimension_table), cls.__name__


def test_wood_screw_head_carries_its_gauge():
    from cadbuildr.foundation.interfaces import interfaces_of, spec_of
    from cadbuildr.stdlib.fasteners import WoodScrew

    screw = WoodScrew("8", 32)
    sizes = {spec_of(n).params.get("size") for n in interfaces_of(screw)}
    assert sizes == {"#8"}


def test_showcase_catalog_json_lists_every_part():
    """github-io/public/catalog.json is the showcase's static fast path:
    regenerate it (github-io/README.md) when parts are added or renamed."""
    import json

    path = PKG.parents[1] / "github-io" / "public" / "catalog.json"
    if not path.exists():
        pytest.skip("showcase site not shipped with this checkout")
    shipped = {e["id"] for e in json.loads(path.read_text())}
    assert shipped == {e.id for e in get_catalog_entries()}
