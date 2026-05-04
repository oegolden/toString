"""
server.py - Server side of the toString messaging application.

This file handles incoming connections and requests from clients. 

Usage: python3 server.py <listening port>

"""

import socket
import threading
import sys
import json
import time
import ssl
from content_moderation import get_moderator as get_content_moderator

# Password hashing imports
import hashlib
import os
import asyncio

from utils.sqlService import init_pool
# mock data


def hash_password(password: str, salt: bytes = None) -> str:
	"""Hash a password using SHA-256 and a salt. Returns salt$hash."""
	if salt is None:
		salt = os.urandom(16)
	hash_bytes = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
	return salt.hex() + '$' + hash_bytes.hex()

def verify_password(stored: str, provided: str) -> bool:
	"""Verify a stored password hash against a provided password."""
	try:
		salt_hex, hash_hex = stored.split('$')
		salt = bytes.fromhex(salt_hex)
		provided_hash = hashlib.pbkdf2_hmac('sha256', provided.encode('utf-8'), salt, 100000).hex()
		return provided_hash == hash_hex
	except Exception:
		return False

# Pre-hash the mock users' passwords
# Add userIDs for audit logging (maps username to unique ID)
_next_user_id = 1
_user_id_map = {}  # username -> user_id

_live_users = {
}

_users = {
	"alice":     {"password": hash_password("pass123"), "role": "user", "email": "alice@example.com", "user_id": 1},
	"bob":       {"password": hash_password("pass456"), "role": "moderator", "email": "bob@example.com", "user_id": 2},
	"admin":     {"password": hash_password("admin"),   "role": "admin", "email": "admin@example.com", "user_id": 3},
}

# Map usernames to userIDs for quick lookup
_user_id_map = {
	"alice": 1,
	"bob": 2,
	"admin": 3,
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

# Track board-specific moderators: board_id -> set of usernames
_board_moderators = {
    1: {"bob"},
    2: {"bob", "admin"},
    3: {"admin"},
    4: {"bob"},
}

# Separate audit logs for different event types
# Login audit: tracks all login attempts (success and failures)
_login_audit_logs = []

# Moderator audit: tracks role changes and board moderator assignments
_moderator_audit_logs = []

# Post audit: tracks all posts and comments with harmful content flags
_post_audit_logs = []

# Moderator request audit: tracks requests for role/moderator upgrades
_moderator_request_logs = []

# Audit log for tracking role changes and moderator actions (legacy, deprecated)
_audit_logs = []

_messages = {
    1: [
        {"id": 101, "board_id": 1, "author": "alice",  "content": "How do I use decorators in Python?",       "timestamp": "2026-03-03 08:12", "comments": [
            {"id": 201, "author": "bob",   "content": "Decorators wrap a function to modify its behavior!",   "timestamp": "2026-03-03 08:45"},
            {"id": 202, "author": "alice", "content": "Oh that makes sense, thanks!",                         "timestamp": "2026-03-03 09:01"},
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

def send_message(connection_socket, message):
	"""Send a text message to the specified socket."""
	try:
		connection_socket.send(message.encode('utf-8'))
		print(f"Sent: {message}")
	except ssl.SSLError as e:
		# Silently handle SSL EOF errors - client disconnected
		if "EOF occurred in violation of protocol" in str(e):
			pass
		else:
			print(f"SSL Error sending message: {e}")
	except Exception as e:
		# Silently ignore errors for closed connections
		pass

def send_json(connection_socket, data):
	"""Send a JSON response to the specified socket."""
	try:
		response = json.dumps(data)
		connection_socket.send(response.encode('utf-8'))
		print(f"Sent JSON: {response[:100]}...")
	except ssl.SSLError as e:
		# Silently handle SSL EOF errors - client disconnected
		if "EOF occurred in violation of protocol" in str(e):
			pass
		else:
			print(f"SSL Error sending JSON: {e}")
	except Exception as e:
		# Silently ignore errors for closed connections
		pass


def send_error(connection_socket, error_message):
	"""Send an ERROR response to the specified socket."""
	response = f"ERROR {error_message}"
	send_message(connection_socket, response)


def log_audit(action, performed_by, target_user=None, board_id=None, details=None, ip_address=None, device_info=None, success=True):
	"""Log audit event for security tracking (legacy, use specific log functions)."""
	# Get user IDs from usernames
	performed_by_id = _user_id_map.get(performed_by, None)
	target_user_id = _user_id_map.get(target_user, None) if target_user else None
	
	log_entry = {
		"action": action,
		"performed_by": performed_by,
		"performed_by_id": performed_by_id,
		"target_user": target_user,
		"target_user_id": target_user_id,
		"board_id": board_id,
		"details": details,
		"ip_address": ip_address,
		"device_info": device_info,
		"success": success,
		"timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
	}
	_audit_logs.append(log_entry)
	_moderator_audit_logs.append(log_entry)
	print(f"[AUDIT] {action} by {performed_by}(ID:{performed_by_id}): {details} | IP: {ip_address} | Device: {device_info} | Success: {success}")


def log_login_attempt(username, ip_address, device_info, success, failure_reason=None):
	"""Log login attempt for security tracking (replaces log_login)."""
	user_id = _user_id_map.get(username, None)
	log_entry = {
		"user_id": user_id,
		"username": username,
		"ip_address": ip_address,
		"device_info": device_info,
		"success": success,
		"failure_reason": failure_reason,
		"timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
	}
	_login_audit_logs.append(log_entry)
	status = "SUCCESS" if success else f"FAILED ({failure_reason})"
	print(f"[LOGIN] {username}(ID:{user_id}) | Status: {status} | IP: {ip_address} | Device: {device_info}")


def log_moderator_action(action, performed_by, target_user=None, board_id=None, details=None, ip_address=None, device_info=None, success=True):
	"""Log moderator actions: promotions, demotions, board assignments."""
	performed_by_id = _user_id_map.get(performed_by, None)
	target_user_id = _user_id_map.get(target_user, None) if target_user else None
	
	log_entry = {
		"action": action,
		"performed_by": performed_by,
		"performed_by_id": performed_by_id,
		"target_user": target_user,
		"target_user_id": target_user_id,
		"board_id": board_id,
		"details": details,
		"ip_address": ip_address,
		"device_info": device_info,
		"success": success,
		"timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
	}
	_moderator_audit_logs.append(log_entry)
	print(f"[MODERATOR] {action}: {performed_by}(ID:{performed_by_id}) -> {target_user}(ID:{target_user_id}) on board {board_id} | IP: {ip_address}")


def log_post_action(message_id, username, board_id, ip_address, device_info, content_preview, action="POST", flagged_harmful=False, reason=None):
	"""Log post/comment action for content tracking."""
	user_id = _user_id_map.get(username, None)
	log_entry = {
		"message_id": message_id,
		"user_id": user_id,
		"username": username,
		"board_id": board_id,
		"ip_address": ip_address,
		"device_info": device_info,
		"content_preview": content_preview[:100] if content_preview else "",  # First 100 chars
		"action": action,
		"flagged_harmful": flagged_harmful,
		"harmful_flag_reason": reason,
		"timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
	}
	_post_audit_logs.append(log_entry)
	harmful_flag = f" [FLAGGED: {reason}]" if flagged_harmful else ""
	print(f"[POST] {action} by {username}(ID:{user_id}) on board {board_id} | IP: {ip_address}{harmful_flag}")


def log_moderator_request(username, request_type, details=None, ip_address=None, device_info=None):
	"""Log moderator/role upgrade requests."""
	user_id = _user_id_map.get(username, None)
	log_entry = {
		"user_id": user_id,
		"username": username,
		"request_type": request_type,  # "MODERATOR_UPGRADE", "BOARD_MODERATOR", etc.
		"details": details,
		"ip_address": ip_address,
		"device_info": device_info,
		"status": "PENDING",
		"timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
	}
	_moderator_request_logs.append(log_entry)
	print(f"[MODERATOR_REQUEST] {username}(ID:{user_id}) requested {request_type} | IP: {ip_address}")


def log_login(username, ip_address, device_info, success, failure_reason=None):
	"""Wrapper for backward compatibility."""
	log_login_attempt(username, ip_address, device_info, success, failure_reason)


def log_post(message_id, username, board_id, ip_address, device_info, content_preview, action="POST", flagged_harmful=False, reason=None):
	"""Wrapper for backward compatibility."""
	log_post_action(message_id, username, board_id, ip_address, device_info, content_preview, action, flagged_harmful, reason)


def extract_device_info(request_metadata=None):
	"""Extract device information from request (simplified for CLI client)."""
	if request_metadata:
		return request_metadata
	return "Python-Client"


def is_user_moderator_of_board(username, board_id):
	"""Check if user is a moderator of a specific board."""
	board_mods = _board_moderators.get(board_id, set())
	return username in board_mods


def is_system_moderator(username):
	"""Check if user has system-wide moderator role."""
	return _users.get(username, {}).get("role") in ("moderator", "admin")


def get_user_board_moderation_list(username):
	"""Get list of boards that a user moderates."""
	moderated_boards = []
	for board_id, mods in _board_moderators.items():
		if username in mods:
			moderated_boards.append(board_id)
	return moderated_boards



""" handle_connection(): listens for messages on a socket until it is closed
inputs:
connection_socket - the socket of the connection 
connection_id - the connection id of the connection
address - the IP address of the source of the connection
"""
def handle_connection(connection_socket, connection_id, address):
	"""
	actions for each connection
	"""
	# Extract IP address from the connection
	client_ip = address[0] if isinstance(address, tuple) else str(address)
	print(f"[CONNECTION] New connection from {client_ip}")
	
	try:
		while True:
			# receive data in bytes
			try:
				data = connection_socket.recv(1024)
			except (ssl.SSLError, BrokenPipeError):
				break
			
			if not data:
				break

			# decode the received data to string 
			message = data.decode()
			print("Got message from", address, ":", message)

			# if the message is "close", close the connection and remove from dict
			if message == "close":
				break

			# add request to the request queue with IP address
			with lock:
				global request_queue
				request_queue.append([message, connection_socket, connection_id, address, client_ip])
	
	except Exception as e:
		if "EOF occurred in violation of protocol" not in str(e):
			print(f"Connection error from {address}: {e}")
	
	finally:
		# Properly close the SSL connection
		try:
			connection_socket.unwrap()
		except:
			pass
		
		try:
			connection_socket.close()
		except:
			pass
		
		global connection_dict
		if connection_id in connection_dict:
			del connection_dict[connection_id]
		print(f"Closing connection {connection_id} from server side with {address}")
	

""" terminate_connection(): closes the connection at the specified connection_id
"""
def terminate_connection(connection_id):
	if connection_id not in connection_dict:
		return
	
	conn = connection_dict[connection_id]['socket']
	try:
		conn.close()
	except:
		pass
	
	if connection_id in connection_dict:
		del connection_dict[connection_id]
	
	print(f"Terminated connection {connection_id}")


""" accept_connections(): keep listening for connection requests
inputs:
s - listening socket
"""
def accept_connection(s):
		s.listen(50) # start listening for up to 50 connections
		while True:
			# accept connection request
			try:
				connection_socket, address = s.accept()
			except ssl.SSLError as e:
				print(f"SSL error on accept: {e}")
				continue

			global connection_counter
			connection_dict[connection_counter] = {
				"socket": connection_socket,
				"listening_port": connection_socket.getsockname()[1],
			}
			connection_counter += 1
			print("Got connection from", address)

			# create a thread to handle the accepted client
			thread = threading.Thread(target=handle_connection, args=(connection_socket, (connection_counter-1), address), daemon=True)
			thread.start()  # start the thread


""" handle_requests(): continuously check for requests from clients and handle them
"""
def handle_requests():
	cur_request = ""
	while True:
		if len(request_queue) > 0:
			with lock:
				cur_request = request_queue.pop(0)
			
			thread = threading.Thread(target=handle_request, args=(cur_request,), daemon=True)
			thread.start()

		
def handle_request(request):
	"""Process a single client request."""
	global _next_message_id, _next_comment_id
	
	# unpack info from the request
	command_str = request[0].strip()
	command_parts = command_str.split(maxsplit=3)
	return_socket = request[1]
	return_id = request[2]
	return_address = request[3]
	client_ip = request[4] if len(request) > 4 else "Unknown"

	if not command_parts:
		send_error(return_socket, "Empty command")
		return

	cmd = command_parts[0]
	device_info = "Python-Client"

	try:

		# auth commands
		if cmd == "LOGIN":
			if len(command_parts) < 3:
				send_error(return_socket, "Invalid command format. Use: LOGIN <username> <password>")
				return
			username = command_parts[1]
			password = command_parts[2]
			if username not in _users:
				log_login(username, client_ip, device_info, False, "User does not exist")
				send_error(return_socket, "User does not exist")
				return
			if username in _live_users:
				log_login(username, client_ip, device_info, False, "User already logged in")
				send_error(return_socket, "User already logged in")
				return
			else:
				_live_users[username] = {
					"login_time": time.time(),
					"ip_address": client_ip,
					"device_info": device_info
				}

			if not verify_password(_users[username]["password"], password):
				log_login(username, client_ip, device_info, False, "Invalid password")
				send_error(return_socket, "Invalid password")
				return
			
			log_login(username, client_ip, device_info, True)
			send_json(return_socket, {
				"username": username,
				"role": _users[username]["role"]
			})

		elif cmd == "LOGOUT":
			if len(command_parts) < 2:
				send_error(return_socket, "Invalid command format. Use: LOGOUT <username>")
				return
			username = command_parts[1]
			if username in _live_users:
				del _live_users[username]
				send_json(return_socket, {"success": True})
			else:
				send_error(return_socket, "User not logged in")

		elif cmd == "REGISTER":
			if len(command_parts) < 4:
				log_login(command_parts[1] if len(command_parts) > 1 else "UNKNOWN", client_ip, device_info, False, "Invalid registration format")
				send_error(return_socket, "Invalid command format. Use: REGISTER <username> <password> <email>")
				return
			username = command_parts[1]
			password = command_parts[2]
			email = command_parts[3]
			if username in _users:
				send_error(return_socket, f"Username '{username}' is already taken")
				return
			if len(password) < 4:
				send_error(return_socket, "Password must be at least 4 characters")
				return
			
			# Create the new user
			hashed = hash_password(password)
			new_user_id = max([_users[u].get("user_id", 0) for u in _users] + [0]) + 1
			_users[username] = {"password": hashed, "role": "user", "email": email, "user_id": new_user_id}
			_user_id_map[username] = new_user_id
			_subscriptions[username] = set()
			
			# Auto-login the new user
			_live_users[username] = {
				"login_time": time.time(),
				"ip_address": client_ip,
				"device_info": device_info
			}
			
			log_login(username, client_ip, device_info, True)
			send_json(return_socket, {
				"username": username,
				"role": "user"
			})

		# board commands
		elif cmd == "LIST_BOARDS":
			send_json(return_socket, list(_boards.values()))

		elif cmd == "GET_SUBSCRIBED_BOARDS":
			if len(command_parts) < 2:
				send_error(return_socket, "Invalid command format. Use: GET_SUBSCRIBED_BOARDS <username>")
				return
			
			username = command_parts[1]
			subs = _subscriptions.get(username, set())
			boards = [_boards[bid] for bid in subs if bid in _boards]
			send_json(return_socket, boards)

		elif cmd == "CREATE_BOARD":
			if len(command_parts) < 4:
				send_error(return_socket, "Invalid command format. Use: CREATE_BOARD <username> <name> <description>")
				return
			
			username = command_parts[1]
			board_name = command_parts[2]
			board_desc = command_parts[3]
			
			if not board_name.startswith("r/"):
				board_name = "r/" + board_name
			
			# Check board name and description for harmful content
			moderator = get_content_moderator()
			name_flagged, name_reason = moderator.moderate(board_name)
			desc_flagged, desc_reason = moderator.moderate(board_desc)
			
			if name_flagged:
				send_error(return_socket, f"Board name violates content policy: {name_reason}")
				log_audit("CREATE_BOARD", username, details=f"Rejected board creation - harmful name: {board_name}", success=False)
				return
			
			if desc_flagged:
				send_error(return_socket, f"Board description violates content policy: {desc_reason}")
				log_audit("CREATE_BOARD", username, details=f"Rejected board creation - harmful description", success=False)
				return
			
			# Check if board name already exists
			for board in _boards.values():
				if board["name"] == board_name:
					send_error(return_socket, "Board name already exists")
					return
			
			new_id = max(_boards.keys()) + 1
			board = {
				"id": new_id,
				"name": board_name,
				"description": board_desc,
				"member_count": 1,
				"creator": username
			}
			_boards[new_id] = board
			_messages[new_id] = []
			_subscriptions.setdefault(username, set()).add(new_id)
			
			send_json(return_socket, board)

		elif cmd == "SUBSCRIBE":
			if len(command_parts) < 3:
				send_error(return_socket, "Invalid command format. Use: SUBSCRIBE <username> <board_id>")
				return
			
			username = command_parts[1]
			try:
				board_id = int(command_parts[2])
			except ValueError:
				send_error(return_socket, "Board ID must be an integer")
				return
			
			if board_id not in _boards:
				send_error(return_socket, "Board not found")
				return
			
			if board_id in _subscriptions.get(username, set()):
				send_error(return_socket, "Already subscribed to this board")
				return
			
			_subscriptions.setdefault(username, set()).add(board_id)
			_boards[board_id]["member_count"] += 1
			
			send_json(return_socket, {"success": True})

		elif cmd == "UNSUBSCRIBE":
			if len(command_parts) < 3:
				send_error(return_socket, "Invalid command format. Use: UNSUBSCRIBE <username> <board_id>")
				return
			
			username = command_parts[1]
			try:
				board_id = int(command_parts[2])
			except ValueError:
				send_error(return_socket, "Board ID must be an integer")
				return
			
			if board_id not in _boards:
				send_error(return_socket, "Board not found")
				return
			
			_subscriptions.get(username, set()).discard(board_id)
			_boards[board_id]["member_count"] = max(0, _boards[board_id]["member_count"] - 1)
			
			send_json(return_socket, {"success": True})

		# message commands
		elif cmd == "GET_MESSAGES":
			if len(command_parts) < 2:
				send_error(return_socket, "Invalid command format. Use: GET_MESSAGES <board_id>")
				return
			
			try:
				board_id = int(command_parts[1])
			except ValueError:
				send_error(return_socket, "Board ID must be an integer")
				return
			
			if board_id not in _boards:
				send_error(return_socket, "Board not found")
				return
			
			messages = _messages.get(board_id, [])
			send_json(return_socket, messages)

		elif cmd == "POST_MESSAGE":
			if len(command_parts) < 4:
				send_error(return_socket, "Invalid command format. Use: POST_MESSAGE <username> <board_id> <content>")
				return
			
			username = command_parts[1]
			try:
				board_id = int(command_parts[2])
			except ValueError:
				send_error(return_socket, "Board ID must be an integer")
				return
			
			content = command_parts[3]
			
			if board_id not in _subscriptions.get(username, set()):
				send_error(return_socket, "You must be subscribed to post on this board")
				return
			
			# Check content for harmful patterns
			moderator = get_content_moderator()
			flagged_harmful, flag_reason = moderator.moderate(content)
			
			if flagged_harmful:
				send_error(return_socket, f"Comment violates content policy: {flag_reason}")
				log_audit("POST_MESSAGE", username, details=f"Rejected content creation - harmful post: {content}", success=False)
				return
			
			
			msg = {
				"id": _next_message_id,
				"board_id": board_id,
				"author": username,
				"content": content,
				"timestamp": time.strftime("%Y-%m-%d %H:%M"),
				"comments": [],
				"flagged": flagged_harmful,
				"flag_reason": flag_reason if flagged_harmful else None
			}
			_next_message_id += 1
			_messages.setdefault(board_id, []).insert(0, msg)
			
			# Log the post action with harmful content flag
			log_post(msg["id"], username, board_id, client_ip, device_info, content, "POST", flagged_harmful, flag_reason)
			
			send_json(return_socket, msg)

		elif cmd == "EDIT_MESSAGE":
			if len(command_parts) < 4:
				send_error(return_socket, "Invalid command format. Use: EDIT_MESSAGE <username> <message_id> <new_content>")
				return
			
			username = command_parts[1]
			try:
				message_id = int(command_parts[2])
			except ValueError:
				send_error(return_socket, "Message ID must be an integer")
				return
			
			new_content = command_parts[3]
			
			# Check content for harmful patterns
			moderator = get_content_moderator()
			flagged_harmful, flag_reason = moderator.moderate(new_content)
			
			if flagged_harmful:
				send_error(return_socket, f"Comment violates content policy: {flag_reason}")
				log_audit("EDIT_MESSAGE", username, details=f"Rejected content edit - harmful post: {new_content}", success=False)
				return
			
			# Find and edit the message
			for board_msgs in _messages.values():
				for msg in board_msgs:
					if msg["id"] == message_id:
						if msg["author"] != username:
							send_error(return_socket, "You can only edit your own messages")
							return
						msg["content"] = new_content + " (edited)"
						msg["flagged"] = flagged_harmful
						msg["flag_reason"] = flag_reason if flagged_harmful else None
						send_json(return_socket, {"success": True})
						return
			
			send_error(return_socket, "Message not found")

		elif cmd == "DELETE_MESSAGE":
			if len(command_parts) < 4:
				send_error(return_socket, "Invalid command format. Use: DELETE_MESSAGE <username> <message_id> <board_id>")
				return

			username = command_parts[1]
			try:
				message_id = int(command_parts[2])
				board_id = int(command_parts[3])
			except ValueError:
				send_error(return_socket, "Message ID and Board ID must be integers")
				return
			
			# Find and delete the message
			for board_msgs in _messages.values():
				for msg in board_msgs:
					if msg["id"] == message_id:
						# Check authorization: message author, board moderator, or admin
						is_author = msg["author"] == username
						is_board_moderator = is_user_moderator_of_board(username, board_id)
						is_admin = _users.get(username, {}).get("role") == "admin"
						
						if not (is_author or is_board_moderator or is_admin):
							send_error(return_socket, "You can only delete your own messages, or manage messages on boards you moderate")
							return
						
						board_msgs.remove(msg)
						action_detail = f"Deleted message {message_id} by {msg['author']}"
						if not is_author:
							action_detail += f" (deleted by {username})"
						log_audit("DELETE_MESSAGE", username, msg["author"], board_id, action_detail)
						
						send_json(return_socket, {"success": True})
						return
			
			send_error(return_socket, "Message not found")

		elif cmd == "POST_COMMENT":
			if len(command_parts) < 4:
				send_error(return_socket, "Invalid command format. Use: POST_COMMENT <username> <message_id> <content>")
				return
			
			username = command_parts[1]
			try:
				message_id = int(command_parts[2])
			except ValueError:
				send_error(return_socket, "Message ID must be an integer")
				return
			
			content = command_parts[3]
			
			# Check content for harmful patterns
			moderator = get_content_moderator()
			flagged_harmful, flag_reason = moderator.moderate(content)
			
			# Find the message and add comment
			for board_msgs in _messages.values():
				for msg in board_msgs:
					if msg["id"] == message_id:
						comment = {
							"id": _next_comment_id,
							"author": username,
							"content": content,
							"timestamp": time.strftime("%Y-%m-%d %H:%M"),
							"flagged": flagged_harmful,
							"flag_reason": flag_reason if flagged_harmful else None
						}
						_next_comment_id += 1
						msg["comments"].append(comment)
						log_post(comment["id"], username, msg["board_id"], client_ip, device_info, content, "COMMENT", flagged_harmful, flag_reason)
						send_json(return_socket, comment)
						return
			
			send_error(return_socket, "Message not found")

		# Moderator management commands
		elif cmd == "UPGRADE_USER":
			"""Upgrade a user to system-wide moderator status. Admin only."""
			if len(command_parts) < 3:
				send_error(return_socket, "Invalid command format. Use: UPGRADE_USER <admin_username> <target_username>")
				return
			
			admin_username = command_parts[1]
			target_username = command_parts[2]
			
			# Verify admin status
			if _users.get(admin_username, {}).get("role") != "admin":
				send_error(return_socket, "Only admins can upgrade users to moderator")
				return
			
			if target_username not in _users:
				send_error(return_socket, f"User '{target_username}' does not exist")
				return
			
			if _users[target_username]["role"] == "moderator":
				send_error(return_socket, f"User '{target_username}' is already a moderator")
				return
			
			# Upgrade user to moderator
			_users[target_username]["role"] = "moderator"
			log_moderator_action("UPGRADE_USER", admin_username, target_username, None, f"Upgraded {target_username} to moderator", client_ip, device_info, success=True)
			
			send_json(return_socket, {
				"success": True,
				"message": f"User '{target_username}' promoted to system moderator",
				"username": target_username,
				"role": "moderator"
			})

		elif cmd == "DOWNGRADE_USER":
			"""Downgrade a moderator back to regular user. Admin only."""
			if len(command_parts) < 3:
				send_error(return_socket, "Invalid command format. Use: DOWNGRADE_USER <admin_username> <target_username>")
				return
			
			admin_username = command_parts[1]
			target_username = command_parts[2]
			
			# Verify admin status
			if _users.get(admin_username, {}).get("role") != "admin":
				send_error(return_socket, "Only admins can downgrade moderators")
				return
			
			if target_username not in _users:
				send_error(return_socket, f"User '{target_username}' does not exist")
				return
			
			current_role = _users[target_username].get("role", "user")
			if current_role not in ("moderator", "admin"):
				send_error(return_socket, f"User '{target_username}' is not a moderator")
				return
			
			# Downgrade user
			_users[target_username]["role"] = "user"
			
			# Remove from all board moderation
			for board_id in list(_board_moderators.keys()):
				_board_moderators[board_id].discard(target_username)
			
			log_moderator_action("DOWNGRADE_USER", admin_username, target_username, None, f"Downgraded {target_username} to regular user", client_ip, device_info, success=True)
			
			send_json(return_socket, {
				"success": True,
				"message": f"User '{target_username}' downgraded to regular user",
				"username": target_username,
				"role": "user"
			})

		elif cmd == "ASSIGN_BOARD_MODERATOR":
			"""Assign a moderator to manage a specific board. Admin only."""
			if len(command_parts) < 4:
				send_error(return_socket, "Invalid command format. Use: ASSIGN_BOARD_MODERATOR <admin_username> <target_username> <board_id>")
				return
			
			admin_username = command_parts[1]
			target_username = command_parts[2]
			try:
				board_id = int(command_parts[3])
			except ValueError:
				send_error(return_socket, "Board ID must be an integer")
				return
			
			# Verify admin status
			if _users.get(admin_username, {}).get("role") != "admin":
				send_error(return_socket, "Only admins can assign board moderators")
				return
			
			if target_username not in _users:
				send_error(return_socket, f"User '{target_username}' does not exist")
				return
			
			if board_id not in _boards:
				send_error(return_socket, f"Board with ID {board_id} does not exist")
				return
			
			# Assign moderator to board
			_board_moderators.setdefault(board_id, set()).add(target_username)
			log_moderator_action("ASSIGN_BOARD_MODERATOR", admin_username, target_username, board_id, f"Assigned {target_username} as moderator for board {board_id}", client_ip, device_info, success=True)
			
			send_json(return_socket, {
				"success": True,
				"message": f"User '{target_username}' assigned as moderator for board '{_boards[board_id]['name']}'",
				"username": target_username,
				"board_id": board_id,
				"board_name": _boards[board_id]["name"]
			})

		elif cmd == "REMOVE_BOARD_MODERATOR":
			"""Remove a moderator from a specific board. Admin only."""
			if len(command_parts) < 4:
				send_error(return_socket, "Invalid command format. Use: REMOVE_BOARD_MODERATOR <admin_username> <target_username> <board_id>")
				return
			
			admin_username = command_parts[1]
			target_username = command_parts[2]
			try:
				board_id = int(command_parts[3])
			except ValueError:
				send_error(return_socket, "Board ID must be an integer")
				return
			
			# Verify admin status
			if _users.get(admin_username, {}).get("role") != "admin":
				send_error(return_socket, "Only admins can remove board moderators")
				return
			
			if target_username not in _users:
				send_error(return_socket, f"User '{target_username}' does not exist")
				return
			
			board_mods = _board_moderators.get(board_id, set())
			if target_username not in board_mods:
				send_error(return_socket, f"User '{target_username}' is not a moderator for this board")
				return
			
			# Remove moderator from board
			_board_moderators[board_id].discard(target_username)
			log_moderator_action("REMOVE_BOARD_MODERATOR", admin_username, target_username, board_id, f"Removed {target_username} as moderator from board {board_id}", client_ip, device_info, success=True)
			
			send_json(return_socket, {
				"success": True,
				"message": f"User '{target_username}' removed as moderator from board '{_boards[board_id]['name']}'",
				"username": target_username,
				"board_id": board_id
			})

		elif cmd == "LIST_BOARD_MODERATORS":
			"""List all moderators for a specific board."""
			if len(command_parts) < 2:
				send_error(return_socket, "Invalid command format. Use: LIST_BOARD_MODERATORS <board_id>")
				return
			
			try:
				board_id = int(command_parts[1])
			except ValueError:
				send_error(return_socket, "Board ID must be an integer")
				return
			
			if board_id not in _boards:
				send_error(return_socket, f"Board with ID {board_id} does not exist")
				return
			
			mods = list(_board_moderators.get(board_id, set()))
			send_json(return_socket, {
				"board_id": board_id,
				"board_name": _boards[board_id]["name"],
				"moderators": mods
			})

		elif cmd == "GET_MODERATED_BOARDS":
			"""Get list of boards that a user moderates."""
			if len(command_parts) < 2:
				send_error(return_socket, "Invalid command format. Use: GET_MODERATED_BOARDS <username>")
				return
			
			username = command_parts[1]
			if username not in _users:
				send_error(return_socket, f"User '{username}' does not exist")
				return
			
			moderated_board_ids = get_user_board_moderation_list(username)
			boards = [_boards[bid] for bid in moderated_board_ids]
			
			send_json(return_socket, {
				"username": username,
				"role": _users[username].get("role", "user"),
				"moderated_boards": boards
			})

		elif cmd == "GET_AUDIT_LOGS":
			"""Retrieve audit logs in various categories. Admin only."""
			if len(command_parts) < 2:
				send_error(return_socket, "Invalid command format. Use: GET_AUDIT_LOGS <admin_username> [log_type] [limit]")
				return
			
			admin_username = command_parts[1]
			
			# Verify admin status
			if _users.get(admin_username, {}).get("role") != "admin":
				send_error(return_socket, "Only admins can view audit logs")
				log_audit("GET_AUDIT_LOGS", admin_username, details="Unauthorized access attempt", success=False)
				return
			
			log_type = command_parts[2] if len(command_parts) > 2 else "all"
			limit = 100
			if len(command_parts) > 3:
				try:
					limit = int(command_parts[3])
				except ValueError:
					pass
			
			# Prepare response based on log type
			response = {
				"total_login_logs": len(_login_audit_logs),
				"total_moderator_logs": len(_moderator_audit_logs),
				"total_post_logs": len(_post_audit_logs),
				"total_request_logs": len(_moderator_request_logs),
			}
			
			if log_type in ("all", "login"):
				response["login_logs"] = _login_audit_logs[-limit:] if limit > 0 else _login_audit_logs
			
			if log_type in ("all", "moderator"):
				response["moderator_logs"] = _moderator_audit_logs[-limit:] if limit > 0 else _moderator_audit_logs
			
			if log_type in ("all", "post"):
				response["post_logs"] = _post_audit_logs[-limit:] if limit > 0 else _post_audit_logs
			
			if log_type in ("all", "request"):
				response["request_logs"] = _moderator_request_logs[-limit:] if limit > 0 else _moderator_request_logs
			
			log_audit("GET_AUDIT_LOGS", admin_username, details=f"Retrieved {log_type} logs", success=True)
			send_json(return_socket, response)
		
		elif cmd == "SEND_RECOVERY_EMAIL":
			# Usage: SEND_RECOVERY_EMAIL <username> <email>
			if len(command_parts) < 3:
				send_error(return_socket, "Invalid command format. Use: SEND_RECOVERY_EMAIL <username> <email>")
				return
			username = command_parts[1]
			email = command_parts[2]
			try:
				from user import User
				user = User(username, email)
				recovery_code = user.send_recovery_email()
				# Store the recovery code in a temporary dict for later verification (in-memory for now)
				_recovery_codes[username] = recovery_code
				send_json(return_socket, {"success": True, "message": f"Recovery email sent to {email}"})
			except Exception as e:
				send_error(return_socket, f"Failed to send recovery email: {e}")

		elif cmd == "RESET_PASSWORD":
			# Usage: RESET_PASSWORD <username> <email> <recovery_code> <new_password>
			if len(command_parts) < 4:
				send_error(return_socket, "Invalid command format. Use: RESET_PASSWORD <username> <email> <recovery_code> <new_password>")
				return
			# The last part may contain spaces in the password, so split accordingly
			username = command_parts[1]
			email = command_parts[2]
			rest = command_parts[3].split(maxsplit=1)
			if len(rest) < 2:
				send_error(return_socket, "Invalid command format. Use: RESET_PASSWORD <username> <email> <recovery_code> <new_password>")
				return
			recovery_code = rest[0]
			new_password = rest[1]
			try:
				# Check recovery code
				if _recovery_codes[username] != recovery_code:
					send_error(return_socket, "Invalid recovery code.")
					return
				from user import User
				user = User(username, email)
				# Await the async reset_password method
				asyncio.run(user.reset_password(new_password))
				del _recovery_codes[username]
				send_json(return_socket, {"success": True, "message": "Password reset successful."})
			except Exception as e:
				send_error(return_socket, f"Failed to reset password: {e}")
		else:
			send_error(return_socket, f"Unknown command: {cmd}")
		
			

	except Exception as e:
		print(f"Error handling request: {e}")
		send_error(return_socket, str(e))
			


# Functions for handling user input from the terminal

def input_handler(sock):
	"""Receive command input from admin console."""
	command = input(">> ").split()

	if not command:
		return

	if command[0] == "help":
		print("Available commands:")
		print("  myip - Display IP address")
		print("  myport - Display listening port")
		print("  list - Show active connections")
		print("  exit - Shutdown server")
		return

	elif command[0] == "myip":
		# Get this server's IP by connecing to smth
		s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		try:
			# Doesn't have to be reachable
			s.connect(('8.8.8.8', 1))
			hostip = s.getsockname()[0]
		except Exception:
			hostip = '127.0.0.1'
		finally:
			s.close()
		print(f"IP address: {hostip}")
		return
	
	elif command[0] == "list":
		if len(connection_dict) == 0:
			print("No current connections")
		else:
			print("Current connections:")
			for conn_id in connection_dict.keys():
				conn = connection_dict[conn_id]['socket']
				try:
					addr = conn.getpeername()
					print(f"  Connection {conn_id}: {addr[0]}:{addr[1]}")
				except:
					print(f"  Connection {conn_id}: (closed)")
		return

	elif command[0] == "myport":
		portnum = sock.getsockname()[1]
		print(f"Listening port: {portnum}")
		return

	elif command[0] == "exit":
		global exit
		exit = True
		return

	else:
		print("Unknown command. Type 'help' for available commands.")
		return


""" input_loop(): continuously handle user input
"""
def input_loop(sock):
	import sys
	if not sys.stdin.isatty():
		return
	while not exit:
		try:
			input_handler(sock)
		except KeyboardInterrupt:
			break
		except Exception as e:
			print(f"Error in input loop: {e}")


# Server startup and main loop

def init():
	"""Initialize global variables for the server."""
	global request_queue, connection_dict, connection_counter
	request_queue = [] 
	connection_dict = {}
	connection_counter = 0
	
	global exit, lock
	exit = False
	lock = threading.Lock()
	global _recovery_codes
	_recovery_codes = {}

	init_pool()

def main():
	# input validation
	if int(sys.argv[1]) not in range(1024,49152):
		raise ValueError("Invalid port number, please enter a number between 1024 and 49152")

	# initialize global server variables
	init()

	# SSL context setup
	context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
	# Use your own certificate and key paths here
	context.load_cert_chain(certfile="server.crt", keyfile="server.key")

	# create a listening socket
	port = int(sys.argv[1])
	s = socket.socket()
	s.bind(("0.0.0.0", port))
	s = context.wrap_socket(s, server_side=True)
	print("Hello. Created new process with listening port", port)

	# start a thread to gather user input
	input_thread = threading.Thread(target=input_loop, name="input_handler_thread", args=(s,), daemon=True)
	input_thread.start()  # start the thread
	print("Started thread", input_thread.name)

	# start a thread to accept connections
	connection_thread = threading.Thread(target=accept_connection, name="connection_thread", args=(s,), daemon=True)
	connection_thread.start()
	print("Started thread connection_thread")

	# start a thread to handle requests from clients
	request_thread = threading.Thread(target=handle_requests, name="request_handler_thread", args=(), daemon=True)
	request_thread.start()

	# wait to get exit signal with proper sleep
	try:
		while not exit:
			time.sleep(0.1)  # Prevent busy-wait
	except KeyboardInterrupt:
		print("\nShutting down server...")
	
	sys.exit()


if __name__ == "__main__":
	main()