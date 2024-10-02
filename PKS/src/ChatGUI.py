from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QLineEdit, QPushButton
from PyQt6.QtCore import pyqtSignal, QThread


class ChatGUI(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user

        # Set up the GUI components
        self.setWindowTitle("Chat")
        self.setGeometry(300, 300, 400, 500)

        layout = QVBoxLayout()

        # Chat log area
        self.chat_log = QTextEdit()
        self.chat_log.setReadOnly(True)
        layout.addWidget(self.chat_log)

        # Input area (to type messages)
        self.message_input = QLineEdit()
        layout.addWidget(self.message_input)

        # Send button (now linked to Enter key)
        send_button = QPushButton("Send")
        send_button.clicked.connect(self.send_message)
        layout.addWidget(send_button)

        self.setLayout(layout)

        # Overriding keyPressEvent for QLineEdit to capture Enter key
        self.message_input.returnPressed.connect(self.send_message)  # Enter bound to send_message()

        # Start listening for incoming messages in a separate thread
        self.listen_thread = ListenThread(self.user)
        self.listen_thread.new_message.connect(self.display_message)
        self.listen_thread.start()

    def send_message(self):
        message = self.message_input.text()
        if message:
            self.chat_log.append(f"You: {message}")
            self.user.send(message)
            self.message_input.clear()

    def display_message(self, message):
        self.chat_log.append(f"Peer: {message}")


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
