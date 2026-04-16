import ssl
import socket
import pytest
from .test_ssl_server_client import start_test_server

SERVER_IP = '127.0.0.1'
SERVER_PORT = 23456  # Use the same test port as server

@pytest.mark.usefixtures("start_test_server")
def test_client_ssl_connect():
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    with socket.create_connection((SERVER_IP, SERVER_PORT)) as sock:
        with context.wrap_socket(sock, server_hostname=SERVER_IP) as ssock:
            # Try sending a simple command
            ssock.send(b'LIST_BOARDS')
            data = ssock.recv(4096)
            assert data, "No response from server over SSL"
            response = data.decode('utf-8')
            assert response.startswith('[') or response.startswith('ERROR'), f"Unexpected response: {response}"
