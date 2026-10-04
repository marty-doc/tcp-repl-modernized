# -*- coding: utf-8 -*-
"""Simple external TCP client for debugging the BigWorld REPL server.

This client speaks a line-based protocol: each command is sent as text, and the
server returns JSON responses.

Python 2.7 compatible.
"""

import json
import socket
import sys


HOST = '127.0.0.1'
PORT = 2222


def recv_line(sock):
    """Read a single line from the socket."""
    data = ''
    while True:
        chunk = sock.recv(4096)
        if not chunk:
            return None
        data += chunk
        if '\n' in data:
            line, rest = data.split('\n', 1)
            return line + '\n'


def read_response(sock):
    """Read and decode a JSON response from the socket."""
    raw = recv_line(sock)
    if raw is None:
        return None

    try:
        return json.loads(raw)
    except ValueError:
        return {'status': 'error', 'message': raw}


def main():
    """Main client loop."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)

    try:
        sock.connect((HOST, PORT))
    except Exception as exc:
        sys.stderr.write('Connection failed: %s\n' % str(exc))
        return 1

    while True:
        response = read_response(sock)
        if response is None:
            break

        status = response.get('status', 'unknown')
        message = response.get('message', '')
        if message:
            sys.stdout.write(message)
            if not message.endswith('\n'):
                sys.stdout.write('\n')
        sys.stdout.flush()

        try:
            command = raw_input('> ')
        except EOFError:
            command = 'exit'

        if not command:
            continue

        try:
            sock.sendall(command + '\r\n')
        except Exception as exc:
            sys.stderr.write('Send error: %s\n' % str(exc))
            break

        if command.strip().lower() in ('exit', 'quit'):
            break

    sock.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
