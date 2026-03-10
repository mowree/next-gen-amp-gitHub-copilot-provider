#!/bin/bash
uv run pytest tests/test_session_factory.py tests/test_sdk_client.py -v --tb=short 2>&1
