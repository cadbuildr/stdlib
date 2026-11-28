"""stdlib as a cadbuildr.foundation.library library: every part has a manifest
entry with widgets; pilots declare inputs with type hints."""

import json

import pytest

from cadbuildr.foundation.dag_utils import show_dag
from cadbuildr.foundation.library import get_manifest, item_for
from cadbuildr.foundation.library.evaluate import evaluate
from cadbuildr.stdlib.bearings.ball_bearings.deep_groove_part import DeepGrooveBearing
from cadbuildr.stdlib.catalog import get_catalog_manifest
from cadbuildr.stdlib.fasteners.screws_and_bolts.din912_part import DIN912Screw

MANIFEST = get_manifest("cadbuildr.stdlib")
ITEMS = {i["cls"]: i for i in MANIFEST["items"]}


def test_manifest_library_block_and_toolbar():
    assert MANIFEST["format"] == "cadbuildr.library-manifest/1"
    assert MANIFEST["library"]["id"] == "stdlib"
    assert MANIFEST["library"]["name"] == "CADbuildr standard library"
    assert MANIFEST["library"]["import_root"] == "cadbuildr.stdlib"
    assert MANIFEST["toolbar"]["tab"] == "Stdlib"
    sections = {s["id"]: s["items"] for s in MANIFEST["toolbar"]["sections"]}
    assert "stdlib:DeepGrooveBearing" in sections["bearings"]
    assert "errors" not in MANIFEST
    json.dumps(MANIFEST)


def test_every_catalog_part_is_a_library_item_with_widgets():
    catalog = {(e["module"], e["cls"]) for e in get_catalog_manifest()}
    items = {(i["module"], i["cls"]) for i in MANIFEST["items"]}
    assert catalog == items
    for item in MANIFEST["items"]:
        assert item["anchors"], item["id"]
        for inp in item["inputs"]:
            assert inp["widget"]["kind"] in ("enum", "number", "bool", "text"), (
                item["id"],
                inp,
            )


def test_deep_groove_bearing_manifest():
    item = ITEMS["DeepGrooveBearing"]
    assert item["id"] == "stdlib:DeepGrooveBearing"
    assert item["inputs"][0]["widget"] == {
        "kind": "enum",
        "options": list(DeepGrooveBearing.TABLE),
        "default": "608",
    }
    assert [c["name"] for c in item["configurations"]] == list(DeepGrooveBearing.TABLE)
    assert item["anchors"] == ["bottom", "top", "axis"]


def test_din912_presets_and_inputs():
    item = ITEMS["DIN912Screw"]
    assert [i["name"] for i in item["inputs"]] == ["size", "length", "with_thread"]
    assert (
        item["inputs"][1]["widget"]["min"] == 3
        and item["inputs"][1]["widget"]["max"] == 80
    )
    assert item["configurations"][:2] == [
        {"name": "Default", "values": {"size": "M6", "length": 20}},
        {"name": "Short M3", "values": {"size": "M3", "length": 8}},
    ]
    screw = DIN912Screw(size="M3", length=8, with_thread=False)
    assert (
        item_for(DIN912Screw).match_configuration(
            {"size": "M3", "length": 8, "with_thread": True}
        )
        == "Short M3"
    )
    assert screw.size == "M3"


def test_bearing_library_ref_in_dag():
    dag = show_dag(DeepGrooveBearing(model="6800"))
    names = {v: k for k, v in dag["serializableNodes"].items()}
    nodes = dag["DAG"]
    root = nodes[dag["rootNodeId"]]
    ref = nodes[root["deps"]["library"]]
    assert names[ref["type"]] == "LibraryRef"
    values = {k: nodes[v]["params"]["value"] for k, v in ref["deps"].items()}
    assert values["item"] == "stdlib:DeepGrooveBearing"
    assert json.loads(values["inputs"]) == {"model": "6800"}
    assert values["configuration"] == "6800"


@pytest.mark.parametrize(
    "cls", ["DeepGrooveBearing", "LinearBearing", "HexNut", "DIN912Screw"]
)
def test_pilots_evaluate(cls):
    item = ITEMS[cls]
    values = {i["name"]: i["widget"]["default"] for i in item["inputs"]}
    result = evaluate({"item": item["id"], "inputs": values})
    assert result["ok"], result


def test_insert_snippet_for_code_sync():
    from cadbuildr.foundation.library.sources import insert

    out = insert("stdlib:DeepGrooveBearing", {"model": "6800"}, var="bearing_1")
    assert (
        out["import"]
        == "from cadbuildr.stdlib.bearings.ball_bearings.deep_groove_part import DeepGrooveBearing"
    )
    assert out["code"] == 'bearing_1 = DeepGrooveBearing(model="6800")'


def test_installed_entry_point():
    from cadbuildr.foundation.library.sources import library_entry_points

    eps = library_entry_points()
    if "cadbuildr.stdlib" not in eps:
        pytest.skip(
            "installed without package metadata: no entry points"
        )
    info = eps["cadbuildr.stdlib"]
    assert info["id"] == "stdlib" and info["dist"] == "cadbuildr-stdlib"
