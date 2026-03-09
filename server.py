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


# mock data

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
	except Exception as e:
		print(f"Error sending message: {e}")


def send_json(connection_socket, data):
	"""Send a JSON response to the specified socket."""
	try:
		response = json.dumps(data)
		connection_socket.send(response.encode('utf-8'))
		print(f"Sent JSON: {response[:100]}...")
	except Exception as e:
		print(f"Error sending JSON: {e}")


def send_error(connection_socket, error_message):
	"""Send an ERROR response to the specified socket."""
	response = f"ERROR {error_message}"
	send_message(connection_socket, response)



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
	while True:
		# receive data in bytes
		data = connection_socket.recv(1024)

		# decode the received data to string 
		message = data.decode()
		print("Got message from", address, ":", message)

		# if the message is "close", close the connection and remove from dict
		if message == "close":
			break

		# add request to the request queue
		with lock:
			global request_queue
			request_queue.append([message, connection_socket, connection_id, address])
			
	connection_socket.close()
	global connection_dict
	del connection_dict[connection_id]
	print(f"Closing connection {connection_id} from server side with", address)
	

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
		connection_socket, address = s.accept()

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

	if not command_parts:
		send_error(return_socket, "Empty command")
		return

	cmd = command_parts[0]

	try:
		# auth commands
		if cmd == "LOGIN":
			if len(command_parts) < 3:
				send_error(return_socket, "Invalid command format. Use: LOGIN <username> <password>")
				return
			
			username = command_parts[1]
			password = command_parts[2]
			
			if username not in _users:
				send_error(return_socket, "User does not exist")
				return
			
			if _users[username]["password"] != password:
				send_error(return_socket, "Invalid password")
				return
			
			send_json(return_socket, {
				"username": username,
				"role": _users[username]["role"]
			})

		elif cmd == "REGISTER":
			if len(command_parts) < 3:
				send_error(return_socket, "Invalid command format. Use: REGISTER <username> <password>")
				return
			
			username = command_parts[1]
			password = command_parts[2]
			
			if username in _users:
				send_error(return_socket, f"Username '{username}' is already taken")
				return
			
			if len(password) < 4:
				send_error(return_socket, "Password must be at least 4 characters")
				return
			
			_users[username] = {"password": password, "role": "user"}
			_subscriptions[username] = set()
			
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
			
			msg = {
				"id": _next_message_id,
				"board_id": board_id,
				"author": username,
				"content": content,
				"timestamp": time.strftime("%Y-%m-%d %H:%M"),
				"comments": []
			}
			_next_message_id += 1
			_messages.setdefault(board_id, []).insert(0, msg)
			
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
			
			# Find and edit the message
			for board_msgs in _messages.values():
				for msg in board_msgs:
					if msg["id"] == message_id:
						if msg["author"] != username:
							send_error(return_socket, "You can only edit your own messages")
							return
						msg["content"] = new_content + " (edited)"
						send_json(return_socket, {"success": True})
						return
			
			send_error(return_socket, "Message not found")

		elif cmd == "DELETE_MESSAGE":
			if len(command_parts) < 4:
				send_error(return_socket, "Invalid command format. Use: DELETE_MESSAGE <username> <message_id> <role>")
				return
			
			username = command_parts[1]
			try:
				message_id = int(command_parts[2])
			except ValueError:
				send_error(return_socket, "Message ID must be an integer")
				return
			
			role = command_parts[3]
			
			# Find and delete the message
			for board_msgs in _messages.values():
				for msg in board_msgs:
					if msg["id"] == message_id:
						if msg["author"] != username and role not in ("moderator", "admin"):
							send_error(return_socket, "You can only delete your own messages")
							return
						board_msgs.remove(msg)
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
			
			# Find the message and add comment
			for board_msgs in _messages.values():
				for msg in board_msgs:
					if msg["id"] == message_id:
						comment = {
							"id": _next_comment_id,
							"author": username,
							"content": content,
							"timestamp": time.strftime("%Y-%m-%d %H:%M")
						}
						_next_comment_id += 1
						msg["comments"].append(comment)
						send_json(return_socket, comment)
						return
			
			send_error(return_socket, "Message not found")

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
		import socket as sock_mod
		hostname = sock_mod.gethostname()
		hostip = sock_mod.gethostbyname(hostname)
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

def main():
	# input validation
	if int(sys.argv[1]) not in range(1023,49152):
		raise ValueError("Invalid port number, please enter a number between 1024 and 49152")

	# initialize global server variables
	init()

	# create a listening socket
	port = int(sys.argv[1])
	s = socket.socket()
	s.bind(("", port))  # input is a tuple with address and port as elements
	print("Hello. Created new process with listening port", port)

	# start a thread to gather user input
	input_thread = threading.Thread(target=input_loop, name="input_handler_thread", args=(s,), daemon=True)
	input_thread.start()  # start the thread
	print("Started thread", input_thread.name)

	# start a thread to accept connections
	connection_thread = threading.Thread(target=accept_connection, name="connection_thread", args=(s,), daemon=True)
	connection_thread.start()
	
    # start a thread to handle requests from clients
	request_thread = threading.Thread(target=handle_requests, name="request_handler_thread", args=(), daemon=True)
	request_thread.start()

	# wait to get exit signal
	while (exit == False):
		pass

	sys.exit()


if __name__ == "__main__":
	main()