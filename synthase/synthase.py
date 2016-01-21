import intrange, concrete_operator, concrete_types, concrete_function


def _define_dynop(op, reverse):
    name = op.to_py_method(reverse=reverse)

    def dyn(self, other):
        return IntegerResult(self, op, other, reverse)

    dyn.__qualname__ = dyn.__name__ = name
    return name, dyn


class IntegerVirtual:
    locals().update(dict(_define_dynop(op, r) for op in concrete_operator.operators for r in [False, True]))


class BytesVirtual:
    def __init__(self, length):
        self.length = length
        assert_that(length >= 0)

    def __getitem__(self, key):
        if isinstance(key, slice):
            assert key.step is None or (type(key.step) == int and key.step == 1), \
                "synthase cannot handle nontrivial slice steps (i.e. steps besides 1): %s"
            start, stop = key.start, key.stop
            assert_that(start >= 0)
            assert_that(stop >= start)
            assert_that(stop <= self.length)
            return BytesSubsequence(self, start, stop - start)
        elif isinstance(key, IntegerVirtual) or isinstance(key, int):
            # Negative indicies are not currently supported by synthase because lengths are not always known.
            assert_that(key >= 0)
            assert_that(key < self.length)
            return IntegerFromBytes(self, key)
        else:
            raise TypeError("Unexpected type of index: %s" % key)


class BytesSubsequence(BytesVirtual):
    def __init__(self, base, start, length):
        BytesVirtual.__init__(self, length)
        assert_that(start >= 0)
        self.base, self.start = base, start

    def __getitem__(self, key):
        if isinstance(key, slice):
            assert type(key.step) == int and key.step == 1, \
                "synthase cannot handle nontrivial slice steps (i.e. steps besides 1)"
            start, stop = key.start, key.stop
            assert_that(start >= 0)
            assert_that(stop >= start)
            assert_that(stop <= self.length)
            return self.base[self.start + start:self.start + stop]
        elif isinstance(key, IntegerVirtual) or isinstance(key, int):
            # Negative indicies are not currently supported by synthase because lengths are not always known.
            assert_that(key >= 0)
            assert_that(key < self.length)
            return self.base[key + self.start]
        else:
            raise TypeError("Unexpected type of index: %s" % key)


class IntegerFromBytes(IntegerVirtual):
    def __init__(self, source, key):
        self.source, self.key = source, key

    def synth(self):
        return "(%s[%s])" % (concrete_function.synth(self.source), concrete_function.synth(self.key))


class IntegerResult(IntegerVirtual):
    def __init__(self, a, operator, b, reverse):
        IntegerVirtual.__init__(self)
        assert isinstance(a, IntegerVirtual) or isinstance(b, IntegerVirtual)
        if reverse:
            self.a, self.operator, self.b = b, operator, a
        else:
            self.a, self.operator, self.b = a, operator, b

    def synth(self):
        return self.operator.to_c(concrete_function.synth(self.a), concrete_function.synth(self.b))

    def assert_bool(self, b):
        if self.operator.is_comparison:
            if isinstance(self.a, IntegerVirtual):
                self.a.assert_comparison(self.operator, self.b)
            else:
                self.b.assert_comparison(self.operator.reverse, self.a)
        else:
            raise Exception("Not yet implemented: %s for %s" % (self.operator, self))


class IntegerArgument(concrete_function.IntegerArgument, IntegerVirtual):
    def __init__(self, name, concrete_type, function):
        assert isinstance(concrete_type, concrete_types.IntegerType)
        IntegerVirtual.__init__(self)
        concrete_function.IntegerArgument.__init__(self, name, concrete_type, function)

    def get_possible_range(self):
        return self.concrete_type.get_range()


class BytesArgument(concrete_function.Argument, BytesVirtual):
    def __init__(self, name, concrete_type, function, length):
        assert isinstance(concrete_type, concrete_types.ByteArrayType)
        assert isinstance(length, IntegerVirtual) or type(length) == type(lambda: None)
        concrete_function.Argument.__init__(self, name, concrete_type, function)
        if not isinstance(length, IntegerVirtual):  # TODO: make this less hacky - this is needed for argument ordering
            length = length()
        BytesVirtual.__init__(self, length)


def make_argument(type, index, function):
    arg_name = "arg_%d" % index
    if isinstance(type, concrete_types.IntegerType):
        return IntegerArgument(arg_name, type, function)
    elif isinstance(type, concrete_types.ByteArrayType):
        l = lambda: IntegerArgument(arg_name + "_len", type.length_type, function)
        b = BytesArgument(arg_name, type, function, l)
        return b
    else:
        raise Exception("Unhandled type: %s" % type)


def assert_that(x):
    assert x is not False, "Runtime assertion known to be false at compile-time"
    if x is not True:
        x.assert_bool(True)


def compile(target, *args, rettype=concrete_types.void):
    func = concrete_function.Function(target.__name__, rettype)
    return func.synth_implementation(target(*(make_argument(arg, i, func) for i, arg in enumerate(args))))
