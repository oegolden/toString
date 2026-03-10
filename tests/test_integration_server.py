"""
Simple pytest-based integration tests for client ↔ server.

These tests start the real server in a subprocess, use client.py to talk to it,
and then shut the server down. They are intentionally small and fast.
"""

import subprocess
import sys
import time

import pytest

import client


@pytest.fixture(scope="module")
def running_server():
    """Start the real server on port 9999 for the duration of this module."""
    proc = subprocess.Popen(
        [sys.executable, "server.py", "9999"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Give the server a moment to start listening.
    time.sleep(1.5)

    try:
        yield
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def test_login_and_get_boards(running_server):
    """
    Connect to the server, log in as alice, and fetch boards.

    This keeps the assertions simple but still verifies that the basic
    client/server path works end-to-end.
    """
    client.connect("127.0.0.1", 9999)
    try:
        # Login should succeed and return expected user info.
        user = client.login("alice", "pass123")
        assert user["username"] == "alice"
        assert user["role"] == "user"

        # Getting all boards should return a non-empty list.
        boards = client.get_all_boards()
        assert isinstance(boards, list)
        assert len(boards) > 0
    finally:
        client.disconnect()

