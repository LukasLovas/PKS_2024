import socket
import threading
from colorama import init, Fore

init(autoreset=True)


class User:
    def __init__(self, ip: str, port: int) -> None:
        self.ip = ip
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((ip, port))
        self.peer = None
        self.handshake_done = False
        print(f"User listening on {self.ip}:{self.port}")

    def set_peer(self, ip: str, port: int) -> None:
        # Peer set after initialization
        self.peer = self.Peer(ip, port)
        print(f"Peer set to {self.peer.peer_ip}:{self.peer.peer_port}")

    class Peer:
        def __init__(self, ip: str, port: int) -> None:
            self.peer_ip = ip
            self.peer_port = port

        def connection_tuple(self):
            return self.peer_ip, self.peer_port

    def send(self, data: str) -> None:
        if self.peer is None:
            print("No peer set. Cannot send message.")
        else:
            self.socket.sendto(data.encode('utf-8'), self.peer.connection_tuple())
            print(f"{Fore.LIGHTCYAN_EX}Sent: {Fore.RESET}{data}")

    def send_syn(self, ip: str, port: int) -> None:
        self.socket.sendto("SYN".encode('utf-8'), (ip, port))
        print(f"{Fore.RED}SYN")

    def send_syn_ack(self, ip: str, port: int) -> None:
        self.socket.sendto("SYN ACK".encode('utf-8'), (ip, port))
        print(f"{Fore.YELLOW}SYN-ACK")

    def send_ack(self, ip: str, port: int) -> None:
        self.socket.sendto("ACK".encode('utf-8'), (ip, port))
        print(f"{Fore.GREEN}ACK")

    def listen(self, buffer_size: int = 1024) -> str:
        try:
            message, address = self.socket.recvfrom(buffer_size)
            sender_ip, sender_port = address
            decoded_message = message.decode('utf-8')
        except OSError:
            print("Error receiving message")
            return ""
        if self.peer is None:
            if decoded_message == "SYN":
                print(f"{Fore.LIGHTGREEN_EX}OK!")
                self.send_syn_ack(sender_ip, sender_port)
            elif decoded_message == "SYN ACK":
                print(f"{Fore.LIGHTGREEN_EX}OK!")
                self.send_ack(sender_ip, sender_port)
                self.set_peer(sender_ip, sender_port)
                self.handshake_done = True
            elif decoded_message == "ACK":
                print(f"{Fore.LIGHTGREEN_EX}OK!")
                self.set_peer(sender_ip, sender_port)
                self.handshake_done = True
        else:
            print(f"{Fore.LIGHTMAGENTA_EX}Receive: {Fore.RESET}{decoded_message}")

        return decoded_message

    def start_listening_thread(self) -> None:
        listen_thread = threading.Thread(target=self.listen_handshake, daemon=True)
        listen_thread.start()

    def listen_handshake(self):
        while not self.handshake_done:
            self.listen()

    def close_socket(self):
        self.socket.close()
