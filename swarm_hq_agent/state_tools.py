from __future__ import annotations

from typing import Iterable

from google.adk.tools.tool_context import ToolContext


def read_team_context(keys: Iterable[str], tool_context: ToolContext) -> dict[str, str]:
    """
    Read specific keys from session state for coordinator synthesis.
    Returns a dict of {key: value_as_string} for present keys.
    """
    out: dict[str, str] = {}
    for k in keys:
        if k in tool_context.state:
            v = tool_context.state[k]
            out[k] = v if isinstance(v, str) else str(v)
    return out

