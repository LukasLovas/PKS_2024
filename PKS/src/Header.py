from crc import Calculator, Crc16


class Header:
    def __init__(self, packet_type: int, fragment_order: int, next_fragment: int, data, crc=None):
        self.packet_type = packet_type
        self.fragment_order = fragment_order
        self.next_fragment = next_fragment  # 0x01 - yes, 0x02 - no
        self.data = data if data is not None else ''
        self.data_length = len(self.data) if data is not None else 0
        self.crc = crc if crc is not None else self.calculate_crc()

    def __str__(self):
        return (f"Header:\n"
                f"  Packet Type: {self.packet_type}\n"
                f"  Fragment Order: {self.fragment_order}\n"
                f"  Next Fragment: {self.next_fragment}\n"
                f"  Data Length: {self.data_length}\n"
                f"  CRC: {hex(self.crc)}\n"
                f"  Data: {self.data}")

    def get_bytes_from_header(self):
        return (
            self.packet_type.to_bytes(1, 'big') +
            self.fragment_order.to_bytes(4, 'big') +
            int(self.next_fragment).to_bytes(1, 'big') +
            self.data_length.to_bytes(2, 'big') +
            self.crc.to_bytes(2, 'big') +
            self.data.encode('utf-8'))

    def get_bytes_from_header_ex_data(self):
        return (
            self.packet_type.to_bytes(1, 'big') +
            self.fragment_order.to_bytes(4, 'big') +
            int(self.next_fragment).to_bytes(1, 'big') +
            self.data_length.to_bytes(2, 'big') +
            self.crc.to_bytes(2, 'big') +
            self.data
        )
    def calculate_crc(self):
        crc_calculator = Calculator(Crc16.MODBUS, optimized=True)
        partial_header = (
            self.packet_type.to_bytes(1, 'big') +
            self.fragment_order.to_bytes(4, 'big') +
            self.next_fragment.to_bytes(1, 'big') +
            self.data_length.to_bytes(2, 'big') +
            self.data
        )
        return crc_calculator.checksum(partial_header)

    @staticmethod
    def get_header_from_bytes(data_bytes):
        packet_type = int.from_bytes(data_bytes[0:1], 'big')
        fragment_order = int.from_bytes(data_bytes[1:5], 'big')
        next_fragment = int.from_bytes(data_bytes[5:6], 'big')
        data_length = int.from_bytes(data_bytes[6:8], 'big')
        crc = int.from_bytes(data_bytes[8:10], 'big')
        data = data_bytes[10:10 + data_length]

        return Header(packet_type, fragment_order, next_fragment, data, crc)

    @staticmethod
    def create_header(packet_type, data, fragment_order: int = 1, next_fragment: int = False, crc=None):
        return Header(packet_type, fragment_order, next_fragment, data, crc)
