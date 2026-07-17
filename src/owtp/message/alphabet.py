"Handles encoding messages into a format that can be passed to the :class:`IInput` method and send to the Workshop mode."

ALPHABET = " !\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~"
"List of characters supported by OWTP."


def encode_character(char: str):
    "Encodes passed character into a numeric value."

    if len(char) != 1:
        raise ValueError(
            f"Cannot encode character `{char}`: passed string doesn't contain a single character."
        )

    if char not in ALPHABET:
        raise ValueError(
            f"Cannot encode character `{char}`: passed character is not in the alphabet."
        )

    return ALPHABET.index(char) + 1


def encode_string(string: str):
    "Encodes passed string into an array of numeric values."
    return [encode_character(char) for char in string]
