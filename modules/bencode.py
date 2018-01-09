ENDING_DELIMETER = b'e'
INT_DELIMETER = b'i'
LIST_DELIMETER = b'l'
DICT_DELIMETER = b'd'
STR_DELIMETER = b':'


def decode(data):
    return decode_list(data)[0]


def decode_list(data):
    l = []
    i = 0
    while i < len(data):
        byte = data[i:i+1]
        sub = data[i+1:]
        if byte == ENDING_DELIMETER:
            return l, i
        elif byte == INT_DELIMETER:
            value, length = decode_integer(sub)
        elif byte == LIST_DELIMETER:
            value, length = decode_list(sub)
        elif byte == DICT_DELIMETER:
            value, length = decode_dict(sub)
        elif byte.decode().isnumeric():
            value, length = decode_string(data[i:])
        else:
            raise ValueError('Unsupported syntax detected '
                             'at {} position.'.format(i))
        l.append(value)
        i += length + 2
    return l, i


def decode_integer(data):
    delimeter_pos = data.find(ENDING_DELIMETER)
    return int(data[:delimeter_pos]), delimeter_pos


def decode_dict(data):
    d = {}
    l, length = decode_list(data)
    if len(l) % 2 != 0:
        raise ValueError('Dictionary must consist of pairs.')
    for i in range(0, len(l), 2):
        key = l[i]
        if not isinstance(key, bytes):
            raise ValueError('Dictionary keys must be strings.')
        d[l[i]] = l[i+1]
    return d, length


def decode_string(data):
    delimeter_pos = data.find(STR_DELIMETER)
    bytes_to_read = int(data[:delimeter_pos])
    start = delimeter_pos + 1
    length = start + bytes_to_read
    decoded_data = data[start:length]
    return decoded_data, length - 2


def encode(data):
    if isinstance(data, int):
        encoded_data = encode_int(data)
    elif isinstance(data, bytes):
        encoded_data = encode_string(data)
    elif isinstance(data, list):
        encoded_data = encode_list(data)
    elif isinstance(data, dict):
        encoded_data = encode_dict(data)
    else:
        raise TypeError('Unsupported data type.')
    return encoded_data


def encode_int(int_):
    return INT_DELIMETER + int_to_bytes(int_) + ENDING_DELIMETER


def encode_string(string):
    return int_to_bytes(len(string)) + STR_DELIMETER + string


def encode_list(list_):
    encoded_data = LIST_DELIMETER
    for e in list_:
        encoded_data += encode(e)
    return encoded_data + ENDING_DELIMETER


def encode_dict(dict_):
    encoded_data = DICT_DELIMETER
    for k, v in dict_.items():
        if not isinstance(k, bytes):
            raise TypeError('Dict keys must be byte strings.')
        encoded_data += encode(k) + encode(v)
    return encoded_data + ENDING_DELIMETER


def int_to_bytes(int_):
    return str(int_).encode()
