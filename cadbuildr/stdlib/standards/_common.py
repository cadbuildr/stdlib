"""Shared plumbing for the standards tables: one error type, size parsing,
"over a up to and including b" range lookup, and nearest-key suggestions."""

from __future__ import annotations

import difflib
import re
from typing import Any, Iterable, Mapping, Sequence, Tuple, TypeVar

__all__ = [
    "StandardsError",
    "UnknownSize",
    "OutOfRange",
    "lookup",
    "metric_diameter",
    "range_index",
    "row_for",
]

V = TypeVar("V")


class StandardsError(ValueError):
    """A standards lookup failed (unknown designation, size out of the table)."""


class UnknownSize(StandardsError, KeyError):
    """The key is not in the table; the message lists the known keys."""

    def __str__(self) -> str:  # KeyError would repr() the message
        return str(self.args[0]) if self.args else ""


class OutOfRange(StandardsError):
    """A numeric size is outside the range a standard covers."""


def lookup(table: Mapping[str, V], key: Any, what: str) -> V:
    """``table[key]`` or :class:`UnknownSize` naming ``what`` and the closest keys."""
    k = str(key).strip()
    if k in table:
        return table[k]
    # Tolerate case for designations like "m6" vs "M6" only when unambiguous.
    folded = {str(t).lower(): t for t in table}
    if k.lower() in folded and len(folded) == len(table):
        return table[folded[k.lower()]]
    close = difflib.get_close_matches(k, [str(t) for t in table], n=3, cutoff=0.5)
    hint = f" Did you mean {', '.join(close)}?" if close else ""
    known = ", ".join(str(t) for t in table)
    raise UnknownSize(f"Unknown {what} {key!r}.{hint} Known: {known}")


_METRIC = re.compile(r"^\s*M\s*(\d+(?:\.\d+)?)(?:\s*[xX×]\s*(\d+(?:\.\d+)?))?\s*$")


def metric_diameter(size: Any) -> Tuple[float, float | None]:
    """``"M6"`` -> (6.0, None); ``"M10x1.25"`` -> (10.0, 1.25); ``6`` -> (6.0, None)."""
    if isinstance(size, (int, float)) and not isinstance(size, bool):
        return float(size), None
    m = _METRIC.match(str(size))
    if not m:
        raise UnknownSize(
            f"Not a metric thread designation: {size!r} (expected 'M6' or 'M10x1.25')"
        )
    return float(m.group(1)), (float(m.group(2)) if m.group(2) else None)


def range_index(size: float, bounds: Sequence[float], what: str) -> int:
    """Index ``i`` with ``bounds[i] < size <= bounds[i + 1]`` (ISO "over / up to and
    including" ranges; the first range also includes its lower bound when it is 0)."""
    s = float(size)
    if s <= 0 or s > bounds[-1] or (bounds[0] > 0 and s <= bounds[0]):
        raise OutOfRange(
            f"{what}: size {size:g} mm is outside the table"
            f" ({bounds[0]:g} < size <= {bounds[-1]:g} mm)"
        )
    for i in range(len(bounds) - 1):
        if s <= bounds[i + 1]:
            return i
    raise OutOfRange(
        f"{what}: size {size:g} mm is outside the table"
    )  # pragma: no cover


def row_for(size: float, rows: Iterable[Tuple[float, float, V]], what: str) -> V:
    """The value of the ``(over, up_to_including, value)`` row containing ``size``."""
    s = float(size)
    rows = list(rows)
    for lo, hi, value in rows:
        if lo < s <= hi:
            return value
    raise OutOfRange(
        f"{what}: {s:g} mm is outside the table ({rows[0][0]:g} .. {rows[-1][1]:g} mm)"
    )
