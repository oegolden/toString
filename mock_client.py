"""
mock_client.py — Fake backend for GUI development and testing.

While the backend is not yet implemented, gui.py imports from here instead.

HOW TO SWAP IN THE REAL BACKEND:
    When client.py is ready, replace:
        from mock_client import ...
    with:
        from client import ...
    in gui.py. All function signatures must match.

RETURN CONVENTIONS (match these exactly in client.py):
    - Success responses return the data directly (dict, list, etc.)
    - Failure responses raise an Exception with a human-readable message
    - Logged-in user state is managed externally (in gui.py's App class)
"""

import time
import random

# ─────────────────────────────────────────────
#  Simulated in-memory "database"
# ─────────────────────────────────────────────

_users = {
    "alice":     {"password": "pass123", "role": "user"},
    "bob":       {"password": "pass456", "role": "moderator"},
    "admin":     {"password": "admin",   "role": "admin"},
}

_boards = {
    1: {"id": 1, "name": "r/PythonHelp",     "description": "Ask anything Python", "member_count": 1204, "creator": "alice"},
    2: {"id": 2, "name": "r/SystemSecurity", "description": "Cybersecurity discussions", "member_count": 892, "creator": "bob"},
    3: {"id": 3, "name": "r/HMCLife",        "description": "Life at Harvey Mudd", "member_count": 543,  "creator": "alice"},
    4: {"id": 4, "name": "r/SocketProg",     "description": "Low-level networking talk", "member_count": 231, "creator": "bob"},
}

_subscriptions = {
    "alice": {1, 3},
    "bob":   {1, 2, 4},
    "admin": {1, 2, 3, 4},
}

_messages = {
    1: [
        {"id": 101, "board_id": 1, "author": "alice",  "content": "How do I use decorators in Python?",       "timestamp": "2026-03-03 08:12", "comments": [
            {"id": 201, "author": "bob",   "content": "Decorators wrap a function to modify its behavior!",   "timestamp": "2026-03-03 08:45"},
            {"id": 202, "author": "alice", "content": "Oh that makes sense, thanks!",                         "timestamp": "2026-03-03 09:01"},
            {"id": 201, "author": "bob", "content": "yeah", "timestamp": "2026-03-04 09:01"},
            {"id": 201, "author": "bob", "content": "yeah", "timestamp": "2026-03-04 09:02"},
            {"id": 201, "author": "bob", "content": "yeah", "timestamp": "2026-03-04 09:03"},
            {"id": 201, "author": "bob", "content": "yeah", "timestamp": "2026-03-04 09:04"},
            {"id": 201, "author": "bob", "content": "yeah", "timestamp": "2026-03-04 09:05"},
            {"id": 201, "author": "bob", "content": "yeah", "timestamp": "2026-03-04 09:06"},
        ]},
        {"id": 102, "board_id": 1, "author": "bob",    "content": "PSA: use type hints, your future self will thank you.", "timestamp": "2026-03-03 10:00", "comments": []},
    ],
    2: [
        {"id": 103, "board_id": 2, "author": "bob",    "content": "SQL injection is still #1 on OWASP Top 10. Use parameterized queries!", "timestamp": "2026-03-03 07:30", "comments": [
            {"id": 203, "author": "admin", "content": "Always sanitize inputs. Never trust user data.",        "timestamp": "2026-03-03 07:55"},
        ]},
    ],
    3: [
        {"id": 104, "board_id": 3, "author": "alice",  "content": "Dining hall has mac and cheese today 🧀",  "timestamp": "2026-03-03 11:30", "comments": []},
    ],
    4: [],
}

_next_message_id = 200
_next_comment_id = 300

# ─────────────────────────────────────────────
#  Auth functions
# ─────────────────────────────────────────────

def login(username: str, password: str) -> dict:
    """
    Attempt to log in with credentials.
    Returns user info dict on success, raises Exception on failure.

    client.py should: send credentials over socket, receive auth token or rejection.
    """
    user = _users.get(username)
    if not user or user["password"] != password:
        raise Exception("Invalid username or password.")
    return {"username": username, "role": user["role"]}


def register(username: str, password: str) -> dict:
    """
    Register a new user account.
    Returns new user info on success, raises Exception if username taken.

    client.py should: send registration request to server, receive confirmation.
    """
    if username in _users:
        raise Exception(f"Username '{username}' is already taken.")
    if len(password) < 4:
        raise Exception("Password must be at least 4 characters.")
    _users[username] = {"password": password, "role": "user"}
    _subscriptions[username] = set()
    return {"username": username, "role": "user"}

# ─────────────────────────────────────────────
#  Board functions
# ─────────────────────────────────────────────

def get_all_boards() -> list:
    """
    Fetch all available boards.
    Returns list of board dicts.

    client.py should: send LIST_BOARDS request, receive JSON list from server.
    """
    return list(_boards.values())


def get_subscribed_boards(username: str) -> list:
    """
    Fetch boards the user is subscribed to.
    Returns list of board dicts.
    """
    subs = _subscriptions.get(username, set())
    return [_boards[bid] for bid in subs if bid in _boards]


def create_board(username: str, name: str, description: str) -> dict:
    """
    Create a new message board.
    Returns the new board dict on success.

    client.py should: send CREATE_BOARD request with name/description.
    """
    global _boards
    if not name.startswith("r/"):
        name = "r/" + name
    new_id = max(_boards.keys()) + 1
    board = {"id": new_id, "name": name, "description": description,
             "member_count": 1, "creator": username}
    _boards[new_id] = board
    _messages[new_id] = []
    _subscriptions[username].add(new_id)
    return board


def subscribe_board(username: str, board_id: int) -> bool:
    """
    Subscribe user to a board. Returns True on success.

    client.py should: send SUBSCRIBE request with board_id.
    """
    if board_id not in _boards:
        raise Exception("Board not found.")
    _subscriptions.setdefault(username, set()).add(board_id)
    _boards[board_id]["member_count"] += 1
    return True


def unsubscribe_board(username: str, board_id: int) -> bool:
    """
    Unsubscribe user from a board. Returns True on success.

    client.py should: send UNSUBSCRIBE request with board_id.
    """
    _subscriptions.get(username, set()).discard(board_id)
    _boards[board_id]["member_count"] = max(0, _boards[board_id]["member_count"] - 1)
    return True

# ─────────────────────────────────────────────
#  Message functions
# ─────────────────────────────────────────────

def get_messages(board_id: int) -> list:
    """
    Fetch all messages for a board.
    Returns list of message dicts (each with nested 'comments' list).

    client.py should: send GET_MESSAGES request with board_id.
    """
    return _messages.get(board_id, [])


def post_message(username: str, board_id: int, content: str) -> dict:
    """
    Post a new message to a board.
    Returns the new message dict.

    client.py should: send POST_MESSAGE request with board_id + content.
    """
    global _next_message_id
    if board_id not in _subscriptions.get(username, set()):
        raise Exception("You must be subscribed to post on this board.")
    msg = {
        "id": _next_message_id,
        "board_id": board_id,
        "author": username,
        "content": content,
        "timestamp": time.strftime("%Y-%m-%d %H:%M"),
        "comments": [],
    }
    _next_message_id += 1
    _messages.setdefault(board_id, []).insert(0, msg)
    return msg


def edit_message(username: str, message_id: int, new_content: str) -> bool:
    """
    Edit an existing message (only author can edit their own).
    Returns True on success.

    client.py should: send EDIT_MESSAGE with message_id + new_content.
    """
    for board_msgs in _messages.values():
        for msg in board_msgs:
            if msg["id"] == message_id:
                if msg["author"] != username:
                    raise Exception("You can only edit your own messages.")
                msg["content"] = new_content + " (edited)"
                return True
    raise Exception("Message not found.")


def delete_message(username: str, message_id: int, role: str) -> bool:
    """
    Delete a message. Authors can delete their own; moderators can delete any.
    Returns True on success.

    client.py should: send DELETE_MESSAGE with message_id. Server checks permissions.
    """
    for board_msgs in _messages.values():
        for msg in board_msgs:
            if msg["id"] == message_id:
                if msg["author"] != username and role not in ("moderator", "admin"):
                    raise Exception("You can only delete your own messages.")
                board_msgs.remove(msg)
                return True
    raise Exception("Message not found.")


def post_comment(username: str, message_id: int, content: str) -> dict:
    """
    Post a comment on a message.
    Returns the new comment dict.

    client.py should: send POST_COMMENT with message_id + content.
    """
    global _next_comment_id
    for board_msgs in _messages.values():
        for msg in board_msgs:
            if msg["id"] == message_id:
                comment = {
                    "id": _next_comment_id,
                    "author": username,
                    "content": content,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M"),
                }
                _next_comment_id += 1
                msg["comments"].append(comment)
                return comment
    raise Exception("Message not found.")