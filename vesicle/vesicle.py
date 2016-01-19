import intset

class Structure:
	coverage = intset.empty
	assertions = []

	def build(self):
		assert self.coverage
		assert self.coverage.low() == 0
		assert self.coverage.is_contiguous()
		return self.coverage.high()

class WithAssertion:
	def __init__(self, base, assertion):
		self.base = base
		self.assertion = assertion
	def __vesicle__(self, struct):
		struct.assertions.append(self.assertion)
		return self.base

class ByteArray:
	def __init__(self, offset, len):
		self._offset = offset
		self._len = len
	def __vesicle__(self, struct):
		coverage = intset.range(self._offset, len = self._len)
		assert not (struct.coverage & coverage), "Coverage overlap: %s and %s" % (struct.coverage, coverage)
		struct.coverage |= coverage
		return self
	def decode(self, source):
		fragment = source[self._offset:self._offset + self._len]
		assert len(fragment) == self._len
		return fragment

class Ascii(ByteArray):
	def __init__(self, offset, len, padding):
		ByteArray.__init__(self, offset, len)
		self.padding = bytes((padding,))
	def decode(self, source):
		data = ByteArray.decode(source)
		data = data.rstrip(self.padding)
		return data.decode("LATIN-1") # why not ASCII? that would assume that it was well-formed... TODO do this better

class Integer(ByteArray):
	def __init__(self, offset, bytes, unsigned, big_endian):
		ByteArray.__init__(self, offset, bytes)
		self.unsigned = unsigned
		self.big_endian = big_endian
	def decode(self, source):
		data = ByteArray.decode(source)
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
	gen.__name__ = gen.__qualname__ = "%sint%d%s" % ("u" if unsigned else "s", bits, "" if bits == 8 else ("b" if big_endian else "l"))
	return gen
def _int_gen_all(target):
	for bits in [8, 16, 32, 64]:
		for unsigned in [False, True]:
			for big_endian in ([False, True] if bits != 8 else [False]):
				gen = _int_gen(bits, unsigned, big_endian)
				target[gen.__name__] = gen
_int_gen_all(locals())

class MetaVesicle(type):
	def __init__(self, name, bases, attrs):
		struct = Structure()
		old_attrs = dict(attrs)
		attrs.clear()
		for k, v in old_attrs.items():
			if k[0:2] != "__":
				while hasattr(v, "__vesicle__"):
					v_new = getattr(v, "__vesicle__")(struct)
					if v_new == v:
						break
					v = v_new
			attrs[k] = v
		if not attrs.get("_incomplete", False):
			self._length = struct.build()
			assert "expected_length" in attrs
			assert self._length == attrs["expected_length"], "unexpected length"
		if "_incomplete" in attrs:
			del attrs["_incomplete"]
		attrs["__struct__"] = struct
		type.__init__(self, name, bases, attrs)

	@property
	def length(self):
		return self._length

class Vesicle(ByteArray, metaclass=MetaVesicle):
	def __init__(self, offset):
		if self != Vesicle:
			ByteArray.__init__(self, offset, self.length)
	@property
	def length(self):
		return self.__class__.length
	_incomplete = True

