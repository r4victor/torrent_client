import os
from threading import Thread, Lock

from modules.torrent import Torrent

DOWNLOAD_DIR = 'downloads'
TORRENT_DIR = 'torrents'


class Client:
    def __init__(self):
        self.torrents = self.get_torrents()
        self.running = True

    def get_torrents(self):
        torrents = []
        os.makedirs(TORRENT_DIR, exist_ok=True)
        for entry in os.listdir(TORRENT_DIR):
            if entry.endswith('.torrent'):
                torrents.append(Torrent(entry, TORRENT_DIR, DOWNLOAD_DIR))
        return torrents

    def change_torrent_status(self, number, files_nums=None):
        def start_torrent(index, files_indices):
            t = Thread(target=self.torrents[index].start,
                       args=(files_indices,))
            t.daemon = True
            t.start()

        index = number - 1
        if self.torrents[index].active:
            self.torrents[index].active = False
        else:
            if files_nums:
                files_indices = [num - 1 for num in files_nums]
            else:
                files_indices = None
            start_torrent(index, files_indices)

    def exit(self):
        self.running = False
        for torrent in self.torrents:
            torrent.active = False
            torrent.save_state()

    def get_torrents_info(self):
        def convert_bytes(bytes_, power):
            return round(bytes_/2**power, 1)

        def to_kb(bytes_):
            return convert_bytes(bytes_, 10)

        def to_mb(bytes_):
            return convert_bytes(bytes_, 20)

        torrents_info = []
        for index, torrent in enumerate(self.torrents):
            torrents_info.append({'number': index + 1,
                                  'name': torrent.name,
                                  'active': torrent.active,
                                  'completed': torrent.completed,
                                  'length': to_mb(torrent.files.total_length),
                                  'peers': torrent.get_num_of_active_peers(),
                                  'uploaded': to_mb(torrent.uploaded),
                                  'downloaded': to_mb(torrent.downloaded),
                                  'speed': to_kb(torrent.speed),
                                  'files': torrent.files.files})
        return torrents_info
