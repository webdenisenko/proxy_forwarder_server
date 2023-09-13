import socket
import time
from typing import Dict, List, Optional

import socks

from app.objetcs.RemotePoint import RemotePoint


class EntryPoint:
    username: str
    password: str
    proxy: 'ForwarderProxy'
    client_host: str
    inspector: Optional[dict]

    remote_points: Dict[str, List[RemotePoint]] # address:port -> RP

    def __init__(self, username: str, password: str, proxy: 'ForwarderProxy', client_host: str, inspector: dict = None):

        # set
        self.username = username
        self.password = password
        self.proxy = proxy
        self.client_host = client_host

        if inspector:
            inspector_socket = socks.socksocket(socket.AF_INET, socket.SOCK_STREAM)
            inspector_socket.settimeout(1)
            if inspector_socket.connect_ex((inspector['address'], inspector['port'])) != 0:
                print(f"Inspector socket {inspector['address']}:{inspector['port']} is not available")
            self.inspector = inspector
        else:
            self.inspector = None

        # default
        self.remote_points = {}
        self.last_activity = time.time()

    def create_remote_point(self, server_address: str, port: int, client_socket: socks.socksocket):
        address_port = f'{server_address}:{port}'

        # add new remote address
        if address_port not in self.remote_points:
            self.remote_points[address_port] = []

        # create remote point
        RP = RemotePoint(server_address, port, client_socket, self.proxy, self.inspector)
        self.remote_points[address_port].append(RP)

        return RP

    def close(self):
        total_proxy_outgoing_usage_b = 0
        total_proxy_incoming_usage_b = 0

        # close connections and get proxy usage counts
        for RPs in self.remote_points.copy().values():
            for RP in RPs:
                if RP.is_active:
                    proxy_outgoing_usage_b, proxy_incoming_usage_b = RP.close()
                    total_proxy_outgoing_usage_b += proxy_outgoing_usage_b
                    total_proxy_incoming_usage_b += proxy_incoming_usage_b

        return total_proxy_outgoing_usage_b, total_proxy_incoming_usage_b
