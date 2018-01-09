#!/usr/bin/env python3
import unittest
import sys
import os

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             os.path.pardir))
from modules.pwp import messages

class MessageBuildingTest(unittest.TestCase):
    def get_bytes_sequence(self, length):
        return b'\xaa' * length

    def get_zero_bytes_sequence(self, length):
        return b'\x00' * length

    def test_keep_alive(self):
        self.assertEqual(b'\x00\x00\x00\x00', messages.build_keep_alive())

    def test_handshake(self):
        info_hash = self.get_bytes_sequence(20)
        peer_id = self.get_bytes_sequence(20)
        reserved = self.get_zero_bytes_sequence(8)
        expected = (b'\x13BitTorrent protocol' + reserved +
                    info_hash + peer_id)
        result = messages.build_handshake(info_hash, peer_id)
        self.assertEqual(expected, result)

    def test_choke(self):
        self.assertEqual(b'\x00\x00\x00\x01\x00', messages.build_choke())

    def test_unchoke(self):
        self.assertEqual(b'\x00\x00\x00\x01\x01', messages.build_unchoke())

    def test_interested(self):
        self.assertEqual(b'\x00\x00\x00\x01\x02', messages.build_interested())

    def test_not_interested(self):
        self.assertEqual(b'\x00\x00\x00\x01\x03',
                         messages.build_not_interested())

    def test_have(self):
        expected = b'\x00\x00\x00\x05\x04\x00\x00\x00\x01'
        result = messages.build_have(1)
        self.assertEqual(expected, result)

    def test_bitfiled(self):
        expected = b'\x00\x00\x00\x05\x05\xff\xff\xff\xff'
        result = messages.build_bitfield(b'\xff\xff\xff\xff')
        self.assertEqual(expected, result)

    def test_request(self):
        expected = (b'\x00\x00\x00\x0d\x06\x00\x00\x00\x00'
                    b'\x00\x00\x00\x00\x00\x00\x10\x00')
        result = messages.build_request(0, 0, 16**3)
        self.assertEqual(expected, result)

    def test_piece(self):
        block = self.get_bytes_sequence(16**3)
        expected = (b'\x00\x00\x10\x09\x07\x00\x00\x00\x00'
                    b'\x00\x00\x00\x00' + block)
        result = messages.build_piece(0, 0, block)
        self.assertEqual(expected, result)


class MessageParsingTest(unittest.TestCase):
    def get_bytes_sequence(self, length):
        return b'\xaa' * length

    def base_test(self, expected, bytes_):
        self.assertListEqual(expected, messages.get_messages(bytes_))

    def test_empty(self):
        self.base_test([], b'')

    def test_handshake(self):
        expected, bytes_ = self.get_handshake_test()
        self.base_test([expected], bytes_)

    def get_handshake_test(self):
        info_hash = self.get_bytes_sequence(20)
        peer_id = self.get_bytes_sequence(20)
        reserved = self.get_bytes_sequence(8)
        bytes_ = (b'\x13BitTorrent protocol' + reserved + info_hash + peer_id)
        expected = {'type': 'handshake', 'info_hash': info_hash,
                     'peer_id': peer_id}
        return expected, bytes_

    def test_chocke(self):
        self.base_test([{'type': 'choke'}], messages.build_choke())

    def test_unchoke(self):
        self.base_test([{'type': 'unchoke'}], messages.build_unchoke())

    def test_interested(self):
        self.base_test([{'type': 'interested'}], messages.build_interested())

    def test_not_interested(self):
        self.base_test([{'type': 'not_interested'}],
                       messages.build_not_interested())

    def test_have(self):
        piece_index = 55
        bytes_ = messages.build_have(piece_index)
        expected = [{'type': 'have', 'piece_index': piece_index}]
        self.base_test(expected, bytes_)

    def test_bitfield(self):
        expected, bytes_ = self.get_bitfield_test()
        self.base_test([expected], bytes_)

    def get_bitfield_test(self):
        bitfield = self.get_bytes_sequence(10)
        bytes_ = messages.build_bitfield(bitfield)
        pieces_indices = [i for i in range(2, 10*8 + 1, 2)]
        expected = {'type': 'bitfield',
                    'pieces_indices': pieces_indices}
        return expected, bytes_

    def test_request(self):
        index = 4
        begin = 4
        length = 4096
        bytes_ = messages.build_request(index, begin, length)
        expected = [{'type': 'request', 'index': index,
                     'begin': begin, 'length': length}]
        self.base_test(expected, bytes_)

    def test_piece(self):
        index = 1000
        begin = 2**14
        block = self.get_bytes_sequence(2**12)
        bytes_ = messages.build_piece(index, begin, block)
        expected = [{'type': 'piece', 'index': index,
                     'begin': begin, 'block': block}]
        self.base_test(expected, bytes_)

    def test_cancel(self):
        index = 4
        begin = 4
        length = 4096
        bytes_ = messages.build_cancel(index, begin, length)
        expected = [{'type': 'cancel', 'index': index,
                     'begin': begin, 'length': length}]
        self.base_test(expected, bytes_)

    def test_port(self):
        port = 56622
        bytes_ = messages.build_port(port)
        expected = [{'type': 'port', 'port': port}]
        self.base_test(expected, bytes_)

    def test_sequence(self):
        h_expected, h_bytes = self.get_handshake_test()
        b_expected, b_bytes = self.get_bitfield_test()
        self.base_test([h_expected, b_expected], h_bytes + b_bytes)


if __name__ == '__main__':
    unittest.main()