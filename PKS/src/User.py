import socket
import threading
from colorama import init, Fore
from Header import Header

init(autoreset=True)


class User:
    def __init__(self, ip: str, port: int, max_fragment_size=1464) -> None:
        self.ip = ip
        self.port = port
        self.max_fragment_size = max_fragment_size
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

    def send(self, message: str, packet_type: int):
        message_bytes = message.encode('utf-8')
        if len(message_bytes) <= self.max_fragment_size:
            print("True")
            header = Header.create_header(packet_type, message, fragment_order=1, next_fragment=2)
            self.socket.sendto(header.get_bytes_from_header(), self.peer.connection_tuple())
            print(f"{Fore.LIGHTCYAN_EX}Sent header: {Fore.RESET}{header}")
        else:
            fragments = [message[i:i + self.max_fragment_size] for i in range(0, len(message), self.max_fragment_size)]
            for i, fragment in enumerate(fragments):
                next_fragment = 1 if i < len(fragments) - 1 else 2
                header = Header.create_header(packet_type, fragment, fragment_order=i + 1, next_fragment=next_fragment)
                self.socket.sendto(header.get_bytes_from_header(), self.peer.connection_tuple())
                print(f"{Fore.LIGHTCYAN_EX}Sent fragment {i + 1}/{len(fragments)}")

    def send_syn(self, ip: str, port: int) -> None:
        header = Header.create_header(1, None)
        header_data = header.get_bytes_from_header()
        self.socket.sendto(header_data, (ip, port))
        print(f"{Fore.RED}SYN")

    def send_syn_ack(self, ip: str, port: int) -> None:
        header = Header.create_header(8, None)
        header_data = header.get_bytes_from_header()
        self.socket.sendto(header_data, (ip, port))
        print(f"{Fore.YELLOW}SYN-ACK")

    def send_ack(self, ip: str, port: int) -> None:
        header = Header.create_header(6, None)
        header_data = header.get_bytes_from_header()
        self.socket.sendto(header_data, (ip, port))
        print(f"{Fore.GREEN}ACK")

    def send_fragment_limit_update(self,value):
        header = Header.create_header(8, value)
        self.socket.sendto(header.get_bytes_from_header(), self.peer.connection_tuple())
        print(f"{Fore.LIGHTCYAN_EX}Sent fragment limit update: {self.max_fragment_size}")

    def listen(self, buffer_size: int = 1024) -> str:
        try:
            message, address = self.socket.recvfrom(buffer_size)
            sender_ip, sender_port = address
            header = Header.get_header_from_bytes(message)
        except OSError:
            print("Error receiving message")
            return ""

        if self.peer is None:
            if header.packet_type == 1:
                print(f"{Fore.LIGHTGREEN_EX}SYN")
                self.send_syn_ack(sender_ip, sender_port)
            elif header.packet_type == 7:
                print(f"{Fore.LIGHTGREEN_EX}SYN-ACK")
                self.send_ack(sender_ip, sender_port)
                self.set_peer(sender_ip, sender_port)
                self.handshake_done = True
            elif header.packet_type == 6:
                print(f"{Fore.LIGHTGREEN_EX}ACK")
                self.set_peer(sender_ip, sender_port)
                self.handshake_done = True
        else:
            print(f"{Fore.LIGHTMAGENTA_EX}Receive: {Fore.RESET}{header}")

        return header.data

    def start_listening_thread(self) -> None:
        listen_thread = threading.Thread(target=self.listen_handshake, daemon=True)
        listen_thread.start()

    def listen_handshake(self):
        while not self.handshake_done:
            self.listen()

    def close_socket(self):
        self.socket.close()
