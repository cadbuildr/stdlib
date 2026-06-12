"""Every catalogued part must instantiate and build a foundation DAG.

The catalog manifest is the single source of truth for what the showcase renders,
so the contract we test is exactly that: for each entry, the declared
``example_config`` builds, and each declared parameter variant builds too. This is
what stops a broken size or a renamed kwarg from silently shipping to the page.
"""

import pytest

from cadbuildr.foundation.dag_utils import show_dag
from cadbuildr.stdlib.catalog import get_catalog_entries


ENTRIES = get_catalog_entries()


def _base_config(entry) -> dict:
    """Default kwargs for an entry: each param's default, overlaid with example."""
    base = {p.name: p.default for p in entry.params}
    base.update(entry.example_config)
    return base


def _build(cls, config) -> None:
    """Instantiate the part and force a full DAG build; raises on failure."""
    dag = show_dag(cls(**config))
    assert dag["DAG"], "DAG built but is empty"


def test_catalog_is_non_empty():
    assert ENTRIES, "catalog discovery returned no parts"


def test_catalog_ids_are_unique():
    ids = [e.id for e in ENTRIES]
    assert len(ids) == len(set(ids)), "duplicate catalog ids"


@pytest.mark.parametrize("entry", ENTRIES, ids=[e.id for e in ENTRIES])
def test_example_config_builds(entry):
    """The hero render the showcase shows first must always work."""
    _build(entry.load_class(), _base_config(entry))


def _variant_cases():
    cases = []
    for entry in ENTRIES:
        base = _base_config(entry)
        for param in entry.params:
            for value in param.variants():
                cfg = {**base, param.name: value}
                cases.append(pytest.param(entry, cfg, id=f"{entry.id}-{param.name}={value}"))
    return cases


@pytest.mark.parametrize("entry,config", _variant_cases())
def test_each_variant_builds(entry, config):
    """Every selectable option on the showcase controls must build."""
    _build(entry.load_class(), config)
