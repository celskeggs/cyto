import intrange, concrete_operator, concrete_types


class Virtual:
    pass


def _define_dynop(op, reverse):
    name = op.to_py_method(reverse=reverse)

    def dyn(self, other):
        return IntegerResult(self, op, other, reverse)

    dyn.__qualname__ = dyn.__name__ = name
    return name, dyn


class IntegerVirtual(Virtual):
    locals().update(dict(_define_dynop(op, r) for op in concrete_operator.operators for r in [False, True]))


class BytesVirtual(Virtual):
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
        return "(%s[%s])" % (synth(self.source), synth(self.key))


class IntegerResult(IntegerVirtual):
    def __init__(self, a, operator, b, reverse):
        IntegerVirtual.__init__(self)
        assert isinstance(a, IntegerVirtual) or isinstance(b, IntegerVirtual)
        if reverse:
            self.a, self.operator, self.b = b, operator, a
        else:
            self.a, self.operator, self.b = a, operator, b

    def synth(self):
        return self.operator.to_c(synth(self.a), synth(self.b))

    def assert_bool(self, b):
        if self.operator.is_comparison:
            if isinstance(self.a, IntegerVirtual):
                self.a.assert_comparison(self.operator, self.b)
            else:
                self.b.assert_comparison(self.operator.reverse, self.a)
        else:
            raise Exception("Not yet implemented: %s for %s" % (self.operator, self))


class Argument:
    def __init__(self, i, assertions, concrete_type):
        self.i = i
        self.assertions = assertions
        self.concrete_type = concrete_type

    def synth(self):
        return self.i

    def synth_as_argument(self):
        return self.concrete_type.to_c() + self.synth()

    def __hash__(self):
        return hash(self.i)

    def __eq__(self, other):
        return type(other) == type(self) and other.i == self.i


class IntegerArgument(Argument, IntegerVirtual):
    def __init__(self, i, assertions, concrete_type):
        assert isinstance(concrete_type, concrete_types.IntegerType)
        IntegerVirtual.__init__(self)
        Argument.__init__(self, i, assertions, concrete_type)

    def assert_comparison(self, operator, other):
        self.assertions.append((self, operator, other))

    def get_possible_range(self):
        return self.concrete_type.get_range()


class BytesArgument(Argument, BytesVirtual):
    def __init__(self, i, assertions, concrete_type, length):
        assert isinstance(concrete_type, concrete_types.ByteArrayType)
        assert isinstance(length, IntegerVirtual)
        BytesVirtual.__init__(self, length)
        Argument.__init__(self, i, assertions, concrete_type)


def make_argument(type, index, args, assertions):
    arg_name = "arg_%d" % index
    if isinstance(type, concrete_types.IntegerType):
        i = IntegerArgument(arg_name, assertions)
        args.append(i)
        return i
    elif isinstance(type, concrete_types.ByteArrayType):
        l = IntegerArgument(arg_name + "_len", assertions, type.length_type)
        b = BytesArgument(arg_name, assertions, type, l)
        args.append(b)
        args.append(l)
        return b
    else:
        raise Exception("Unhandled type: %s" % type)


def assert_that(x):
    assert x is not False, "Runtime assertion known to be false at compile-time"
    if x is not True:
        x.assert_bool(True)


def synth(x):
    if hasattr(x, "synth"):
        return x.synth()
    elif type(x) == int:
        return str(x)
    else:
        raise Exception("No synth method added to %s" % x)


# (a, op, b): a is ALWAYS an argument
def collapse_assertions(assertions, arguments):
    known_ranges = {}
    for arg in arguments:
        if isinstance(arg, IntegerArgument):
            known_ranges[arg] = arg.get_possible_range()

    remain = []
    for a, op, b in assertions:
        if type(b) == int:
            if op.to_py() == "eq":
                known_ranges[a] &= intrange.singular(b)
            elif op.to_py() == "ne":
                known_ranges[a] -= intrange.singular(b)
            elif op.to_py() == "lt":
                known_ranges[a] &= intrange.range_to(known_ranges[a].low(), b)
            elif op.to_py() == "le":
                known_ranges[a] &= intrange.range_to(known_ranges[a].low(), b + 1)
            elif op.to_py() == "gt":
                known_ranges[a] &= intrange.range_to(b + 1, known_ranges[a].high())
            elif op.to_py() == "ge":
                known_ranges[a] &= intrange.range_to(b, known_ranges[a].high())
            else:
                raise Exception("Invalid comparison operation: %s" % op)
            assert known_ranges[a], "No way to satisfy constraints on %s" % a
        else:
            remain.append((a, op, b))
    assert not remain, "Not yet handled."

    assertions = []  # now in C-form

    for arg, range in known_ranges.items():
        possible = arg.get_possible_range()
        if range == possible:
            continue
        these = []
        plow, phigh = possible.low(), possible.high()
        for low, high in range.elems:
            if low != plow:
                if high != phigh:
                    these.append("%d <= %s && %s < %d" % (low, arg.synth(), arg.synth(), high))
                else:
                    these.append("%s >= %d" % (arg.synth(), low))
            else:
                assert high != phigh  # because range != possible
                these.append("%s < %d" % (arg.synth(), high))
        assertions.append(" || ".join(these))

    return " && ".join(assertions) if assertions else "1"


C_FUNCTION_TEMPLATE = """{rettype} sya_{name}({arguments}) {o}\n\tif (!({assertions})) {o}\n\t\tabort_assert_fail();\n\t{c}\n\t{body}\n{c}"""


def compile(x, *args, rettype=None):
    all_arguments = []
    assertions = []
    proxies = [make_argument(arg, i, all_arguments, assertions) for i, arg in enumerate(args)]
    proxy_out = x(*proxies)

    assertions = collapse_assertions(assertions, all_arguments)
    arguments = ", ".join(arg.synth_as_argument() for arg in all_arguments)
    if rettype is None:
        body = synth(proxy_out) + ";"
    else:
        body = "return " + synth(proxy_out) + ";"

    # TODO: pass length information in return type as well
    return C_FUNCTION_TEMPLATE.format(rettype=rettype.to_c(), name=x.__name__, arguments=arguments,
                                      assertions=assertions, body=body, o="{", c="}")
