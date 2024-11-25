import os
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
        self.running = True
        self.ip = ip
        self.port = port
        self.max_fragment_size = max_fragment_size
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((ip, port))
        self.peer = None
        self.connected = False
        self.header_buffer = {}  # Receiving header buffer
        self.fragments = {}  # Fragments to send
        self.sender_queue = queue.Queue()
        self.response_queue = queue.Queue()  # Response queue
        self.keepalive_running = False
        self.heartbeats = 0  # Heartbeats without response
        self.chat_gui = None
        self.current_filename = None
        self.file_directory = self.setup_file_dir()
        self.keepalive_thread = None
        self.sender_thread = None
        self.crc_error_simulation = False
        self.lock = threading.Lock()
        print(f"User listening on {self.ip}:{self.port}")

        # Start sender and receiver threads
        self.sender_thread = threading.Thread(target=self.send_queue_loop, daemon=True)
        self.sender_thread.start()
        self.receiver_thread = threading.Thread(target=self.listen_loop, daemon=True)
        self.receiver_thread.start()

    # Setting up file directory in case it doesn´t exist
    def setup_file_dir(self, directory_name="received_files"):
        project_root = os.path.abspath(os.path.dirname(__file__))
        file_dir_path = os.path.join(project_root, directory_name)
        if not os.path.exists(file_dir_path):
            os.makedirs(file_dir_path)
            print(f"Created file directory: {file_dir_path}")
        return file_dir_path

    # Setting peer
    def set_peer(self, ip: str, port: int) -> None:
        self.peer = self.Peer(ip, port)
        print(f"Peer set to {self.peer.peer_ip}:{self.peer.peer_port}")

    #Peer class for helping with sending
    class Peer:
        def __init__(self, ip: str, port: int) -> None:
            self.peer_ip = ip
            self.peer_port = port

        def connection_tuple(self):
            return self.peer_ip, self.peer_port

    #Transform message into fragments for sending
    def fragment_message(self, data: str, packet_type: int):
        fragment_size = self.max_fragment_size
        data_encoded = data.encode("utf-8")
        total_fragments = (len(data_encoded) + fragment_size - 1) // fragment_size
        fragments = {}

        for i in range(total_fragments):
            fragment_order = i + 1
            fragment_data = data_encoded[i * fragment_size:(i + 1) * fragment_size].decode("utf-8")
            next_fragment = 0x01 if fragment_order < total_fragments else 0x02
            header = Header.create_header(packet_type, fragment_data, fragment_order, next_fragment)
            fragments[fragment_order] = header # return object
            self.fragments[header.fragment_order] = header  # storing in case of resend

        return fragments

    #Fragment file into fragments for sending
    def fragment_file(self, file_path: str, packet_type: int):
        fragment_size = self.max_fragment_size
        with open(file_path, "rb") as file:
            file_data = file.read()

        filename = os.path.basename(file_path)
        data_encoded = filename.encode("utf-8") + DELIMITER.encode("utf-8") + file_data

        total_fragments = (len(data_encoded) + fragment_size - 1) // fragment_size
        fragments = {}

        for i in range(total_fragments):
            fragment_order = i + 1
            fragment_data = data_encoded[i * fragment_size:(i + 1) * fragment_size]
            fragment_data_str = fragment_data.decode('latin1')
            next_fragment = 0x01 if fragment_order < total_fragments else 0x02
            header = Header.create_header(packet_type, fragment_data_str, fragment_order, next_fragment)
            fragments[fragment_order] = header
            self.fragments[header.fragment_order] = header  # Store for potential retransmission

        return fragments

    # Send message method
    def send_message(self, message: str):
        fragments = self.fragment_message(message, packet_type=2)
        for fragment_order, header in fragments.items():
            packet = {
                'data': header.to_bytes(),
                'address': self.peer.connection_tuple(),
                'packet_type': header.packet_type,
                'fragment_order': header.fragment_order,
                'header': header  # Keep header for retransmission
            }
            self.sender_queue.put(packet)
            print(
                f"Put type {packet.get('packet_type')} into sender queue, sender queue state: {[packet['packet_type'] for packet in self.sender_queue.queue]}")

    # Send file method
    def send_file(self, file_path: str):
        fragments = self.fragment_file(file_path, packet_type=3)
        for fragment_order, header in fragments.items():
            packet = {
                'data': header.to_bytes(),
                'address': self.peer.connection_tuple(),
                'packet_type': header.packet_type,
                'fragment_order': header.fragment_order,
                'header': header  # Keep header for retransmission
            }
            self.sender_queue.put(packet)
            print(
                f"Put type {packet.get('packet_type')} into sender queue, sender queue state: {[packet['packet_type'] for packet in self.sender_queue.queue]}")
        if self.chat_gui:
            filename = os.path.basename(file_path)
            self.chat_gui.chat_log.append(f"You sent a file: {filename}")

    # Unified sending method
    def send_packet(self, packet):
        # Determine if we need to wait for an ACK based on packet type
        # Data packets (2,3,7,8) require ACK
        wait_for_response = packet['packet_type'] in [2, 3, 7]
        max_retries = 3
        retries = 0
        while retries < max_retries:
            with self.lock:
                if self.crc_error_simulation and retries == 0 and packet['packet_type'] == 2:
                    # Simulate CRC error on first attempt
                    packet['data'] = self.corrupt_packet(packet['data'])
                    print(f"{Fore.RED}Simulated CRC error in fragment {packet['fragment_order']}")
                    self.crc_error_simulation = False
                elif retries > 0:
                    # Recalculate CRC in case it was previously corrupted
                    packet['header'].crc = packet['header'].calculate_crc()
                    packet['data'] = packet['header'].to_bytes()

            # Send the packet
            self.socket.sendto(packet['data'], packet['address'])
            print(
                f"Sent packet type {packet['packet_type']} fragment {packet['fragment_order']} to {packet['address']}")
            if wait_for_response:
                # Wait for response
                try:
                    print(f"STUCK: {time.time()}")
                    response = self.response_queue.get(timeout=3)  # Increased timeout to 10 seconds
                    if response.packet_type == 5:  # ACK
                        acked_fragment = int(response.data)
                        if acked_fragment == packet['fragment_order']:
                            print(f"{Fore.GREEN}ACK received for fragment {acked_fragment}")
                            break  # ACK received, proceed to next packet
                        else:
                            print(
                                f"{Fore.YELLOW}Received ACK for fragment {acked_fragment}, expected {packet['fragment_order']}")
                    elif response.packet_type == 7:  # ARQ
                        missing_fragments = list(map(int, response.data.split(",")))
                        print(f"{Fore.RED}ARQ received for fragments {missing_fragments}")
                        # Send ACK for ARQ
                        # self.send_ack(0, True)
                        # Resend missing fragments
                        for fragment_order in missing_fragments:
                            if fragment_order in self.fragments:
                                header_to_resend = self.fragments[fragment_order]
                                header_to_resend.crc = header_to_resend.calculate_crc()
                                resend_packet = {
                                    'data': header_to_resend.to_bytes(),
                                    'address': packet['address'],
                                    'packet_type': header_to_resend.packet_type,
                                    'fragment_order': header_to_resend.fragment_order,
                                    'header': header_to_resend
                                }
                                self.sender_queue.put(resend_packet)
                                print(
                                    f"Put type {resend_packet.get('packet_type')} into sender queue, sender queue "
                                    f"state: {[packet['packet_type'] for packet in self.sender_queue.queue]}")
                                print(f"Resending fragment {fragment_order}")
                        # Do not increment retries here; continue waiting for ACK
                        continue
                except queue.Empty:
                    print(f"{Fore.YELLOW}Timeout waiting for ACK for fragment {packet['fragment_order']}, retrying...")
                    retries += 1
            else:
                # Control packets, no need to wait for ACK
                break

        if wait_for_response and retries == max_retries:
            print(f"{Fore.RED}Failed to send packet after {max_retries} retries")

    # Receiver loop
    def listen_loop(self):
        while self.running:
            if self.socket is None:
                print("Socket is None, exiting listen loop")
                break
            self.listen()

    # Process received packets
    def listen(self):
        try:
            if self.socket is None:
                print("Socket is None, exiting listen method")
                self.running = False
                return
            data, address = self.socket.recvfrom(1500)
            sender_ip, sender_port = address
            header = Header.from_bytes(data)
            if header.calculate_crc() != header.crc:
                print(f"{Fore.RED}Invalid CRC for fragment {header.fragment_order}")
                # Send ARQ for the missing fragment
                self.send_arq([header.fragment_order], address)
            else:
                if self.peer is None:
                    self.handle_handshake(header, sender_ip, sender_port)
                else:
                    if header.packet_type == 2:  # Message packet
                        print(f"Received message fragment {header.fragment_order}")
                        # Process message fragment
                        self.handle_message_fragment(header)
                        # Send ACK
                        self.send_ack(header.fragment_order)
                    elif header.packet_type == 3:  # File packet
                        print(f"Received file fragment {header.fragment_order}")
                        # Process file fragment
                        self.handle_file_fragment(header)
                        # Send ACK
                        self.send_ack(header.fragment_order)
                    elif header.packet_type == 5:  # ACK
                        self.response_queue.put(header)
                        print(
                            f"Put type {header.packet_type} into sender queue, sender queue "
                            f"state: {[packet['packet_type'] for packet in self.sender_queue.queue]}")
                        print(f"{Fore.GREEN}ACK received for fragment {header.data}")
                    elif header.packet_type == 7:  # ARQ
                        print(f"{Fore.RED}ARQ received for fragments {header.data}")
                        # Send ACK for ARQ
                        self.send_ack(0, True)
                        # Resend the requested fragments
                        missing_fragments = list(map(int, header.data.split(",")))
                        for fragment_order in missing_fragments:
                            if fragment_order in self.fragments:
                                header_to_resend = self.fragments[fragment_order]
                                header_to_resend.crc = header_to_resend.calculate_crc()
                                resend_packet = {
                                    'data': header_to_resend.to_bytes(),
                                    'address': (self.peer.peer_ip, self.peer.peer_port),
                                    'packet_type': header_to_resend.packet_type,
                                    'fragment_order': header_to_resend.fragment_order,
                                    'header': header_to_resend
                                }
                                self.sender_queue.put(resend_packet)
                                print(
                                    f"Put type {resend_packet.get('packet_type')} into sender queue, sender queue state: {[packet['packet_type'] for packet in self.sender_queue.queue]}")
                                print(f"Resending fragment {fragment_order}")
                            else:
                                print(f"No fragment found with order {fragment_order} to resend")
                    elif header.packet_type == 1:  # SYN
                        print(f"SYN received from {address}")
                        self.set_peer(sender_ip, sender_port)
                        self.send_syn_ack(sender_ip, sender_port)
                    elif header.packet_type == 6:  # SYN-ACK
                        print(f"SYN-ACK received from {address}")
                        self.set_peer(sender_ip, sender_port)
                        self.send_ack(0)
                        self.connected = True
                    elif header.packet_type == 4:  # Heartbeat
                        self.heartbeats = 0
                        print("Heartbeat received")
                    elif header.packet_type == 8:
                        self.peer = None
                        self.close_socket()
        except OSError as e:
            print(f"Socket closed, exiting listen method: {e}")
            self.running = False
        except Exception as e:
            print(f"Error in listen loop: {e}")
            self.running = False

    # Send ACK
    def send_ack(self, fragment_order=1, immediate=False):
        header = Header.create_header(5, str(fragment_order))
        packet = {
            'data': header.to_bytes(),
            'address': (self.peer.peer_ip, self.peer.peer_port),
            'packet_type': header.packet_type,
            'fragment_order': fragment_order,
            'header': header
        }
        if immediate:
            self.send_packet(packet)
            print("SENT IMMEDIATE ACK")
        else:
            self.sender_queue.put(packet)
        print(
            f"Put type {packet.get('packet_type')} into sender queue, sender queue state: {[packet['packet_type'] for packet in self.sender_queue.queue]}")
        print(f"{Fore.GREEN}ACK sent for fragment {fragment_order}")

    # Send ACK
    def send_terminate(self, fragment_order=1):
        if self.connected:
            header = Header.create_header(8, str(fragment_order))
            packet = {
                'data': header.to_bytes(),
                'address': (self.peer.peer_ip, self.peer.peer_port),
                'packet_type': header.packet_type,
                'fragment_order': fragment_order,
                'header': header
            }
            self.send_packet(packet)

    # Send ARQ
    def send_arq(self, missing_fragments, address):
        missing_fragments_str = ",".join(map(str, missing_fragments))
        header = Header.create_header(7, missing_fragments_str)
        packet = {
            'data': header.to_bytes(),
            'address': address,
            'packet_type': header.packet_type,
            'fragment_order': 0,
            'header': header
        }
        self.sender_queue.put(packet)
        print(
            f"Put type {packet.get('packet_type')} into sender queue, sender queue state: {[packet['packet_type'] for packet in self.sender_queue.queue]}")
        print(f"{Fore.YELLOW}ARQ sent for fragments {missing_fragments}")

    # Handle handshake
    def handle_handshake(self, header, sender_ip, sender_port):
        if header.packet_type == 1:
            print(f"{Fore.LIGHTGREEN_EX}SYN received")
            self.send_syn_ack(sender_ip, sender_port)
        elif header.packet_type == 6:
            print(f"{Fore.LIGHTGREEN_EX}SYN-ACK received")
            self.set_peer(sender_ip, sender_port)
            self.send_ack(0)
            self.connected = True
        elif header.packet_type == 5:
            print(f"{Fore.LIGHTGREEN_EX}ACK received")
            self.set_peer(sender_ip, sender_port)
            self.connected = True

    # Handle message fragments
    def handle_message_fragment(self, header: Header):
        if not hasattr(self, 'message_buffer'):
            self.message_buffer = {}
        self.message_buffer[header.fragment_order] = header.data

        if header.next_fragment == 0x02:  # Last fragment
            # Check for missing fragments
            missing_fragments = [
                i for i in range(1, max(self.message_buffer.keys()) + 1)
                if i not in self.message_buffer
            ]
            if missing_fragments:
                print(f"Missing message fragments: {missing_fragments}")
                self.send_arq(missing_fragments, self.peer.connection_tuple())
            else:
                # Reassemble the full message
                full_message = ''.join(
                    self.message_buffer[i] for i in sorted(self.message_buffer)
                )
                print(f"{Fore.MAGENTA}Reassembled full message: {Fore.RESET}{full_message}")
                if self.chat_gui:
                    self.chat_gui.display_message(f"{full_message}")
                self.message_buffer.clear()  # Clear the buffer after reassembly

    # Handle file fragments
    def handle_file_fragment(self, header: Header):
        if not hasattr(self, 'file_buffer'):
            self.file_buffer = {}
            self.current_filename = None

        # Store fragment data
        self.file_buffer[header.fragment_order] = header.data

        if header.fragment_order == 1:
            # Extract filename
            data_parts = header.data.split(DELIMITER, 1)
            self.current_filename = data_parts[0]
            self.file_buffer[header.fragment_order] = data_parts[1] if len(data_parts) > 1 else ''

        if header.next_fragment == 0x02:  # Last fragment
            # Check for missing fragments
            missing_fragments = [
                i for i in range(1, max(self.file_buffer.keys()) + 1)
                if i not in self.file_buffer
            ]
            if missing_fragments:
                print(f"Missing file fragments: {missing_fragments}")
                self.send_arq(missing_fragments, self.peer.connection_tuple())
            else:
                # Reassemble the full file data
                full_file_data = ''.join(
                    self.file_buffer[i] for i in sorted(self.file_buffer)
                ).encode('latin1')
                # Save the file
                self.save_file(self.current_filename, full_file_data)
                self.file_buffer.clear()  # Clear the buffer after reassembly

    # Save received file
    def save_file(self, filename: str, data: bytes):
        file_path = os.path.join(self.file_directory, filename)
        try:
            with open(file_path, "wb") as f:
                f.write(data)
            print(f"{Fore.BLUE}File saved at: {file_path}")
            if self.chat_gui:
                self.chat_gui.chat_log.append(f"Received a file: {filename}")
        except Exception as e:
            print(f"{Fore.RED}Error saving file '{filename}': {e}")

    # Send SYN
    def send_syn(self, ip: str, port: int) -> None:
        header = Header.create_header(1, "")
        packet = {
            'data': header.to_bytes(),
            'address': (ip, port),
            'packet_type': header.packet_type,
            'fragment_order': 0,
            'header': header
        }
        self.sender_queue.put(packet)
        print(
            f"Put type {packet.get('packet_type')} into sender queue, sender queue state: {[packet['packet_type'] for packet in self.sender_queue.queue]}")
        print(f"{Fore.RED}SYN sent to {(ip, port)}")

    # Send SYN-ACK
    def send_syn_ack(self, ip: str, port: int) -> None:
        header = Header.create_header(6, "")
        packet = {
            'data': header.to_bytes(),
            'address': (ip, port),
            'packet_type': header.packet_type,
            'fragment_order': 0,
            'header': header
        }
        self.sender_queue.put(packet)
        print(
            f"Put type {packet.get('packet_type')} into sender queue, sender queue state: {[packet['packet_type'] for packet in self.sender_queue.queue]}")
        print(f"{Fore.YELLOW}SYN-ACK sent to {(ip, port)}")

    # Sender loop
    def send_queue_loop(self):
        while True:
            try:
                packet = self.sender_queue.get()
                print(
                    f"Took type {packet.get('packet_type')} into sender queue, sender queue state: {[packet['packet_type'] for packet in self.sender_queue.queue]}")
                if packet is None:
                    break  # Exit the thread
                self.send_packet(packet)
            except Exception as e:
                print(f"Error in sending thread: {e}")
                break

    # Start keepalive thread
    def start_keepalive_thread(self):
        self.keepalive_running = True
        self.keepalive_thread = threading.Thread(target=self.keepalive_loop, daemon=True)
        print(f"Keepalive started for {self.peer.peer_ip}:{self.peer.peer_port}")
        self.keepalive_thread.start()

    # Adjusted keepalive_loop
    def keepalive_loop(self):
        while self.keepalive_running:
            if not self.response_queue.empty():
                time.sleep(1)
                continue
            self.send_heartbeat()
            time.sleep(5)
            if self.heartbeats >= 3:
                self.close_socket()
                break
        print("Keepalive thread terminated.")

    def send_heartbeat(self):
        if self.peer:
            header = Header.create_header(packet_type=4, data="")
            packet = {
                'data': header.to_bytes(),
                'address': (self.peer.peer_ip, self.peer.peer_port),
                'packet_type': header.packet_type,
                'fragment_order': 0,
                'header': header
            }
            self.sender_queue.put(packet)
            print(
                f"Put type {packet.get('packet_type')} into sender queue, sender queue state: {[packet['packet_type'] for packet in self.sender_queue.queue]}")
            print(f"{Fore.BLUE}Heartbeat sent.")
            self.heartbeats += 1

    def close_socket(self):
        if self.peer is not None:
            self.send_terminate()
        self.running = False
        self.connected = False
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

    def enable_crc_error_simulation(self):
        self.crc_error_simulation = True

    def corrupt_packet(self, data: bytes) -> bytes:
        header = Header.from_bytes(data)
        header.crc = header.crc // 2
        return header.to_bytes()
