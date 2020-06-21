#!/usr/bin/python3

import socket
import sys
from zlib import decompress

HOST, PORT =sys.argv[1], 1001
data = " ".join(sys.argv[2:])

# SOCK_DGRAM is the socket type to use for UDP sockets
sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)

# As you can see, there is no connect() call; UDP has no connections.
# Instead, data is directly sent to the recipient via sendto().
sock.sendto(bytes(data + "\n", "utf-8"), (HOST, PORT))
received = str((sock.recv(1024), "utf-8"))

print("Sent:     {}".format(data))
print("Received: {}".format(received))
