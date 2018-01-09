#!/usr/bin/env python3
import unittest
import sys
import os

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             os.path.pardir))
from modules.tracker import Tracker

class TestTracker(unittest.TestCase):
    def setUp(self):
        self.tracker = Tracker('')

    def test_binary_peers(self):
        peers = b'\xc0\xc0\xee\xee\xa0\x00'
        expected = [{'ip': '192.192.238.238', 'port': 40960}]
        self.assertListEqual(expected, self.tracker.get_peers(peers))

    def test_dict_peers(self):
        peers = [{b'ip': b'\xc0\xc0\xee\xee', b'port': 40960}]
        expected = [{'ip': '192.192.238.238', 'port': 40960}]
        self.assertListEqual(expected, self.tracker.get_peers(peers))

if __name__ == '__main__':
    unittest.main()

