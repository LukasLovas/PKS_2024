import sys
import socket
from PyQt6.QtWidgets import QApplication
from ChatGUI import ChatGUI
from User import User


if __name__ == "__main__":
    my_ip = socket.gethostbyname(socket.gethostname())
    my_port = int(input("Enter your port: "))

    user = User(my_ip, my_port)
    user.start_listening_thread()

    if int(input("Do you want to initialize a connection? [0/1]: ")) == 1:
        peer_ip = socket.gethostbyname(socket.gethostname())
        peer_port = int(input("Enter the peer's port: "))
        user.send_syn(peer_ip, peer_port)
    else:
        print()

    while not user.handshake_done:
        pass

    app = QApplication(sys.argv)
    chat_gui = ChatGUI(user)
    chat_gui.show()
    sys.exit(app.exec())
