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
    """Login succeeds and LIST_BOARDS returns a non-empty list."""
    client.connect("127.0.0.1", 9999)
    try:
        user = client.login("alice", "pass123")
        assert user["username"] == "alice"
        assert user["role"] == "user"

        boards = client.get_all_boards()
        assert isinstance(boards, list)
        assert len(boards) > 0
    finally:
        client.logout("alice")
        client.disconnect()


def test_duplicate_login_rejected(running_server):
    """A second login attempt while already logged in is rejected."""
    client.connect("127.0.0.1", 9999)
    try:
        client.login("alice", "pass123")
        with pytest.raises(Exception, match="already logged in"):
            client.login("alice", "pass123")
    finally:
        client.logout("alice")
        client.disconnect()


def test_wrong_password_does_not_lock_account(running_server):
    """A failed login (wrong password) must not prevent a subsequent correct login."""
    client.connect("127.0.0.1", 9999)
    try:
        with pytest.raises(Exception, match="Invalid password"):
            client.login("alice", "wrongpassword")
        # Account must still be accessible with the correct password.
        user = client.login("alice", "pass123")
        assert user["username"] == "alice"
    finally:
        client.logout("alice")
        client.disconnect()

