"""Catalog registry for the CADbuildr standard library.

This is the DRY backbone behind the public showcase. Every part decorates its
class with :func:`catalog_part`, declaring how it should appear and which
parameters are configurable. The showcase (and the test-suite) read the result
through :func:`get_catalog_manifest`, so **adding a part is a one-file change** --
no second index to keep in sync, and the github.io page picks it up automatically.

Parts are discovered by importing every submodule of ``cadbuildr.stdlib`` once,
which runs each ``@catalog_part`` decorator. Discovery uses :func:`pkgutil.walk_packages`
so it works identically from a checkout, an installed wheel, and a zipimport
inside Pyodide.
"""

from __future__ import annotations

import dataclasses
import importlib
import pkgutil
from dataclasses import dataclass, field
from typing import Any, Optional


# --------------------------------------------------------------------------- #
# Parameter specs
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class ParamSpec:
    """One configurable constructor argument, used to build the showcase controls.

    ``kind`` is one of ``"enum"``, ``"number"`` or ``"bool"``. Use the
    classmethods rather than constructing directly -- they keep the irrelevant
    fields ``None`` so the manifest stays compact.
    """

    name: str
    kind: str
    label: Optional[str] = None
    default: Any = None
    unit: Optional[str] = None
    # enum
    choices: Optional[list] = None
    # number
    min: Optional[float] = None
    max: Optional[float] = None
    step: Optional[float] = None

    @classmethod
    def enum(cls, name, choices, default, *, label=None, unit=None) -> "ParamSpec":
        return cls(
            name=name,
            kind="enum",
            label=label or _humanize(name),
            default=default,
            unit=unit,
            choices=list(choices),
        )

    @classmethod
    def number(
        cls, name, *, min, max, default, step=1, label=None, unit="mm"
    ) -> "ParamSpec":
        return cls(
            name=name,
            kind="number",
            label=label or _humanize(name),
            default=default,
            unit=unit,
            min=min,
            max=max,
            step=step,
        )

    @classmethod
    def boolean(cls, name, default, *, label=None) -> "ParamSpec":
        return cls(
            name=name,
            kind="bool",
            label=label or _humanize(name),
            default=default,
        )

    def variants(self) -> list:
        """Representative values the test-suite should exercise for this param."""
        if self.kind == "enum":
            return list(self.choices or [])
        if self.kind == "bool":
            return [True, False]
        return [self.default]


# --------------------------------------------------------------------------- #
# Catalog entries
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class CatalogEntry:
    id: str
    category: str
    subcategory: str
    name: str
    standard: str
    description: str
    module: str
    cls: str
    params: list = field(default_factory=list)
    featured: bool = False
    example_config: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = dataclasses.asdict(self)
        # drop None fields inside each param to keep the manifest compact
        d["params"] = [
            {k: v for k, v in p.items() if v is not None} for p in d["params"]
        ]
        return d

    def load_class(self):
        module = importlib.import_module(self.module)
        return getattr(module, self.cls)


_REGISTRY: dict[str, CatalogEntry] = {}


def catalog_part(
    *,
    id: str,
    category: str,
    subcategory: str,
    name: str,
    standard: str,
    description: str,
    params: Optional[list] = None,
    featured: bool = False,
    example_config: Optional[dict] = None,
):
    """Class decorator that registers a Part/Assembly into the catalog."""

    def _wrap(cls):
        entry = CatalogEntry(
            id=id,
            category=category,
            subcategory=subcategory,
            name=name,
            standard=standard,
            description=description,
            module=cls.__module__,
            cls=cls.__name__,
            params=list(params or []),
            featured=featured,
            example_config=dict(example_config or {}),
        )
        # Last registration wins -- keeps re-imports idempotent.
        _REGISTRY[id] = entry
        cls._catalog_id = id  # back-reference, handy for debugging
        return cls

    return _wrap


# --------------------------------------------------------------------------- #
# Discovery + manifest
# --------------------------------------------------------------------------- #
_discovered = False


def _discover() -> None:
    """Import every ``cadbuildr.stdlib`` submodule so decorators run (once)."""
    global _discovered
    if _discovered:
        return
    _discovered = True  # set first: a part module importing us must not re-enter

    import cadbuildr.stdlib as root

    for mod in pkgutil.walk_packages(root.__path__, prefix=root.__name__ + "."):
        if mod.name.rsplit(".", 1)[-1] == "catalog":
            continue
        importlib.import_module(mod.name)


def get_catalog_entries() -> list[CatalogEntry]:
    """All registered entries, sorted by (category, subcategory, name)."""
    _discover()
    return sorted(
        _REGISTRY.values(), key=lambda e: (e.category, e.subcategory, e.name)
    )


def get_catalog_manifest() -> list[dict]:
    """JSON-serializable manifest consumed by the showcase and the tests."""
    return [e.to_dict() for e in get_catalog_entries()]


def _humanize(name: str) -> str:
    return name.replace("_", " ").strip().capitalize()
