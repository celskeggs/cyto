import intrange


class Type:
    def to_py(self):
        raise Exception("Cannot convert type to Python: %s" % self)

    def to_c(self):
        raise Exception("Cannot convert type to C: %s" % self)

    def __hash__(self):
        return hash(self.to_c())  # hmm... this might fail if to_c is not overridden...

    def __eq__(self, other):
        return hasattr(other, "to_c") and self.to_c() == other.to_c()


class IntegerType(Type):
    def __init__(self, bits, unsigned):
        assert type(bits) == int and 0 < bits and type(unsigned) == bool
        self.bits, self.unsigned = bits, unsigned

    def to_py(self):
        return int

    def to_c(self):
        return ("uint%d_t " if self.unsigned else "int%d_t ") % self.bits

    def get_range(self):
        if self.unsigned:
            return intrange.range(0, 2 ** 32)
        else:
            return intrange.range(-2 ** 31, 2 ** 32)

    def __hash__(self):
        return hash(self.bits if self.unsigned else -self.bits)

    def __eq__(self, other):
        return isinstance(other, IntegerType) and self.bits == other.bits and self.unsigned == other.unsigned


class ByteArrayType(Type):
    def __init__(self, length_type):
        assert isinstance(length_type, IntegerType) and length_type.unsigned
        self.length_type = length_type

    def to_py(self):
        return bytes

    def to_c(self):
        return "uint8_t *"

    def __hash__(self):
        return hash(self.length_type)

    def __eq__(self, other):
        return isinstance(other, ByteArrayType) and self.length_type == other.length_type


class VoidType(Type):
    def to_py(self):
        return None

    def to_c(self):
        return "void "

    def __hash__(self):
        return 0

    def __eq__(self, other):
        return isinstance(other, VoidType)


u8 = IntegerType(8, True)
s8 = IntegerType(8, False)
u16 = IntegerType(16, True)
s16 = IntegerType(16, False)
u32 = IntegerType(32, True)
s32 = IntegerType(32, False)
u64 = IntegerType(64, True)
s64 = IntegerType(64, False)
binary = ByteArrayType(u32)
void = VoidType()
