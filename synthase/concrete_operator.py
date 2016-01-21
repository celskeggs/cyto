import operator, intrange


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

    def valid_result_range(self, second_param, low_min, high_max):
        if self.python_name == "eq":
            return intrange.singular(second_param)
        elif self.python_name == "ne":
            if low_min <= second_param < high_max:
                return intrange.range_to(low_min, second_param) | intrange.range_to(second_param + 1, high_max)
            else:
                return intrange.range_to(low_min, high_max)
        elif self.python_name == "lt":
            return intrange.range_to(low_min, second_param)
        elif self.python_name == "ge":
            return intrange.range_to(second_param, high_max)
        elif self.python_name == "le":
            return intrange.range_to(low_min, second_param + 1)
        elif self.python_name == "gt":
            return intrange.range_to(second_param + 1, high_max)
        else:
            raise Exception("Result range calculation not yet available for: %s" % self)

    def to_c(self, a, b):
        return "(%s %s %s)" % (a, self.c_symbol, b)

    def join_c(self, args):
        args = list(args)
        assert args
        if len(args) == 1:
            return args[0]
        return "(%s)" % (" %s " % self.c_symbol).join(args)

    def __repr__(self):
        return "Operator(%s, %s)" % (self.python_name, self.c_symbol)


# Should Operator("truediv", "/") be included? floordiv would be // in python, but it's not so in C...
operators = [Operator("add", "+"), Operator("sub", "-"), Operator("mul", "*"), Operator("floordiv", "/"),
             Operator("lshift", "<<"), Operator("rshift", ">>"),
             Operator("or", "|"), Operator("xor", "^"), Operator("and", "&"),
             Operator("lt", "<", True, "gt"), Operator("gt", ">", True, "lt"),
             Operator("le", "<=", True, "ge"), Operator("ge", ">=", True, "le"),
             Operator("eq", "==", True, "eq"), Operator("ne", "!=", True, "ne"),
             # Not treated as real by Python:
             Operator("logical_and", "&&"), Operator("logical_or", "||")]
operator_dict = {op.to_py(): op for op in operators}

lt, gt, le, ge, eq, ne = [operator_dict[k] for k in ("lt", "le", "gt", "ge", "eq", "ne")]
logical_and, logical_or = operator_dict["logical_and"], operator_dict["logical_or"]
