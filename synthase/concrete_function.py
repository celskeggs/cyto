import concrete_types, concrete_operator


def synth(x):
    if hasattr(x, "synth"):
        return x.synth()
    elif type(x) == int:
        return str(x)
    else:
        raise Exception("No synth method added to %s" % x)


class Argument:
    def __init__(self, name, concrete_type, function):
        assert type(name) == str
        assert isinstance(concrete_type, concrete_types.Type)
        assert isinstance(function, Function)
        self.name = name
        self.concrete_type = concrete_type
        self.function = function
        assert all(other_arg.name != name for other_arg in function._arguments)
        function._arguments.append(self)

    def synth(self):
        return self.name

    def synth_as_argument(self):
        return self.concrete_type.to_c() + self.synth()

    def __hash__(self):
        return hash(self.name) + hash(self.function) * 3

    def __eq__(self, other):
        return type(other) == type(self) and other.i == self.name and other.function == self.function

    def synth_assertions(self):
        return None


class IntegerArgument(Argument):
    def __init__(self, name, concrete_type, function):
        assert isinstance(concrete_type, concrete_types.IntegerType)
        Argument.__init__(self, name, concrete_type, function)
        self.asserted_range = concrete_type.get_range()

    def assert_comparison(self, operator, other):
        if type(other) == int:
            self.asserted_range &= operator.valid_result_range(other, self.asserted_range.low(),
                                                               self.asserted_range.high())
            assert self.asserted_range, "No way to satisfy constraints on %s!" % (self)
        else:
            self.function.complex_assertions.append((self, operator, other))

    def synth_assertions(self):
        possible = self.concrete_type.get_range()
        if self.asserted_range == possible:
            return None
        these = []
        plow, phigh = possible.low(), possible.high()
        for low, high in self.asserted_range.elems:
            if low != plow:
                if high != phigh:
                    these.append(
                            concrete_operator.logical_and.to_c(
                                    concrete_operator.le.to_c(low, self.synth()),
                                    concrete_operator.lt.to_c(self.synth(), high)))
                else:
                    these.append(concrete_operator.ge.to_c(self.synth(), low))
            else:
                assert high != phigh  # because range != possible
                these.append(concrete_operator.lt.to_c(self.synth(), high))
        assert these
        return concrete_operator.logical_or.join_c(these)


C_FUNCTION_TEMPLATE = """
%s {
    if (!(%s)) {
        abort_assert_fail();
    }
    %s
}"""
FUNC_PREFIX = "sya_"


class Function:
    def __init__(self, function_name, return_type):
        assert isinstance(return_type, concrete_types.Type)
        self.function_name = FUNC_PREFIX + function_name
        self._arguments = []
        self.complex_assertions = []
        self.return_type = return_type

    def synth_arguments(self):
        return ", ".join(arg.synth_as_argument() for arg in self._arguments)

    def synth_assertions(self):
        assert not self.complex_assertions, "Complex assertions not currently handled"
        subasserts = filter(None, (arg.synth_assertions() for arg in self._arguments))
        if subasserts:
            return concrete_operator.logical_and.join_c(subasserts)
        else:
            return "1"

    def synth_declaration(self):
        # TODO: pass byte array length information in return type as well
        return "{rettype}{name}({arguments})".format(
                rettype=self.return_type.to_c(), name=self.function_name,
                arguments=self.synth_arguments())

    def synth_body(self, value):
        if self.return_type == concrete_types.void:
            return synth(value) + ";"
        else:
            return "return " + synth(value) + ";"

    def synth_implementation(self, value):
        return C_FUNCTION_TEMPLATE % (self.synth_declaration(), self.synth_assertions(), self.synth_body(value))
