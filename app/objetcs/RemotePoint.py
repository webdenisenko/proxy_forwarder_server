import base64
import ipaddress
import select
import socket
import struct
import threading
import time
from typing import Optional

import socks

from app.settings import GOOGLE_IPS
from app.utils.get_logger import get_logger

BUFFER_SIZE = 4096
logger = get_logger(__name__)


class RemotePoint:
    remote_address: str
    port: int
    client_socket: socks.socksocket
    server_socket: socks.socksocket

    is_active: bool
    created_at: float
    updated_at: float

    reason_skip_proxy: Optional[str]
    proxy_outgoing_usage_b: int # total bytes size (only proxy usage)
    proxy_incoming_usage_b: int # total bytes size (only proxy usage)

    inspector: Optional[dict]
    inspector_socket: Optional[socks.socksocket]
    inspector_lock: threading.Lock

    def __init__(self, remote_address: str, port: int, client_socket: socks.socksocket, proxy: 'ForwarderProxy', inspector: dict = None):
        self.remote_address = remote_address
        self.port = port
        self.client_socket = client_socket

        # connect to inspector socket (if necessary)
        if inspector:
            self.inspector_socket = socks.socksocket(socket.AF_INET, socket.SOCK_STREAM)
            self.inspector_socket.connect((inspector['address'], inspector['port']))
            self.inspector_socket.sendall(bytes(remote_address.ljust(18), 'utf-8'))
            self.inspector_lock = threading.Lock()
        else:
            self.inspector_socket = None
            self.inspector_lock = None

        self.inspector = inspector

        self.proxy_outgoing_usage_b = 0
        self.proxy_incoming_usage_b = 0
        self.is_active = False
        self.created_at = self.updated_at = time.time()

        # connecting to remote
        self.server_socket = socks.socksocket(socket.AF_INET, socket.SOCK_STREAM)

        # don't use proxy for local network and Google servers
        if self.is_local_ip(remote_address):
            self.reason_skip_proxy = 'local network'
        elif self.is_google_ip(remote_address):
            self.reason_skip_proxy = 'google server'
        else:
            self.reason_skip_proxy = None

        # default connection for local network
        if self.reason_skip_proxy:
            self.server_socket.connect((self.remote_address, port))
            logger.info(f'Connected to {self.remote_address}:{self.port} ({self.reason_skip_proxy})')

        # connect proxy
        else:
            self.server_socket.connect((proxy.host, proxy.port))
            self.server_socket.sendall(b'CONNECT %s:%s HTTP/1.1\r\n'
                                       b'Proxy-Authorization: Basic %s\r\n\r\n' %
                                       (self.remote_address.encode(), str(self.port).encode(), base64.b64encode(bytes(f'{proxy.username}:{proxy.password}', 'utf-8'))))
            logger.info(f'Connected to {self.remote_address}:{self.port} (via proxy - {proxy.country})')

        bind_address = self.server_socket.getsockname()
        addr = int.from_bytes(socket.inet_aton(bind_address[0]), 'big', signed=False)
        port = bind_address[1]

        reply = b''.join([
            int(5).to_bytes(1, 'big'), # socket version
            int(0).to_bytes(1, 'big'),
            int(0).to_bytes(1, 'big'),
            int(1).to_bytes(1, 'big'),
            addr.to_bytes(4, 'big'),
            port.to_bytes(2, 'big')
        ])
        self.client_socket.sendall(reply)

        # establish data exchange
        if reply[1] != 0:
            raise self.refuse_connection(self.client_socket)

        # get proxy response
        if not self.reason_skip_proxy:
            proxy_response = self.server_socket.recv(BUFFER_SIZE).decode('utf-8')
            if not proxy_response.startswith('HTTP/1.1 200'):
                raise self.refuse_connection(self.client_socket, f'the proxy did not confirm the connection to {remote_address}')

        # connected via proxy
        self.is_active = True

    def watch(self):
        try:
            # communicate
            while True:

                # wait until client or remote is available for read
                try:
                    r, w, e = select.select([self.client_socket, self.server_socket], [], [])
                except OSError:
                    break

                # update last activity
                self.updated_at = time.time()

                # send from client
                if self.client_socket in r:
                    data = self.client_socket.recv(BUFFER_SIZE)

                    if self.server_socket.send(data) <= 0:
                        break

                    # process
                    threading.Thread(target=self.process_package, args=(data, True), daemon=True).start()

                # receive from remote
                if self.server_socket in r:
                    data = self.server_socket.recv(BUFFER_SIZE)

                    if self.client_socket.send(data) <= 0:
                        break

                    # process
                    threading.Thread(target=self.process_package, args=(data, False), daemon=True).start()
        finally:
            # close connection
            self.close()

    def close(self):
        try:
            self.client_socket.close()
        except:
            pass

        try:
            self.server_socket.close()
        except:
            pass

        self.is_active = False

        return (self.proxy_outgoing_usage_b, self.proxy_incoming_usage_b) if not self.reason_skip_proxy else (0, 0)

    def process_package(self, data, is_outgoing: bool):
        package_size = len(data)
        key = 'outgoing' if is_outgoing else 'incoming'

        # counting proxy usage
        if not self.reason_skip_proxy:
            setattr(self, f'proxy_{key}_usage_b', getattr(self, f'proxy_{key}_usage_b') + package_size)

        if self.inspector_socket:

            # filters
            if self.inspector['filters'] and not any([ipaddress.IPv4Address(self.remote_address) in ipaddress.IPv4Network(ip_mask) for ip_mask in self.inspector['filters']]):
                return

            with self.inspector_lock:
                package_size = struct.pack('>I', package_size)
                is_outgoing = int(is_outgoing).to_bytes(1, 'little')

                try:
                    self.inspector_socket.sendall(package_size + is_outgoing + data)
                except BrokenPipeError:
                    self.inspector_socket = None
                    logger.error('inspector socket close connection')

    @staticmethod
    def refuse_connection(connection: socks.socksocket, message: str = 'connection refused'):
        try:
            connection.sendall(bytes([1, 0xFF]))
            connection.close()
            return ConnectionError(message)
        except OSError:
            # connection already closed
            return

    @staticmethod
    def is_local_ip(ip: str):
        return ip.startswith('192.168.') or ip.startswith('127.0.')

    @staticmethod
    def is_google_ip(ip: str):
        return any([ipaddress.IPv4Address(ip) in ipaddress.IPv4Network(ip_mask) for ip_mask in GOOGLE_IPS])
