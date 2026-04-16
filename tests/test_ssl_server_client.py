import subprocess
import sys
import os
import pytest
import socket
import time
import ssl
SERVER_IP = '127.0.0.1'
SERVER_PORT = 23456  # Use a test port

# Paths to test cert and key (must exist for test to run)
CERTFILE = 'server.crt'
KEYFILE = 'server.key'

@pytest.fixture(scope="module")
def start_test_server():
    # Start the server in a subprocess
    server_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    proc = subprocess.Popen([
        sys.executable, 'server.py', str(SERVER_PORT)
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=server_dir)
    # Wait for server to start (retry loop)
    max_attempts = 10
    for attempt in range(max_attempts):
        try:
            test_sock = socket.create_connection((SERVER_IP, SERVER_PORT), timeout=1)
            test_sock.close()
            break
        except (ConnectionRefusedError, OSError):
            time.sleep(0.5)
    else:
        out, err = proc.communicate(timeout=2)
        print('SERVER STDOUT:', out.decode(errors='ignore'))
        print('SERVER STDERR:', err.decode(errors='ignore'))
        proc.terminate()
        proc.wait()
        raise RuntimeError("Server did not start in time for SSL test")
    yield
    proc.terminate()
    proc.wait()


def test_ssl_connection(start_test_server):
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    with socket.create_connection((SERVER_IP, SERVER_PORT)) as sock:
        with context.wrap_socket(sock, server_hostname=SERVER_IP) as ssock:
            # Send a dummy command and expect an error or valid response
            ssock.send(b'LOGIN alice pass123')
            data = ssock.recv(4096)
            assert data, "No response from server over SSL"
            # Should be JSON or ERROR
            response = data.decode('utf-8')
            assert response.startswith('{') or response.startswith('ERROR'), f"Unexpected response: {response}"
