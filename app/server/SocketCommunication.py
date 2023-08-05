import functools
import inspect
import json
import pickle
import struct

import socket
import threading
import traceback
from typing import Type

from app.utils.get_logger import get_logger

EXCEPTION = b'x8742365__exc__'
BUF_SIZE = 4096
ENCODING = 'utf-8'


logger = get_logger(__name__)


class SocketData:
    """
    Wrapper for encode/decode data between sockets.
    """

    method_name: str
    args: tuple
    kwargs: dict

    def __init__(self, method_name: str, args, kwargs):
        self.method_name = method_name
        self.args = args
        self.kwargs = kwargs

    @staticmethod
    def send(result, connection: socket.socket):

        # exception
        if isinstance(result, Exception):
            bytes_package = EXCEPTION + pickle.dumps(result)

        # or result
        else:
            bytes_package = json.dumps(result).encode(ENCODING)

        package_size = struct.pack('>I', len(bytes_package))
        connection.sendall(package_size + bytes_package)
        return True

    @staticmethod
    def receive(connection: socket.socket):
        packet_size = struct.unpack('>I', connection.recv(4))[0]

        data = b""
        while len(data) < packet_size:
            chunk = connection.recv(BUF_SIZE)
            if not chunk: break
            data += chunk

        # exception
        if data.startswith(EXCEPTION):
            exc = data.replace(EXCEPTION, b'')
            exc = pickle.loads(exc)
            raise exc

        # decode result
        data = json.loads(data.decode(ENCODING))

        return data


class SocketListener:
    instance: Type[object]
    port: int
    methods: list

    listener: socket

    def __init__(self, instance: Type[object], port: int, methods: list):
        self.instance = instance
        self.port = port
        self.methods = methods

        logger.debug(f'inited for {type(instance).__name__} on port ::{port}')

        threading.Thread(target=self.start_listener, daemon=True).start()

    def start_listener(self):
        """Launch socket listener"""
        logger.debug('starting...')

        # Create socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as self.listener:
            logger.debug('socket created')

            # faster terminate (pass `Address already in use` exc)
            self.listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            # Bind localhost listener on special port
            self.listener.bind(('127.0.0.1', self.port))
            logger.debug(f'socket bound on :{self.port}')

            # Start listener
            self.listener.listen()
            logger.debug(f'listening...')

            while True:

                try:
                    # waiting for request
                    conn, _addr = self.listener.accept()

                except ConnectionAbortedError:
                    logger.critical('listener closed')
                    self.listener = None
                    break

                except:
                    logger.critical(traceback.format_exc())
                    return

                # delegate connection to thread
                threading.Thread(target=self.connection, args=(conn, _addr)).start()

    def connection(self, conn, _addr):
        logger.debug(f'connection accepted from {_addr}')

        try:
            # get method and data
            socket_action = SocketData.receive(conn)
            logger.debug(f'request: method `{socket_action["method_name"]}` args `{socket_action["args"]}` kwargs `{socket_action["kwargs"]}`')

            # process method
            assert socket_action['method_name'] in self.methods

            result = getattr(self.instance, socket_action['method_name'])(*socket_action['args'], **socket_action['kwargs'])
            logger.debug(f'result: `{result}`')

            with conn:
                SocketData.send(result, conn)
                logger.debug('result sent successfully')

        except Exception as exc:
            logger.exception(exc)
            SocketData.send(exc, conn)

    @classmethod
    def send(cls, port: int, action_data: dict):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:

            # Try to connect
            try:
                s.connect(('127.0.0.1', port))
            except ConnectionRefusedError:
                raise ConnectionRefusedError(f'lister down on 127.0.0.1:{port}')

            # Send request
            SocketData.send(action_data, s)

            # Get response
            result = SocketData.receive(s)

            return result


def listen(port: int):
    """
    Make a class as socket listener with a public methods.

    @param int port:
        Port of listener. Should be the same with port of public methods.
    """

    def decorator(cls):
        @functools.wraps(cls)
        def wrapper(*args, **kwargs):
            inited_cls = cls(*args, **kwargs)

            # get decorated methods of cls (by source)
            methods = []
            source_lines = inspect.getsourcelines(cls)[0]
            for i, line in enumerate(source_lines):
                if line.strip().split('(')[0].strip() == '@SocketCommunication.method':
                    methods.append(source_lines[i+1].split('def')[1].split('(')[0].strip())

            # set listener object
            inited_cls._socket_communication = SocketListener(
                instance=inited_cls,
                port=port,
                methods=methods,
            )

            return inited_cls
        return wrapper
    return decorator


def method(port: int):
    """
    Use only as @SocketCommunication.method for make the method public.

    @param int port:
        Set port of listener.
    """

    def decorator(cls_method):
        def wrapper(*args, **kwargs):

            # call from inside class
            if args and hasattr(args[0], '__class__') and hasattr(args[0], '_socket_communication'):
                return cls_method(args[0], *args[1:], **kwargs)

            # call as static method
            else:
                return SocketListener.send(port, {
                    'method_name': cls_method.__name__,
                    'args': args,
                    'kwargs': kwargs
                })

        return wrapper
    return decorator
