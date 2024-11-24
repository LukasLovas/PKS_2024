import traceback
from pathlib import Path

from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QLineEdit, QPushButton, QMenu, QInputDialog, QFileDialog
from PyQt6.QtCore import pyqtSignal, QThread
import random


class ChatGUI(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user

        self.setWindowTitle(f"{self.user.ip}:{self.user.port}")
        self.setGeometry(300, 300, 400, 500)

        layout = QVBoxLayout()

        # Menu button for options
        menu_button = QPushButton("Menu")
        menu_button.setMenu(self.create_menu())
        layout.addWidget(menu_button)

        # Chat log area
        self.chat_log = QTextEdit()
        self.chat_log.setReadOnly(True)
        layout.addWidget(self.chat_log)

        # Input area
        self.message_input = QLineEdit()
        layout.addWidget(self.message_input)

        # Send button
        send_button = QPushButton("Send")
        send_button.clicked.connect(self.send_message)
        layout.addWidget(send_button)

        self.setLayout(layout)
        self.message_input.returnPressed.connect(self.send_message)

        # Start listening for incoming messages
        self.listen_thread = ListenThread(self.user)
        self.listen_thread.new_message.connect(self.display_message)
        self.listen_thread.start()

    def create_menu(self):
        """Creates the menu for fragment size and error simulation options."""
        menu = QMenu()

        # Send file Option
        fragment_size_action = menu.addAction("Send File")
        fragment_size_action.triggered.connect(self.send_file)

        # Fragment Size Option
        fragment_size_action = menu.addAction("Fragment Size")
        fragment_size_action.triggered.connect(self.open_fragment_size_dialog)

        # Error Simulation CRC Option
        crc_error_action = menu.addAction("Error Simulation CRC")
        crc_error_action.triggered.connect(self.simulate_crc_error)

        # Error Simulation Lost Packet Option
        packet_loss_action = menu.addAction("Error Simulation Lost Packet")
        packet_loss_action.triggered.connect(self.simulate_packet_loss)

        # Directory Option
        save_directory_action = menu.addAction("Set Save Directory")
        save_directory_action.triggered.connect(self.set_save_directory)

        return menu

    def send_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select File to Send")
        if file_path:
            try:
                self.user.send_file(file_path)
                self.chat_log.append(f"File sent successfully.")
            except Exception:
                print(traceback.format_exc())

    def set_save_directory(self):
        selected_dir = QFileDialog.getExistingDirectory(self, "Select Save Directory", self.user.file_directory)
        if selected_dir:
            self.user.file_directory = selected_dir
            self.chat_log.append(f"Save directory updated to: {selected_dir}")
            print(f"Save directory updated to: {selected_dir}")

    def open_fragment_size_dialog(self):
        """Opens a modal dialog for setting fragment size."""
        fragment_size, ok = QInputDialog.getInt(self, "Set Fragment Size", "Fragment Size (bytes):",
                                                self.user.max_fragment_size, 100, 1462)
        if ok:
            self.user.max_fragment_size = fragment_size
            print(f"Updated fragment limit to {fragment_size} bytes")

    def simulate_crc_error(self):
        message = "CRC TEST MESSAGE"
        fragments = self.user.fragment_message(message, 2)
        fragments[1].crc = int(fragments[1].crc / 2)  # Change CRC
        print("Simulating CRC error...")
        self.user.send_fragments(fragments)
        self.user.handle_response(fragments)
        print("CRC ERROR SIMULATION DONE")

    def simulate_packet_loss(self):
        message = Path("resources/lorem_ipsum").read_text()
        if message:
            fragments = self.user.fragment_message(message, 2)
            # Decide which fragments to "lose" by skipping their transmission
            lost_fragments = random.sample(list(fragments.keys()), k=min(2, len(fragments)))
            print(f"Simulating packet loss, not sending fragments: {lost_fragments}")
            # Send all fragments except the ones marked for "loss"
            for fragment_order, header in fragments.items():
                if fragment_order not in lost_fragments:
                    self.user.send_fragment(header)
            self.message_input.clear()

    def send_message(self):
        message = self.message_input.text()
        if message:
            self.chat_log.append(f"You: {message}")
            self.user.send(message, 2)
            self.message_input.clear()

    def display_message(self, message):
        self.chat_log.append(f"Peer: {message}")

    def closeEvent(self, event: QCloseEvent) -> None:
        self.user.close_socket()
        event.accept()

    def display_message_end(self, message):
        self.chat_log.append(message)


class ListenThread(QThread):
    new_message = pyqtSignal(str)

    def __init__(self, user):
        super().__init__()
        self.user = user

    def run(self):
        while True:
            message = self.user.listen()
            if message:
                self.new_message.emit(message)
