
import pytest
import client
import time
import threading
import sys
import importlib
from unittest.mock import MagicMock


TEST_USERNAME = "testuser_pwreset"
TEST_EMAIL = "ogolden@g.hmc.edu"
TEST_PASSWORD = "initialpass"
NEW_PASSWORD = "newpass123"

SERVER_PORT = 12345
server_thread = None
server_module = None


def setup_module(module):
    global server_thread, server_module
    # Start the server in a background thread
    def run_server():
        sys.argv = ["server.py", str(SERVER_PORT)]
        import server
        server.main()

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    # Wait for server to start
    time.sleep(1.5)
    # Import server module for test access
    server_module = importlib.import_module("server")
    # Connect client
    client.connect("127.0.0.1", SERVER_PORT)
    # Register the test user (ignore if already exists)
    try:
        client.register(TEST_USERNAME, TEST_PASSWORD)
    except Exception:
        pass


def teardown_module(module):
    client.disconnect()
    # Attempt to stop the server gracefully
    import socket
    try:
        # Connect and send 'close' to trigger server shutdown logic if implemented
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("127.0.0.1", SERVER_PORT))
        s.send(b"close")
        s.close()
    except Exception:
        pass
    time.sleep(1)

def test_send_recovery_email():
    # Should succeed and return a success message
    resp = client.send_recovery_email(TEST_USERNAME, TEST_EMAIL)
    assert resp["success"] is True
    assert "Recovery email sent" in resp["message"]

def test_reset_password(monkeypatch):
    # Mock the server's recovery code storage and sending
    # We assume the server is running in the same process or test environment
    # and _recovery_codes is accessible for test purposes
    fake_code = "FAKECODE1234567890"
    server_module._recovery_codes[TEST_USERNAME] = fake_code
    # No need to actually send email
    resp = client.reset_password(TEST_USERNAME, TEST_EMAIL, fake_code, NEW_PASSWORD)
    assert resp["success"] is True
    assert "Password reset successful" in resp["message"]
