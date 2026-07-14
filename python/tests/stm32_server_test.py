import socket

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

server.bind(("192.168.30.1", 5000))
server.listen(1)

print("Waiting STM32...")

conn, addr = server.accept()

print("Connected:", addr)

while True:

    data = conn.recv(1024)

    if not data:
        break

    print("RAW :", data)
    print("TEXT:", data.decode(errors="ignore"))