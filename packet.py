def xor_packet(data, key):
    data_xor = bytearray(len(data))
    for i in range(len(data)):
        data_xor[i] = data[i] ^ key
    return data_xor


def split_packet(data, delimiter):
    arguments = list()
    current_argument = bytearray()
    for byte in data:
        if byte == delimiter and len(current_argument) != 0:
            arguments.append(current_argument)
            current_argument = bytearray()
        elif byte != delimiter:
            current_argument.append(byte)
    if len(current_argument) != 0:
        arguments.append(current_argument)
    return arguments
