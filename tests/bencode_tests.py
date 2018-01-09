#!/usr/bin/env python3
import unittest
import sys
import os

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             os.path.pardir))
from modules import bencode

class TestDecoding(unittest.TestCase):
    def base_test(self, data, expected):
        self.assertListEqual(expected, bencode.decode(data))

    def test_empty(self):
        self.base_test(b'', [])

    def test_string(self):
        self.base_test(b'7:torrent', [b'torrent'])

    def test_integer(self):
        self.base_test(b'i12e', [12])

    def test_empty_list(self):
        self.base_test(b'le', [[]])

    def test_list(self):
        self.base_test(b'li4ei10ee', [[4, 10]])

    def test_empty_dict(self):
        self.base_test(b'de', [{}])

    def test_dict(self):
        self.base_test(b'd3:foo2:v13:bar2:v2', 
                       [{b'foo': b'v1', b'bar': b'v2'}])

    def test_dict_as_dict_value(self):
        self.base_test(b'd4:dictd4:smthi5eee',
                       [{b'dict': {b'smth': 5}}])


class TestEncoding(unittest.TestCase):
    def base_test(self, data, expected):
        self.assertEqual(expected, bencode.encode(data))

    def test_int(self):
        self.base_test(12, b'i12e')

    def test_empty_string(self):
        self.base_test(b'', b'0:')

    def test_string(self):
        self.base_test(b'torrent', b'7:torrent')

    def test_empty_list(self):
        self.base_test([], b'le')

    def test_list(self):
        self.base_test([422], b'li422ee')

    def test_list_inside_list(self):
        self.base_test([[]], b'llee')

    def test_empty_dict(self):
        self.base_test({}, b'de')

    def test_dict(self):
        self.base_test({b'key1': b'val1', b'key2': [12, []]},
                       b'd4:key14:val14:key2li12eleee')

if __name__ == '__main__':
    unittest.main()