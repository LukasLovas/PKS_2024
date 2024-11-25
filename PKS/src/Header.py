from crc import Calculator, Crc16
class Header:
    def __init__(self, packet_type: int, fragment_order: int, next_fragment: int, data: str = "", crc: int = None):
        self.packet_type = packet_type
        self.fragment_order = fragment_order
        self.next_fragment = next_fragment
        self.data = data if data is not None else ""
        self.data_length = len(self.data.encode("utf-8")) if data is not None else 0
        self.crc = crc if crc is not None else self.calculate_crc()

    def __str__(self):
        return (f"Header:\n"
                f"  Packet Type: {self.packet_type}\n"
                f"  Fragment Order: {self.fragment_order}\n"
                f"  Next Fragment: {self.next_fragment}\n"
                f"  Data Length: {self.data_length} bytes\n"
                f"  CRC: {hex(self.crc)}\n"
                f"  Data: {self.data[:50]}{'...' if len(self.data) > 50 else ''}")

    def calculate_crc(self) -> int:
        """
        Calculate CRC for the header.

        :return: CRC checksum as an integer.
        """
        crc_calculator = Calculator(Crc16.MODBUS, optimized=True)
        partial_header = (
            self.packet_type.to_bytes(1, "big") +
            self.fragment_order.to_bytes(4, "big") +
            self.next_fragment.to_bytes(1, "big") +
            self.data_length.to_bytes(2, "big") +
            self.data.encode("utf-8")
        )
        return crc_calculator.checksum(partial_header)

    def to_bytes(self) -> bytes:
        """
        Serialize the Header into bytes for transmission.

        :return: Serialized header as bytes.
        """
        return (
            self.packet_type.to_bytes(1, "big") +
            self.fragment_order.to_bytes(4, "big") +
            self.next_fragment.to_bytes(1, "big") +
            self.data_length.to_bytes(2, "big") +
            self.crc.to_bytes(2, "big") +
            self.data.encode("utf-8")
        )

    @classmethod
    def from_bytes(cls, data_bytes: bytes):
        """
        Deserialize bytes into a Header object with decoded values.

        :param data_bytes: Serialized header bytes.
        :return: Header object.
        """
        packet_type = int.from_bytes(data_bytes[0:1], "big")
        fragment_order = int.from_bytes(data_bytes[1:5], "big")
        next_fragment = int.from_bytes(data_bytes[5:6], "big")
        data_length = int.from_bytes(data_bytes[6:8], "big")
        crc = int.from_bytes(data_bytes[8:10], "big")
        data = data_bytes[10:10 + data_length].decode("utf-8")  # Decode to string
        return cls(packet_type, fragment_order, next_fragment, data, crc)

    @staticmethod
    def create_header(packet_type: int, data: str, fragment_order: int = 1, next_fragment: int = 0x02, crc: int = None):
        """
        Create a new Header instance.

        :param packet_type: Packet type.
        :param data: Data payload (string).
        :param fragment_order: Fragment order.
        :param next_fragment: Next fragment indicator.
        :param crc: CRC checksum (optional).
        :return: Header instance.
        """
        return Header(packet_type, fragment_order, next_fragment, data, crc)
