import os
import pickle


BLOCK_SIZE = 16384


class Files:
    def __init__(self, info, root_dir):
        self.info = info
        self.root_dir = root_dir
        self.mode = self.get_mode()
        self.hashes = self.get_hashes()
        self.piece_num = len(self.hashes)
        self.files = self.get_files(root_dir)
        self.total_length = self.get_total_length()
        self.piece_length = self.info[b'piece length']
        self.pieces = self.get_pieces()
        self.pieces_belonging = self.get_pieces_belonging()

    def get_mode(self):
        return 'multiple' if b'files' in self.info else 'single'

    def get_hashes(self):
        str_ = self.info[b'pieces']
        return [str_[i:i+20] for i in range(0, len(str_), 20)]

    def get_bitfield(self):
        bitfield = self.get_binary_bitfield()
        while len(bitfield) % 8 != 0:
            bitfield += '0'
        return int(bitfield, 2).to_bytes(len(bitfield) // 8, byteorder='big')

    def save_bitfield(self):
        with open(self.root_dir + '/bitfield.pickle', 'wb') as f:
            pickle.dump(self.get_binary_bitfield(), f)

    def get_binary_bitfield(self):
        return ''.join(['1' if piece['have'] else '0'
                       for piece in self.pieces])

    def restore_bitfield(self):
        try:
            raw_bitfiled = self.read_bitfield()
        except IOError:
            return [False] * self.piece_num
        return [i == '1' for i in raw_bitfiled]

    def read_bitfield(self):
        with open(self.root_dir + '/bitfield.pickle', 'rb') as f:
            return pickle.load(f)

    def download_files(self):
        for file in self.files:
            file['skip'] = False

    def download_file(self, index):
        self.files[index]['skip'] = False

    def get_files(self, root_dir):
        def get_file(path, length):
            return {'file': open('{}/{}'.format(root_dir, path), 'wb'),
                    'path': path, 'length': length, 'skip': True}

        def create_dir(name):
            os.makedirs('{}/{}'.format(root_dir, name), exist_ok=True)

        def get_path(byte_list):
            return b'/'.join(byte_list).decode()

        create_dir('/')
        if self.mode == 'single':
            return [get_file(self.info[b'name'].decode(),
                             self.info[b'length'])]
        files = []
        files_info = self.info[b'files']
        for file_info in files_info:
            path = file_info[b'path']
            if len(path) > 1:
                create_dir(get_path(path[:-1]))
            files.append(get_file(get_path(path), file_info[b'length']))
        return files

    def get_total_length(self):
        if self.mode == 'multiple':
            return sum(file['length'] for file in self.files)
        return self.files[0]['length']

    def get_pieces(self):
        def get_blocks(piece_length):
            blocks = []
            for i in range(piece_length // BLOCK_SIZE):
                blocks.append({'length': BLOCK_SIZE,
                               'begin': BLOCK_SIZE * i})
            left = piece_length % BLOCK_SIZE
            if left:
                blocks.append({'length': left,
                               'begin': BLOCK_SIZE * len(blocks)})
            return blocks

        pieces = []
        bitfield = self.restore_bitfield()
        for i, h in enumerate(self.hashes):
            if i == len(self.hashes) - 1:
                blocks = get_blocks(self.get_last_piece_length())
            else:
                blocks = get_blocks(self.piece_length)
            pieces.append({'hash': h, 'have': bitfield[i],
                           'requested': None, 'blocks': blocks})
        return pieces

    def get_last_piece_length(self):
        return self.total_length - (self.piece_num - 1) * self.piece_length

    def get_pieces_belonging(self):
        def get_info(index, left):
            start_pos = 0
            file_num = 0
            while True:
                next_start_pos = start_pos + self.files[file_num]['length']
                if index < next_start_pos:
                    break
                start_pos = next_start_pos
                file_num += 1
            file_info = self.files[file_num]
            begin = index - start_pos
            length = min(next_start_pos - index, left)
            return file_info, begin, length

        pieces_belonging = []
        index = 0
        for piece in self.pieces:
            piece_belonging = []
            left = self.get_piece_length(piece)
            while left > 0:
                file_info, begin, length = get_info(index, left)
                index += length
                left -= length
                piece_belonging.append({'file_info': file_info,
                                        'begin': begin,
                                        'length': length})
            pieces_belonging.append(piece_belonging)
        return pieces_belonging

    def piece_skip(self, index):
        for piece_belonging in self.pieces_belonging[index]:
            if piece_belonging['file_info']['skip']:
                return True
        return False

    def get_piece_length(self, piece):
        return sum(block['length'] for block in piece['blocks'])

    def get_downloaded(self):
        return sum(self.get_piece_length(piece) for piece in self.pieces
                   if piece['have'])

    def write_piece(self, piece_index, data):
        piece = self.pieces[piece_index]
        if piece['have']:
            return
        written = 0
        for f in self.pieces_belonging[piece_index]:
            self.write_data(f['file_info']['file'], f['begin'],
                            data[written:written + f['length']])
            written += f['length']
        piece['have'] = True

    def hash_is_correct(self, piece_index, hash_):
        return self.hashes[piece_index] == hash_

    def write_data(self, file, pos, data):
        file.seek(pos)
        file.write(data)
        file.flush()

    def close_files(self):
        for file in self.files:
            os.fsync(file['file'].fileno())
            file['file'].close()
