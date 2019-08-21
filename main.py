from server import Database
from loginserver import LoginServer, LoginClient
# import pydevd
# pydevd.settrace(suspend=False, trace_only_current_thread=True)

LOGIN_SERVER_PORT = 5330
LOCALHOST = '127.0.0.1'
DATABASE_NAME = 'warrock_data.db'


def main():
    db = Database(DATABASE_NAME)
    login_server = LoginServer(LOCALHOST, LOGIN_SERVER_PORT, db)
    login_server.setup_server(LoginClient)


main()
