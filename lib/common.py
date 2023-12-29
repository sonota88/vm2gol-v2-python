import sys

from pprint import pformat

def puts_e(arg):
    print(arg, file=sys.stderr)

def inspect(arg):
    return pformat(arg, indent=4)

def p_e(arg):
    puts_e(inspect(arg))

def read_stdin_all():
    str = ""
    while True:
        line = sys.stdin.readline()
        if not line: break
        str += line
    return str

class Token:
    def __init__(self, kind, value, lineno):
        self.kind = kind
        self.value = value
        self.lineno = lineno

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return f"Token(kind='{self.kind}', value='{self.value}', lineno={self.lineno})"

    def get_value(self):
        if self.kind == "ident":
            return self.value
        elif self.kind == "int":
            return int(self.value)
        else:
            raise Exception("invalid kind")
