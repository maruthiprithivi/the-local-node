"""The four trap axes. An answer can look similar to the question and still be wrong.
Each axis is scored pass or fail on its own; they are never averaged together."""
from enum import Enum


class TrapAxis(str, Enum):
    FRESHNESS = "freshness"                       # access changed between two near identical asks
    IDENTITY_PERMISSION = "identity_permission"   # a different user asks, or a leaver asks through someone else
    ENTITY = "entity"                             # same ask, different employee ID
    MEANING_FLIP = "meaning_flip"                 # negation or a changed condition


TRAP_AXES = tuple(a.value for a in TrapAxis)

DESCRIPTIONS = {
    TrapAxis.FRESHNESS: "same ask, before and after a move",
    TrapAxis.IDENTITY_PERMISSION: "a different user, or a leaver asking",
    TrapAxis.ENTITY: "same ask, a different employee ID",
    TrapAxis.MEANING_FLIP: "negation or a changed condition",
}
