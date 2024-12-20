import json, re, sys

from lib.common import Token
from lib.common import read_stdin_all

def to_json(token):
    return json.dumps(
        [token.lineno, token.kind, token.value]
    )

def is_kw(value):
    return value in [
        "func", "return", "var", "set", "call", "call_set", "case", "when", "while",
        "_cmt", "_debug"
    ]

def tokenize(src):
    tokens = []
    pos = 0
    lineno = 1

    re_space = r"( +)"
    re_comment = r"(//.*)\n"
    re_str = r"\"(.*)\""
    re_int = r"(-?[0-9]+)"
    re_sym = r"(==|!=|[(){}=;+*,])"
    re_ident = r"([a-z_][a-z0-9_]*)"

    while pos < len(src):
        rest = src[pos:]

        if rest[0] == "\n":
            pos += 1
            lineno += 1
        elif re.match(re_space, rest):
            m = re.match(re_space, rest)
            s = m.group(1)
            pos += len(s)
        elif re.match(re_comment, rest):
            m = re.match(re_comment, rest)
            s = m.group(1)
            pos += len(s)
        elif re.match(re_str, rest):
            m = re.match(re_str, rest)
            s = m.group(1)
            tokens.append(Token("str", s, lineno))
            pos += len(s) + 2
        elif re.match(re_int, rest):
            m = re.match(re_int, rest)
            s = m.group(1)
            tokens.append(Token("int", s, lineno))
            pos += len(s)
        elif re.match(re_sym, rest):
            m = re.match(re_sym, rest)
            s = m.group(1)
            tokens.append(Token("sym", s, lineno))
            pos += len(s)
        elif re.match(re_ident, rest):
            m = re.match(re_ident, rest)
            s = m.group(1)
            if is_kw(s):
                tokens.append(Token("kw", s, lineno))
            else:
                tokens.append(Token("ident", s, lineno))
            pos += len(s)
        else:
            raise not_yet_impl("rest", rest)

    return tokens

src = read_stdin_all()
tokens = tokenize(src)

for token in tokens:
    print(to_json(token))
