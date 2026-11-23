"""WoodScrew: geometry sanity + the connect_with_screw contract."""

import pytest

from cadbuildr.foundation import show_dag
from cadbuildr.stdlib.fasteners import WoodScrew


@pytest.mark.parametrize("gauge", ["4", "6", "8", "10", "12"])
def test_all_gauges_instantiate_and_mesh(gauge):
    screw = WoodScrew(gauge, 32)
    dag = show_dag(screw)
    assert len(dag["DAG"]) > 0


def test_connect_with_screw_contract_attrs():
    screw = WoodScrew("8", 32)
    assert screw.body_height == 32
    assert screw.body_radius == pytest.approx(2.1)
    assert screw.head_radius > screw.body_radius
    # Fully-embedded seat: the head TOP is the seat plane.
    seat = screw.anchor("head_seat")
    assert seat.frame.position[2] == pytest.approx(32.0)


def test_int_gauge_accepted():
    assert WoodScrew(8, 25).gauge == "8"


def test_too_short_raises():
    with pytest.raises(ValueError):
        WoodScrew("12", 6)


def test_unknown_gauge_raises():
    with pytest.raises(ValueError):
        WoodScrew("7", 30)
