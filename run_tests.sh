#!/bin/bash
uv run pytest tests/test_session_factory.py tests/test_deny_hook_breach_detector.py -v --tb=short 2>&1
