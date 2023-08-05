import time


class EntryPoint:
    username: str
    password: str
    proxy: 'ForwarderProxy'
    client_host: str

    connections: list
    last_activity: float

    def __init__(self, username: str, password: str, proxy: 'ForwarderProxy', client_host: str):

        # set
        self.username = username
        self.password = password
        self.proxy = proxy
        self.client_host = client_host

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
