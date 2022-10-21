import os
from dotenv import find_dotenv, load_dotenv
load_dotenv(find_dotenv())

class Settings:
    def __init__(self):
        self.server_ip = os.environ['SERVER_IP']
        self.server_port = int(os.environ['SERVER_PORT'])
        self.max_connections_accepted = int(os.environ['MAX_CONNECTIONS_ACCEPTED'])
        self.header_size = 10
