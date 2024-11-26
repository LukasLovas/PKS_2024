####TODO aby sa fragmenty odoslali v opačnom poradí vrátane prečíslovania fragmentov (posledný vytvorený fragment bude mat fragment order 1 a bude posledný ako prvý)

# def fragment_file(self, file_path: str, packet_type: int):
#     fragment_size = self.max_fragment_size
#     with open(file_path, "rb") as file:
#         file_data = file.read()
#
#     total_fragments = (len(file_data) + fragment_size - 1) // fragment_size
#     fragments = []
#
#     for i in range(total_fragments):
#         fragment_data = file_data[i * fragment_size:(i + 1) * fragment_size]
#         fragment_data_str = fragment_data.decode('latin1')
#         header = Header.create_header(packet_type, fragment_data_str)
#         fragments.append(header)
#
#     fragments_reversed = fragments[::-1]
#     for i, header in enumerate(fragments_reversed):
#         header.fragment_order = i + 1
#         header.next_fragment = 0x01 if i < total_fragments - 1 else 0x02
#         header.crc = header.calculate_crc()
#         self.fragments[header.fragment_order] = header
#
#     filename = os.path.basename(file_path)
#     last_fragment_data = filename + DELIMITER + fragments[len(fragments) - 1].data
#     fragments[len(fragments) - 1].data = last_fragment_data
#     print(fragments[len(fragments) - 1])
#
#     fragments_dict = {header.fragment_order: header for header in fragments_reversed}
#
#     return fragments_dict

# def fragment_message(self, data: str, packet_type: int):
#     fragment_size = self.max_fragment_size
#     data_encoded = data.encode("utf-8")
#     total_fragments = (len(data_encoded) + fragment_size - 1) // fragment_size
#     fragments = []
#
#     for i in range(total_fragments):
#         fragment_data = data_encoded[i * fragment_size:(i + 1) * fragment_size].decode("utf-8")
#         header = Header.create_header(packet_type, fragment_data)
#         fragments.append(header)
#
#     fragments_reversed = fragments[::-1]
#     for i, header in enumerate(fragments_reversed):
#         header.fragment_order = i + 1
#         header.next_fragment = 0x01 if i < total_fragments - 1 else 0x02
#         header.crc = header.calculate_crc()
#         self.fragments[header.fragment_order] = header
#
#     fragments_dict = {header.fragment_order: header for header in fragments_reversed}
#
#     return fragments_dict

# def send_message(self, message: str):
#     fragments = self.fragment_message(message, packet_type=2)
#     total_fragments = len(fragments)
#     fragment_size = self.max_fragment_size
#     last_fragment_size = len(fragments[1].data.encode("utf-8"))
#     message_size = len(message.encode("utf-8"))
#
#     print(f"Sending message of size {message_size} bytes")
#     print(f"Number of fragments: {total_fragments}")
#     print(f"Fragment size: {fragment_size} bytes")
#     if last_fragment_size != fragment_size:
#         print(f"Last fragment size: {last_fragment_size} bytes")
#
#     for fragment_order in sorted(fragments.keys()):
#         header = fragments[fragment_order]
#         packet = {
#             'data': header.to_bytes(),
#             'address': self.peer.connection_tuple(),
#             'packet_type': header.packet_type,
#             'fragment_order': header.fragment_order,
#             'header': header
#         }
#         self.sender_queue.put(packet)
#         # print(
#         #     f"Put type {packet.get('packet_type')} into sender queue, sender queue state: {[packet['packet_type'] for packet in self.sender_queue.queue]}")

# def send_file(self, file_path: str):
#     fragments = self.fragment_file(file_path, packet_type=3)
#     total_fragments = len(fragments)
#     fragment_size = self.max_fragment_size
#     last_fragment_size = len(fragments[1].data.encode("latin1"))
#     file_size = os.path.getsize(file_path)
#
#     filename = os.path.basename(file_path)
#
#     print(f"Sending file '{filename}' of size {file_size} bytes")
#     print(f"Number of fragments: {total_fragments}")
#     print(f"Fragment size: {fragment_size} bytes")
#     if last_fragment_size != fragment_size:
#         print(f"Last fragment size: {last_fragment_size} bytes")
#
#     for fragment_order in sorted(fragments.keys()):
#         if fragment_order == 1:
#             print(fragments[fragment_order])
#         header = fragments[fragment_order]
#         packet = {
#             'data': header.to_bytes(),
#             'address': self.peer.connection_tuple(),
#             'packet_type': header.packet_type,
#             'fragment_order': header.fragment_order,
#             'header': header  # Keep header for retransmission
#         }
#         self.sender_queue.put(packet)
#         # print(
#         #     f"Put type {packet.get('packet_type')} into sender queue, sender queue state: {[packet['packet_type'] for packet in self.sender_queue.queue]}")
#     if self.chat_gui:
#         filename = os.path.basename(file_path)
#         self.chat_gui.chat_log.append(f"You sent a file: {filename}")


#TODO aby odosielatel vypocital zo suboru hash SHA256 a poslal ako poslednu spravu(cize sprava, ktora nasleduje po poslednom fragmente suboru). Prijimac nasledne vypocita SHA256 z prijatej spravy a porovna ho s hashom, ktory prijal spolu so spravou, nasledne vypise vysledok porovnania (pouzi kniznicu hashlib)

#import hashlib

# def send_file(self, file_path: str):
#     with open(file_path, "rb") as file:
#         file_data = file.read()
#     file_hash = hashlib.sha256(file_data).hexdigest()
#
#     fragments = self.fragment_file(file_path, packet_type=3)
#     total_fragments = len(fragments)
#     fragment_size = self.max_fragment_size
#     last_fragment_size = len(fragments[total_fragments].data.encode("latin1"))
#     file_size = os.path.getsize(file_path)
#
#     filename = os.path.basename(file_path)
#
#     print(f"Sending file '{filename}' of size {file_size} bytes")
#     print(f"Number of fragments: {total_fragments}")
#     print(f"Fragment size: {fragment_size} bytes")
#     if last_fragment_size != fragment_size:
#         print(f"Last fragment size: {last_fragment_size} bytes")
#
#     for fragment_order, header in fragments.items():
#         packet = {
#             'data': header.to_bytes(),
#             'address': self.peer.connection_tuple(),
#             'packet_type': header.packet_type,
#             'fragment_order': header.fragment_order,
#             'header': header
#         }
#         self.sender_queue.put(packet)
#         # print(
#         #     f"Put type {packet.get('packet_type')} into sender queue, sender queue state: {[packet['packet_type'] for packet in self.sender_queue.queue]}")
#
#     hash_header = Header.create_header(packet_type=9, data=file_hash)
#     hash_packet = {
#         'data': hash_header.to_bytes(),
#         'address': self.peer.connection_tuple(),
#         'packet_type': hash_header.packet_type,
#         'fragment_order': 0,
#         'header': hash_header
#     }
#     self.sender_queue.put(hash_packet)
#     print(f"Sent SHA256 hash: {file_hash}")
#
#     if self.chat_gui:
#         filename = os.path.basename(file_path)
#         self.chat_gui.chat_log.append(f"You sent a file: {filename}")


def listen_loop(self):
    while self.running:
        if self.socket is None:
            print("Socket is None, exiting listen loop")
            break
        self.listen()


# Process received packets
# def listen(self):
#     try:
#         if self.socket is None:
#             print("Socket is None, exiting listen method")
#             self.running = False
#             return
#         data, address = self.socket.recvfrom(1500)
#         sender_ip, sender_port = address
#         header = Header.from_bytes(data)
#         if header.calculate_crc() != header.crc:
#             print(f"Received fragment {header.fragment_order} {Fore.RED}with errors")
#             self.send_arq([header.fragment_order], address)
#         else:
#             print(f"Received fragment {header.fragment_order}{Fore.GREEN} without error")
#             if self.peer is None:
#                 self.handle_handshake(header, sender_ip, sender_port)
#             else:
#                 if header.packet_type == 2:  # Message packet
#                     print(f"Received message fragment {header.fragment_order}")
#                     self.handle_message_fragment(header)
#                     self.send_ack(header.fragment_order)
#                 elif header.packet_type == 3:  # File packet
#                     # print(f"Received file fragment {header.fragment_order}")
#                     self.handle_file_fragment(header)
#                     self.send_ack(header.fragment_order)
#                 elif header.packet_type == 9:  # Hash packet
#                     self.handle_hash_packet(header)
#                 elif header.packet_type == 5:  # ACK
#                     self.response_queue.put(header)
#                     # print(
#                     #     f"Put type {header.packet_type} into sender queue, sender queue "
#                     #     f"state: {[packet['packet_type'] for packet in self.sender_queue.queue]}")
#                     print(f"{Fore.GREEN}ACK received for fragment {header.data}")
#                 elif header.packet_type == 7:  # ARQ
#                     print(f"{Fore.RED}ARQ received for fragments {header.data}")
#                     self.send_ack(0, True)
#                     missing_fragments = list(map(int, header.data.split(",")))
#                     for fragment_order in missing_fragments:
#                         if fragment_order in self.fragments:
#                             header_to_resend = self.fragments[fragment_order]
#                             header_to_resend.crc = header_to_resend.calculate_crc()
#                             resend_packet = {
#                                 'data': header_to_resend.to_bytes(),
#                                 'address': (self.peer.peer_ip, self.peer.peer_port),
#                                 'packet_type': header_to_resend.packet_type,
#                                 'fragment_order': header_to_resend.fragment_order,
#                                 'header': header_to_resend
#                             }
#                             self.sender_queue.put(resend_packet)
#                             # print(
#                             #     f"Put type {resend_packet.get('packet_type')} into sender queue, sender queue state: {[packet['packet_type'] for packet in self.sender_queue.queue]}")
#                             print(f"Resending fragment {fragment_order}")
#                         else:
#                             print(f"No fragment found with order {fragment_order} to resend")
#                 elif header.packet_type == 1:  # SYN
#                     print(f"SYN received from {address}")
#                     self.set_peer(sender_ip, sender_port)
#                     self.send_syn_ack(sender_ip, sender_port)
#                 elif header.packet_type == 6:  # SYN-ACK
#                     print(f"SYN-ACK received from {address}")
#                     self.set_peer(sender_ip, sender_port)
#                     self.send_ack(0)
#                     self.connected = True
#                 elif header.packet_type == 4:  # Heartbeat
#                     self.heartbeats = 0
#                     print("Heartbeat received")
#                 elif header.packet_type == 8:
#                     self.peer = None
#                     self.close_socket()
#     except OSError as e:
#         print(f"Socket closed, exiting listen method: {e}")
#         self.running = False
#     except Exception as e:
#         print(f"Error in listen loop: {e}")
#         self.running = False


    # def handle_hash_packet(self, header: Header):
    #     received_hash = header.data
    #     # Compute SHA256 hash of the received file
    #     file_path = os.path.abspath(os.path.join(self.file_directory, self.current_filename))
    #     with open(file_path, "rb") as file:
    #         file_data = file.read()
    #     computed_hash = hashlib.sha256(file_data).hexdigest()
    #
    #     print(f"Received SHA256 hash: {received_hash}")
    #     print(f"Computed SHA256 hash: {computed_hash}")
    #
    #     if received_hash == computed_hash:
    #         print(f"{Fore.GREEN}File integrity verified successfully.")
    #     else:
    #         print(f"{Fore.RED}File integrity verification failed.")
    #
    #     # Reset current filename after verification
    #     self.current_filename = None
