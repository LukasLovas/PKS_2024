import queue
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
        self.header_buffer = {}
        self.arq_queue = queue.Queue()
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
        fragments = [message[i:i + self.max_fragment_size] for i in range(0, len(message), self.max_fragment_size)]
        sent_fragments = {}
        for i, fragment in enumerate(fragments):
            next_fragment = 1 if i < len(fragments) - 1 else 2
            header = Header.create_header(packet_type, fragment, fragment_order=i + 1, next_fragment=next_fragment)
            self.socket.sendto(header.get_bytes_from_header(), self.peer.connection_tuple())
            print(f"{Fore.LIGHTCYAN_EX}Sent fragment {i + 1}/{len(fragments)}")
            print(header)
            sent_fragments[header.fragment_order] = header

        self.handle_response(sent_fragments)

    def handle_response(self, sent_fragments):
        response = self.arq_queue.get()
        if response.packet_type == 9:
            self.send_ack(self.peer.peer_ip, self.peer.peer_port)
            print("ARQ received")
            missing_fragments = response.data.split("|")
            for fragment_number in missing_fragments:
                header = sent_fragments.get(fragment_number)
                self.socket.sendto(header.get_bytes_from_header(), self.peer.connection_tuple())
            self.handle_response(sent_fragments)
        else:
            print("No problem with fragments.")

    def send_syn(self, ip: str, port: int) -> None:
        header = Header.create_header(1, None)
        header_data = header.get_bytes_from_header()
        self.socket.sendto(header_data, (ip, port))
        print(f"{Fore.RED}SYN")

    def send_syn_ack(self, ip: str, port: int) -> None:
        header = Header.create_header(7, None)
        header_data = header.get_bytes_from_header()
        self.socket.sendto(header_data, (ip, port))
        print(f"{Fore.YELLOW}SYN-ACK")

    def send_ack(self, ip: str, port: int) -> None:
        header = Header.create_header(6, None)
        header_data = header.get_bytes_from_header()
        self.socket.sendto(header_data, (ip, port))
        print(f"{Fore.GREEN}ACK")

    def listen(self, buffer_size: int = 1500) -> str:
        try:
            message, address = self.socket.recvfrom(buffer_size)
            sender_ip, sender_port = address
            header = Header.get_header_from_bytes(message)
        except OSError:
            print("Error receiving message")
            return ""
        if self.peer is None:
            self.handle_handshake(header, sender_ip, sender_port)
        else:
            if header.packet_type == 6:
                self.arq_queue.put(header)
                print("ACK received, putting in queue")
            if header.packet_type == 2:
                self.header_buffer[header.fragment_order] = header
                print(f"Added header n. {header.fragment_order} to header buffer")
                if header.next_fragment == 2:  # If last, reassemble message
                    full_message = ''.join(self.header_buffer[i].data for i in self.header_buffer)
                    print(f"{Fore.LIGHTMAGENTA_EX}Receive full message: {Fore.RESET}{full_message}")
                    self.send_ack(self.peer.connection_tuple[0], self.peer.connection_tuple[1])
                    del self.header_buffer
                    print("Header buffer deleted.")
                    return full_message

    def handle_handshake(self, header, sender_ip, sender_port):
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

    def start_listening_thread(self) -> None:
        listen_thread = threading.Thread(target=self.listen_handshake, daemon=True)
        listen_thread.start()

    def listen_handshake(self):
        while not self.handshake_done:
            self.listen()

    def close_socket(self):
        self.socket.close()
