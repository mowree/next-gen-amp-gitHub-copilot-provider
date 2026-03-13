"""Event translation / streaming module. Contract: event-vocabulary.md

Feature: F-005, F-006, F-038

F-038: Kernel Type Migration
- Added to_chat_response() method that converts accumulated response to kernel ChatResponse
- Uses TextBlock/ThinkingBlock (Pydantic from message_models)
"""

import fnmatch
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from amplifier_core import ChatResponse

logger = logging.getLogger(__name__)


class DomainEventType(Enum):
    """Domain event types per event-vocabulary.md."""

    CONTENT_DELTA = "CONTENT_DELTA"
    TOOL_CALL = "TOOL_CALL"
    USAGE_UPDATE = "USAGE_UPDATE"
    TURN_COMPLETE = "TURN_COMPLETE"
    SESSION_IDLE = "SESSION_IDLE"
    ERROR = "ERROR"


class EventClassification(Enum):
    """How to handle SDK events."""

    BRIDGE = "bridge"
    CONSUME = "consume"
    DROP = "drop"


@dataclass
class DomainEvent:
    """Domain event emitted from SDK event translation."""

    type: DomainEventType
    data: dict[str, Any] = field(default_factory=lambda: {})
    block_type: str | None = None


@dataclass
class AccumulatedResponse:
    """Accumulated response from streaming events."""

    text_content: str = ""
    thinking_content: str = ""
    tool_calls: list[dict[str, Any]] = field(default_factory=lambda: [])
    usage: dict[str, Any] | None = None
    finish_reason: str | None = None
    error: dict[str, Any] | None = None
    is_complete: bool = False


@dataclass
class StreamingAccumulator:
    """Accumulates streaming domain events into final response."""

    text_content: str = ""
    thinking_content: str = ""
    tool_calls: list[dict[str, Any]] = field(default_factory=lambda: [])
    usage: dict[str, Any] | None = None
    finish_reason: str | None = None
    error: dict[str, Any] | None = None
    is_complete: bool = False

    def add(self, event: DomainEvent) -> None:
        """Add domain event to accumulator."""
        if event.type == DomainEventType.CONTENT_DELTA:
            text = event.data.get("text", "")
            if event.block_type == "THINKING":
                self.thinking_content += text
            else:
                self.text_content += text
        elif event.type == DomainEventType.TOOL_CALL:
            self.tool_calls.append(event.data)
        elif event.type == DomainEventType.USAGE_UPDATE:
            self.usage = event.data
        elif event.type == DomainEventType.TURN_COMPLETE:
            self.finish_reason = event.data.get("finish_reason", "stop")
            self.is_complete = True
        elif event.type == DomainEventType.ERROR:
            self.error = event.data
            self.is_complete = True

    def get_result(self) -> AccumulatedResponse:
        """Get accumulated response."""
        return AccumulatedResponse(
            text_content=self.text_content,
            thinking_content=self.thinking_content,
            tool_calls=self.tool_calls,
            usage=self.usage,
            finish_reason=self.finish_reason,
            error=self.error,
            is_complete=self.is_complete,
        )

    def to_chat_response(self) -> "ChatResponse":
        """Convert accumulated response to kernel ChatResponse.

        Feature: F-038

        IMPORTANT: Uses TextBlock/ThinkingBlock (Pydantic from message_models),
        NOT TextContent/ThinkingContent (dataclass from content_models).

        Returns:
            ChatResponse with content blocks, tool_calls, usage, and finish_reason.
        """
        from amplifier_core import (
            ChatResponse,
            TextBlock,
            ThinkingBlock,
            ToolCall,
            Usage,
        )

        content: list[TextBlock | ThinkingBlock] = []

        # Add text content using Pydantic TextBlock
        if self.text_content:
            content.append(TextBlock(text=self.text_content))

        # Add thinking content using Pydantic ThinkingBlock
        if self.thinking_content:
            content.append(ThinkingBlock(thinking=self.thinking_content))

        # Convert tool calls to kernel ToolCall
        tool_calls: list[ToolCall] | None = None
        if self.tool_calls:
            tool_calls = [
                ToolCall(
                    id=tc.get("id", ""),
                    name=tc.get("name", ""),
                    arguments=tc.get("arguments", {})
                    if isinstance(tc.get("arguments"), dict)
                    else {},
                )
                for tc in self.tool_calls
            ]

        # Convert usage - all three fields REQUIRED
        usage: Usage | None = None
        if self.usage:
            usage = Usage(
                input_tokens=self.usage.get("input_tokens", 0),
                output_tokens=self.usage.get("output_tokens", 0),
                total_tokens=self.usage.get("total_tokens", 0),
            )

        return ChatResponse(
            content=content,  # type: ignore[arg-type]
            tool_calls=tool_calls,
            usage=usage,
            finish_reason=self.finish_reason,
        )


def _empty_str_to_str_dict() -> dict[str, str]:
    """Factory for empty string-to-string dict."""
    return {}


@dataclass
class EventConfig:
    """Configuration for event translation."""

    bridge_mappings: dict[str, tuple[DomainEventType, str | None]] = field(
        default_factory=lambda: {}
    )
    consume_patterns: list[str] = field(default_factory=lambda: [])
    drop_patterns: list[str] = field(default_factory=lambda: [])
    finish_reason_map: dict[str, str] = field(default_factory=_empty_str_to_str_dict)


def load_event_config(config_path: str | Path | None = None) -> EventConfig:
    """Load event classification config from YAML. Defaults to config/events.yaml.

    AC-1 (F-021): Gracefully handles missing files by returning default config.
    """
    if config_path is None:
        package_root = Path(__file__).parent.parent.parent
        config_path = str(package_root / "config" / "events.yaml")

    path = Path(config_path)
    if not path.exists():
        return EventConfig()  # AC-1: Graceful fallback on missing file

    with open(config_path) as f:
        raw = yaml.safe_load(f)

    if not raw:
        return EventConfig()

    classifications = raw.get("event_classifications", {})

    bridge_mappings: dict[str, tuple[DomainEventType, str | None]] = {}
    for mapping in classifications.get("bridge", []):
        sdk_type = mapping["sdk_type"]
        domain_type = DomainEventType[mapping["domain_type"]]
        bridge_mappings[sdk_type] = (domain_type, mapping.get("block_type"))

    # Load finish_reason_map (AC-5)
    finish_reason_map = raw.get("finish_reason_map", {})

    return EventConfig(
        bridge_mappings=bridge_mappings,
        consume_patterns=classifications.get("consume", []),
        drop_patterns=classifications.get("drop", []),
        finish_reason_map=finish_reason_map,
    )


def _matches_pattern(event_type: str, patterns: list[str]) -> bool:
    """Check if event type matches any pattern (supports wildcards)."""
    return any(fnmatch.fnmatch(event_type, p) for p in patterns)


def classify_event(sdk_event_type: str, config: EventConfig) -> EventClassification:
    """Classify SDK event type using config."""
    if sdk_event_type in config.bridge_mappings:
        return EventClassification.BRIDGE
    if _matches_pattern(sdk_event_type, config.consume_patterns):
        return EventClassification.CONSUME
    if _matches_pattern(sdk_event_type, config.drop_patterns):
        return EventClassification.DROP
    logger.warning(f"Unknown SDK event type: {sdk_event_type}")
    return EventClassification.DROP


def _extract_event_data(sdk_event: dict[str, Any]) -> dict[str, Any]:
    """Extract data from SDK event dict."""
    return {k: v for k, v in sdk_event.items() if k != "type"}


def translate_event(sdk_event: dict[str, Any], config: EventConfig) -> DomainEvent | None:
    """Translate SDK event to domain event. Contract: event-vocabulary.md."""
    event_type: str = str(sdk_event.get("type", ""))
    classification = classify_event(event_type, config)

    if classification != EventClassification.BRIDGE:
        return None

    domain_type, block_type = config.bridge_mappings[event_type]
    data = _extract_event_data(sdk_event)

    # AC-5 (F-021): Apply finish_reason_map for TURN_COMPLETE events
    if domain_type == DomainEventType.TURN_COMPLETE and config.finish_reason_map:
        sdk_finish_reason = data.get("finish_reason", "")
        # Map SDK finish_reason to domain finish_reason, with fallback to _default
        mapped_reason = config.finish_reason_map.get(
            sdk_finish_reason,
            config.finish_reason_map.get("_default", sdk_finish_reason),
        )
        data["finish_reason"] = mapped_reason

    return DomainEvent(
        type=domain_type,
        data=data,
        block_type=block_type,
    )
