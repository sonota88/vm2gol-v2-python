import json
import sys
from pprint import pformat

from lib.common import Token

def puts_e(arg):
    print(arg, file=sys.stderr)

def inspect(arg):
    return pformat(arg, indent=4)

def p_e(arg):
    puts_e(inspect(arg))

def read_file(path):
    text = ""
    with open(path) as f:
        for line in f:
            text += line
    return text

def to_json(data):
    return json.dumps(data, indent=2)

def parse_json(json_):
    return json.loads(json_)

def read_tokens(path):
    tokens = []

    with open(path) as f:
        for line in f:
            parts = parse_json(line)
            tokens.append(Token(parts[0], parts[1]))

    return tokens

# --------------------------------

def not_yet_impl(k, v):
    return Exception(f"{k} ({v})")

def parse_error(val=None):
    return Exception("parse error " + inspect(val))

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def is_end(self):
        return len(self.tokens) <= self.pos

    def peek(self, offset = 0):
        return self.tokens[self.pos + offset]

    def rest_head(self):
        return list(
            map(lambda t: f"{t.type}<{t.value}>", (
                self.tokens[self.pos : self.pos + 8]
            ))
        )

    def dump_state(self, msg=""):
        p_e([
            msg, self.pos, self.rest_head()
        ])

    def assert_value(self, pos, exp):
        t = self.peek()

        if t.value != exp:
            msg = f"Assersion failed: expected({inspect(exp)}) actual({inspect(t)})"
            raise Exception(msg)

    def consume(self, s):
        self.assert_value(self.pos, s)
        self.pos += 1

    # --------------------------------

    def _parse_arg(self):
        t = self.peek()
        if t.type == "ident":
            self.pos += 1
            return t.value
        elif t.type == "int":
            self.pos += 1
            return int(t.value)
        else:
            raise parse_error(t)

    def parse_args(self):
        args = []

        if self.peek().value == ")":
            return args

        args.append(self._parse_arg())

        while(self.peek().value == ","):
            self.consume(",")
            args.append(self._parse_arg())

        return args

    def parse_func(self):
        self.consume("func")

        t = self.peek()
        self.pos += 1
        func_name = t.value

        self.consume("(")
        args = self.parse_args()
        self.consume(")")

        self.consume("{")

        stmts = []
        while self.peek().value != "}":
            if self.peek().value == "var":
                stmts.append(self.parse_var())
            else:
                stmts.append(self.parse_stmt())

        self.consume("}")

        return ["func", func_name, args, stmts]

    def parse_var_declare(self):
        t = self.peek()
        self.pos += 1
        var_name = t.value

        self.consume(";")

        return ["var", var_name]

    def parse_var_init(self):
        t = self.peek()
        self.pos += 1
        var_name = t.value

        self.consume("=")

        expr = self.parse_expr()

        self.consume(";")

        return ["var", var_name, expr]

    def parse_var(self):
        self.consume("var")

        t = self.peek(1)

        if t.value == ";":
            return self.parse_var_declare()
        elif t.value == "=":
            return self.parse_var_init()
        else:
            raise parse_error(t)

    def parse_expr_right(self, expr_l):
        t = self.peek()

        if t.value == ";" or t.value == ")":
            return expr_l

        if t.value == "+":
            self.consume("+")
            expr_r = self.parse_expr()
            return ["+", expr_l, expr_r]
        elif t.value == "*":
            self.consume("*")
            expr_r = self.parse_expr()
            return ["*", expr_l, expr_r]
        elif t.value == "==":
            self.consume("==")
            expr_r = self.parse_expr()
            return ["eq", expr_l, expr_r]
        elif t.value == "!=":
            self.consume("!=")
            expr_r = self.parse_expr()
            return ["neq", expr_l, expr_r]
        else:
            raise parse_error(t)
            

    def parse_expr(self):
        t_left = self.peek()

        if t_left.value == "(":
            self.consume("(")
            expr_l = self.parse_expr()
            self.consume(")")
            return self.parse_expr_right(expr_l)

        if t_left.type == "int" or t_left.type == "ident":
            self.pos += 1

            if t_left.type == "int":
                expr_l = int(t_left.value)
            elif t_left.type == "ident":
                expr_l = t_left.value
            else:
                raise Exception("invalid type")

            return self.parse_expr_right(expr_l)
        else:
            raise parse_error()

    def parse_set(self):
        self.consume("set")

        t = self.peek()
        self.pos += 1
        var_name = t.value

        self.consume("=")

        expr = self.parse_expr()

        self.consume(";")
        
        return ["set", var_name, expr]

    def parse_call(self):
        self.consume("call")

        funcall = self.parse_funcall()

        self.consume(";")

        return ["call", *funcall]

    def parse_funcall(self):
        t = self.peek()
        self.pos += 1
        func_name = t.value

        self.consume("(")
        args = self.parse_args()
        self.consume(")")

        return [func_name, *args]

    def parse_call_set(self):
        self.consume("call_set")

        t = self.peek()
        self.pos += 1
        var_name = t.value

        self.consume("=")

        expr = self.parse_funcall()

        self.consume(";")

        return ["call_set", var_name, expr]

    def parse_return(self):
        self.consume("return")

        t = self.peek()

        expr = self.parse_expr()
        self.consume(";")

        return ["return", expr]

    def parse_while(self):
        self.consume("while")

        self.consume("(")
        expr = self.parse_expr()
        self.consume(")")

        self.consume("{")
        stmts = self.parse_stmts()
        self.consume("}")

        return ["while", expr, stmts]

    def _parse_when_clause(self):
        t = self.peek()
        if t.value == "}":
            return None

        self.consume("when")
        self.consume("(")
        expr = self.parse_expr()
        self.consume(")")

        self.consume("{")
        stmts = self.parse_stmts()
        self.consume("}")

        return [expr, *stmts]

    def parse_case(self):
        self.consume("case")

        self.consume("{")

        when_clauses = []

        while(True):
            when_clause = self._parse_when_clause()
            if when_clause is None:
                break
            else:
                when_clauses.append(when_clause)

        self.consume("}")

        return ["case", *when_clauses]

    def parse_vm_comment(self):
        self.consume("_cmt")
        self.consume("(")

        t = self.peek()
        self.pos += 1
        comment = t.value

        self.consume(")")
        self.consume(";")

        return ["_cmt", comment]

    def parse_stmt(self):
        t = self.peek()

        if t.value == "when": # case の場合に出現
            return None
        elif t.value == "set":
            return self.parse_set()
        elif t.value == "call":
            return self.parse_call()
        elif t.value == "call_set":
            return self.parse_call_set()
        elif t.value == "return":
            return self.parse_return()
        elif t.value == "while":
            return self.parse_while()
        elif t.value == "case":
            return self.parse_case()
        elif t.value == "_cmt":
            return self.parse_vm_comment()
        else:
            raise Exception("parse error")

    def parse_stmts(self):
        stmts = []

        while self.peek().value != "}":
            stmts.append(self.parse_stmt())

        return stmts

    def parse_top_stmt(self):
        if self.peek().value == "func":
            return self.parse_func()
        else:
            raise Exception("unexpected token")

    def parse_top_stmts(self):
        stmts = []
        while not self.is_end():
            stmts.append(self.parse_top_stmt())

        return stmts

    def parse(self):
        try:
            stmts = self.parse_top_stmts()
        except Exception as e:
            self.dump_state()
            raise e
            
        return ["top_stmts", *stmts]

# --------------------------------

in_file = sys.argv[1]
tokens = read_tokens(in_file)
# p_e(tokens)

parser = Parser(tokens)
tree = parser.parse()
# p_e(tree)

print(to_json(tree))
