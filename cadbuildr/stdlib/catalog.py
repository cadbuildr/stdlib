"""Catalog registry for the CADbuildr standard library.

This is the DRY backbone behind the public showcase. Every part decorates its
class with :func:`cadbuildr.foundation.library.part` (typed inputs, category,
``catalog_id``), declaring how it should appear and which parameters are
configurable. The showcase (and the test-suite) read the result through
:func:`get_catalog_manifest`, so **adding a part is a one-file change** -- no
second index to keep in sync, and the github.io page picks it up automatically.

Parts are discovered by importing every submodule of ``cadbuildr.stdlib`` once,
which runs each ``@part`` decorator. Discovery uses :func:`pkgutil.walk_packages`
so it works identically from a checkout, an installed wheel, and a zipimport
inside Pyodide.
"""

from __future__ import annotations

import dataclasses
import importlib
import pkgutil
import re
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


def _param_widget(p: ParamSpec) -> dict:
    """A ``ParamSpec`` as a library widget (``cadbuildr.foundation.library``)."""
    if p.kind == "enum":
        return {
            "kind": "enum",
            "options": [str(c) for c in p.choices or []],
            "default": str(p.default),
        }
    if p.kind == "bool":
        return {"kind": "bool", "default": bool(p.default)}
    w = {
        "kind": "number",
        "integer": False,
        "default": p.default,
        "unit": p.unit or "mm",
    }
    for key in ("min", "max", "step"):
        if getattr(p, key) is not None:
            w[key] = getattr(p, key)
    return w


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
    """Class decorator that registers a Part/Assembly into the catalog.

    .. deprecated:: 0.5
        Use :func:`cadbuildr.foundation.library.part` with typed inputs
        (``OneOf[TABLE]``, ``Num(min, max)``, ``bool``) and
        ``catalog_id=`` / ``featured=`` / ``example=``. No stdlib part uses
        this alias any more; it stays for third-party libraries.

    A thin alias over :func:`cadbuildr.foundation.library.part` (or
    ``assembly``): the class becomes a library item (manifest entry with
    widgets, ``library_ref`` stamping), and the catalog fields are kept for
    :func:`get_catalog_manifest`.
    """
    import warnings

    from cadbuildr.foundation import Assembly
    from cadbuildr.foundation.library import assembly, part

    warnings.warn(
        "catalog_part is deprecated: decorate with cadbuildr.foundation.library.part "
        "and declare inputs with type hints (OneOf / Num / bool).",
        DeprecationWarning,
        stacklevel=2,
    )
    params = list(params or [])

    def _wrap(cls):
        decorator = assembly if issubclass(cls, Assembly) else part
        decorator(
            category=f"{category}/{subcategory}",
            name=name,
            standard=standard,
            description=description,
            inputs={
                p.name: {"widget": _param_widget(p), "label": p.label} for p in params
            },
            catalog={
                "id": id,
                "category": category,
                "subcategory": subcategory,
                "params": params,
            },
            catalog_id=id,
            featured=featured,
            example=dict(example_config or {}),
        )(cls)
        cls._catalog_id = id  # back-reference, handy for debugging
        return cls

    return _wrap


# --------------------------------------------------------------------------- #
# Catalog entries from the library registry
# --------------------------------------------------------------------------- #


def _kebab(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "-", name).lower()


def _params_from_inputs(item) -> list:
    """ParamSpecs derived from a ``@part`` item's widgets (enum / number / bool)."""
    out = []
    for entry in item.inputs():
        w = entry["widget"]
        label = entry["label"]
        if w["kind"] == "enum":
            out.append(
                ParamSpec.enum(entry["name"], w["options"], w["default"], label=label)
            )
        elif w["kind"] == "bool":
            out.append(ParamSpec.boolean(entry["name"], w["default"], label=label))
        elif (
            w["kind"] == "number"
            and w.get("min") is not None
            and w.get("max") is not None
        ):
            out.append(
                ParamSpec.number(
                    entry["name"],
                    min=w["min"],
                    max=w["max"],
                    default=w["default"],
                    step=w.get("step", 1),
                    label=label,
                    unit=w.get("unit", "mm"),
                )
            )
    return out


def _entry_for(item) -> CatalogEntry:
    meta = item.extra.get("catalog") or {}
    category, _, subcategory = (item.category or "Other").partition("/")
    return CatalogEntry(
        id=meta.get("id") or item.extra.get("catalog_id") or _kebab(item.cls),
        category=meta.get("category") or category,
        subcategory=meta.get("subcategory") or subcategory or category,
        name=item.name,
        standard=item.standard or "",
        description=item.description or "",
        module=item.module,
        cls=item.cls,
        params=list(meta["params"]) if "params" in meta else _params_from_inputs(item),
        featured=bool(item.extra.get("featured")),
        example_config=dict(item.extra.get("example") or {}),
    )


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
    """All stdlib library items as catalog entries, sorted by (category, subcategory, name)."""
    from cadbuildr.foundation.library import items

    _discover()
    entries = {}
    for item in items("cadbuildr.stdlib"):
        if item.kind not in ("part", "assembly"):
            continue
        entry = _entry_for(item)
        entries[entry.id] = entry  # last registration wins
    return sorted(entries.values(), key=lambda e: (e.category, e.subcategory, e.name))


def get_catalog_manifest() -> list[dict]:
    """JSON-serializable manifest consumed by the showcase and the tests."""
    return [e.to_dict() for e in get_catalog_entries()]


def _humanize(name: str) -> str:
    return name.replace("_", " ").strip().capitalize()
