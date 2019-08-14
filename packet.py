import struct


class Packet:
    def __init__(self, bytes_=None):
        self.content = list()
        self.bytes = None
        self.bytes_split = list()

        if bytes_:
            if type(bytes_) == bytearray:
                self.bytes = Packet.bytearray_to_bytes(bytes_)
            elif type(bytes_) == bytes:
                self.bytes = bytes_
            else:
                raise TypeError

    def unpack_from_bytes(self, unpack_string):
        for i, arg in enumerate(self.bytes_split):
            if unpack_string[i] == 's':
                self.add_to_packet(arg.decode(), 's')
            else:
                self.add_to_packet(struct.unpack(unpack_string[i], arg)[0], unpack_string[i])

    def reset_packet(self):
        self.content = list()
        self.bytes = None

    def add_to_packet(self, value, type_):
        self.content.append((value, type_))

    def build_packet(self, delimiter, end):
        if type(delimiter) == str:
            delimiter = ord(delimiter)
        if type(end) == str:
            end = ord(end)
        len_ = len(self.content)
        tmp_bytearray = bytearray()
        for i, argument in enumerate(self.content):
            if argument[1] == 's':
                tmp_bytearray.extend(argument[0].encode())
            else:
                tmp_bytearray.extend(struct.pack(argument[1], argument[0]))
            if delimiter != '' and i != len_ - 1:
                tmp_bytearray.append(delimiter)
            if i == len_ - 1:
                tmp_bytearray.append(end)
        self.bytes = Packet.bytearray_to_bytes(tmp_bytearray)

    def xor_packet(self, key):
        data_xor = bytearray(len(self.bytes))
        for i in range(len(self.bytes)):
            data_xor[i] = self.bytes[i] ^ key
        self.bytes = Packet.bytearray_to_bytes(data_xor)

    def split_packet(self, delimiter):
        if type(delimiter) == str:
            delimiter = ord(delimiter)
        arguments = list()
        current_argument = bytearray()
        for byte in self.bytes:
            if byte == delimiter and len(current_argument) != 0:
                arguments.append(current_argument)
                current_argument = bytearray()
            elif byte != delimiter:
                current_argument.append(byte)
        if len(current_argument) != 0:
            arguments.append(current_argument)
        self.bytes_split = arguments

    @staticmethod
    def bytes_to_bytearray(bytes_):
        bytearray_ = bytearray(len(bytes_))
        for byte in bytes_:
            bytearray_.append(byte)
        return bytearray_

    @staticmethod
    def bytearray_to_bytes(bytearray_):
        return bytes(bytearray_)
