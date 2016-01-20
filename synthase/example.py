import synthase, concrete_types

def from_bytes_little(x):
    return x[0] | (x[1] << 8) | (x[2] << 16) | (x[3] << 24)

def example(x):
    return from_bytes_little(x[0:4]) * from_bytes_little(x[4:8])

def example2(x, y):
    return (x + 2) * 10 - y * 2

print(synthase.compile(example, concrete_types.binary, rettype=concrete_types.u32))
