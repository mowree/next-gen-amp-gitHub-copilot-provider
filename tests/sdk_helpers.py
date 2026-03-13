"""SDK integration test helper functions.

These helpers handle the reality that SDK events may be dicts OR typed objects,
and that SDK versions may change field names or structures.
"""

from typing import Any, cast


def get_event_type(event: Any) -> str:
    """Extract event type from SDK event (handles dict or object).

    SDK events may be:
    - dict with "type" key
    - object with "type" attribute
    - object with "event_type" attribute
    """
    if isinstance(event, dict):
        event_dict = cast(dict[str, Any], event)
        return str(event_dict.get("type", "unknown"))
    result: str = getattr(event, "type", getattr(event, "event_type", "unknown"))
    return result


def get_event_field(event: Any, field: str) -> Any:
    """Extract field from SDK event (handles dict or object).

    Args:
        event: SDK event (dict or typed object)
        field: Field name to extract

    Returns:
        Field value or None if not found
    """
    if isinstance(event, dict):
        return event.get(field)
    return getattr(event, field, None)


def describe_event(event: Any) -> str:
    """Human-readable description of an SDK event for debugging.

    Useful for test failure messages and drift detection.
    """
    if isinstance(event, dict):
        return str(event)
    cls = type(event).__name__
    try:
        attrs = {k: v for k, v in vars(event).items() if not k.startswith("_")}
        return f"{cls}({attrs})"
    except TypeError:
        # Some objects don't support vars()
        return f"{cls}(<non-inspectable>)"


def collect_event_types(events: list[Any]) -> list[str]:
    """Extract event types from a list of SDK events.

    Args:
        events: List of SDK events

    Returns:
        List of event type strings
    """
    return [get_event_type(e) for e in events]


def has_event_type(events: list[Any], event_type: str) -> bool:
    """Check if any event in the list has the given type.

    Args:
        events: List of SDK events
        event_type: Event type to search for

    Returns:
        True if at least one event has the type
    """
    return event_type in collect_event_types(events)


def count_event_type(events: list[Any], event_type: str) -> int:
    """Count events of a specific type.

    Args:
        events: List of SDK events
        event_type: Event type to count

    Returns:
        Number of events with that type
    """
    return collect_event_types(events).count(event_type)
