import socket
from User import User

if __name__ == "__main__":  #Nastavenie vlastnych parametrov
    my_ip = socket.gethostbyname(socket.gethostname())
    my_port = int(input("Enter your port: "))

    # Init Usera
    user = User(my_ip, my_port)
    user.start_listening_thread()

    send_initial = input("Do you want to send the first message? (yes/no): ").strip().lower()

    if send_initial == 'yes':
        # If sending the first message, ask for the peer's IP and port
        peer_ip = socket.gethostbyname(socket.gethostname())
        peer_port = int(input("Enter the peer's port: "))
        user.send_initial(peer_ip, peer_port)

    # Main loop
    try:
        while True:
            message = input("Enter message to send (or type 'exit' to quit): ")
            if message.lower() == 'exit':
                break
            user.send(message)

    except KeyboardInterrupt:
        print("\nCtrl+C detected. Exiting program...")

    finally:
        user.close_socket()


