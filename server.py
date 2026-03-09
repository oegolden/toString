"""
server.py - Server side of the toString messaging application.

This file handles incoming connections and requests from clients. 

Usage: python3 server.py <listening port>

"""

import socket
import threading
import sys

from messageBoard import MessageBoard
from user import User


helpmenu = """""
Command Manual: \n

help - Display this help menu \n
myip - Display the IP address of this process \n
myport - Display the port on which this process is listening for connections \n
list - Display a numbered list of all the connections this process is part of. \n
terminate <connection id> - Terminate the connection listed under the specified connection id. \n
exit - Close all connections and terminate this process. \n
"""""


# Functions for handling connections and requests from clients

""" send_message(): sends a message to the specified socket
inputs:
connection_socket - the socket to send the message to
message - the message to be sent
"""
def send_message(connection_socket, message):
	s = connection_socket

	# encode the message to bytes and send using the socket
	s.send(message.encode())
	print("Message", message, " sent to ", s.getpeername())
	
	if message == "close":
		print("Closing connection from client side")
		s.close()
	return



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
	

""" terminate_connection(): closes the connection at the specifiec connection_id and updates the dict of connections
inputs:
connection_id: the connection id of the connection to be closed
"""
def terminate_connection(connection_id):
	# conn = connection_dict[connection_id]
	conn = connection_dict[connection_id]['socket']
	send_message(conn, "close")
	del connection_dict[connection_id]
	print("Terminated connection", connection_id)
	return


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

		
""" handle_request(): processes a single request 
input:
request - the request to be processed
"""
def handle_request(request):
	# unpack info from the request
	command = request[0]
	command = command.split()
	return_socket = request[1]
	return_id = request[2]
	return_address = request[3]

	# run the requested command
	match command[0]:
		case "LOGIN":
			try:
				username = command[1]
				password = command[2]
			except:
				send_message(return_socket, "ERROR Invalid command format for LOGIN. Please use 'LOGIN <username> <password>'")
			if username not in _users:
				send_message(return_socket, "ERROR User does not exist")
			if password == _users[username].password:
				send_message(return_socket, "Login successful")
			else:
				send_message(return_socket, "ERROR Login failed")

		case "REGISTER":
			try:
				username = command[1]
				password = command[2]
			except:
				send_message(return_socket, "ERROR Invalid command format for REGISTER. Please use 'REGISTER <username> <password>'")
			if username in _users:
				send_message(return_socket, "ERROR Username already exists")
			else:
				_users[username] = User(username, password)
				send_message(return_socket, "Registration successful")

		case "LIST_BOARDS":
			send_message(return_socket, "json board")

		case "CREATE_BOARD":
			username = command[1]
			board_name = command[2]
			board_desc = command[3]
			if board_name in _boards:
				send_message(return_socket, "ERROR Board name already exists")
			else:
				_boards[board_name] = MessageBoard(username, board_name, board_desc)
				send_message(return_socket, "Board created successfully")

		case "SUBSCRIBE":
			username = command[1]
			board_name = command[2]
			if board_name not in _boards:
				send_message(return_socket, "ERROR Board does not exist")
			elif username in _boards[board_name].subscribers:
				send_message(return_socket, "ERROR Already subscribed to board")
			else:
				_boards[board_name].subscribe(username)
				send_message(return_socket, "Subscribed to board successfully")

		case "UNSUBSCRIBE":
			username = command[1]
			board_name = command[2]
			if board_name not in _boards:
				send_message(return_socket, "ERROR Board does not exist")
			else:
				_boards[board_name].unsubscribe(username)
				send_message(return_socket, "Unsubscribed from board successfully")
		case "GET_MESSAGES":
			username = command[1]
			board_name = command[2]
			if board_name not in _boards:
				send_message(return_socket, "ERROR Board does not exist")
			else:
				messages = _boards[board_name].get_messages(username)
				send_message(return_socket, messages)
			


# Functions for handling user input from the terminal

""" input_handler() - receives command input and does appropriate action
input: 
sock - the socket of the current device
"""
def input_handler(sock):
	command = input("Input command: ").split()

	if command[0] == "help":
		print(helpmenu)
		return

	elif command[0] == "myip":
		hostname = socket.gethostname()
		hostip = socket.gethostbyname(hostname)
		print("The IPv4 address of this process is ", hostip)
		return(hostip)
	
	elif command[0] == "list":
		if len(connection_dict) == 0:
			print("No current connections")
		else:
			print("Current connections: ")
			for conn_id in connection_dict.keys():
				conn = connection_dict[conn_id]['socket']
				print("Connection ID:", conn_id, " | IP Address:", conn.getpeername()[0], " | Listening Port:", connection_dict[conn_id]['listening_port'])
		return

	elif command[0] == "myport":
		portnum = sock.getsockname()[1]
		print("The listening socket of this process is ", portnum)
		return
	
	# terminate <connection id>
	elif command[0] == "terminate":
		connection_id = int(command[1])

		# verify the given connection ID exists
		global connection_dict
		if connection_id not in connection_dict.keys():
			print("Invalid connection ID, please try again")
			return
		
		conn = connection_dict[int(connection_id)]['socket']
		
		terminate_connection(connection_id)
		return
		
	elif command[0] == "adduser":
		username = command[1]
		password = command[2]
		if username in _users:
			print("ERROR Username already exists")
		else:
			_users[username] = user.User(username, password)
			print("User added successfully")
		return
	
	elif command[0] == "createboard":
		board_name = command[1]
		board_desc = command[2]
		if board_name in _boards:
			print("ERROR Board name already exists")
		else:
			_boards[board_name] = messageBoard.MessageBoard(board_name, board_desc)
			print("Board created successfully")
		return

	elif command[0] == "exit":
		for conn_id in list(connection_dict.keys()):
			print("looping through connection_dict keys, currently at", conn_id)
			conn = connection_dict[int(conn_id)]['socket']
			print("found the socket" if conn else "did not find the socket")
			if conn.getsockname()[0] != socket.gethostbyname(socket.gethostname()) or conn.getsockname()[1] != sock.getsockname()[1]:
				terminate_connection(conn_id)

		# set exit flag to true
		global exit
		exit = True

	else:
		print("Invalid command, please try again")
		return
	return


""" input_loop(): continuously handle user input until done
inputs:
sock - the socket of this device
"""
def input_loop(sock):
	while True:
		input_handler(sock)


# Server startup and main loop

""" init(): initializes global variables for the server
"""
def init():
	global _users, _boards
	_users = {} # username: User object
	_boards = {} # board name: MessageBoard object

	global exit, lock
	exit = False
	lock = threading.Lock()

	global request_queue, connection_dict, connection_counter
	request_queue = [] 
	connection_dict = {}
	connection_counter = 0

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