"""
conftest.py — Pytest fixtures for .toString(object) test suite.

Provides shared fixtures and setup for all tests.
"""

import sys
import os
import pytest

# Add project root to path so we can import mock_client
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import mock_client


@pytest.fixture(autouse=True)
def reset_state():
    """Reset mock state before every test so tests stay independent."""
    mock_client.reset_test_state()
