import socket  # import socket library         
import threading

s = socket.socket()  # next create a socket object    
port = 12345  # reserve listening port      

s.bind(('', port))  # bind to the listening port  

def capitalize_message(input_str):
    return input_str.upper()

# keep listening
s.listen(5)  # maximum pending connections is 5 
while True: 
  connection_socket, address = s.accept()  # establish connection socket
  thread = threading.Thread(target=capitalize_message, 
                            args=(connection_socket, address),
                            daemon=True)
  connection_socket.send('Thank you for connecting'.encode()) 
  connection_socket.close()  # close connection
  break
