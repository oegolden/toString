"""
client.py - Client side of the toString messaging application.

This file connects to the server and allows the user to send commands and receive responses. Integrates with
the gui.py file to provide a user-friendly interface for the client.
The client communicates with server.py using JSON.

Usage: python3 client.py <server IP> <server port>
"""

import socket
import json
import time

# server configuration
server_ip = '127.0.0.1'
server_port = 1234

# global socket
server_socket = None
MAX_BUFFER_SIZE = 8192

# SERVER PROCESSING ---------------------------------

def _send_request(command: str) -> str:
    """
    Send a command to the server and receive the response.
    Returns the raw response string.
    Raises Exception if the server returns an ERROR.
    """
    if server_socket is None:
        raise Exception("Not connected to server. Call connect() first.")
    
    try:
        server_socket.send(command.encode('utf-8'))
        response = server_socket.recv(MAX_BUFFER_SIZE).decode('utf-8')
        
        # Check for error response
        if response.startswith("ERROR"):
            raise Exception(response[6:].strip())  # Strip "ERROR " prefix
        
        return response
    except socket.error as e:
        raise Exception(f"Network error: {e}")


def _parse_json_response(response: str):
    """Parse a JSON response from the server."""
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        raise Exception(f"Invalid server response: {response}")


def connect(ip: str = server_ip, port: int = server_port):
    """
    Connect to the server. Must be called before any other operations.
    """
    global server_socket
    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.connect((ip, port))
    except socket.error as e:
        raise Exception(f"Failed to connect to server at {ip}:{port}: {e}")


def disconnect():
    """Disconnect from the server."""
    global server_socket
    if server_socket:
        try:
            server_socket.close()
        except:
            pass
        server_socket = None

# AUTHORIZATION FUNCTIONS ---------------------------------

def login(username: str, password: str) -> dict:
    """
    Attempt to log in with credentials.
    Returns user info dict with username and role on success.
    Raises Exception on failure.
    """
    command = f"LOGIN {username} {password}"
    response = _send_request(command)
    
    # Parse JSON response
    data = _parse_json_response(response)
    return {"username": data.get("username"), "role": data.get("role")}


def register(username: str, password: str) -> dict:
    """
    Register a new user account.
    Returns new user info dict with username and role on success.
    Raises Exception if username is taken or validation fails.
    """
    command = f"REGISTER {username} {password}"
    response = _send_request(command)
    
    # Parse JSON response
    data = _parse_json_response(response)
    return {"username": data.get("username"), "role": data.get("role")}

# BOARD FUNCTIONS ---------------------------------

def get_all_boards() -> list:
    """
    Fetch all available boards.
    Returns list of board dicts.
    """
    command = "LIST_BOARDS"
    response = _send_request(command)
    return _parse_json_response(response)


def get_subscribed_boards(username: str) -> list:
    """
    Fetch boards the user is subscribed to.
    Returns list of board dicts.
    """
    command = f"GET_SUBSCRIBED_BOARDS {username}"
    response = _send_request(command)
    return _parse_json_response(response)


def create_board(username: str, name: str, description: str) -> dict:
    """
    Create a new message board.
    Returns the new board dict on success.
    """
    # Ensure name starts with "r/"
    if not name.startswith("r/"):
        name = "r/" + name
    
    command = f"CREATE_BOARD {username} {name} {description}"
    response = _send_request(command)
    return _parse_json_response(response)


def subscribe_board(username: str, board_id: int) -> bool:
    """
    Subscribe user to a board. Returns True on success.
    """
    command = f"SUBSCRIBE {username} {board_id}"
    response = _send_request(command)
    # Response should be JSON with a success indicator
    data = _parse_json_response(response)
    return data.get("success", True)


def unsubscribe_board(username: str, board_id: int) -> bool:
    """
    Unsubscribe user from a board. Returns True on success.
    """
    command = f"UNSUBSCRIBE {username} {board_id}"
    response = _send_request(command)
    # Response should be JSON with a success indicator
    data = _parse_json_response(response)
    return data.get("success", True)

# MESSAGE FUNCTIONS ---------------------------------

def get_messages(board_id: int) -> list:
    """
    Fetch all messages for a board.
    Returns list of message dicts (each with nested 'comments' list).
    """
    command = f"GET_MESSAGES {board_id}"
    response = _send_request(command)
    return _parse_json_response(response)


def post_message(username: str, board_id: int, content: str) -> dict:
    """
    Post a new message to a board.
    Returns the new message dict.
    """
    command = f"POST_MESSAGE {username} {board_id} {content}"
    response = _send_request(command)
    return _parse_json_response(response)


def edit_message(username: str, message_id: int, new_content: str) -> bool:
    """
    Edit an existing message (only author can edit their own).
    Returns True on success.
    """
    command = f"EDIT_MESSAGE {username} {message_id} {new_content}"
    response = _send_request(command)
    # Response should be JSON with a success indicator
    data = _parse_json_response(response)
    return data.get("success", True)


def delete_message(username: str, message_id: int, role: str) -> bool:
    """
    Delete a message. Authors can delete their own; moderators can delete any.
    Returns True on success.
    """
    command = f"DELETE_MESSAGE {username} {message_id} {role}"
    response = _send_request(command)
    # Response should be JSON with a success indicator
    data = _parse_json_response(response)
    return data.get("success", True)


def post_comment(username: str, message_id: int, content: str) -> dict:
    """
    Post a comment on a message.
    Returns the new comment dict.
    """
    command = f"POST_COMMENT {username} {message_id} {content}"
    response = _send_request(command)
    return _parse_json_response(response)


# INIT AND MAIN ---------------------------------
def init():
    """
    Initialize client connection to the server.
    """
    connect()
    
    # Example interactive shell
    print("Connected to server. Type 'exit' to quit.")
    while True:
        try:
            message = input("> ").strip()
            
            if message.lower() == "exit":
                break
            
            if not message:
                continue
            
            try:
                response = _send_request(message)
                print(f"Response: {response}")
            except Exception as e:
                print(f"Error: {e}")
                
        except KeyboardInterrupt:
            break
    
    disconnect()

        
def main():
    init()


if __name__ == "__main__":
    main()