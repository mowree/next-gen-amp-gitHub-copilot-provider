"""
Tests for Loop Controller (F-011).

Contract: SDK boundary control
Feature: specs/features/F-011-loop-controller.md

Acceptance Criteria:
- AC-1: LoopController tracks turn count
- AC-2: Circuit breaker trips at max_turns
- AC-3: Abort callback invoked once only
- AC-4: should_abort() returns True after trip
- AC-5: Default max_turns is 3
"""

from unittest.mock import MagicMock


class TestLoopState:
    """LoopState tracks loop progress."""

    def test_loop_state_class_exists(self) -> None:
        from amplifier_module_provider_github_copilot.sdk_adapter.loop_control import LoopState

        assert LoopState is not None

    def test_initial_turn_count_is_zero(self) -> None:
        from amplifier_module_provider_github_copilot.sdk_adapter.loop_control import LoopState

        state = LoopState()
        assert state.turn_count == 0

    def test_first_turn_captured_initially_false(self) -> None:
        from amplifier_module_provider_github_copilot.sdk_adapter.loop_control import LoopState

        state = LoopState()
        assert state.first_turn_captured is False

    def test_abort_requested_initially_false(self) -> None:
        from amplifier_module_provider_github_copilot.sdk_adapter.loop_control import LoopState

        state = LoopState()
        assert state.abort_requested is False

    def test_elapsed_seconds_property(self) -> None:
        from amplifier_module_provider_github_copilot.sdk_adapter.loop_control import LoopState

        state = LoopState()
        elapsed = state.elapsed_seconds
        assert elapsed >= 0.0
        assert elapsed < 5.0  # Should complete in under 5 seconds

    def test_error_field_initially_none(self) -> None:
        from amplifier_module_provider_github_copilot.sdk_adapter.loop_control import LoopState

        state = LoopState()
        assert state.error is None


class TestLoopExitMethod:
    """LoopExitMethod enum exists."""

    def test_loop_exit_method_exists(self) -> None:
        from amplifier_module_provider_github_copilot.sdk_adapter.loop_control import LoopExitMethod

        assert LoopExitMethod is not None

    def test_has_abort_value(self) -> None:
        from amplifier_module_provider_github_copilot.sdk_adapter.loop_control import LoopExitMethod

        assert LoopExitMethod.ABORT.value == "abort"

    def test_has_disconnect_value(self) -> None:
        from amplifier_module_provider_github_copilot.sdk_adapter.loop_control import LoopExitMethod

        assert LoopExitMethod.DISCONNECT.value == "disconnect"


class TestLoopControllerInit:
    """LoopController initialization."""

    def test_class_exists(self) -> None:
        from amplifier_module_provider_github_copilot.sdk_adapter.loop_control import LoopController

        assert LoopController is not None

    def test_default_max_turns_is_3(self) -> None:
        """AC-5: Default max_turns is 3."""
        from amplifier_module_provider_github_copilot.sdk_adapter.loop_control import LoopController

        controller = LoopController()
        assert controller.max_turns == 3

    def test_custom_max_turns(self) -> None:
        from amplifier_module_provider_github_copilot.sdk_adapter.loop_control import LoopController

        controller = LoopController(max_turns=5)
        assert controller.max_turns == 5

    def test_default_state_is_fresh(self) -> None:
        from amplifier_module_provider_github_copilot.sdk_adapter.loop_control import LoopController

        controller = LoopController()
        assert controller.state.turn_count == 0
        assert controller.state.abort_requested is False

    def test_max_turns_zero_is_valid(self) -> None:
        """Edge case: max_turns=0 should be accepted."""
        from amplifier_module_provider_github_copilot.sdk_adapter.loop_control import LoopController

        controller = LoopController(max_turns=0)
        assert controller.max_turns == 0


class TestOnTurnStart:
    """AC-1: on_turn_start() increments turn count and enforces circuit breaker."""

    def test_increments_turn_count(self) -> None:
        """AC-1: Turn count increments on each call."""
        from amplifier_module_provider_github_copilot.sdk_adapter.loop_control import LoopController

        controller = LoopController(max_turns=5)
        controller.on_turn_start()
        assert controller.state.turn_count == 1

        controller.on_turn_start()
        assert controller.state.turn_count == 2

    def test_returns_true_when_under_limit(self) -> None:
        from amplifier_module_provider_github_copilot.sdk_adapter.loop_control import LoopController

        controller = LoopController(max_turns=3)
        result = controller.on_turn_start()  # turn 1
        assert result is True

        result = controller.on_turn_start()  # turn 2
        assert result is True

        result = controller.on_turn_start()  # turn 3
        assert result is True

    def test_returns_false_when_over_limit(self) -> None:
        """AC-2: Circuit breaker trips at max_turns."""
        from amplifier_module_provider_github_copilot.sdk_adapter.loop_control import LoopController

        controller = LoopController(max_turns=3)
        controller.on_turn_start()  # turn 1
        controller.on_turn_start()  # turn 2
        controller.on_turn_start()  # turn 3
        result = controller.on_turn_start()  # turn 4 - trips breaker

        assert result is False

    def test_sets_abort_when_over_limit(self) -> None:
        """AC-2: abort_requested becomes True when breaker trips."""
        from amplifier_module_provider_github_copilot.sdk_adapter.loop_control import LoopController

        controller = LoopController(max_turns=1)
        controller.on_turn_start()  # turn 1 - ok
        controller.on_turn_start()  # turn 2 - trips breaker

        assert controller.state.abort_requested is True

    def test_max_turns_zero_trips_on_first_turn(self) -> None:
        """Edge case: max_turns=0 means first turn triggers abort."""
        from amplifier_module_provider_github_copilot.sdk_adapter.loop_control import LoopController

        controller = LoopController(max_turns=0)
        result = controller.on_turn_start()  # turn 1 > 0

        assert result is False
        assert controller.state.abort_requested is True


class TestAbortCallback:
    """AC-3: Abort callback invoked once only."""

    def test_callback_invoked_on_circuit_trip(self) -> None:
        from amplifier_module_provider_github_copilot.sdk_adapter.loop_control import LoopController

        callback = MagicMock()
        controller = LoopController(max_turns=1)
        controller.set_abort_callback(callback)

        controller.on_turn_start()  # turn 1 - ok
        controller.on_turn_start()  # turn 2 - trips

        callback.assert_called_once()

    def test_callback_invoked_only_once_on_multiple_trips(self) -> None:
        """AC-3: Callback invoked only once even if circuit trips repeatedly."""
        from amplifier_module_provider_github_copilot.sdk_adapter.loop_control import LoopController

        callback = MagicMock()
        controller = LoopController(max_turns=1)
        controller.set_abort_callback(callback)

        controller.on_turn_start()  # turn 1
        controller.on_turn_start()  # turn 2 - trips
        controller.on_turn_start()  # turn 3 - already tripped
        controller.on_turn_start()  # turn 4 - already tripped

        callback.assert_called_once()

    def test_callback_that_raises_is_silenced(self) -> None:
        """Edge case: Abort callback raises -> log, don't re-raise."""
        from amplifier_module_provider_github_copilot.sdk_adapter.loop_control import LoopController

        def raising_callback() -> None:
            raise RuntimeError("callback exploded")

        controller = LoopController(max_turns=0)
        controller.set_abort_callback(raising_callback)

        # Should not raise even though callback raises
        controller.on_turn_start()  # trips immediately

    def test_request_abort_invokes_callback(self) -> None:
        from amplifier_module_provider_github_copilot.sdk_adapter.loop_control import LoopController

        callback = MagicMock()
        controller = LoopController(max_turns=10)
        controller.set_abort_callback(callback)

        controller.request_abort("test abort")

        callback.assert_called_once()
        assert controller.state.abort_requested is True

    def test_request_abort_callback_only_once(self) -> None:
        """Multiple request_abort calls only fire callback once."""
        from amplifier_module_provider_github_copilot.sdk_adapter.loop_control import LoopController

        callback = MagicMock()
        controller = LoopController(max_turns=10)
        controller.set_abort_callback(callback)

        controller.request_abort("first")
        controller.request_abort("second")

        callback.assert_called_once()


class TestShouldAbort:
    """AC-4: should_abort() returns True after trip."""

    def test_should_abort_false_initially(self) -> None:
        from amplifier_module_provider_github_copilot.sdk_adapter.loop_control import LoopController

        controller = LoopController()
        assert controller.should_abort() is False

    def test_should_abort_true_after_circuit_trip(self) -> None:
        """AC-4: should_abort() returns True after circuit breaker trips."""
        from amplifier_module_provider_github_copilot.sdk_adapter.loop_control import LoopController

        controller = LoopController(max_turns=1)
        controller.on_turn_start()  # turn 1 - ok
        controller.on_turn_start()  # turn 2 - trips

        assert controller.should_abort() is True

    def test_should_abort_true_after_request_abort(self) -> None:
        from amplifier_module_provider_github_copilot.sdk_adapter.loop_control import LoopController

        controller = LoopController(max_turns=10)
        controller.request_abort("external signal")

        assert controller.should_abort() is True


class TestSetAbortCallback:
    """set_abort_callback() wires up callback correctly."""

    def test_set_abort_callback_is_callable(self) -> None:
        from amplifier_module_provider_github_copilot.sdk_adapter.loop_control import LoopController

        controller = LoopController()
        assert callable(controller.set_abort_callback)

    def test_no_callback_does_not_raise_on_trip(self) -> None:
        """If no callback set, circuit trip should still work silently."""
        from amplifier_module_provider_github_copilot.sdk_adapter.loop_control import LoopController

        controller = LoopController(max_turns=0)
        # No callback set - should not raise
        controller.on_turn_start()  # trips immediately
        assert controller.should_abort() is True
