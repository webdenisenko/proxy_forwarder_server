import ipaddress
import time

from controller.objetcs.Proxy import Proxy


class EntryPoint:
    username: str
    password: str
    proxy: Proxy
    entry_host: str

    connections: list
    last_activity: float

    def __init__(self, username: str, password: str, proxy_ident: str, entry_host: str):

        # set
        self.username = username
        self.password = password
        self.proxy = Proxy(proxy_ident)
        self.entry_host = ipaddress.ip_address(entry_host).compressed

        # default
        self.connections = []
        self.last_activity = time.time()

    def update_activity(self):
        self.last_activity = time.time()

    def close_all_connections(self):
        for connection in self.connections.copy():
            try:
                connection.close()
            except:
                pass

        self.connections = []

        return True
