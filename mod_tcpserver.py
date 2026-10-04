# -*- coding: utf-8 -*-
"""TCP REPL server for BigWorld-based game mods.

This module provides a simple TCP-based remote Python REPL for debugging and
study. It replaces the prompt-based protocol (">>>" / "...") with a clean
line-based command protocol and sends JSON responses.

Python 2.7 compatible.
"""

import json
import socket
import sys
import threading
import traceback

try:
    import Queue
except ImportError:
    import queue as Queue

import codeop

try:
    import BigWorld
except ImportError:
    BigWorld = None


HOST = '127.0.0.1'
PORT = 2222

_rx = Queue.Queue()
_commands = Queue.Queue()
_sock = None
_buffer = ''
_block = []
_repl = {
    '__name__': '__tcp_repl__',
}

if BigWorld is not None:
    _repl['BigWorld'] = BigWorld

_io = threading.local()
_real_stdout = sys.stdout
_real_stderr = sys.stderr


class Capture(object):
    """Capture stdout/stderr output."""

    def __init__(self):
        self.data = []

    def write(self, data):
        self.data.append(str(data))

    def flush(self):
        pass

    def getvalue(self):
        return ''.join(self.data)


class Proxy(object):
    """Proxy stdout/stderr to per-thread capture if present."""

    def __init__(self, real, name):
        self.real = real
        self.name = name

    def write(self, data):
        capture = getattr(_io, self.name, None)
        if capture is not None:
            capture.write(data)
        else:
            self.real.write(data)

    def flush(self):
        capture = getattr(_io, self.name, None)
        if capture is not None:
            capture.flush()
        else:
            self.real.flush()

    def __getattr__(self, name):
        return getattr(self.real, name)


sys.stdout = Proxy(_real_stdout, 'out')
sys.stderr = Proxy(_real_stderr, 'err')


def _send_response(status, message, command_id=None):
    """Send a JSON-encoded response to the connected client."""
    if _sock is None:
        return

    payload = {
        'status': status,
        'message': message,
    }
    if command_id is not None:
        payload['id'] = command_id

    try:
        data = json.dumps(payload) + '\n'
        _sock.sendall(data.encode('utf-8'))
    except Exception:
        pass


def execute(code):
    """Execute a Python code object and capture output."""
    out = Capture()
    err = Capture()
    _io.out = out
    _io.err = err

    try:
        exec(code, _repl, _repl)
    except Exception:
        traceback.print_exc(file=err)
    finally:
        _io.out = None
        _io.err = None

    return out.getvalue(), err.getvalue()


def process_input():
    """Process incoming TCP data and enqueue complete commands."""
    global _buffer

    while True:
        try:
            data = _rx.get_nowait()
        except Queue.Empty:
            break

        if not isinstance(data, basestring):
            data = str(data)

        _buffer += data

        while '\n' in _buffer:
            line, _buffer = _buffer.split('\n', 1)
            line = line.rstrip('\r')

            if not line:
                if _block:
                    source = '\n'.join(_block) + '\n'
                    try:
                        code = codeop.compile_command(
                            source, '<tcp-repl>', 'single'
                        )
                    except (SyntaxError, OverflowError, ValueError) as exc:
                        _block[:] = []
                        _send_response('error', 'SyntaxError: %s' % exc)
                        continue

                    if code is None:
                        _block[:] = []
                        _send_response(
                            'error',
                            'SyntaxError: incomplete input'
                        )
                        continue

                    _block[:] = []
                    _commands.put(code)
                continue

            _block.append(line)

            source = '\n'.join(_block)
            try:
                code = codeop.compile_command(
                    source, '<tcp-repl>', 'single'
                )
            except (SyntaxError, OverflowError, ValueError) as exc:
                _block[:] = []
                _send_response('error', 'SyntaxError: %s' % exc)
                continue

            if code is not None:
                _block[:] = []
                _commands.put(code)

        _rx.task_done()

    if BigWorld is not None:
        BigWorld.callback(0.01, process_input)


def process_commands():
    """Execute queued Python code and return result."""
    try:
        code = _commands.get_nowait()
    except Queue.Empty:
        if BigWorld is not None:
            BigWorld.callback(0.01, process_commands)
        return

    output, error = execute(code)

    if error:
        _send_response('error', error)
    else:
        _send_response('success', output if output else 'OK')

    _commands.task_done()

    if BigWorld is not None:
        BigWorld.callback(0.01, process_commands)


def client_thread(sock):
    """Receive commands from a single client connection."""
    try:
        while True:
            data = sock.recv(4096)
            if not data:
                break
            _rx.put(data.decode('utf-8', 'replace'))
    except Exception:
        pass


def server_thread():
    """Listen for client connections."""
    global _sock

    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind((HOST, PORT))
    server_sock.listen(1)

    while True:
        try:
            sock, _ = server_sock.accept()
            _sock = sock
            _send_response('info', 'Connected')
            thread = threading.Thread(target=client_thread, args=(sock,))
            thread.daemon = True
            thread.start()
        except Exception:
            break


def start():
    """Start the TCP REPL server."""
    thread = threading.Thread(target=server_thread)
    thread.daemon = True
    thread.start()

    if BigWorld is not None:
        BigWorld.callback(0.01, process_input)
        BigWorld.callback(0.01, process_commands)


def init():
    """Initialization entry point used by the game engine."""
    start()


if __name__ == '__main__':
    start()
    print 'TCP REPL server started on %s:%d' % (HOST, PORT)
    try:
        while True:
            pass
    except KeyboardInterrupt:
        sys.exit(0)
