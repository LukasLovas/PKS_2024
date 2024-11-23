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
        self.peer = self.Peer(ip, port)
        print(f"Peer set to {self.peer.peer_ip}:{self.peer.peer_port}")

    class Peer:
        def __init__(self, ip: str, port: int) -> None:
            self.peer_ip = ip
            self.peer_port = port

        def connection_tuple(self):
            return self.peer_ip, self.peer_port

    def fragment_message(self, message: str, packet_type: int):
        fragments = {
            i + 1: Header.create_header(packet_type, message[i:i + self.max_fragment_size],
                                        fragment_order=i + 1,
                                        next_fragment=(1 if i < len(message) // self.max_fragment_size else 2))
            for i in range(0, len(message), self.max_fragment_size)
        }
        return fragments

    def send_fragments(self, fragments: dict):
        print(f"{Fore.YELLOW}# of fragments to send: {len(fragments)}")
        for fragment_order, header in fragments.items():
            self.send_fragment(header)

    def send_fragment(self, header: Header):
        self.socket.sendto(header.get_bytes_from_header(), self.peer.connection_tuple())
        print(f"{Fore.LIGHTCYAN_EX}Sent fragment {header.fragment_order}{Fore.RESET}")
        print(f"{Fore.LIGHTCYAN_EX}{header}")

    def send(self, message: str, packet_type: int):
        fragments = self.fragment_message(message, packet_type)
        self.send_fragments(fragments)
        self.handle_response(fragments)

    def handle_response(self, sent_fragments):
        response = self.arq_queue.get()
        print(f"{Fore.YELLOW}Removed {response.packet_type} from queue")
        if response.packet_type == 9:
            missing_fragments = response.data.split("|") if "|" in response.data else response.data
            missing_fragments = [int(fragment_number) for fragment_number in missing_fragments]
            for fragment_number in missing_fragments:
                header = sent_fragments.get(fragment_number)
                if header:
                    header.crc = header.calculate_crc()
                    self.send_fragment(header)
            self.handle_response(sent_fragments)
        elif response.packet_type == 6:
            print(f"{Fore.GREEN}ACK {Fore.MAGENTA}received for response")

    def receive_message(self):
        try:
            message, address = self.socket.recvfrom(1500)
            sender_ip, sender_port = address
            header = Header.get_header_from_bytes(message)
            return header, sender_ip, sender_port
        except OSError:
            print(f"{Fore.MAGENTA}Error receiving message")
            return None, None, None

    def listen(self):
        header, sender_ip, sender_port = self.receive_message()
        if header.calculate_crc() == header.crc:  # Received a header with already calculated crc, calculate and compare
            if self.peer is None:
                self.handle_handshake(header, sender_ip, sender_port)
            else:
                print(f"{Fore.LIGHTMAGENTA_EX}{header}")
                if header.packet_type == 6:
                    self.arq_queue.put(header)
                    print(f"{Fore.YELLOW}Put {header.packet_type} to queue")
                    print(f"{Fore.GREEN} ACK {Fore.MAGENTA} received")
                if header.packet_type == 9:
                    self.arq_queue.put(header)
                    print(f"{Fore.YELLOW}Put {header.packet_type} to queue")
                if header.packet_type == 2:
                    self.header_buffer[header.fragment_order] = header
                    if header.next_fragment == 2:  # If last, reassemble message
                        full_message = ''.join(self.header_buffer[i].data for i in self.header_buffer)
                        print(f"{Fore.MAGENTA}Received full message: {Fore.RESET}{full_message}")
                        self.send_ack(self.peer.peer_ip, self.peer.peer_port)
                        self.header_buffer.clear()
                        print(f"{Fore.YELLOW}Header buffer deleted.")
                        return full_message
        else:
            print(f"{Fore.LIGHTMAGENTA_EX}{header}")
            self.send_arq(str(header.fragment_order))

    def send_arq(self, data):
        print(f"{Fore.RED}ARQ{Fore.LIGHTCYAN_EX} sent")
        fragments = self.fragment_message(data, 9)
        self.send_fragments(fragments)

    def handle_handshake(self, header, sender_ip, sender_port):
        if header.packet_type == 1:
            print(f"{Fore.LIGHTGREEN_EX}SYN {Fore.MAGENTA} received")
            self.send_syn_ack(sender_ip, sender_port)
        elif header.packet_type == 7:
            print(f"{Fore.LIGHTGREEN_EX}SYN-ACK {Fore.MAGENTA} received")
            self.send_ack(sender_ip, sender_port)
            self.set_peer(sender_ip, sender_port)
            self.handshake_done = True
        elif header.packet_type == 6:
            print(f"{Fore.LIGHTGREEN_EX}ACK {Fore.MAGENTA} received")
            self.set_peer(sender_ip, sender_port)
            self.handshake_done = True

    def send_syn(self, ip: str, port: int) -> None:
        header = Header.create_header(1, None)
        header_data = header.get_bytes_from_header()
        self.socket.sendto(header_data, (ip, port))
        print(f"{Fore.RED}SYN {Fore.LIGHTCYAN_EX}sent")

    def send_syn_ack(self, ip: str, port: int) -> None:
        header = Header.create_header(7, None)
        header_data = header.get_bytes_from_header()
        self.socket.sendto(header_data, (ip, port))
        print(f"{Fore.YELLOW}SYN-ACK {Fore.LIGHTCYAN_EX}sent")

    def send_ack(self, ip: str, port: int) -> None:
        header = Header.create_header(6, None)
        header_data = header.get_bytes_from_header()
        self.socket.sendto(header_data, (ip, port))
        print(f"{Fore.GREEN}ACK {Fore.LIGHTCYAN_EX}sent")

    def start_listening_thread(self) -> None:
        listen_thread = threading.Thread(target=self.listen_handshake, daemon=True)
        listen_thread.start()

    def listen_handshake(self):
        while not self.handshake_done:
            self.listen()

    def close_socket(self):
        self.socket.close()
