import json, sys

from lib.common import Token
from lib.common import read_stdin_all, puts_e, inspect, p_e

def read_tokens(src):
    tokens = []

    for line in src.split("\n"):
        if line != "":
            parts = json.loads(line)
            tokens.append(Token(parts[1], parts[2], parts[0]))

    return tokens

# --------------------------------

tokens = None
pos = 0

def not_yet_impl(k, v):
    return Exception(f"{k} ({v})")

def parse_error(val=None):
    return Exception("parse error " + inspect(val))

def bump():
    global pos
    pos += 1

def is_end():
    return len(tokens) <= pos

def peek(offset = 0):
    global tokens
    global pos

    return tokens[pos + offset]

def peek_and_next():
    t = peek()
    bump()
    return t

def rest_head():
    return list(
        map(lambda t: f"{t.kind}<{t.value}>", (
            tokens[pos : pos + 8]
        ))
    )

def dump_state(msg=""):
    p_e([
        msg, pos, rest_head()
    ])

def assert_value(pos, exp):
    t = peek()

    if t.value != exp:
        msg = f"Assersion failed: expected({inspect(exp)}) actual({inspect(t)})"
        raise Exception(msg)

def consume(s):
    assert_value(pos, s)
    bump()

# --------------------------------

def _parse_arg():
    t = peek_and_next()
    return t.get_value()

def parse_args():
    args = []

    if peek().value == ")":
        return args

    args.append(_parse_arg())

    while(peek().value == ","):
        consume(",")
        args.append(_parse_arg())

    return args

def parse_func():
    consume("func")

    func_name = peek_and_next().value

    consume("(")
    args = parse_args()
    consume(")")

    consume("{")

    stmts = []
    while peek().value != "}":
        if peek().value == "var":
            stmts.append(parse_var())
        else:
            stmts.append(parse_stmt())

    consume("}")

    return ["func", func_name, args, stmts]

def _parse_var_declare():
    var_name = peek_and_next().value

    consume(";")

    return ["var", var_name]

def _parse_var_init():
    var_name = peek_and_next().value

    consume("=")

    expr = parse_expr()

    consume(";")

    return ["var", var_name, expr]

def parse_var():
    consume("var")

    t = peek(1)

    if t.value == ";":
        return _parse_var_declare()
    elif t.value == "=":
        return _parse_var_init()
    else:
        raise parse_error(f"unexpected token ({t})")

def _parse_expr_factor():
    t = peek()

    if t.kind == "int" or t.kind == "ident":
        return peek_and_next().get_value()
    elif t.kind == "sym":
        consume("(")
        expr = parse_expr()
        consume(")")
        return expr
    else:
        raise parse_error(f"unexpected token ({t})")

def is_binop(t):
    return t.value in ["+", "*", "==", "!="]

def parse_expr():
    expr = _parse_expr_factor()

    while(is_binop(peek())):
        op = peek_and_next().value

        factor = _parse_expr_factor()
        expr = [op, expr, factor]

    return expr


def parse_set():
    consume("set")

    var_name = peek_and_next().value

    consume("=")

    expr = parse_expr()

    consume(";")

    return ["set", var_name, expr]

def parse_funcall():
    func_name = peek_and_next().value

    consume("(")
    args = parse_args()
    consume(")")

    return [func_name, *args]

def parse_call():
    consume("call")

    funcall = parse_funcall()

    consume(";")

    return ["call", funcall]

def parse_call_set():
    consume("call_set")

    var_name = peek_and_next().value

    consume("=")

    funcall = parse_funcall()

    consume(";")

    return ["call_set", var_name, funcall]

def parse_return():
    consume("return")

    expr = parse_expr()
    consume(";")

    return ["return", expr]

def parse_while():
    consume("while")

    consume("(")
    expr = parse_expr()
    consume(")")

    consume("{")
    stmts = parse_stmts()
    consume("}")

    return ["while", expr, stmts]

def _parse_when_clause():
    consume("when")
    consume("(")
    expr = parse_expr()
    consume(")")

    consume("{")
    stmts = parse_stmts()
    consume("}")

    return [expr, *stmts]

def parse_case():
    consume("case")

    when_clauses = []

    while peek().value == "when":
        when_clauses.append(_parse_when_clause())

    return ["case", *when_clauses]

def parse_vm_comment():
    consume("_cmt")
    consume("(")

    comment = peek_and_next().value

    consume(")")
    consume(";")

    return ["_cmt", comment]

def parse_debug():
    consume("_debug")
    consume("(")
    consume(")")
    consume(";")

    return ["_debug"]

def parse_stmt():
    t = peek()

    if t.value == "set":
        return parse_set()
    elif t.value == "call":
        return parse_call()
    elif t.value == "call_set":
        return parse_call_set()
    elif t.value == "return":
        return parse_return()
    elif t.value == "while":
        return parse_while()
    elif t.value == "case":
        return parse_case()
    elif t.value == "_cmt":
        return parse_vm_comment()
    elif t.value == "_debug":
        return parse_debug()
    else:
        raise Exception("parse error")

def parse_stmts():
    stmts = []

    while peek().value != "}":
        stmts.append(parse_stmt())

    return stmts

def parse_top_stmt():
    if peek().value == "func":
        return parse_func()
    else:
        raise Exception("unexpected token")

def parse_top_stmts():
    stmts = []
    while not is_end():
        stmts.append(parse_top_stmt())

    return stmts

def parse():
    try:
        stmts = parse_top_stmts()
    except Exception as e:
        dump_state()
        raise e

    return ["top_stmts", *stmts]

# --------------------------------

src = read_stdin_all()
tokens = read_tokens(src)

tree = parse()

print(json.dumps(tree, indent=2))

