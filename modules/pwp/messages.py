PROTOCOL_NAME = b'BitTorrent protocol'
RESERVED = 8

CHOKE_ID = 0
UNCHOKE_ID = 1
INTERESTED_ID = 2
NOT_INTERESTED_ID = 3
HAVE_ID = 4
BITFIELD_ID = 5
REQUEST_ID = 6
PIECE_ID = 7
CANCEL_ID = 8
PORT_ID = 9
EXTENDED_ID = 20

LEN_LEN = 4
LEN_ID = 1
LEN_PIECE_INDEX = 4
LEN_INDEX = 4
LEN_BEGIN = 4
LEN_BLOCK_LEN = 4


def int_to_bytes(int_, length):
    return int_.to_bytes(length, byteorder='big')


def int_from_bytes(bytes_):
    return int.from_bytes(bytes_, byteorder='big')


def get_protocol_name_length(protocol_name):
    return int_to_bytes(len(protocol_name), 1)


def get_reserved_bytes(length):
    return b'\x00' * length


def build_handshake(info_hash, peer_id):
    return (get_protocol_name_length(PROTOCOL_NAME) +
            PROTOCOL_NAME + get_reserved_bytes(RESERVED) +
            info_hash + peer_id)


def build_message(length, message_id=None, payload=b''):
    def message_id_to_bytes():
        if message_id is None:
            return b''
        return int_to_bytes(message_id, LEN_ID)

    return int_to_bytes(length, LEN_LEN) + message_id_to_bytes() + payload


def build_keep_alive():
    return build_message(0)


def build_choke():
    return build_message(LEN_ID, CHOKE_ID)


def build_unchoke():
    return build_message(LEN_ID, UNCHOKE_ID)


def build_interested():
    return build_message(LEN_ID, INTERESTED_ID)


def build_not_interested():
    return build_message(LEN_ID, NOT_INTERESTED_ID)


def build_have(piece_index):
    payload = int_to_bytes(piece_index, LEN_PIECE_INDEX)
    return build_message(len(payload) + LEN_ID, HAVE_ID, payload)


def build_bitfield(bitfield):
    return build_message(len(bitfield) + LEN_ID, BITFIELD_ID, bitfield)


def get_index_begin_payload(index, begin):
    return int_to_bytes(index, LEN_INDEX) + int_to_bytes(begin, LEN_BEGIN)


def get_request_payload(index, begin, length):
    return (get_index_begin_payload(index, begin) +
            int_to_bytes(length, LEN_BLOCK_LEN))


def build_request(index, begin, length):
    payload = get_request_payload(index, begin, length)
    return build_message(len(payload) + LEN_ID, REQUEST_ID, payload)


def build_piece(index, begin, block):
    payload = get_index_begin_payload(index, begin) + block
    return build_message(len(payload) + LEN_ID, PIECE_ID, payload)


def build_cancel(index, begin, length):
    payload = get_request_payload(index, begin, length)
    return build_message(len(payload) + LEN_ID, CANCEL_ID, payload)


def build_port(port):
    payload = int_to_bytes(port, 2)
    return build_message(len(payload) + LEN_ID, PORT_ID, payload)


def get_messages(bytes_):
    if not bytes_:
        return []
    messages = []
    handshake_length = get_handshake_length()
    if len(bytes_) >= handshake_length:
        handshake = get_handshake(bytes_[:handshake_length])
        if handshake:
            messages.append(handshake)
            messages.extend(get_messages(bytes_[handshake_length:]))
            return messages
    length = LEN_LEN + get_message_length(bytes_)
    message = get_message(bytes_[:length])
    if message:
        messages.append(message)
        messages.extend(get_messages(bytes_[length:]))
        return messages
    return [{'type': 'not_used', 'data': bytes_}]


def get_handshake_length():
    return 1 + len(PROTOCOL_NAME) + RESERVED + 20 + 20


def get_handshake(handshake):
    length = get_protocol_name_length(PROTOCOL_NAME)
    if handshake[0:1] != length or handshake[1:20] != PROTOCOL_NAME:
        return None
    info_hash_start = RESERVED + 20
    peer_id_start = info_hash_start + 20
    info_hash = handshake[info_hash_start:peer_id_start]
    peer_id = handshake[peer_id_start:]
    return {'type': 'handshake', 'info_hash': info_hash, 'peer_id': peer_id}


def get_message_length(bytes_):
    return int_from_bytes(bytes_[:LEN_LEN])


def get_message(bytes_):
    try:
        raw_msg = parse_message(bytes_)
    except ValueError:
        return None
    if raw_msg['length'] == 0:
        return {'type': 'keep-alive'}
    if raw_msg['length'] == LEN_ID:
        return {'type': get_message_type(raw_msg['id'])}
    return get_message_parser(raw_msg['id'])(raw_msg)


def parse_message(bytes_):
    def check_message_length():
        if len(bytes_) < LEN_LEN:
            raise ValueError('Message must contain' +
                             'at least {} bytes.'.format(LEN_LEN))
        if get_message_length(bytes_) != len(bytes_[LEN_LEN:]):
            raise ValueError('Wrong message length.')

    check_message_length()
    length = get_message_length(bytes_)
    id_ = bytes_[LEN_LEN] if length != 0 else None
    payload = bytes_[LEN_LEN + LEN_ID:] if length > 1 else b''
    return {'length': length, 'id': id_, 'payload': payload}


def get_message_type(message_id):
    types = {CHOKE_ID: 'choke',
             UNCHOKE_ID: 'unchoke',
             INTERESTED_ID: 'interested',
             NOT_INTERESTED_ID: 'not_interested',
             HAVE_ID: 'have',
             BITFIELD_ID: 'bitfield',
             REQUEST_ID: 'request',
             PIECE_ID: 'piece',
             CANCEL_ID: 'cancel',
             PORT_ID: 'port',
             EXTENDED_ID: 'extended'}
    if message_id in types:
        return types[message_id]
    raise ValueError('Unknown message id.')


def get_message_parser(message_id):
    parsers = {HAVE_ID: parse_have,
               BITFIELD_ID: parse_bitfield,
               REQUEST_ID: parse_request,
               PIECE_ID: parse_piece,
               CANCEL_ID: parse_cancel,
               PORT_ID: parse_port,
               EXTENDED_ID: parse_extended}
    if message_id in parsers:
        return parsers[message_id]
    raise ValueError('No parser for message with id {}.'.format(message_id))


def parse_have(raw_msg):
    return {'type': get_message_type(HAVE_ID),
            'piece_index': int_from_bytes(raw_msg['payload'])}


def parse_bitfield(raw_msg):
    def get_pieces_indices():
        bit_str = bin(int.from_bytes(raw_msg['payload'], byteorder='big'))
        return [i for i, bit in enumerate(bit_str) if bit == '1']

    return {'type': get_message_type(BITFIELD_ID),
            'pieces_indices': get_pieces_indices()}


def parse_request(raw_msg):
    return get_request_format(raw_msg, REQUEST_ID)


def parse_cancel(raw_msg):
    return get_request_format(raw_msg, CANCEL_ID)


def get_request_format(raw_msg, message_id):
    return {'type': get_message_type(message_id),
            'index': get_index(raw_msg),
            'begin': get_begin(raw_msg),
            'length': get_length(raw_msg)}


def parse_piece(raw_msg):
    def get_block():
        return raw_msg['payload'][LEN_INDEX + LEN_BEGIN:]
    return {'type': get_message_type(PIECE_ID),
            'index': get_index(raw_msg),
            'begin': get_begin(raw_msg),
            'block': get_block()}


def get_index(raw_msg):
    return int_from_bytes(raw_msg['payload'][:LEN_INDEX])


def get_begin(raw_msg):
    return int_from_bytes(raw_msg['payload'][LEN_INDEX:LEN_INDEX + LEN_BEGIN])


def get_length(raw_msg):
    return int_from_bytes(raw_msg['payload'][LEN_INDEX + LEN_BEGIN:])


def parse_port(raw_msg):
    return {'type': 'port',
            'port': int_from_bytes(raw_msg['payload'])}


def parse_extended(raw_msg):
    return {'type': 'extended',
            'data': raw_msg['payload']}
