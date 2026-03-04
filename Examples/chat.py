import socket
import threading
import sys
import base64
import os

exit = False

connection_dict = {}
connection_counter = 0 

helpmenu = """""
Command Manual: \n

myip - Display the IP address of this process \n
myport - Display the port on which this process is listening for connections \n
connect <destination> <port no> - Establish a new TCP connection to the specified destination at the specified port number.\n
list - Display a numbered list of all the connections this process is part of. \n
terminate <connection id> - Terminate the connection listed under the specified connection id. \n
send <connection id> <message> - Send the message to the host on the connection specified by the connection id. \n
exit - Close all connections and terminate this process. \n

"""""

""" encode_img: encode the given image file as a string

"""
def encode_img(img_file):
	with open(img_file, "rb") as img:
		b64_byte = base64.b64encode(img.read())
		b64_str = b64_str.decode(b64_byte)
	return b64_str

def decodeImg(img_str):
	img_bytes= base64.b64decode(img_str)
	return img_bytes

""" Connect: opens a connection with another device at the specified ip and port
inputs: 
ip - the IP address of the device to connect to
port - the port number to connect to
"""
def connect(ip, port):
	global connection_counter
	print(f"Opened connection {connection_counter}")
	s = socket.socket()  # next create a socket object
	s.connect((ip, port))  # connect to the server on local computer
	# connection_dict[connection_counter] = s 
	connection_dict[connection_counter] = {
		"socket": s,
		"listening_port": s.getpeername()[1],
	}
	connection_counter += 1

	# keep getting user input
	thread = threading.Thread(target=handle_connection, args=(s, (connection_counter-1), s.getsockname()), daemon=True)
	thread.start()


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

def send_textfile(connection_socket, filepath):
	try: 
		with open(filepath, 'r', encoding='utf-8') as f:
				file_content = f.read()
		file_name = os.path.basename(filepath)
		file_length = len(file_content)
		start_marker = f"FILE_START:TEXT:{file_name}:{file_length}"
		end_marker = f"FILE_END"

		print(f"Beginning file transfer with header {start_marker}")
		# connection_socket.sendall(start_marker.encode())
		connection_socket.send(start_marker.encode())
		print("Header complete, transmitting data")
		connection_socket.sendall(file_content.encode('utf-8'))
		print("Finishing file transfer, sending end-of-file signal")
		connection_socket.sendall(end_marker.encode('utf-8'))
		print(f"Finished sending text file {file_name}")
	except Exception:
		print(f"Error: couldn't send {filepath}")
	
def send_imagefile(connection_socket, filepath):
	# try: 
	print("trying to send img")
	with open(filepath, 'rb') as f:
			# file_content = f.read()
			file_content = (base64.b64encode(f.read()))
	print("opened image file")
	# encoded_content = encode_img(file_content)
	# print("encoded image file")

	# encoded_content = encode_img(encoded_content)
	# with open(filepath, 'rb', encoding='utf-8') as f:
	# 		file_content = f.read()
	# print("opened image file")
	print("encoded image file")

	file_name = os.path.basename(filepath)
	file_length = len(file_content)
	start_marker = f"FILE_START:IMAGE:{file_name}:{file_length}"
	end_marker = f"FILE_END"

	print(f"Beginning file transfer with header {start_marker}")
	connection_socket.sendall(start_marker.encode('utf-8'))
	print("Header complete, transmitting data")
	connection_socket.sendall(file_content)
	print("Finishing file transfer, sending end-of-file signal")
	connection_socket.sendall(end_marker.encode('utf-8'))
	print(f"Finished sending image file {file_name}")
	# except Exception:
	# 	print(f"Error: couldn't send {filepath}")
	


def send_file(connection_socket, filepath):

	if not os.path.exists(filepath):
		print(f"Filepath Error: couldn't find filepath {filepath}")
		return
	else: 
		file_type = filepath.split('.')[1] # after the .
		print(f"file type is {file_type}")
		if file_type in ['jpg', 'png', 'jpeg']:
			print('sending image')
			send_imagefile(connection_socket, filepath) # TODO THIS ISNT IMPLEMETNED YET
		else:
			print('sending text')
			send_textfile(connection_socket, filepath)

def receive_file(connection_socket, address, message):
	# get the length of the file
	prefix = message.split(":")
	file_type = prefix[1] # TEXT or IMAGE
	file_name = prefix[2]
	file_length = int(prefix[3]) 
	received_length = 0
	file_content = ""
	print(f"Receiving a {file_type} named {file_name} of size {file_length}")

	# keep receiving until the full file is received
	print_i = 0
	while received_length < file_length:
		data = connection_socket.recv(8)
		if file_type == "IMAGE":
			file_chunk = data.decode()
		else:
			file_chunk = data.decode()
		file_content += file_chunk
		received_length += len(file_chunk)
		if print_i % 1024 == 0:
			print(f"Received {received_length} of {file_length} chars")
		print_i +=1

	data = connection_socket.recv(8)
	if file_type == "IMAGE":
		file_chunk = data.decode()
	else:
		file_chunk = data.decode()
	file_content += file_chunk
	received_length += len(file_chunk)
	print(f"Received {received_length} of {file_length} chars")

	suffix = file_content[-8:]
	file_content = file_content[:-8] # don't write the file marker
	print(f"suffix is now {suffix}")
	print("Ready to write out")

	modfile_name = "copy_of_" + file_name
	if suffix == "FILE_END":
		if file_type == "TEXT":
		
			with open(modfile_name, 'w', encoding='utf-8') as received_file:
				received_file.write(file_content)
			
		elif file_type == "IMAGE":
			imgData = decodeImg(file_content)
			
			with open(modfile_name, 'wb') as imgFile:
				imgFile.write(imgData)
				# imgFile.write(file_content)



				# f = open('encode.bin', 'rb')  # Open encoded file.
				# byte = f.read()  # Read data.
				# f.close()

			# decode = open('stringtoimage.webp', 'wb')  # Open image file to save.
			# decode.write(base64.b64decode(imgFile))  # Decode and write data.
			# decode.close()
		else:
			raise Exception("Unknown file type")
	else:
		raise Exception("Did not receive END suffix after file transfer")	
	
	return file_name


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

		# decode the received data to string and print out
		message = data.decode()

		# stop checking messages and break
		if message == "close":
			break

		# receive file from file transfer
		if message.startswith("FILE_START"):
			file_name = receive_file(connection_socket, address, message)
			print("File received from", address[0])
			print("Sender's port:", address[1])
			print("File name:", file_name)

		else: 
			# else print the message received
			print("Message received from", address[0])
			print("Sender's port:", address[1])
			print("Message: ", message)


	connection_socket.close()
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

""" input_handler() - receives command input and does appropriate action
input: 
sock - the socket of the current device
"""
def input_handler(sock):
	command = input("Input command: ")

	if type(command) != str:
		print("Invalid input, please enter a string")
		return

	if command == "help":
		print(helpmenu)
		return

	elif command == "myip":
		hostname = socket.gethostname()
		hostip = socket.gethostbyname(hostname)
		print("The IPv4 address of this process is ", hostip)
		return(hostip)
	
	elif command == "list":
		if len(connection_dict) == 0:
			print("No current connections")
		else:
			print("Current connections: ")
			for conn_id in connection_dict.keys():
				conn = connection_dict[conn_id]['socket']
				print("Connection ID:", conn_id, " | IP Address:", conn.getpeername()[0], " | Listening Port:", connection_dict[conn_id]['listening_port'])
		return

	elif command == "myport":
		portnum = sock.getsockname()[1]
		print("The listening socket of this process is ", portnum)
		return
	
	elif command[0:7] == "connect":	
		# split input to get <destination> and <port> arguments
		args = command.split()

		# input validation
		if (len(args) < 3):
			print("Invalid arguments: Must provide IP address and port number.")
			return
		ip = args[1]
		port = int(args[2])

		# validate inputted port number
		if port < 1024 or port > 65535:
			print("Invalid port number, please enter a number between 1024 and 65535")
			return
		elif port == sock.getsockname()[1]:
			print("Cannot connect to self")
			return
		
		connect(ip, port)

	elif command[0:4] == "send" and command[0:8] != "sendfile":
		# split input to get <connection id> and <message> arguments
		args = command.split()

		# input validation
		if (len(args) < 3): 
			print("Invalid arguments: Must provide connection id and message.")
			return
		
		connection_id = int(args[1])
		message = " ".join(args[2:])

		# verify the given connection ID exists
		if connection_id not in connection_dict.keys():
			print("Invalid connection ID, please try again")
			return

		# conn = connection_dict[int(connection_id)]
		conn = connection_dict[int(connection_id)]['socket']
		# if conn.getsockname()[0] == socket.gethostbyname(socket.gethostname()) and conn.getsockname()[1] == sock.getsockname()[1]:
		# 	print("Cannot send message to self")
		# 	return

		send_message(conn, message)
		return
	

	elif command[0:8] == "sendfile":
		# sendfile <connection id> <pathname>
		args = command.split()

		connection_id = int(args[1])
		conn = connection_dict[int(connection_id)]['socket']
		filename = args[2]
		
		send_file(conn, filename)
		return

	elif command[0:9] == "terminate":
		# split input to get <connection id> argument
		args = command.split()
		connection_id = int(args[1])

		# verify the given connection ID exists
		if connection_id not in connection_dict.keys():
			print("Invalid connection ID, please try again")
			return
		
		conn = connection_dict[int(connection_id)]['socket']
		# if conn.getsockname()[0] == socket.gethostbyname(socket.gethostname()) and conn.getsockname()[1] == sock.getsockname()[1]:
		# 	print("Cannot terminate connection with self")
		# 	return
		
		terminate_connection(connection_id)
		return
		
	elif command == "exit":
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


def main():
	# input validation
	if int(sys.argv[1]) not in range(1023,49152):
		raise ValueError("Invalid port number, please enter a number between 1024 and 49152")

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

	# wait to get exit signal
	while (exit == False):
		pass

	sys.exit()


if __name__ == "__main__":
	main()