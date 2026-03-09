"""
Event translation / streaming module.

Config-driven event classification: BRIDGE/CONSUME/DROP.

Contract: event-vocabulary.md
"""

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

    BRIDGE = "bridge"  # Translate to domain event
    CONSUME = "consume"  # Process internally
    DROP = "drop"  # Ignore


@dataclass
class DomainEvent:
    """
    Domain event emitted from SDK event translation.

    Contract: event-vocabulary.md
    """

    type: DomainEventType
    data: dict[str, Any] = field(default_factory=lambda: {})
    block_type: str | None = None  # For CONTENT_DELTA: TEXT, THINKING


@dataclass
class AccumulatedResponse:
    """
    Accumulated response from streaming events.

    Contract: streaming-contract.md
    """

    text_content: str = ""
    thinking_content: str = ""
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    usage: dict[str, Any] | None = None
    finish_reason: str | None = None
    error: dict[str, Any] | None = None
    is_complete: bool = False


class StreamingAccumulator:
    """
    Accumulates streaming domain events into final response.

    Contract: streaming-contract.md

    Usage:
        accumulator = StreamingAccumulator()
        for event in domain_events:
            accumulator.add(event)
        result = accumulator.get_result()
    """

    def __init__(self) -> None:
        """Initialize empty accumulator."""
        self._text_content: str = ""
        self._thinking_content: str = ""
        self._tool_calls: list[dict[str, Any]] = []
        self._usage: dict[str, Any] | None = None
        self._finish_reason: str | None = None
        self._error: dict[str, Any] | None = None
        self._is_complete: bool = False

    def add(self, event: DomainEvent) -> None:
        """
        Add domain event to accumulator.

        Contract:
        - CONTENT_DELTA with TEXT block_type -> append to text_content
        - CONTENT_DELTA with THINKING block_type -> append to thinking_content
        - TOOL_CALL -> append to tool_calls
        - USAGE_UPDATE -> update usage
        - TURN_COMPLETE -> set finish_reason, mark complete
        - ERROR -> set error, mark complete

        Args:
            event: Domain event from translate_event()
        """
        if event.type == DomainEventType.CONTENT_DELTA:
            text = event.data.get("text", "")
            if event.block_type == "THINKING":
                self._thinking_content += text
            else:  # TEXT or None
                self._text_content += text

        elif event.type == DomainEventType.TOOL_CALL:
            self._tool_calls.append(event.data)

        elif event.type == DomainEventType.USAGE_UPDATE:
            self._usage = event.data

        elif event.type == DomainEventType.TURN_COMPLETE:
            self._finish_reason = event.data.get("finish_reason", "stop")
            self._is_complete = True

        elif event.type == DomainEventType.ERROR:
            self._error = event.data
            self._is_complete = True

    def get_result(self) -> AccumulatedResponse:
        """
        Get accumulated response.

        Returns:
            AccumulatedResponse with all accumulated data.
        """
        return AccumulatedResponse(
            text_content=self._text_content,
            thinking_content=self._thinking_content,
            tool_calls=self._tool_calls,
            usage=self._usage,
            finish_reason=self._finish_reason,
            error=self._error,
            is_complete=self._is_complete,
        )

    @property
    def is_complete(self) -> bool:
        """True if TURN_COMPLETE or ERROR received."""
        return self._is_complete


@dataclass
class EventConfig:
    """Configuration for event translation."""

    bridge_mappings: dict[str, tuple[DomainEventType, str | None]]
    consume_patterns: list[str]
    drop_patterns: list[str]


def load_event_config(config_path: str | None = None) -> EventConfig:
    """
    Load event classification config from YAML.

    Args:
        config_path: Path to config file. Defaults to config/events.yaml.

    Returns:
        EventConfig with parsed mappings and patterns.
    """
    if config_path is None:
        # Default path relative to package root
        package_root = Path(__file__).parent.parent.parent
        config_path = str(package_root / "config" / "events.yaml")

    with open(config_path) as f:
        raw = yaml.safe_load(f)

    classifications = raw.get("event_classifications", {})

    # Parse bridge mappings
    bridge_mappings: dict[str, tuple[DomainEventType, str | None]] = {}
    for mapping in classifications.get("bridge", []):
        sdk_type = mapping["sdk_type"]
        domain_type = DomainEventType[mapping["domain_type"]]
        block_type = mapping.get("block_type")
        bridge_mappings[sdk_type] = (domain_type, block_type)

    # Parse consume patterns
    consume_patterns = classifications.get("consume", [])

    # Parse drop patterns
    drop_patterns = classifications.get("drop", [])

    return EventConfig(
        bridge_mappings=bridge_mappings,
        consume_patterns=consume_patterns,
        drop_patterns=drop_patterns,
    )


def _matches_pattern(event_type: str, patterns: list[str]) -> bool:
    """Check if event type matches any pattern (supports wildcards)."""
    return any(fnmatch.fnmatch(event_type, p) for p in patterns)


def classify_event(sdk_event_type: str, config: EventConfig) -> EventClassification:
    """
    Classify SDK event type using config.

    Args:
        sdk_event_type: The SDK event type string.
        config: Event classification config.

    Returns:
        EventClassification (BRIDGE, CONSUME, or DROP).
    """
    # Check bridge first (exact match)
    if sdk_event_type in config.bridge_mappings:
        return EventClassification.BRIDGE

    # Check consume patterns
    if _matches_pattern(sdk_event_type, config.consume_patterns):
        return EventClassification.CONSUME

    # Check drop patterns
    if _matches_pattern(sdk_event_type, config.drop_patterns):
        return EventClassification.DROP

    # Unknown events: log warning, drop
    logger.warning(f"Unknown SDK event type: {sdk_event_type}")
    return EventClassification.DROP


def _extract_event_data(sdk_event: dict[str, Any]) -> dict[str, Any]:
    """Extract data from SDK event dict."""
    return {k: v for k, v in sdk_event.items() if k != "type"}


def translate_event(sdk_event: dict[str, Any], config: EventConfig) -> DomainEvent | None:
    """
    Translate SDK event to domain event.

    Contract: event-vocabulary.md

    - BRIDGE events → DomainEvent
    - CONSUME events → None (processed internally)
    - DROP events → None (ignored)

    Args:
        sdk_event: Raw SDK event as dict with 'type' key.
        config: Event classification config.

    Returns:
        DomainEvent if BRIDGE, None otherwise.
    """
    event_type: str = str(sdk_event.get("type", ""))

    classification = classify_event(event_type, config)

    if classification == EventClassification.DROP:
        return None

    if classification == EventClassification.CONSUME:
        # Could process internally here if needed
        return None

    # BRIDGE: translate to domain event
    domain_type, block_type = config.bridge_mappings[event_type]
    return DomainEvent(
        type=domain_type,
        data=_extract_event_data(sdk_event),
        block_type=block_type,
    )
