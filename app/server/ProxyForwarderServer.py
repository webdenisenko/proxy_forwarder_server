import socket
import threading
import time
import traceback
from typing import Dict, List

from decouple import config

from app.objetcs.EntryPoint import EntryPoint
from app.objetcs.ForwarderProxy import ForwarderProxy
from app.objetcs.RemotePoint import RemotePoint
from app.server import SocketCommunication
from app.utils.get_logger import get_logger

PUBLIC_PROXY_PORT = config('PUBLIC_PROXY_PORT', cast=int)
INSIDE_SOCKET_PORT = config('INSIDE_SOCKET_PORT', cast=int)

logger = get_logger(__name__)


@SocketCommunication.listen(INSIDE_SOCKET_PORT)
class ProxyForwarderServer:
    INACTIVE_TIMEOUT = 300 # sec

    DISALLOW_ADDRESSES = [
        '8.8.8.8'
    ]

    listening_socket: socket

    entry_points: Dict[str, EntryPoint] # username as entry point identificator
    allowed_hosts: Dict[str, List[str]] # host as key, list of usernames on host as value

    def __init__(self):
        """
        Run proxy server forwarder to another proxy by targets and entry points.
        """

        # default init
        self.entry_points = {}
        self.allowed_hosts = {}

        # init listener socket
        self.listening_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Bind proxy server on special port
        self.listening_socket.bind(('0.0.0.0', PUBLIC_PROXY_PORT))

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

                print('data', conn.recv(4015))

                # refuse unrecognized entry hosts
                if addr[0] not in self.allowed_hosts:
                    RemotePoint.refuse_connection(conn)
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

            # send welcome message (5 - is socket version)
            connection.sendall(bytes([5, 2]))

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
            return RemotePoint.refuse_connection(connection)
        
        # send to connection thread
        threading.Thread(target=self._connection_thread, args=(connection, username)).start()

    def _connection_thread(self, connection, username):
        version, cmd, _, address_type = connection.recv(4)

        if cmd != 1:
            return RemotePoint.refuse_connection(connection)

        if address_type == 1:  # IPv4
            address = socket.inet_ntoa(connection.recv(4))
        elif address_type == 3:  # Domain name
            domain_length = connection.recv(1)[0]
            address = connection.recv(domain_length)
            address = socket.gethostbyname(address)
        else:
            return RemotePoint.refuse_connection(connection)

        # remote address disallowed
        if address in self.DISALLOW_ADDRESSES:
            return RemotePoint.refuse_connection(connection)

        # convert bytes to unsigned short array
        port = int.from_bytes(connection.recv(2), 'big', signed=False)

        try:
            # create connection to remote
            remote_point = self.entry_points[username].create_remote_point(
                server_address=address,
                port=port,
                client_socket=connection,
            )
        except (ConnectionError, TimeoutError) as exc:
            logger.error(f'failed connection to {address}:{port} ({type(exc)}): {exc}')
        except:
            traceback.print_exc()
        else:
            # watch while connected
            remote_point.watch()

    def _inactive_connection_monitoring(self):
        while True:
            inactive_entry_points = [username for username in self.entry_points.keys() if time.time() - self.entry_points[username].last_activity > self.INACTIVE_TIMEOUT]

            for username in inactive_entry_points:
                self.delete_entry_point(username)
                logger.info(f'entry point `{username}` closed due to inactivity')

            time.sleep(self.INACTIVE_TIMEOUT)

    @SocketCommunication.method(INSIDE_SOCKET_PORT)
    def create_entry_point(self, username: str, password: str, proxy_kwargs: dict, client_host: str = None, inspector: dict = None):

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
            inspector=inspector
        )

        # allow host
        if client_host not in self.allowed_hosts:
            self.allowed_hosts[client_host] = []

        # set link to entry point object
        self.allowed_hosts[client_host].append(username)

        # set entry point object
        self.entry_points[username] = entry_point

        return time.time()

    @SocketCommunication.method(INSIDE_SOCKET_PORT)
    def delete_entry_point(self, username: str):

        if username not in self.entry_points:
            return None

        # close entry point and all connections
        total_proxy_outgoing_usage_b, total_proxy_incoming_usage_b = self.entry_points[username].close()

        # delete from allowed hosts
        client_host = self.entry_points[username].client_host
        self.allowed_hosts[client_host].remove(username)

        # delete allowed host if empty
        if not self.allowed_hosts[client_host]:
            del self.allowed_hosts[client_host]

        # delete entry point
        del self.entry_points[username]

        return {
            'deleted_at': time.time(),
            'total_proxy_outgoing_usage_b': total_proxy_outgoing_usage_b,
            'total_proxy_incoming_usage_b': total_proxy_incoming_usage_b
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