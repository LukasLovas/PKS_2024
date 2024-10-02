import socket

SERVER_IP = "147.175.163.35"  # Server host IP (local IP for testing)
SERVER_PORT = 50601  # Server port for receiving communication


class Server:
    def __init__(self, ip, port) -> None:
        # Create a UDP socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Bind the socket to the server's IP and port
        self.sock.bind((ip, port))  # Needs to be a tuple (string, int)
        self.client = None

    def receive(self):
        data = None
        if self.client is None:
            while data is None:
                data, addr = self.sock.recvfrom(1024)
                print(data.decode("utf-8"))
                if data.decode("utf-8") == "SYN":
                    self.sock.sendto(b"SYN ACK", addr)
                    print("SYNACK sent")
                    data = None
                    while data is None:
                        data, addr = self.sock.recvfrom(1024)
                        print(data.decode("utf-8"))
                        if data.decode("utf-8") == "ACK":
                            print("Connection successful.")
                            data = "empty"
                            break
                else:
                    data = None

        while data is None:
            data, self.client = self.sock.recvfrom(1024)  # Buffer size is 1024 bytes
            print(f"Received message: {data}")
        # Return the data as a decoded string using UTF-8 encoding
        return str(data, encoding="utf-8")

    def send_response(self):
        # Send a response message back to the client
        self.sock.sendto(b"", self.client)

    def send_last_response(self):
        # Send a final response message back to the client before closing the connection
        self.sock.sendto(b"End connection message received... closing connection", self.client)

    def quit(self):
        # Correctly close the socket
        self.sock.close()
        print("Server closed...")


if __name__ == "__main__":
    server = Server(SERVER_IP, SERVER_PORT)
    data = "empty"

    # Keep receiving messages until "End connection" is received
    while data != "End connection":
        if data != "empty":
            server.send_response()
        data = server.receive()

    # Send the final response and close the server
    server.send_last_response()
    server.quit()
