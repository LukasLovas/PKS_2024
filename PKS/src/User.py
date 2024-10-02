import socket
import threading


class User:
    def __init__(self, ip: str, port: int) -> None:
        self.ip = ip
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((ip, port))
        self.peer = None  # Peer ako pomocna struktura, nastavi sa po prvej message
        print(f"User listening on {self.ip}:{self.port}")


    def set_peer(self, ip: str, port: int) -> None:
        #Peer sa nastavi po prvej sprave
        self.peer = self.Peer(ip, port)
        print(f"Peer set to {self.peer.peer_ip}:{self.peer.peer_port}")



    class Peer:
        def __init__(self, ip: str, port: int) -> None:
            self.peer_ip = ip
            self.peer_port = port


        def connection_tuple(self):
            return self.peer_ip, self.peer_port



    def send_initial(self, ip: str, port: int) -> None:
        #Prva inicializacna sprava
        self.socket.sendto("Initialize".encode('utf-8'), (ip, port))
        print(f"Sent initial message to {ip}:{port}")



    def send(self, data: str) -> None:
        #Klasicke poslanie spravy
        if self.peer is None:
            print("No peer set. Cannot send message.")
        else:
            self.socket.sendto(data.encode('utf-8'), self.peer.connection_tuple())
            print(f"Sent: {data} to {self.peer.peer_ip}:{self.peer.peer_port}")



    def listen(self, buffer_size: int = 1024) -> None:
        #Listening loop
        while True:
            try:
                message, address = self.socket.recvfrom(buffer_size)
                sender_ip, sender_port = address
                print(f"Received message: {message.decode('utf-8')} from {sender_ip}:{sender_port}\nEnter message to send (or type 'exit' to quit): \n")

                #Nastavenie peer usera
                if self.peer is None:
                    self.set_peer(sender_ip, sender_port)

            except OSError:
                break



    def start_listening_thread(self) -> None:
        #Zapnutie pocuvacieho threadu
        listen_thread = threading.Thread(target=self.listen, daemon=True)
        listen_thread.start()



    def close_socket(self):
        #Vypnutie socketu
        self.socket.close()
