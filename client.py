from packet import Packet


class Client:
    class UnknownOPCodeError(Exception):
        def __init__(self, op_code):
            self.op_code = op_code

    def __init__(self, client_socket, address, server):
        self.address = address
        self.connection_socket = client_socket
        self.server = server
        self.packet_recv = Packet()
        self.packet_send = Packet()

    def receive_packet(self, delimiter):
        total_data = []
        while True:
            try:
                data = self.connection_socket.recv(2048)
                if not data:
                    break
                if data[-1] == delimiter:
                    total_data.append(data[:-1])
                    self.packet_recv = Packet(b''.join(total_data))
                    self.process_received_packet()
                else:
                    total_data.append(data)
            except ConnectionResetError:
                print('Connection with', self.address, 'was terminated.')
                break
            except Client.UnknownOPCodeError as e:
                print('Unknown op code encountered:', e.op_code)

    def process_connection(self):
        raise NotImplementedError

    def process_received_packet(self):
        raise NotImplementedError
