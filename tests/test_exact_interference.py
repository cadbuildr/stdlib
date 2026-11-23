"""The worked examples are interference-free on the real solids.

``assembly.check_interference(exact=True)`` (foundation >= 0.2.18) meshes every
part through the kernel API and intersects the meshes with manifold3d, so
jointed pairs (gear mesh, bolt in its hole, shaft in its coupling) are checked
too, and line-to-line fits (shaft == bore) must come out clean.
``test_gear_mesh.py`` is the fast, kernel-free fallback for the gears.

Needs ``cadbuildr-foundation[exact]`` (manifold3d) and a reachable kernel API
(``CAD_COMPILE_API_BASE_URL``; a local ``tsjs/apps/kernel-api`` with no token
configured runs in open mode). Skips, with the reason, when either is missing.
"""

import pytest

pytest.importorskip("manifold3d")

from cadbuildr.foundation.interference import kernel_api_mesher
from cadbuildr.stdlib.examples import (
    build_bolted_plate,
    build_gear_pair,
    build_motor_leadscrew_stack,
)
from cadbuildr.stdlib.fasteners import DIN125Washer


@pytest.fixture(scope="module")
def mesher():
    mesh = kernel_api_mesher()
    try:
        vertices, triangles = mesh(DIN125Washer("M8"))
    except Exception as exc:  # no kernel API reachable / not authorised
        pytest.skip(f"kernel API unavailable for exact interference: {exc}")
    assert len(vertices) and len(triangles)
    return mesh


EXAMPLES = {
    "gear_pair": lambda: build_gear_pair()[0],
    # Modeled threads are cosmetic (the nut bore is plain), so compare the
    # thread-less solids: shank vs nut bore must touch, not overlap.
    "bolted_plate": lambda: build_bolted_plate(with_thread=False)[0],
    "motor_leadscrew_stack": lambda: build_motor_leadscrew_stack(with_thread=False)[0],
}


@pytest.mark.parametrize("name", sorted(EXAMPLES))
def test_example_has_no_solid_overlap(name, mesher):
    assembly = EXAMPLES[name]()
    found = assembly.check_interference(exact=True, mesher=mesher)
    unknown = [r for r in found if r.status == "unknown"]
    assert not unknown, f"{name}: parts the kernel could not mesh: {unknown}"
    overlaps = [r for r in found if r.is_overlap]
    # foundation >= 0.2.19 meshes finely and ignores sub-0.02 mm depth, so the
    # motor stack's line-to-line shaft-in-bore fits come out clean too.
    assert overlaps == [], f"{name}: solid overlap: {overlaps}"


def test_exact_check_catches_a_mis_phased_gear(mesher, monkeypatch):
    """Control: half a tooth off puts tooth on tooth (~20 mm^3 on openclaw)."""
    import math

    from cadbuildr.foundation import Assembly
    from cadbuildr.stdlib.power_transmission.gears import SpurGear
    from cadbuildr.stdlib.power_transmission.gears import connections

    good = connections.mesh_phase
    monkeypatch.setattr(
        connections,
        "mesh_phase",
        lambda d, n, angle=0.0: good(d, n, angle) + math.pi / n.teeth,
    )
    pinion, wheel = SpurGear(teeth=12, bore=5), SpurGear(teeth=30, bore=8)
    asm = Assembly()
    asm.add_component(pinion)
    connections.mesh_gears(asm, pinion, wheel)
    hits = [
        r for r in asm.check_interference(exact=True, mesher=mesher) if r.is_overlap
    ]
    assert hits and hits[0].volume > 1.0
