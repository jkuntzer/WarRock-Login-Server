from server import Server, Database
from client import Client
import random
import time
import string
import hashlib
from socket import timeout


class LoginServer(Server):
    ENCODE_KEY = 150
    DECODE_KEY = 195

    def __init__(self, address: str, port: int, database: Database):
        super().__init__(address, port, database)

    def populate_op_code_table(self):
        type(self).OP_CODE_TABLE = dict()
        type(self).OP_CODE_TABLE['4352'] = self.op_4352
        type(self).OP_CODE_TABLE['4608'] = self.op_4608

    @staticmethod
    def op_4608(client):
        packet = client.packet_send
        packet.reset_packet()
        packet.add_to_packet([str(int(time.time() * 1000)), '4608', ''.join(random.choices(string.digits, k=9))],
                             's'*3)
        client.send_packet()

    @staticmethod
    def op_4352(client):
        packet_send = client.packet_send
        packet_recv = client.packet_recv
        db = client.server.database
        packet_args = packet_recv.unpack_multiple('s' * 8)
        login_success = False
        warrock_ID, warrock_name, level, experience, account_ID, user_name = '', '', '', '', '', ''

        db_reply = db.execute_command('SELECT user_name FROM user_data WHERE user_name=?;', (packet_args[2],))
        if not db_reply:
            reply_code = '72010'
        else:
            try:
                (account_ID, user_name) = db.execute_command('SELECT account_ID, user_name FROM user_data '
                                                             'WHERE user_name=? AND password=?;',
                                                             (packet_args[2],
                                                              hashlib.sha256(packet_args[3].encode()).hexdigest()))[0]
                reply_code = '1'
                login_success = True
            except ValueError:
                reply_code = '72020'
        packet_send.reset_packet()
        packet_send.add_to_packet([str(int(time.time() * 1000)), '4352', reply_code], 's'*3)
        if login_success:
            (warrock_ID, warrock_name, level, experience) = db.execute_command('SELECT warrock_ID, '
                                                                               'warrock_name, level, experience '
                                                                               'FROM warrock_data '
                                                                               'WHERE account_ID=?;', (account_ID,))[0]
            packet_send.add_to_packet([account_ID, '0', user_name, warrock_ID, warrock_name], 's'*5)
            packet_send.add_to_packet(['0', '0', experience, level, '1.00000'], 's'*5)
            packet_send.add_to_packet([str(int(time.time() * 1000))
                                      + '-' + ''.join(random.choices(string.hexdigits, k=16)).upper()], 's')
            packet_send.add_to_packet(['-1' for _ in range(8)], 's'*8)
            packet_send.add_to_packet(['1', '2', 'Bossplayer', '127.0.0.1', '10375', '4000', '1'], 's'*7)
        client.send_packet()


class LoginClient(Client):

    def __init__(self, client_socket, address, server: LoginServer):
        super().__init__(client_socket, address, server)
        # self.login_name = ''
        # self.warrock_name = ''
        # self.login_id = 0
        # self.warrock_id = 0

    def process_received_packet(self):
        self.packet_recv.xor_packet(LoginServer.DECODE_KEY)
        self.packet_recv.split_packet(32)
        func_ = self.return_op_code_handler()
        func_(self)

    def return_op_code_handler(self):
        op_code = self.packet_recv.unpack_multiple('ss')[1]
        if op_code in LoginServer.OP_CODE_TABLE:
            return LoginServer.OP_CODE_TABLE[op_code]
        else:
            raise Client.UnknownOPCodeError(op_code)

    def send_packet(self):
        self.packet_send.build_packet(' ', '\n')
        self.packet_send.xor_packet(LoginServer.ENCODE_KEY)
        self.connection_socket.sendall(self.packet_send.bytes)

    def process_connection(self):
        try:
            # send welcome packet first
            LoginServer.op_4608(self)
            self.receive_packet(201)
            self.connection_socket.close()
        except timeout:
            print('Connection from', self.address, 'timed out.')
