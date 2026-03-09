"""
client.py - Client side of the toString messaging application.

This file connects to the server and allows the user to send commands and receive responses. It should integrate with
the gui.py file to provide a user-friendly interface for the client.

Usage: python3 client.py <server IP> <server port>
"""

import socket
import time
import random

server_ip = '127.0.0.1'
server_port = 1236


def send_request(request):
    server_socket.send(request.encode())

    # wait for server response
    response = server_socket.recv(1024).decode()
    return response

def login(username, password):
    response = send_request(f"LOGIN {username} {password}").split()
    if response[0] == "ERROR":
        raise Exception(response[1])
    
    username = response[0]
    role = response[1]
    
    return {"username": username, "role": role}

def init():
    global server_socket
    server_socket = socket.socket()

    # connect to the server using the known listening port
    server_socket.connect((server_ip, server_port))


    # keep getting user input
    while True:
        message = input(">")

        # encode the message to bytes and send using the socket
        server_socket.send(message.encode())

        # print replies from server
        data = server_socket.recv(1024)
        print(data.decode())
        
        if message == "close":
            break

    server_socket.close()
        
def main():
    init()

if __name__ == "__main__":
    main()