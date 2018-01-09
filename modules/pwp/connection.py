import socket
import select
from collections import deque
import time

from modules.pwp import messages


HANDSHAKE_TIMEOUT = 5
MESSAGE_TIMEOUT = 5
MAX_IDLES = 24


class Connection:
    def __init__(self, client_id, info_hash, files, lock):
        self.lock = lock
        self.client_id = client_id
        self.info_hash = info_hash
        self.client_files = files
        self.peer_id = None
        self.broken = False
        self.am_choking = True
        self.am_interested = False
        self.choking = True
        self.interested = False
        self.messages = deque()
        self.requests = deque()
        self.pieces = {}
        self.completed_pieces = {}
        self.has_pieces = set()
        self.idles = 0

    def initiate(self, ip, port):
        try:
            self.sock = socket.create_connection((ip, port))
        except (TimeoutError, ConnectionError, OSError):
            self.broken = True
            return
        self.sock.setblocking(0)
        self.give_handshake()
        self.recieve_messages(HANDSHAKE_TIMEOUT)
        self.handle_handshake()
        if not self.broken:
            self.send_bitfield()
            self.loop()

    def accept(self, sock):
        self.sock = sock
        self.recieve_messages(HANDSHAKE_TIMEOUT)
        self.handle_handshake()
        if not self.broken:
            self.give_handshake()
            self.send_bitfield()
            self.loop()

    def request_piece(self, piece_index):
        for block in self.client_files.pieces[piece_index]['blocks']:
            self.requests.append({'index': piece_index,
                                  'begin': block['begin'],
                                  'length': block['length']})

    def loop(self):
        while True:
            if self.idles > MAX_IDLES or self.broken:
                self.broken = True
                break
            self.handle_messages()
            self.collect_completed_pieces()
            if self.requests and not self.am_interested:
                self.send_interested()
            if self.interested and not self.am_choking:
                self.send_unchoke()
            if self.requests and not self.choking:
                self.send_request(self.requests.popleft())
            self.recieve_messages(MESSAGE_TIMEOUT)

    def recieve_messages(self, timeout):
        rs, ws, es = select.select([self.sock], [], [], timeout)
        if self.sock in rs:
            try:
                data = self.sock.recv(4096)
            except:
                self.broken = True
                return
            for m in messages.get_messages(self.get_not_used_data() + data):
                self.messages.append(m)
        else:
            self.idles += 1

    def get_not_used_data(self):
        not_used_data = b''
        while self.messages and self.messages[-1]['type'] == 'not_used':
            not_used_data = self.messages.pop()['data'] + not_used_data
        return not_used_data

    def handle_handshake(self):
        def is_valid_handshake(message):
            return (message['type'] == 'handshake' and
                    message['info_hash'] == self.info_hash)
        if self.messages:
            handshake = self.messages.popleft()
            if is_valid_handshake(handshake):
                self.peer_id = handshake['peer_id']
            else:
                self.broken = True
        else:
            self.broken = True

    def handle_messages(self):
        while self.messages and self.messages[0]['type'] != 'not_used':
            self.handle_message(self.messages.popleft())

    def handle_message(self, message):
        no_payload_handlers = {'keep-alive': self.handle_keep_alive,
                               'choke': self.handle_choke,
                               'unchoke': self.handle_unchoke,
                               'interested': self.handle_interested,
                               'not_interested': self.handle_not_interested}
        payload_handlers = {'have': self.handle_have,
                            'bitfield': self.handle_bitfield,
                            'piece': self.handle_piece}
        type_ = message['type']
        if type_ in no_payload_handlers:
            no_payload_handlers[type_]()
        elif type_ in payload_handlers:
            payload_handlers[type_](message)

    def handle_keep_alive(self):
        self.send_keep_alive()

    def handle_choke(self):
        self.choking = True

    def handle_unchoke(self):
        self.choking = False

    def handle_interested(self):
        self.interested = True

    def handle_not_interested(self):
        self.interested = False

    def handle_have(self, message):
        self.has_pieces.add(message['piece_index'])

    def handle_bitfield(self, message):
        self.has_pieces.update(message['pieces_indices'])

    def handle_piece(self, message):
        if message['index'] not in self.pieces:
            self.pieces[message['index']] = []
        self.pieces[message['index']].append({'begin': message['begin'],
                                              'data': message['block']})

    def give_handshake(self):
        message = messages.build_handshake(self.info_hash,
                                           self.client_id.encode())
        self.send_message(message)

    def collect_completed_pieces(self):
        def get_piece_data(blocks):
            return b''.join([block['data']
                             for block in sorted(blocks,
                                                 key=lambda x:x['begin'])])

        completed = []
        for index, blocks in self.pieces.items():
            client_blocks = self.client_files.pieces[index]['blocks']
            if len(blocks) == len(client_blocks):
                with self.lock:
                    self.completed_pieces[index] = get_piece_data(blocks)
                    self.send_have(index)
                completed.append(index)
        for index in completed:
            del self.pieces[index]

    def send_keep_alive(self):
        self.send_message(messages.build_keep_alive())

    def send_choke(self):
        self.am_choking = True
        self.send_message(messages.build_choke())

    def send_unchoke(self):
        self.am_choking = False
        self.send_message(messages.build_unchoke())

    def send_interested(self):
        self.am_interested = True
        self.send_message(messages.build_interested())

    def send_not_interested(self):
        self.am_interested = False
        self.send_message(messages.build_not_interested())

    def send_bitfield(self):
        bitfield = self.client_files.get_bitfield()
        if bitfield != b'\x00' * len(bitfield):
            self.send_message(messages.build_bitfield(bitfield))

    def send_request(self, request):
        self.send_message(messages.build_request(request['index'],
                                                 request['begin'],
                                                 request['length']))

    def send_have(self, index):
        self.send_message(messages.build_have(index))

    def send_message(self, message):
        self.sock.sendall(message)
