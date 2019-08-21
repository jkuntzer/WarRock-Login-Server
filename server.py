import socket
import sys
import threading
import sqlite3
from client import Client


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


class Server:
    OP_CODE_TABLE = None  # has to be initialized by the inherited class

    def __init__(self, address: str, port: int, database: Database):
        self.address = address
        self.port = port
        self.server = None
        self.database = database
        self.op_code_table = dict()
        self.populate_op_code_table()

    def populate_op_code_table(self):
        raise NotImplementedError

    def setup_server(self, client_class):
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
                new_client = client_class(client_socket, cl_address, self)
                thread_ = threading.Thread(target=new_client.process_connection)
                thread_.start()
            except:
                print('An unknown error was raised while talking to the client.')
                print(sys.exc_info()[0], '|', sys.exc_info()[1])
                break
        self.server.close()
