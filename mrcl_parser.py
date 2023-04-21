import json
import sys
from pprint import pformat

from lib.common import Token
from lib.common import read_stdin_all

def puts_e(arg):
    print(arg, file=sys.stderr)

def inspect(arg):
    return pformat(arg, indent=4)

def p_e(arg):
    puts_e(inspect(arg))

def to_json(data):
    return json.dumps(data, indent=2)

def parse_json(json_):
    return json.loads(json_)

def read_tokens(src):
    tokens = []

    for line in src.split("\n"):
        if line != "":
            parts = parse_json(line)
            tokens.append(Token(parts[1], parts[2], parts[0]))

    return tokens

# --------------------------------

tokens = None
pos = 0

def not_yet_impl(k, v):
    return Exception(f"{k} ({v})")

def parse_error(val=None):
    return Exception("parse error " + inspect(val))

def is_end():
    return len(tokens) <= pos

def peek(offset = 0):
    global tokens
    global pos

    return tokens[pos + offset]

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
    global pos

    assert_value(pos, s)
    pos += 1

# --------------------------------

def _parse_arg():
    global pos

    t = peek()
    pos += 1
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
    global pos

    consume("func")

    t = peek()
    pos += 1
    func_name = t.value

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
    global pos

    t = peek()
    pos += 1
    var_name = t.value

    consume(";")

    return ["var", var_name]

def _parse_var_init():
    global pos

    t = peek()
    pos += 1
    var_name = t.value

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
    global pos

    t = peek()

    if t.kind == "int" or t.kind == "ident":
        pos += 1
        return t.get_value()
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
    global pos

    expr = _parse_expr_factor()

    while(is_binop(peek())):
        op = peek().value
        pos += 1

        factor = _parse_expr_factor()
        expr = [op, expr, factor]

    return expr


def parse_set():
    global pos

    consume("set")

    t = peek()
    pos += 1
    var_name = t.value

    consume("=")

    expr = parse_expr()

    consume(";")

    return ["set", var_name, expr]

def parse_funcall():
    global pos

    t = peek()
    pos += 1
    func_name = t.value

    consume("(")
    args = parse_args()
    consume(")")

    return [func_name, *args]

def parse_call():
    consume("call")

    funcall = parse_funcall()

    consume(";")

    return ["call", *funcall]

def parse_call_set():
    global pos

    consume("call_set")

    t = peek()
    pos += 1
    var_name = t.value

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
    global pos

    consume("_cmt")
    consume("(")

    t = peek()
    pos += 1
    comment = t.value

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

    if t.value == "when": # case の場合に出現
        return None
    elif t.value == "set":
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
# p_e(tokens)

tree = parse()
# p_e(tree)

print(to_json(tree))
