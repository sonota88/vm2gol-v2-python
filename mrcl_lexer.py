import json
import re
import sys

from lib.common import Token

def read_file(path):
    text = ""
    with open(path) as f:
        for line in f:
            text += line
    return text

def to_json(token):
    return json.dumps(
        [token.type, token.value]
    )

def is_kw(value):
    return value in [
        "func",
        "set",
        "var",
        "call_set",
        "call",
        "return",
        "case",
        "while",
        "when",
        "_cmt",
        "_debug"
    ]

def tokenize(src):
    tokens = []
    pos = 0

    re_space = r"([ \n]+)"
    re_comment = r"(//.*)\n"
    re_str = r"\"(.*)\""
    re_int = r"(-?[0-9]+)"
    re_sym = r"(==|!=|[(){}=;+*,])"
    re_ident = r"([a-z_][a-z0-9_]*)"

    while pos < len(src):
        rest = src[pos:]

        if re.match(re_space, rest):
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
            tokens.append( Token("str", s) )
            pos += len(s) + 2
        elif re.match(re_int, rest):
            m = re.match(re_int, rest)
            s = m.group(1)
            tokens.append( Token("int", s) )
            pos += len(s)
        elif re.match(re_sym, rest):
            m = re.match(re_sym, rest)
            s = m.group(1)
            tokens.append( Token("sym", s) )
            pos += len(s)
        elif re.match(re_ident, rest):
            m = re.match(re_ident, rest)
            s = m.group(1)
            if is_kw(s):
                tokens.append( Token("kw", s) )
            else:
                tokens.append( Token("ident", s) )
            pos += len(s)
        else:
            raise not_yet_impl("rest", rest)

    return tokens

in_file = sys.argv[1]
tokens = tokenize(read_file(in_file))

for token in tokens:
    print(to_json(token))
