import os.path
import queue
import socket
import threading
import time
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
        self.header_buffer = {}  # Receiving headers buffer
        self.fragments = {}  # Fragments to send
        self.response_queue = queue.Queue()  # Response queue
        self.keepalive_running = False
        self.heartbeats = 0  # Heartbeats without response
        self.chat_gui = None
        self.current_filename = None
        self.file_directory = self.setup_file_dir()
        self.keepalive_thread = None
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

    def fragment_message(self, data: str, packet_type: int) -> dict:
        fragment_size = self.max_fragment_size
        data_encoded = data.encode("utf-8")
        total_fragments = (len(data_encoded) + fragment_size - 1) // fragment_size
        fragments = {}

        for i in range(total_fragments):
            fragment_order = i + 1
            fragment_data = data_encoded[i * fragment_size:(i + 1) * fragment_size].decode("utf-8")
            next_fragment = 0x01 if fragment_order < total_fragments else 0x02
            header = Header.create_header(packet_type, fragment_data, fragment_order, next_fragment)
            fragments[fragment_order] = header
            self.fragments[header.fragment_order] = header
        print(fragments.keys())
        return fragments

    def fragment_file(self, data: bytes, packet_type: int) -> dict:
        fragment_size = self.max_fragment_size
        total_fragments = (len(data) + fragment_size - 1) // fragment_size
        fragments = {}

        for i in range(total_fragments):
            fragment_order = i + 1
            fragment_data = data[i * fragment_size:(i + 1) * fragment_size].decode("utf-8")
            next_fragment = 0x01 if fragment_order < total_fragments else 0x02
            fragments[fragment_order] = Header.create_header(packet_type, fragment_data, fragment_order, next_fragment)

        print(fragments.keys())
        return fragments

    def send_fragments(self, fragments: dict):
        print(f"{Fore.YELLOW}# of fragments to send: {len(fragments)}")
        unacknowledged_fragments = set(fragments.keys())  # Start with all fragments unacknowledged
        max_retries = 3
        retries = 0

        while unacknowledged_fragments and retries < max_retries:
            for fragment_order in list(unacknowledged_fragments):
                header = fragments[fragment_order]

                if retries > 0:
                    if header.crc != header.calculate_crc():
                        print(
                            f"{Fore.RED}CRC mismatch: fragment {fragment_order}")
                        header.crc = header.calculate_crc()

                self.send_fragment(header)

                try:
                    response = self.response_queue.get(timeout=60)
                    if response.packet_type == 5:  # ACK
                        acked_fragment = int(response.data)  # ACK data contains the fragment order
                        if acked_fragment in unacknowledged_fragments:
                            unacknowledged_fragments.remove(acked_fragment)

                    elif response.packet_type == 7:  # ARQ
                        missing_fragments = list(map(int, response.data.split(",")))
                        for missing in missing_fragments:
                            if missing in fragments:
                                unacknowledged_fragments.add(missing)

                except queue.Empty:
                    print(f"{Fore.RED}Timeout waiting for ACK or ARQ for fragments: {unacknowledged_fragments}")

            retries += 1
            print(f"{Fore.YELLOW}Retrying unacknowledged fragments ({len(unacknowledged_fragments)} remaining)...")

        if unacknowledged_fragments:
            print(f"{Fore.RED}Failed to send all fragments after {max_retries} retries: {unacknowledged_fragments}")
        else:
            print(f"{Fore.GREEN}All fragments sent successfully.")

    def send_fragment(self, header: Header):
        if self.socket:
            self.socket.sendto(header.to_bytes(), self.peer.connection_tuple())
        #print(f"{Fore.LIGHTCYAN_EX}Sent fragment {header.fragment_order}| Next fragment: {True if header.next_fragment == 1 else False}{Fore.RESET}")
        # print(f"{Fore.LIGHTCYAN_EX}{header}")

    def send(self, message: str, packet_type: int):
        fragments = self.fragment_message(message, packet_type)
        self.send_fragments(fragments)

    def send_file(self, file_path):
        filename = os.path.basename(file_path)
        with open(file_path, "rb") as file:
            file_data = file.read()
            header_data = f"{filename}{DELIMITER}".encode("utf-8") + file_data
            fragments = self.fragment_file(header_data, packet_type=3)
            self.send_fragments(fragments)

    def receive_message(self):
        try:
            message, address = self.socket.recvfrom(1500)
            sender_ip, sender_port = address
            header = Header.from_bytes(message)
            return header, sender_ip, sender_port
        except ConnectionResetError:
            self.handle_connection_loss()
        except OSError as e:
            if e.errno == 10038:  # WinError 10038: Operation on a closed socket
                return None
            else:
                self.handle_connection_loss()
        except Exception as e:
            print(f"Unexpected error receiving message: {e}")
        return None

    def listen(self):
        header, sender_ip, sender_port = self.receive_message()
        if header:
            if header.calculate_crc() == header.crc:  # Validate CRC
                if self.peer is None:
                    self.handle_handshake(header, sender_ip, sender_port)
                else:
                    if header.packet_type == 2:  # Message packet
                        print(f"Received fragment no. {header.fragment_order} for message.")

                        # Store the fragment in the buffer
                        if header.fragment_order not in self.header_buffer:
                            self.header_buffer[header.fragment_order] = header.data
                            self.send_ack(sender_ip, sender_port, header.fragment_order)
                        else:
                            print(f"Duplicate fragment {header.fragment_order} received and ignored.")

                        if header.next_fragment == 0x02:  # Last fragment
                            # Check for missing fragments
                            missing_fragments = [
                                i for i in range(1, max(self.header_buffer.keys()) + 1)
                                if i not in self.header_buffer
                            ]
                            if missing_fragments:
                                print(f"Missing fragments: {missing_fragments}")
                                self.send_arq(",".join(map(str, missing_fragments)))
                            else:
                                # Reassemble the full message
                                full_message = ''.join(
                                    self.header_buffer[i] for i in sorted(self.header_buffer)
                                )
                                print(f"{Fore.MAGENTA}Reassembled full message: {Fore.RESET}{full_message}")
                                self.header_buffer.clear()  # Clear the buffer after reassembly
                                return full_message  # Pass the message back to the ChatGUI

                    elif header.packet_type == 3:  # File packet
                        print(f"Received fragment no. {header.fragment_order}")

                        if header.fragment_order == 1:
                            file_data = header.data.split(DELIMITER, 1)
                            self.current_filename = file_data[0]
                            header.data = file_data[1]

                        # fragment reassembly
                        if header.fragment_order not in self.header_buffer:
                            self.header_buffer[header.fragment_order] = header.data.encode("utf-8")
                            self.send_ack(sender_ip, sender_port, header.fragment_order)

                        else:
                            print(f"Duplicate fragment {header.fragment_order} received and ignored.")
                        if header.next_fragment == 0x02:  # Last fragment
                            missing_fragments = [
                                i for i in range(1, max(self.header_buffer.keys()) + 1)
                                if i not in self.header_buffer
                            ]
                            if missing_fragments:
                                print(f"Missing fragments: {missing_fragments}")
                                self.send_arq(",".join(map(str, missing_fragments)))
                            else:
                                full_file_data = b"".join(
                                    self.header_buffer[i] for i in sorted(self.header_buffer)
                                )
                                self.save_file(self.current_filename, full_file_data)
                                self.header_buffer.clear()
                                print("File reassembled and saved successfully.")

                    elif header.packet_type == 4:  # Heartbeat
                        self.heartbeats = 0

                    elif header.packet_type == 5:  # ACK
                        self.response_queue.put(header)
                        print(f"{Fore.GREEN}ACK received for fragment {header.data}")

                    elif header.packet_type == 7:  # ARQ
                        self.response_queue.put(header)
                        self.send_ack(sender_ip, sender_port, header.fragment_order)
                        print(f"{Fore.RED}ARQ received: Missing fragments {header.data}")



            else:
                print(f"{Fore.RED}Invalid CRC for fragment {header.fragment_order}")
                self.send_arq(str(header.fragment_order))

    def send_arq(self, missing_fragments):
        missing_fragments_str = ",".join(map(str, missing_fragments))
        print(f"Sending ARQ for missing fragments: {missing_fragments_str}")
        fragments = self.fragment_message(missing_fragments_str, packet_type=7)
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
        header = Header.create_header(1, "")
        header_data = header.to_bytes()
        self.socket.sendto(header_data, (ip, port))
        print(f"{Fore.RED}SYN {Fore.LIGHTCYAN_EX}sent")

    def send_syn_ack(self, ip: str, port: int) -> None:
        header = Header.create_header(6, "")
        header_data = header.to_bytes()
        self.socket.sendto(header_data, (ip, port))
        print(f"{Fore.YELLOW}SYN-ACK {Fore.LIGHTCYAN_EX}sent")

    def send_ack(self, ip: str, port: int, fragment_order=1) -> None:
        header = Header.create_header(5, str(fragment_order))
        header_data = header.to_bytes()
        self.socket.sendto(header_data, (ip, port))
        print(f"{Fore.GREEN}ACK {Fore.LIGHTCYAN_EX}sent")

    def start_listening_thread(self) -> threading.Thread:
        listen_thread = threading.Thread(target=self.listen_handshake, daemon=True)
        listen_thread.start()
        return listen_thread

    def listen_handshake(self):
        while not self.handshake_done:
            self.listen()

    def close_socket(self):
        self.keepalive_running = False
        try:
            if self.socket:
                self.socket.close()
                self.socket = None
                print("Socket successfully closed.")
        except Exception as e:
            print(f"Error while closing socket: {e}")

    ###KEEP ALIVE CAST

    def start_keepalive_thread(self):
        self.keepalive_running = True
        self.keepalive_thread = threading.Thread(target=self.keepalive_loop, daemon=True)
        self.keepalive_thread.start()
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
            #print(f"{Fore.BLUE}Heartbeat sent.")
            self.heartbeats += 1

    def handle_connection_loss(self):
        self.keepalive_running = False
        try:
            if self.socket:
                self.socket.close()
                self.socket = None
                print("Socket successfully closed.")
        except Exception as e:
            print(f"Error while closing socket: {e}")
        print(f"{Fore.RED}Connection lost. Communication terminated.")
        if self.chat_gui:
            self.chat_gui.display_message("Connection lost. Communication terminated.")

