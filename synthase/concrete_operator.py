import operator


class Operator:
    def __init__(self, python_name, c_symbol, is_comparison=False, py_reverse=None):
        self.python_name, self.c_symbol, self.is_comparison, self.py_reverse = python_name, c_symbol, is_comparison, py_reverse

    def to_py(self):
        return self.python_name

    def to_py_method(self, reverse=False):
        return "__%s%s__" % ("r" if reverse else "", self.python_name)

    def to_py_func(self):
        return getattr(operator, self.to_py())

    @property
    def reverse(self):
        assert self.py_reverse
        return operator_dict[self.py_reverse]

    def to_c(self, a, b):
        return "(%s %s %s)" % (a, self.c_symbol, b)

    def __repr__(self):
        return "Operator(%s, %s)" % (self.python_name, self.c_symbol)


# Should Operator("truediv", "/") be included? floordiv would be // in python, but it's not so in C...
operators = [Operator("add", "+"), Operator("sub", "-"), Operator("mul", "*"), Operator("floordiv", "/"),
             Operator("lshift", "<<"), Operator("rshift", ">>"),
             Operator("or", "|"), Operator("xor", "^"), Operator("and", "&"),
             Operator("lt", "<", True, "gt"), Operator("gt", ">", True, "lt"),
             Operator("le", "<=", True, "ge"), Operator("ge", ">=", True, "le"),
             Operator("eq", "==", True, "eq"), Operator("ne", "!=", True, "ne")]
operator_dict = {op.to_py(): op for op in operators}
