"""Interface types stdlib adds to the foundation vocabulary, with their rules.

Foundation ships the core types (``ScrewHole``, ``Shaft``, ``BearingSeat``,
``TSlot``...). Catalogue families that need a mating site foundation does not
have declare it here, the same way any library may
(:mod:`cadbuildr.foundation.interfaces.types`): subclass ``Interface`` and
register a ``mate_rule``. Importing a stdlib part module imports this one, so
``assembly.connect`` knows the rules whenever the parts exist.

* ``InsertPocket(size)`` (female, a blind hole sized for a heat-set insert,
  +Z out of the face) <-> ``InsertBody(size)`` (the insert's top face, +Z
  out of it): rigid, flush (same +Z).
* ``RailTrack(series)`` (a profile rail's datum: bottom centre, +Z along the
  rail, +X up) <-> ``RailBlock(series)`` (a carriage's datum, same frame):
  slider — the carriage runs along the rail (``offset``).
"""

from __future__ import annotations

from cadbuildr.foundation.interfaces import Interface, mate_rule

__all__ = [
    "InsertBody",
    "InsertPocket",
    "RailBlock",
    "RailTrack",
]


class InsertPocket(Interface):
    """Mouth of a pocket for a heat-set / press-fit threaded insert (+Z out
    of the face, the pocket along -Z)."""

    PARAMS = ("size", "depth")
    ROLE = "female"
    AXISYMMETRIC = True


class InsertBody(Interface):
    """Top face of a threaded insert (+Z out of it; it sits flush)."""

    PARAMS = ("size",)
    ROLE = "male"
    AXISYMMETRIC = True


class RailTrack(Interface):
    """Datum of a profile (miniature) linear rail: bottom centre at the rail
    start, +Z along the rail, +X up out of the mounting face."""

    PARAMS = ("series",)
    ROLE = "female"


class RailBlock(Interface):
    """Datum of a rail carriage, in the rail's frame (bottom of the rail,
    +Z along the rail, +X up): a block on its rail shares the frame."""

    PARAMS = ("series",)
    ROLE = "male"


@mate_rule(InsertBody, InsertPocket, flip=False, equal=["size"])
def insert_in_pocket(body, pocket, ctx):
    """A threaded insert pressed flush into its pocket."""
    return None


@mate_rule(RailBlock, RailTrack, joint="slider", flip=False, equal=["series"])
def carriage_on_rail(block, track, ctx):
    """A carriage runs along its rail (offset along the rail)."""
    return None
