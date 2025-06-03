"""
Finite-state machine for the journalist sequence.
Add / tweak timings or states as your workflow evolves.
"""

from __future__ import annotations

import os
from enum import Enum
from typing import Literal, Tuple


# ────────────────────────────────────────────────────────────────────
# 1)  States
# ────────────────────────────────────────────────────────────────────
class State(str, Enum):
    NEW = "NEW"  # never contacted yet
    E1_SENT = "E1_SENT"  # initial pitch
    R1C_SENT = "R1C_SENT"  # 1st follow-up (clip)
    R2C_SENT = "R2C_SENT"  # 2nd follow-up (explicit)
    R2CS_SENT = "R2CS_SENT"  # soft-close
    REPLIED = "REPLIED"  # positive reply → we sent R1s/R2s
    STOPPED = "STOPPED"  # dead end (negative reply / OOO / bounce)


TerminalState = Literal[State.REPLIED, State.STOPPED]


# ────────────────────────────────────────────────────────────────────
# 2)  Static maps
# ────────────────────────────────────────────────────────────────────
# Which e-mail template to send when a timer fires in *this* state
_NEXT_TEMPLATE: dict[State, str] = {
    State.NEW: "E1",
    State.E1_SENT: "R1c",
    State.R1C_SENT: "R2c",
    State.R2C_SENT: "R2cs",
}

# Hours to wait once we *enter* the given state
_WAIT_HOURS: dict[State, int] = {
    State.E1_SENT: 48,  # 2 days → R1c
    State.R1C_SENT: 72,  # 3 days → R2c
    State.R2C_SENT: 72,  # 3 days → R2cs
    State.R2CS_SENT: 99999,  # effectively “never”
}

# Subjects (Python str.format-able)
_SUBJECTS = {
    "E1": "Quick question re your {publication} piece",
    "R1c": "Following up on my last note",
    "R2c": "Another angle you might like",
    "R2cs": "One last resource for your story",
    # Reply-triggered templates (sent inside webhook logic)
    "R1s": "Materials you asked for",
    "R2s": "Data & methodology inside",
}


# ────────────────────────────────────────────────────────────────────
# 3)  Public helpers (used by scheduler + webhook)
# ────────────────────────────────────────────────────────────────────
def pick_template(state: State) -> str:
    """Return the template code the scheduler should send *now*."""
    return _NEXT_TEMPLATE[state]


def subject_for(template_code: str, **merge_tags) -> str:
    """Resolve merge-tags into the subject line."""
    return _SUBJECTS[template_code].format(**merge_tags)


def advance(
    state: State,
    signal: Literal["timer", "reply_positive", "reply_negative", "reply_ooo"],
) -> Tuple[State, int]:
    """
    Given current state + external signal, return (new_state, wait_hours).
    wait_hours == 0 for terminal states → scheduler will ignore them.
    """

    # ─── Positive reply → REPLIED (webhook may send R1s/R2s instantly) ───
    if signal == "reply_positive":
        return State.REPLIED, 0

    # ─── Negative / OOO reply → STOPPED ──────────────────────────────────
    if signal in {"reply_negative", "reply_ooo"}:
        return State.STOPPED, 0

    # ─── Timer fired → straight-line progression ────────────────────────
    if signal == "timer":
        next_state = {
            State.NEW: State.E1_SENT,
            State.E1_SENT: State.R1C_SENT,
            State.R1C_SENT: State.R2C_SENT,
            State.R2C_SENT: State.R2CS_SENT,
        }[state]
        return next_state, _WAIT_HOURS.get(next_state, 0)

    # Anything else is a programming error
    raise ValueError(f"Unhandled transition: {state=} {signal=}")


if os.getenv("FAST_TEST"):
    _WAIT_HOURS.update(
        {State.E1_SENT: 0.001, State.R1C_SENT: 0.001, State.R2C_SENT: 0.001}  # 3.6 s
    )
