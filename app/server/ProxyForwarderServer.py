import base64
import ipaddress
import pickle
import socket
import threading
import select
import time
from typing import Dict, List

import socks
from decouple import config

from app.objetcs.EntryPoint import EntryPoint
from app.objetcs.ForwarderProxy import ForwarderProxy
from app.server import SocketCommunication
from app.utils.get_logger import get_logger

PUBLIC_PROXY_PORT = config('PUBLIC_PROXY_PORT', cast=int)
INSIDE_SOCKET_PORT = config('INSIDE_SOCKET_PORT', cast=int)

SOCKS_VERSION = 5
logger = get_logger(__name__)


@SocketCommunication.listen(INSIDE_SOCKET_PORT)
class ProxyForwarderServer:

    TELEGRAM_SERVERS = [
        '91.105.192.0/23', '91.108.4.0/22', '91.108.8.0/22', '91.108.12.0/22',
        '91.108.16.0/22', '91.108.20.0/22', '91.108.56.0/23', '91.108.58.0/23',
        '95.161.64.0/20', '149.154.160.0/21', '149.154.168.0/22', '149.154.172.0/22',
        '185.76.151.0/24',
    ]

    BUFFER_SIZE = 4096
    INACTIVE_TIMEOUT = 300 # sec

    DISALLOW_ADDRESSES = [
        '8.8.8.8'
    ]

    listening_socket: socket

    entry_points: Dict[str, EntryPoint] # username as entry point identificator
    allowed_hosts: Dict[str, List[str]] # host as key, list of usernames on host as value
    dump_streams: Dict[str, List[Dict]] # username as dump identificator, connection session -> {outgoing_stream: bytes, outgoing_size_b: float, incoming_stream: bytes, incoming_size_b: float} as value

    def __init__(self):
        """
        Run proxy server forwarder to another proxy by targets and entry points.
        """

        # default init
        self.entry_points = {}
        self.allowed_hosts = {}
        self.dump_streams = {}

        # init listener socket
        self.listening_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Bind proxy server on special port
        self.listening_socket.bind(('127.0.0.1', PUBLIC_PROXY_PORT))

        # run listener socket
        self.listening_socket.listen(socket.SOMAXCONN)

        # monitoring connections
        threading.Thread(target=self._watch_new_connections).start()

        # monitoring inactive connection
        threading.Thread(target=self._inactive_connection_monitoring, daemon=True).start()

        logger.info(f'Proxy forwarder server launched on port ::{PUBLIC_PROXY_PORT}')

    def _watch_new_connections(self):

        # watch connections
        while True:
            try:
                conn, addr = self.listening_socket.accept()

                # refuse unrecognized entry hosts
                if addr[0] not in self.allowed_hosts:
                    self._refuse_connection(conn)
                    continue

                # send to validation
                threading.Thread(target=self._validate_new_connection, args=(conn, addr[0])).start()

            except (ConnectionAbortedError, OSError):
                logger.debug('listener closed')
                return

    def _validate_new_connection(self, connection, entry_address):
        try:
            version, nmethods = connection.recv(2)
            methods = [ord(connection.recv(1)) for i in range(nmethods)]
            assert 2 in set(methods)

            # send welcome message
            connection.sendall(bytes([SOCKS_VERSION, 2]))

            # verify username and password
            version = ord(connection.recv(1))  # should be 1
            username_len = ord(connection.recv(1))
            username = connection.recv(username_len).decode('utf-8')
            password_len = ord(connection.recv(1))
            password = connection.recv(password_len).decode('utf-8')

            # validation: has in entry points
            assert username in self.entry_points

            # validation: password match
            assert self.entry_points[username].password == password

            # validation: entry hosts match
            assert self.entry_points[username].client_host == entry_address

            connection.sendall(bytes([version, 0]))
        except:
            # invalid request
            return self._refuse_connection(connection)
        
        # send to connection thread
        threading.Thread(target=self._connection_thread, args=(connection, username)).start()

    def _connection_thread(self, connection, username):
        version, cmd, _, address_type = connection.recv(4)

        if cmd != 1:
            return self._refuse_connection(connection)

        if address_type == 1:  # IPv4
            address = socket.inet_ntoa(connection.recv(4))
        elif address_type == 3:  # Domain name
            domain_length = connection.recv(1)[0]
            address = connection.recv(domain_length)
            address = socket.gethostbyname(address)
        else:
            return self._refuse_connection(connection)

        # remote address disallowed
        if address in self.DISALLOW_ADDRESSES:
            return self._refuse_connection(connection)

        # convert bytes to unsigned short array
        port = int.from_bytes(connection.recv(2), 'big', signed=False)

        # append connection
        self.entry_points[username].connections.append(connection)

        # connecting to remote
        remote = socks.socksocket(socket.AF_INET, socket.SOCK_STREAM)

        # connect proxy
        proxy = self.entry_points[username].proxy
        remote.connect((proxy.host, proxy.port))
        remote.sendall(b'CONNECT %s:%s HTTP/1.1\r\n'
                       b'Proxy-Authorization: Basic %s\r\n\r\n' %
                       (address.encode(), str(port).encode(), base64.b64encode(bytes(f'{proxy.username}:{proxy.password}', 'utf-8'))))

        bind_address = remote.getsockname()
        logger.info(f'Connected to {address}:{port} via http proxy({str(proxy)[:20]}...)')

        addr = int.from_bytes(socket.inet_aton(bind_address[0]), 'big', signed=False)
        port = bind_address[1]

        reply = b''.join([
            SOCKS_VERSION.to_bytes(1, 'big'),
            int(0).to_bytes(1, 'big'),
            int(0).to_bytes(1, 'big'),
            int(1).to_bytes(1, 'big'),
            addr.to_bytes(4, 'big'),
            port.to_bytes(2, 'big')
        ])
        connection.sendall(reply)

        # append connection
        self.entry_points[username].connections.append(remote)

        # establish data exchange
        if reply[1] == 0:

            # is telegram stream
            dump_stream = any([ipaddress.IPv4Address(address) in ipaddress.IPv4Network(ip_mask) for ip_mask in self.TELEGRAM_SERVERS])

            # define current stream index in slot
            dump_index = len(self.dump_streams)
            self.dump_streams[username].append({
                'outgoing_stream': [] if dump_stream else None,
                'outgoing_size_b': 0,
                'incoming_stream': [] if dump_stream else None,
                'incoming_size_b': 0,
            })

            # proxy connected
            proxy_response = remote.recv(self.BUFFER_SIZE).decode('utf-8')
            if not proxy_response.startswith('HTTP/1.1 200'):
                return self._refuse_connection(connection)

            # communicate
            while True:

                # wait until client or remote is available for read
                r, w, e = select.select([connection, remote], [], [])

                # update last activity
                self.entry_points[username].update_activity()

                # send from client
                if connection in r:
                    data = connection.recv(self.BUFFER_SIZE)

                    # dump stream data
                    if dump_stream:
                        self.dump_streams[username][dump_index]['outgoing_stream'].append((time.time(), data))

                    # increase stream size
                    self.dump_streams[username][dump_index]['outgoing_size_b'] += len(data)

                    if remote.send(data) <= 0:
                        break

                # receive from remote
                if remote in r:
                    data = remote.recv(self.BUFFER_SIZE)

                    # dump stream data
                    if dump_stream:
                        self.dump_streams[username][dump_index]['incoming_stream'].append((time.time(), data))

                    # increase stream size
                    self.dump_streams[username][dump_index]['incoming_size_b'] += len(data)

                    if connection.send(data) <= 0:
                        break

        # close connection
        try:
            connection.close()
        except:
            pass

        try:
            remote.close()
        except:
            pass

    @staticmethod
    def _refuse_connection(connection):
        try:
            connection.sendall(bytes([1, 0xFF]))
            connection.close()
        except OSError:
            # connection already closed
            return

    def _inactive_connection_monitoring(self):
        while True:
            inactive_entry_points = [username for username in self.entry_points.keys() if time.time() - self.entry_points[username].last_activity > self.INACTIVE_TIMEOUT]

            for username in inactive_entry_points:
                self.delete_entry_point(username)
                logger.info(f'entry point `{username}` closed due to inactivity')

            time.sleep(self.INACTIVE_TIMEOUT)

    @SocketCommunication.method(INSIDE_SOCKET_PORT)
    def create_entry_point(self, username: str, password: str, proxy_kwargs: dict, client_host: str = None):

        # check duplicate
        if username in self.entry_points:
            return None

        # localhost as default
        client_host = client_host or '127.0.0.1'

        proxy = ForwarderProxy(**proxy_kwargs)

        # create entry point object
        entry_point = EntryPoint(
            username=username,
            password=password,
            proxy=proxy,
            client_host=client_host,
        )

        # allow host
        if client_host not in self.allowed_hosts:
            self.allowed_hosts[client_host] = []

        # set link to entry point object
        self.allowed_hosts[client_host].append(username)

        # set entry point object
        self.entry_points[username] = entry_point

        # set dump slot
        self.dump_streams[username] = []

        return time.time()

    @SocketCommunication.method(INSIDE_SOCKET_PORT)
    def delete_entry_point(self, username: str):

        if username not in self.entry_points:
            return None

        # close all entry point connections
        self.entry_points[username].close_all_connections()

        # delete from allowed hosts
        client_host = self.entry_points[username].client_host
        self.allowed_hosts[client_host].remove(username)

        # delete allowed host if empty
        if not self.allowed_hosts[client_host]:
            del self.allowed_hosts[client_host]

        # delete entry point
        del self.entry_points[username]

        # convert and clear dump
        dump_stream = pickle.dumps(self.dump_streams[username]).hex()
        del self.dump_streams[username]

        return {
            'stream': dump_stream,
            'timestamp': time.time()
        }

    @SocketCommunication.method(INSIDE_SOCKET_PORT)
    def exists_entry_point(self, username: str):
        return username in self.entry_points

    @SocketCommunication.method(INSIDE_SOCKET_PORT)
    def terminate(self):
        # response until socket alive and close all sockets
        return threading.Thread(target=self._terminate).start()

    def _terminate(self):
        # close all active connections
        [self.delete_entry_point(entry_points) for entry_points in self.entry_points.copy().keys()]

        # close listener
        self.listening_socket.close()

        # close socket communicator
        self._socket_communication.listener.close()


if __name__ == '__main__':
    ProxyForwarderServer()