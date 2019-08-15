import socket
import sys
import time
import random
import string
import threading
import sqlite3
from packet import *
import hashlib

# import pydevd
# pydevd.settrace(suspend=False, trace_only_current_thread=True)


class Database:
    def __init__(self, file_name):
        self.file_name = file_name

    def execute_command(self, command, args, commit=False):
        db = sqlite3.connect(self.file_name)
        cursor = db.cursor()
        cursor.execute(command, args)

        if commit:
            db.commit()
        db_reply = cursor.fetchall()
        db.close()
        return db_reply


class UnknownOPCodeError(Exception):
    def __init__(self, op_code):
        self.op_code = op_code


class LoginServer:
    ENCODE_KEY = 150
    DECODE_KEY = 195
    OP_CODE_TABLE_FUNCS = dict()

    def __init__(self, address: str, port: int, database: Database):
        self.address = address
        self.port = port
        self.server = None
        self.database = database

    @staticmethod
    def populate_op_code_table_funcs():
        if not LoginServer.OP_CODE_TABLE_FUNCS:
            LoginServer.OP_CODE_TABLE_FUNCS['4352'] = LoginServer.op_4352

    def setup_server(self):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((self.address, self.port))
        # max amount of connections is system dependent
        self.server.listen(10)
        print('Server is setup and awaiting connections.')

        while True:
            try:
                client_socket, cl_address = self.server.accept()
                client_socket.settimeout(10)
                print('Server has accepted connection from:', cl_address[0])
                new_client = Client(client_socket, cl_address, self)
                thread_ = threading.Thread(target=new_client.process_connection)
                thread_.start()
            except:
                print('An unknown error was raised while talking to the client.')
                print(sys.exc_info()[0], '|', sys.exc_info()[1])
                break
        self.server.close()

    @staticmethod
    def op_4608(client):
        packet = client.packet_send
        packet.reset_packet()
        packet.add_to_packet(str(int(time.time() * 1000)), 's')
        packet.add_to_packet('4608', 's')
        packet.add_to_packet(''.join(random.choices(string.digits, k=9)), 's')
        client.send_packet()

    @staticmethod
    def op_4352(client):
        packet_send = client.packet_send
        packet_recv = client.packet_recv
        db = client.server.database
        packet_args = packet_recv.unpack_multiple('s' * 8)

        db_reply = db.execute_command('SELECT user_name FROM user_data WHERE user_name=?;', (packet_args[2],))
        if not db_reply:
            reply_code = '72010'
        else:
            db_reply = db.execute_command('SELECT user_name FROM user_data WHERE user_name=? AND password=?;',
                                          (packet_args[2], hashlib.sha256(packet_args[3].encode()).hexdigest()))
            if not db_reply:
                reply_code = '72020'
            else:
                reply_code = '0'
                print('Correct login!')
        packet_send.reset_packet()
        packet_send.add_to_packet(str(int(time.time() * 1000)), 's')
        packet_send.add_to_packet('4352', 's')
        packet_send.add_to_packet(reply_code, 's')
        client.send_packet()


LoginServer.populate_op_code_table_funcs()


class Client:
    def __init__(self, client_socket, address, server: LoginServer):
        self.address = address
        self.connection_socket = client_socket
        self.server = server
        self.packet_recv = Packet()
        self.packet_send = Packet()

    def process_connection(self):
        try:
            # send welcome packet first
            LoginServer.op_4608(self)
            self.handle_requests(201)
            self.connection_socket.close()
        except socket.timeout:
            print('Connection from', self.address, 'timed out.')

    def handle_requests(self, delimiter):
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
            except UnknownOPCodeError as e:
                print('Unknown op code encountered:', e.op_code)

    def process_received_packet(self):
        self.packet_recv.xor_packet(LoginServer.DECODE_KEY)
        self.packet_recv.split_packet(32)
        func_ = self.return_op_code_handler()
        func_(self)

    def return_op_code_handler(self):
        op_code = self.packet_recv.unpack_multiple('ss')[1]
        if op_code in LoginServer.OP_CODE_TABLE_FUNCS:
            return LoginServer.OP_CODE_TABLE_FUNCS[op_code]
        else:
            raise UnknownOPCodeError(op_code)

    def send_packet(self):
        self.packet_send.build_packet(' ', '\n')
        self.packet_send.xor_packet(LoginServer.ENCODE_KEY)
        self.connection_socket.sendall(self.packet_send.bytes)

