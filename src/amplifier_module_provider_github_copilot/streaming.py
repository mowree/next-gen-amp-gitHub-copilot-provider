"""Event translation / streaming module. Contract: event-vocabulary.md"""

import fnmatch
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import yaml

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


@dataclass
class EventConfig:
    """Configuration for event translation."""

    bridge_mappings: dict[str, tuple[DomainEventType, str | None]]
    consume_patterns: list[str]
    drop_patterns: list[str]


def load_event_config(config_path: str | None = None) -> EventConfig:
    """Load event classification config from YAML. Defaults to config/events.yaml."""
    if config_path is None:
        package_root = Path(__file__).parent.parent.parent
        config_path = str(package_root / "config" / "events.yaml")

    with open(config_path) as f:
        raw = yaml.safe_load(f)

    classifications = raw.get("event_classifications", {})

    bridge_mappings: dict[str, tuple[DomainEventType, str | None]] = {}
    for mapping in classifications.get("bridge", []):
        sdk_type = mapping["sdk_type"]
        domain_type = DomainEventType[mapping["domain_type"]]
        bridge_mappings[sdk_type] = (domain_type, mapping.get("block_type"))

    return EventConfig(
        bridge_mappings=bridge_mappings,
        consume_patterns=classifications.get("consume", []),
        drop_patterns=classifications.get("drop", []),
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
    return DomainEvent(
        type=domain_type,
        data=_extract_event_data(sdk_event),
        block_type=block_type,
    )
