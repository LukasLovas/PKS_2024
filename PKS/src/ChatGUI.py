from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QLineEdit, QPushButton, QLabel, QSpinBox
from PyQt6.QtCore import pyqtSignal, QThread

class ChatGUI(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user

        self.setWindowTitle(f"{self.user.ip}:{self.user.port}")
        self.setGeometry(300, 300, 400, 500)

        layout = QVBoxLayout()

        # Fragment limit control
        fragment_label = QLabel("Fragment Size (bytes):")
        self.fragment_limit_spinbox = QSpinBox()
        self.fragment_limit_spinbox.setRange(100, 1464)  # Limit range to avoid MTU issues
        self.fragment_limit_spinbox.setValue(self.user.max_fragment_size)
        self.fragment_limit_spinbox.valueChanged.connect(self.update_fragment_limit)
        layout.addWidget(fragment_label)
        layout.addWidget(self.fragment_limit_spinbox)

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

    def update_fragment_limit(self, value):
        self.user.max_fragment_size = value
        self.user.send_fragment_limit_update(value)
        print(f"Updated fragment limit to {value} bytes")

    def send_message(self):
        message = self.message_input.text()
        if message:
            self.chat_log.append(f"You: {message}")
            self.user.send(message,2)
            self.message_input.clear()

    def display_message(self, message):
        self.chat_log.append(f"Peer: {message}")

    def closeEvent(self, event: QCloseEvent) -> None:
        self.user.close_socket()
        print("Socket closed.")

        event.accept()


class ListenThread(QThread):
    new_message = pyqtSignal(str)

    def __init__(self, user):
        super().__init__()
        self.user = user

    def run(self):
        while True:
            message = self.user.listen()
            if message:
                if message == 7:
                    self.user.close_socket()
                    message = "Communication closed"
                self.new_message.emit(message)
