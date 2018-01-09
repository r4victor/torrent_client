import random
import string
import time
from urllib import parse
from hashlib import sha1
from threading import Thread, Lock

from modules import bencode
from modules.files import Files
from modules.tracker import Tracker
from modules.pwp.connection import Connection


ID_PREFIX = 'VT1001'
PORT = 57893

REQUEST_TIMEOUT = 90
LOOP_TIME = 2


class Torrent:
    def __init__(self, filename, torrent_dir, download_dir):
        self.id = self.generate_id()
        tracker_url, info = self.parse_meta(torrent_dir + '/' + filename)
        self.info = info
        self.info_hash = self.get_info_hash()
        self.name = filename[:-8]
        self.files = Files(info, download_dir + '/' + self.name)
        self.tracker = Tracker(tracker_url)
        self.uploaded = 0
        self.downloaded = self.files.get_downloaded()
        self.speed = 0
        self.started = False
        self.active = False
        self.completed = False
        self.connections = {}
        self.connections_updated = None
        self.lock = Lock()

    def generate_id(self):
        unique_part = ''.join(random.choices(string.digits, k=12))
        return '-{}-{}'.format(ID_PREFIX, unique_part)

    def parse_meta(self, filename):
        raw_meta = bencode.decode(open(filename, 'rb').read())[0]
        return raw_meta[b'announce'].decode(), raw_meta[b'info']

    def get_info_hash(self):
        return sha1(bencode.encode(self.info)).digest()

    def get_num_of_active_peers(self):
        return len([c for c in self.connections.values()
                    if not c.broken])

    def start(self, files_indices):
        self.set_files_status(files_indices)
        self.update_connections()
        self.started = True
        self.active = True
        while self.downloaded < self.files.total_length and self.active:
            self.update_connections()
            self.distribute_requests()
            self.collect_pieces()
            time.sleep(LOOP_TIME)
        self.speed = 0
        if self.downloaded == self.files.total_length:
            self.completed = True

    def set_files_status(self, files_indices):
        if not files_indices:
            self.files.download_files()
        else:
            for index in files_indices:
                if index < 0 or index >= len(self.files.files):
                    continue
                self.files.download_file(index)

    def save_state(self):
        with self.lock:
            self.files.close_files()
        self.files.save_bitfield()

    def get_download_info(self):
        return '{} of {} KB on {} kbps'.format(self.downloaded,
                                               self.files.total_length,
                                               self.speed/1000)

    def update_connections(self):
        if (self.connections_updated and
            time.time() - self.connections_updated <
                self.tracker.interval):
            return
        for peer in self.request_peers():
            if peer['ip'] in self.connections:
                continue
            conn = Connection(self.id, self.info_hash,
                              self.files, Lock())
            self.connections[peer['ip']] = conn
            t = Thread(target=conn.initiate, args=(peer['ip'],
                       peer['port']))
            t.daemon = True
            t.start()
        self.peers_updated = time.time()

    def request_peers(self):
        def get_query():
            def get_event():
                return 'started' if not self.started else ''

            params = {'info_hash': parse.quote(self.info_hash),
                      'peer_id': self.id,
                      'port': PORT,
                      'uploaded': self.uploaded,
                      'downloaded': self.downloaded,
                      'left': self.get_left()}
            event = get_event()
            if event:
                params['event'] = event
            return '?{}'.format('&'.join(['{}={}'.format(k, v)
                                          for k, v in params.items()]))

        return self.tracker.announce(get_query())

    def get_left(self):
        return self.files.total_length - self.downloaded

    def distribute_requests(self):
        def should_request(index, piece):
            return (not self.files.piece_skip(index) and
                    not piece['have'] and (not piece['requested'] or
                    time.time() - piece['requested'] > REQUEST_TIMEOUT))

        def get_max_requests_num():
            return max(2, 2 * self.speed / self.files.piece_length)

        requested = 0
        conn_list = list(self.connections.values())
        for index, piece in enumerate(self.files.pieces):
            if should_request(index, piece):
                random.shuffle(conn_list)
                for conn in conn_list:
                    if index in conn.has_pieces and not conn.broken:
                        conn.request_piece(index)
                        piece['requested'] = time.time()
                        requested += 1
                        break
            if requested == get_max_requests_num():
                break

    def collect_pieces(self):
        data_length = 0
        for conn in self.connections.values():
            with conn.lock:
                taken_pieces = []
                for index, data in conn.completed_pieces.items():
                    hash_ = sha1(data).digest()
                    if self.files.hash_is_correct(index, hash_):
                        with self.lock:
                            self.files.write_piece(index, data)
                        data_length += len(data)
                        taken_pieces.append(index)
                for index in taken_pieces:
                    conn.completed_pieces.pop(index)
        self.downloaded += data_length
        self.speed = data_length / LOOP_TIME
