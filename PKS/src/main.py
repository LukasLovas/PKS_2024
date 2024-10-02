import sys
import socket
from PyQt6.QtWidgets import QApplication
from ChatGUI import ChatGUI  # Import the separate GUI class
from User import User


if __name__ == "__main__":
    # Initialize the socket-based user
    my_ip = socket.gethostbyname(socket.gethostname())
    my_port = int(input("Enter your port: "))

    user = User(my_ip, my_port)
    user.start_listening_thread()

    peer_ip = socket.gethostbyname(socket.gethostname())
    peer_port = int(input("Enter the peer's port: "))
    user.send_initial(peer_ip, peer_port)

    # Start the PyQt application
    app = QApplication(sys.argv)
    chat_gui = ChatGUI(user)  # Pass the User instance to the GUI
    chat_gui.show()
    sys.exit(app.exec())
