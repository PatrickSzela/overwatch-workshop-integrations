def encode_ascii_character(char: str):
    return ascii.index(char) + 1


def encode_ascii_string(string: str):
    return [encode_ascii_character(char) for char in string]


# list of printable characters in ASCII table, with some additions
ascii = " !\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~"
