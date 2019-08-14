import socket
import sys
import struct
import time
import random
import string
import threading
import sqlite3
from packet import *

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
        db.close()
        return cursor.fetchall()


class LoginServer:
    ENCODE_KEY = 150
    DECODE_KEY = 195
    OP_CODE_TABLE = dict()

    def __init__(self, address: str, port: int, database: Database):
        self.address = address
        self.port = port
        self.server = None
        self.database = database

    @staticmethod
    def populate_op_code_table():
        if not LoginServer.OP_CODE_TABLE:
            LoginServer.OP_CODE_TABLE['4352'] = LoginServer.op_4352

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
        client.add_to_packet(str(int(time.time() * 1000)), 'str')
        client.add_to_packet('4608', 'str')
        client.add_to_packet(''.join(random.choices(string.digits, k=9)), 'str')

    @staticmethod
    def op_4352(client):
        client.add_to_packet(str(int(time.time() * 1000)), 'str')
        client.add_to_packet('4352', 'str')

        client.add_to_packet('72020', 'str')


LoginServer.populate_op_code_table()


class Client:
    def __init__(self, client_socket, address, server):
        self.address = address
        self.connection_socket = client_socket
        self.packet_content = list()
        self.packet_bytes = bytearray()
        self.server = server
        self.packet_received_args = list()

    def reset_packet(self):
        self.packet_content = list()
        self.packet_bytes = bytearray()

    def process_connection(self):
        try:
            # send welcome packet first
            self.send_packet(LoginServer.op_4608)
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
                    self.process_received_packet(b''.join(total_data))
                else:
                    total_data.append(data)
            except ConnectionResetError:
                print('Connection with', self.address, 'was terminated.')
                break

    def process_received_packet(self, data):
        packet_dec = xor_packet(data, LoginServer.DECODE_KEY)
        self.packet_received_args = split_packet(packet_dec, delimiter=32)


    def return_op_code_handler(self):
        op_code = self.packet_received_args[1].decode()
        if op_code in LoginServer.OP_CODE_TABLE:
            return LoginServer.OP_CODE_TABLE[op_code]
        else:
            print('Unknown op code encountered:', op_code)
            return None

    def send_packet(self, func_):
        if not func_:
            return False
        self.reset_packet()
        func_(self)
        self.build_packet(' ', '\n')
        self.packet_bytes = xor_packet(self.packet_bytes, LoginServer.ENCODE_KEY)
        self.connection_socket.sendall(self.packet_bytes)
        return True

    def add_to_packet(self, value, type_):
        self.packet_content.append((value, type_))

    def build_packet(self, delimiter='', end=''):
        len_ = len(self.packet_content)
        for i, argument in enumerate(self.packet_content):
            if argument[1] == 'str':
                for char_ in argument[0]:
                    self.packet_bytes.append(ord(char_))
            else:
                self.packet_bytes.extend(struct.pack(argument[1], argument[0]))
            if delimiter != '' and i != len_ - 1:
                self.packet_bytes.append(ord(delimiter))
            if i == len_ - 1:
                self.packet_bytes.append(ord(end))
