import sys
from PyQt6.QtWidgets import QApplication
from ChatGUI import ChatGUI
from User import User


if __name__ == "__main__":
    #my_ip = str(input("Enter IP:"))
    my_ip = "localhost"
    my_port = int(input("Enter your port: "))

    user = User(my_ip, my_port)
    thread = user.start_listening_thread()

    if int(input("Do you want to initialize a connection? [0/1]: ")) == 1:
        #peer_ip = str(input("Enter IP:"))
        peer_ip = "localhost"
        peer_port = int(input("Enter the peer's port: "))
        user.send_syn(peer_ip, peer_port)
    else:
        print()

    while not user.handshake_done:
        pass
    thread.join()
    user.start_keepalive_thread()

    app = QApplication(sys.argv)
    chat_gui = ChatGUI(user)
    user.chat_gui = chat_gui
    chat_gui.show()
    sys.exit(app.exec())
