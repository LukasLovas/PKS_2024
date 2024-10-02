class Header:
    def __init__(self, packet_type, fragment_order, next_fragment, data, crc):
        self.packet_type = packet_type
        self.fragment_order = fragment_order
        self.next_fragment = next_fragment
        self.data = data
        self.crc = crc

    def get_byte_data(self):
        return self.packet_type + self.fragment_order + self.next_fragment + self.data + self.crc