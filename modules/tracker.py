from urllib import request

from modules import bencode


class Tracker:
    def __init__(self, url):
        self.url = url
        self.interval = None
        self.min_interval = None
        self.tracker_id = None
        self.complete = 0
        self.incomplete = 0

    def announce(self, query):
        if self.tracker_id:
            query += '?trackerid={}'.format(self.tracker_id)
        response = self.send_request(query)
        return self.handle_response(response)

    def send_request(self, query):
        return request.urlopen(self.url + query).read()

    def handle_response(self, response):
        data = bencode.decode(response)[0]
        self.update_state(data)
        return self.get_peers(data[b'peers'])

    def update_state(self, data):
        def set_attr(key, attr, update=True):
            if key in data and (update or not getattr(self, attr)):
                setattr(self, attr, data[key])

        set_attr(b'interval', 'interval')
        set_attr(b'min interval', 'min_interval')
        set_attr(b'tracker id', 'tracker_id', False)
        set_attr(b'complete', 'complete')
        set_attr(b'incomplete', 'incomplete')

    def get_peers(self, peers):
        def convert_ip(ip):
            return '{}.{}.{}.{}'.format(*ip)

        def peers_dict_model():
            return [{k.decode(): convert_ip(v) if k == b'ip' else v
                     for k, v in peer.items()} for peer in peers]

        def peers_binary_model():
            chunks = [peers[i:i+6] for i in range(0, len(peers), 6)]
            return [{'ip': convert_ip(chunk[:4]),
                     'port': int.from_bytes(chunk[4:], byteorder='big')}
                    for chunk in chunks]

        if isinstance(peers, list):
            return peers_dict_model()
        elif isinstance(peers, bytes):
            return peers_binary_model()
        else:
            raise ValueError('Unsupported peer model.')
