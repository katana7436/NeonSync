import socket

for i in [13, 172, 173, 205, 244]:
    try:
        socket.create_connection((f'192.168.29.{i}', 5577), 1)
        print(f'FOUND: 192.168.29.{i}')
    except:
        pass