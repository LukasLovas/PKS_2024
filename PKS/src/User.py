import os.path
import queue
import socket
import threading
import time

from PyQt6.QtWidgets import QFileDialog
from colorama import init, Fore
from Header import Header

init(autoreset=True)

DELIMITER = "|:|"

class User:
    def __init__(self, ip: str, port: int, max_fragment_size=1462) -> None:
        self.ip = ip
        self.port = port
        self.max_fragment_size = max_fragment_size
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((ip, port))
        self.peer = None
        self.handshake_done = False
        self.header_buffer = {}
        self.response_queue = queue.Queue()
        self.keepalive_running = False
        self.heartbeats = 0
        self.chat_gui = None
        self.current_filename = None
        self.file_directory = self.setup_file_dir()
        print(f"User listening on {self.ip}:{self.port}")

    def setup_file_dir(self, directory_name="received_files"):
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        file_dir_path = os.path.join(project_root, directory_name)
        if not os.path.exists(file_dir_path):
            os.makedirs(file_dir_path)
            print(f"Created file directory: {file_dir_path}")
        return file_dir_path

    def set_peer(self, ip: str, port: int) -> None:
        self.peer = self.Peer(ip, port)
        print(f"Peer set to {self.peer.peer_ip}:{self.peer.peer_port}")

    class Peer:
        def __init__(self, ip: str, port: int) -> None:
            self.peer_ip = ip
            self.peer_port = port

        def connection_tuple(self):
            return self.peer_ip, self.peer_port

    def fragment_message(self, data_encoded: bytes, packet_type: int) -> dict:
        fragment_size = self.max_fragment_size
        total_fragments = (len(data_encoded) + fragment_size - 1) // fragment_size
        fragments = {}

        for i in range(total_fragments):
            fragment_order = i + 1
            fragment_data = data_encoded[i * fragment_size:(i + 1) * fragment_size]

            fragments[fragment_order] = Header.create_header(
                packet_type,
                fragment_data,
                fragment_order=fragment_order,
                next_fragment=(1 if fragment_order < total_fragments else 2)
            )

        return fragments

    def send_fragments(self, fragments: dict):
        print(f"{Fore.YELLOW}# of fragments to send: {len(fragments)}")
        for fragment_order, header in fragments.items():
            self.send_fragment(header)

    def send_fragment(self, header: Header):
        self.socket.sendto(header.get_bytes_from_header_ex_data(), self.peer.connection_tuple())
        # print(f"{Fore.LIGHTCYAN_EX}Sent fragment {header.fragment_order}{Fore.RESET}")
        # print(f"{Fore.LIGHTCYAN_EX}{header}")

    def send(self, message: str, packet_type: int):
        data_encoded = message.encode("utf-8")
        fragments = self.fragment_message(data_encoded, packet_type)
        self.send_fragments(fragments)

    def send_file(self, file_path):
        filename = os.path.basename(file_path)
        with open(file_path, "rb") as file:
            file_data = file.read()
            header_data = f"{filename}{DELIMITER}".encode("utf-8") + file_data
            fragments = self.fragment_message(header_data, packet_type=3)
            self.send_fragments(fragments)

    def receive_message(self):
        try:
            message, address = self.socket.recvfrom(1500)
            sender_ip, sender_port = address
            header = Header.get_header_from_bytes(message)
            return header, sender_ip, sender_port
        except ConnectionResetError:
            self.handle_connection_loss()
        except OSError as e:
            print(f"Error receiving message: {e}")

    def listen(self):
        header, sender_ip, sender_port = self.receive_message()
        if header.calculate_crc() == header.crc:  # Received a header with already calculated crc, calculate and compare
            if self.peer is None:
                self.handle_handshake(header, sender_ip, sender_port)
            else:
                #print(f"{Fore.LIGHTMAGENTA_EX}{header}")
                if header.packet_type == 2: #Message
                    header.data = header.data
                    self.header_buffer[header.fragment_order] = header
                    if header.next_fragment == 2:  # If last, reassemble message
                        full_data_encoded = b''.join(self.header_buffer[i] for i in sorted(self.header_buffer))
                        full_message = full_data_encoded.decode("utf-8")  # Decode to string
                        print(f"{Fore.MAGENTA}Received full message: {Fore.RESET}{full_message}")
                        self.send_ack(self.peer.peer_ip, self.peer.peer_port)
                        self.header_buffer.clear()
                        print(f"{Fore.YELLOW}Header buffer deleted.")
                        return full_message
                if header.packet_type == 3: #File
                    if header.fragment_order == 1:
                        data_split = header.data.split(DELIMITER)
                        self.current_filename = data_split[0].decode("utf-8")
                        header.data = data_split[1] if len(data_split) > 1 else b""
                    else:
                        header.data = header.data
                    self.header_buffer[header.fragment_order] = header
                    print(f"received fragment no. {header.fragment_order} ")
                    if header.next_fragment == 2:
                        full_file_data = b"".join(self.header_buffer[i].data for i in self.header_buffer)
                        self.save_file(self.current_filename, full_file_data)
                if header.packet_type == 4:
                    self.heartbeats = 0
                if header.packet_type == 5:
                    self.response_queue.put(header)
                    #print(f"{Fore.YELLOW}Put {header.packet_type} to queue")
                    print(f"{Fore.GREEN} ACK {Fore.MAGENTA} received")
                if header.packet_type == 7:
                    self.response_queue.put(header)
                    #print(f"{Fore.YELLOW}Put {header.packet_type} to queue")
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
        elif header.packet_type == 6:
            print(f"{Fore.LIGHTGREEN_EX}SYN-ACK {Fore.MAGENTA} received")
            self.send_ack(sender_ip, sender_port)
            self.set_peer(sender_ip, sender_port)
            self.handshake_done = True
        elif header.packet_type == 5:
            print(f"{Fore.LIGHTGREEN_EX}ACK {Fore.MAGENTA} received")
            self.set_peer(sender_ip, sender_port)
            self.handshake_done = True

    def save_file(self, filename: str, file_data: bytes):
        file_path = os.path.join(self.file_directory, filename)
        try:
            with open(file_path, "wb") as file:
                file.write(file_data)
                print(f"{Fore.BLUE}File saved at: {file_path}")
        except Exception as e:
            print(f"{Fore.RED}Error saving file '{filename}': {e}")

    def send_syn(self, ip: str, port: int) -> None:
        header = Header.create_header(1, None)
        header_data = header.get_bytes_from_header()
        self.socket.sendto(header_data, (ip, port))
        print(f"{Fore.RED}SYN {Fore.LIGHTCYAN_EX}sent")

    def send_syn_ack(self, ip: str, port: int) -> None:
        header = Header.create_header(6, None)
        header_data = header.get_bytes_from_header()
        self.socket.sendto(header_data, (ip, port))
        print(f"{Fore.YELLOW}SYN-ACK {Fore.LIGHTCYAN_EX}sent")

    def send_ack(self, ip: str, port: int) -> None:
        header = Header.create_header(5, None)
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

    ###KEEP ALIVE CAST

    def start_keepalive_thread(self):
        self.keepalive_running = True
        heartbeat_thread = threading.Thread(target=self.keepalive_loop, daemon=True)
        heartbeat_thread.start()
        print(f"Keepalive started for {self.peer.peer_ip}:{self.peer.peer_port}")

    def keepalive_loop(self):
        while self.keepalive_running:
            if not self.handshake_done:
                break
            if not self.response_queue.empty():
                time.sleep(1)
                continue
            self.send_heartbeat()
            time.sleep(5)
            if self.heartbeats >= 3:
                self.handle_connection_loss()
                break
        print("Keepalive thread terminated.")

    def send_heartbeat(self):
        if self.peer:
            header = Header.create_header(packet_type=4, data="")
            self.send_fragment(header)
            print(f"{Fore.BLUE}Heartbeat sent.")
            self.heartbeats += 1

    def handle_connection_loss(self):
        self.keepalive_running = False
        print(f"{Fore.RED}Connection lost. Communication terminated.")
        self.close_socket()
        if self.chat_gui:
            self.chat_gui.display_message("Connection lost. Communication terminated.")
