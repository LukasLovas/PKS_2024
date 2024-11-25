import time
import traceback
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QLineEdit, QPushButton, QMenu, QInputDialog, QFileDialog, \
    QLabel
from PyQt6.QtCore import pyqtSignal, QThread


class ChatGUI(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.user.chat_gui = self  # Link back to the GUI

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
        self.message_input.setMaxLength(2097152)
        layout.addWidget(self.message_input)

        # Message size counter
        self.message_size_label = QLabel("Message size: 0 bytes")
        layout.addWidget(self.message_size_label)

        # Send button
        send_button = QPushButton("Send")
        send_button.clicked.connect(self.send_message)
        layout.addWidget(send_button)

        self.setLayout(layout)
        self.message_input.textChanged.connect(self.update_message_size)
        self.message_input.returnPressed.connect(self.send_message)

        # Start listening for incoming messages
        self.listen_thread = ListenThread(self.user)
        self.listen_thread.new_message.connect(self.display_message)
        self.listen_thread.start()

    def update_message_size(self):
        """Update the message size counter."""
        message_size = len(self.message_input.text().encode('utf-8'))
        self.message_size_label.setText(f"Message size: {message_size} bytes")

    def create_menu(self):
        """Creates the menu for options."""
        menu = QMenu()

        # Send File Option
        send_file_action = menu.addAction("Send File")
        send_file_action.triggered.connect(self.send_file)

        # Fragment Size Option
        fragment_size_action = menu.addAction("Fragment Size")
        fragment_size_action.triggered.connect(self.open_fragment_size_dialog)

        # Error Simulation CRC Option
        crc_error_action = menu.addAction("Error Simulation CRC")
        crc_error_action.triggered.connect(self.simulate_crc_error)

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

    def simulate_crc_error(self):
        self.user.enable_crc_error_simulation()
        self.chat_log.append("CRC Error Simulation enabled for the next message.")

    def open_fragment_size_dialog(self):
        """Opens a modal dialog for setting fragment size."""
        fragment_size, ok = QInputDialog.getInt(self, "Set Fragment Size", "Fragment Size (bytes):",
                                                self.user.max_fragment_size, 100, 1462)
        if ok:
            self.user.max_fragment_size = fragment_size
            print(f"Updated fragment limit to {fragment_size} bytes")

    def send_message(self):
        message = self.message_input.text()
        if message:
            self.chat_log.append(f"You: {message}")
            self.user.send_message(message)
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
            # The listen method now handles message reassembly and GUI updates
            time.sleep(1)
