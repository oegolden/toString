import socket  # import socket library         

s = socket.socket()  # next create a socket object            

port = 12345  # use the listening port on the server

# connect to the server on local computer 
s.connect(('127.0.0.1', port)) 

while True:
    message = input(">")
    s.send(message.encode())
    # receive data from the server and decoding to get the string.
    # print (s.recv(1024).decode())
    break

# close the connection 
s.close()
