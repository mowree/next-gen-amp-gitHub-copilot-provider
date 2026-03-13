"""
Tool parsing module.

Extracts tool calls from SDK response and returns kernel ToolCall types.

Contract: provider-protocol.md (parse_tool_calls method)
Feature: F-004, F-037

F-037 additions:
- WARNING log for empty tool arguments (LLM may have hallucinated)
"""

import json
import logging
from dataclasses import dataclass
from typing import Any, Protocol

logger = logging.getLogger(__name__)


@dataclass
class ToolCall:
    """
    Tool call extracted from LLM response.

    Contract: provider-protocol.md (E3 correction)

    NOTE: Uses `arguments` not `input` per kernel contract.

    Attributes:
        id: Unique identifier for this tool call.
        name: Name of the tool to invoke.
        arguments: Parsed arguments as a dictionary.
    """

    id: str
    name: str
    arguments: dict[str, Any]


class HasToolCalls(Protocol):
    """Protocol for objects that may contain tool calls."""

    @property
    def tool_calls(self) -> list[Any] | None: ...


def parse_tool_calls(response: Any) -> list[ToolCall]:
    """
    Extract tool calls from response.

    Contract: provider-protocol.md

    - MUST return ToolCall with `arguments` field (not `input`)
    - MUST handle empty/missing tool_calls gracefully
    - MUST parse JSON string arguments if needed

    Args:
        response: ChatResponse or any object with tool_calls attribute

    Returns:
        List of ToolCall objects (may be empty)

    Raises:
        ValueError: If tool call has invalid JSON arguments
    """
    tool_calls = getattr(response, "tool_calls", None)

    if not tool_calls:
        return []

    result: list[ToolCall] = []
    for tc in tool_calls:
        # Get arguments - handle both dict and string
        args = getattr(tc, "arguments", {})
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in tool call arguments: {e}") from e

        tool_id = getattr(tc, "id", "")
        tool_name = getattr(tc, "name", "")

        # F-037: Warn on empty arguments (LLM may have hallucinated)
        # Note: Only warn for explicit empty dict {}, not for None
        if args == {}:
            logger.warning(
                "[TOOL_PARSING] Empty arguments for tool '%s' (id=%s) - LLM may have hallucinated",
                tool_name,
                tool_id,
            )

        result.append(
            ToolCall(
                id=tool_id,
                name=tool_name,
                arguments=args,
            )
        )

    return result
