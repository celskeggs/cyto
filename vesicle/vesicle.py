import intset, operator


class Structure:
    coverage = intset.empty
    assertions = []

    def build(self):
        assert self.coverage
        assert self.coverage.low() == 0
        assert self.coverage.is_contiguous()
        return self.coverage.high()


def _define_dynop(on, name, op, reverse):
    name = ("__r%s__" if reverse else "__%s__") % name

    def dyn(self, other):
        if self._decode_target is not None:
            return getattr(self._decode_target, name)(self, other)
        return DynamicOperator(other, op, self) if reverse else DynamicOperator(self, op, other)

    dyn.__qualname__ = dyn.__name__ = name
    on[name] = dyn


def _define_decodable():
    attrs = {"_decode_target": None}
    for k in ["add", "sub", "mul", "truediv", "floordiv"]:
        op = getattr(operator, k)
        for r in [False, True]:
            _define_dynop(attrs, k, op, r)
    return type("Decodable", (), attrs)


Decodable = _define_decodable()


class DynamicOperator(Decodable):
    def __init__(self, a, op, b):
        Decodable.__init__(self)
        self.a, self.op, self.b = a, op, b

    def decode(self, source):
        print("DECODE", source, "on", self.a, self.op, self.b)
        return self.op(self.a.decode(source), self.b.decode(source))


class WithAssertion(Decodable):
    def __init__(self, base, assertion):
        Decodable.__init__(self)
        self.base = base
        self.assertion = assertion
        self._decode_target = base

    def __vesicle__(self, struct):
        struct.assertions.append(self.assertion)
        return self.base


class ByteArray(Decodable):
    def __init__(self, offset, len):
        Decodable.__init__(self)
        self._offset = offset
        self._len = len

    def __vesicle__(self, struct):
        coverage = intset.range(self._offset, len=self._len)
        assert not (struct.coverage & coverage), "Coverage overlap: %s and %s" % (struct.coverage, coverage)
        struct.coverage |= coverage
        return self

    def decode(self, source):
        fragment = source[self._offset:self._offset + self._len]
        print("Decoded:", source, len(source), self._offset, self._len, fragment)
        assert len(fragment) == self._len, "Wrong length: given '%s' of len %d but expected %d" % (
        fragment, len(fragment), self._len)
        return fragment


class Ascii(ByteArray):
    def __init__(self, offset, len, padding):
        ByteArray.__init__(self, offset, len)
        self.padding = bytes((padding,))

    def decode(self, source):
        data = ByteArray.decode(self, source)
        data = data.rstrip(self.padding)
        return data.decode("LATIN-1")  # why not ASCII? that would assume that it was well-formed... TODO do this better


class Integer(ByteArray):
    def __init__(self, offset, bytes, unsigned, big_endian):
        ByteArray.__init__(self, offset, bytes)
        self.unsigned = unsigned
        self.big_endian = big_endian

    def decode(self, source):
        data = ByteArray.decode(self, source)
        return int.from_bytes(data, "big" if self.big_endian else "little", signed=not self.unsigned)


def byte_array(offset, len):
    return ByteArray(offset, len)


def fixed(offset, *nums):
    expect = bytes(nums)
    barr = byte_array(offset, len=len(expect))
    return WithAssertion(barr, lambda x: barr.decode(x) == expect)


def ascii(offset, len, padding=0x00):
    return Ascii(offset, len, padding)


def _int_any(offset, bits, unsigned=False, big_endian=False):
    assert bits % 8 == 0
    return Integer(offset, bits // 8, unsigned, big_endian)


def _int_gen(bits, unsigned, big_endian):
    def gen(offset):
        return _int_any(offset, bits, unsigned=unsigned, big_endian=big_endian)

    gen.__name__ = gen.__qualname__ = "%sint%d%s" % (
    "u" if unsigned else "s", bits, "" if bits == 8 else ("b" if big_endian else "l"))
    return gen


def _int_gen_all(target):
    for bits in [8, 16, 32, 64]:
        for unsigned in [False, True]:
            for big_endian in ([False, True] if bits != 8 else [False]):
                gen = _int_gen(bits, unsigned, big_endian)
                target[gen.__name__] = gen


_int_gen_all(locals())


def should_include_value(x):
    if hasattr(x, "decode"):
        return True
    elif hasattr(x, "__call__"):
        return False
    elif hasattr(x, "__add__"):
        return True
    else:
        return False


class MetaVesicle(type):
    def __new__(cls, name, bases, attrs):
        struct = Structure()
        old_attrs = dict(attrs)
        attrs.clear()
        decodable = []
        for k, v in old_attrs.items():
            if k[0:2] != "__":
                while hasattr(v, "__vesicle__"):
                    v_new = getattr(v, "__vesicle__")(struct)
                    if v_new == v:
                        break
                    v = v_new
                if should_include_value(v):
                    decodable.append(k)
            attrs[k] = v
        if not attrs.get("_incomplete", False):
            attrs["length"] = struct.build()
            assert "expected_length" in attrs
            assert attrs["length"] == attrs["expected_length"], "unexpected length"
        if "_incomplete" in attrs:
            del attrs["_incomplete"]
        attrs["__decodable__"] = decodable
        attrs["__struct__"] = struct
        return type.__new__(cls, name, bases, attrs)


class Decoded:
    def list(self):
        return [k for k in self.__dict__.keys() if k[0:2] != "__"]

    def __repr__(self):
        return "{%s}" % ", ".join("%s = %s" % (k, getattr(self, k)) for k in sorted(self.list()))


class Vesicle(ByteArray, metaclass=MetaVesicle):
    def __init__(self, offset):
        if self != Vesicle:
            ByteArray.__init__(self, offset, self.length)

    _incomplete = True

    def decode(self, source):
        source = ByteArray.decode(self, source)
        assert len(source) == self.length
        dec = Decoded()
        for k in self.__decodable__:
            v = getattr(self.__class__, k)
            if hasattr(v, "decode"):
                v = v.decode(source)
            setattr(dec, k, v)
        for assertion in self.__struct__.assertions:
            print(assertion(source))
        return dec

    @classmethod
    def parse(cls, data):
        assert len(data) == cls.length
        return cls(0).decode(data)
