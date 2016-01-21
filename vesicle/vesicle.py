# TODO: signed integers

from synthase import assert_that, len


# def assert_that(x):  # temporary
#     assert x


class Parsable:
    # TODO: should I compute coverage of the input array?
    def __init__(self, array, expected_length):
        print("comparing", len(array), "to", expected_length, "=>", len(array).__eq__(expected_length))
        assert_that(len(array) == expected_length)
        self.array = array

    def fixed(self, offset, *array):
        assert_that(self.array[offset:offset + len(array)] == bytes(array))

    def ascii(self, offset, length, padding=0x00):
        return self.array[offset:offset + length].rstrip(bytes([padding])).decode("LATIN-1")

    def byte_array(self, offset, length):
        return self.array[offset:offset + length]

    def subparse(self, offset, base):
        return base(self.array[offset:base.expected_length])

    def uint8(self, offset):
        return self.array[offset]

    def uint16l(self, offset):
        return self.uint8(offset) | (self.uint8(offset + 1) << 8)

    def uint16b(self, offset):
        return self.uint8(offset + 1) | (self.uint8(offset) << 8)

    def uint32l(self, offset):
        return self.uint16l(offset) | (self.uint16l(offset + 2) << 16)

    def uint32b(self, offset):
        return self.uint16b(offset + 2) | (self.uint16b(offset) << 16)

    def uint64l(self, offset):
        return self.uint32l(offset) | (self.uint32l(offset + 4) << 32)

    def uint64b(self, offset):
        return self.uint32b(offset + 4) | (self.uint32b(offset) << 32)


class Vesicle:
    expected_length = None

    def begin(self, data):
        assert self.expected_length is not None, "expected_length not specified on Vesicle subclass: %s" % self.__class__
        return Parsable(data, self.expected_length)

    def __repr__(self):
        return "{%s}" % ", ".join("%s = %s" % (k, v) for k, v in sorted(self.__dict__.items()) if k[0] != '_')
