class IntegerSet:
    def __init__(self, elems):
        for elem in elems:
            assert 0 <= elem[0] < elem[1]
        self.elems = sorted(elems, key=lambda x: x[0])
        i = 0
        while i < len(self.elems) - 1:
            a = self.elems[i]
            b = self.elems[i + 1]
            if a[1] >= b[0]:
                del self.elems[i + 1]
                self.elems[i] = (a[0], b[1])
            else:
                i += 1

    def __or__(self, other):
        if isinstance(other, IntegerSet):
            return IntegerSet(self.elems + other.elems)
        else:
            return NotImplemented

    def __and__(self, other):
        if isinstance(other, IntegerSet):
            remain = other.elems
            out = []
            for elem in self.elems:
                while remain and remain[0][1] <= elem[0]:  # next remain can be skipped
                    remain = remain[1:]
                if not remain: break
                if elem[1] <= remain[0][0]:  # next elem can be skipped
                    continue
                # remain end > elem start; remain start > elem end
                out.append((max(elem[0], remain[0][0]), min(elem[1], remain[0][1])))
            return IntegerSet(out)
        else:
            return NotImplemented

    def __bool__(self):
        return bool(self.elems)

    def __repr__(self):
        return repr(self.elems)

    def low(self):
        return self.elems[0][0]

    def high(self):
        return self.elems[-1][1]

    def is_contiguous(self):
        return len(self.elems) <= 1


empty = IntegerSet([])


def range(start, len):
    assert start >= 0 and len >= 0
    return IntegerSet([(start, start + len)])
