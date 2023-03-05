import json
import re
import sys
from pprint import pformat

def puts_e(arg):
    print(arg, file=sys.stderr)

def inspect(arg):
    return pformat(arg, indent=4)

def p_e(arg):
    puts_e(inspect(arg))

# --------------------------------

def read_file(path):
    text = ""
    with open(path) as f:
        for line in f:
            text += line
    return text

def not_yet_impl(k, v):
    return Exception(f"{k} ({v})")

# --------------------------------

g_label_id = 0

def asm_prologue():
    print("  push bp")
    print("  cp sp bp")

def asm_epilogue():
    print("  cp bp sp")
    print("  pop bp")

def to_fn_arg_disp(fn_arg_names, fn_arg_name):
    i = fn_arg_names.index(fn_arg_name)
    return i + 2

def to_lvar_addr(lvar_names, lvar_name):
    i = lvar_names.index(lvar_name)
    return -(i + 1)

# --------------------------------

def _gen_expr_add():
    print("  pop reg_b")
    print("  pop reg_a")
    print("  add_ab")

def _gen_expr_mult():
    print("  pop reg_b")
    print("  pop reg_a")
    print("  mult_ab")

def _gen_expr_eq():
    global g_label_id

    g_label_id += 1
    label_id = g_label_id

    label_end = f"end_eq_{label_id}"
    label_then = f"then_{label_id}"

    print(f"  pop reg_b")
    print(f"  pop reg_a")

    print(f"  compare")
    print(f"  jump_eq {label_then}")

    print(f"  cp 0 reg_a")
    print(f"  jump {label_end}")

    print(f"label {label_then}")
    print(f"  cp 1 reg_a")

    print(f"label {label_end}")

def _gen_expr_neq():
    global g_label_id

    g_label_id += 1
    label_id = g_label_id

    label_end = f"end_neq_{label_id}"
    label_then = f"then_{label_id}"

    print(f"  pop reg_b")
    print(f"  pop reg_a")

    print(f"  compare")
    print(f"  jump_eq {label_then}")

    print(f"  cp 1 reg_a")
    print(f"  jump {label_end}")

    print(f"label {label_then}")
    print(f"  cp 0 reg_a")

    print(f"label {label_end}")

def gen_expr(fn_arg_names, lvar_names, expr):
    if type(expr) == int:
        print(f"  cp {expr} reg_a")
    elif type(expr) == str:
        if expr in fn_arg_names:
            disp = to_fn_arg_disp(fn_arg_names, expr)
            print(f"  cp [bp:{disp}] reg_a")
        elif expr in lvar_names:
            disp = to_lvar_addr(lvar_names, expr)
            print(f"  cp [bp:{disp}] reg_a")
        else:
            raise not_yet_impl("expr", expr)
    elif type(expr) == list:
        _gen_expr_binary(fn_arg_names, lvar_names, expr)
    else:
        raise Exception("expr", expr)

def _gen_expr_binary(fn_arg_names, lvar_names, expr):
    global g_label_id

    operator = expr[0]
    args = expr[1:]

    arg_l = args[0]
    arg_r = args[1]

    gen_expr(fn_arg_names, lvar_names, arg_l)
    print(f"  push reg_a")
    gen_expr(fn_arg_names, lvar_names, arg_r)
    print(f"  push reg_a")

    if operator == "+":
        _gen_expr_add()
    elif operator == "*":
        _gen_expr_mult()
    elif operator == "==":
        _gen_expr_eq()
    elif operator == "!=":
        _gen_expr_neq()
    else:
        raise not_yet_impl("todo", operator)

def _gen_funcall(fn_arg_names, lvar_names, funcall):
    fn_name = funcall[0]
    fn_args = funcall[1:]

    for fn_arg in reversed(fn_args):
        gen_expr(fn_arg_names, lvar_names, fn_arg)
        print(f"  push reg_a")

    gen_vm_comment(f"call  {fn_name}")
    print(f"  call {fn_name}")
    print(f"  add_sp {len(fn_args)}")

def gen_call(fn_arg_names, lvar_names, stmt):
    funcall = stmt[1:]
    _gen_funcall(fn_arg_names, lvar_names, funcall)

def gen_call_set(fn_arg_names, lvar_names, stmt):
    lvar_name = stmt[1]
    funcall = stmt[2]

    _gen_funcall(fn_arg_names, lvar_names, funcall)

    disp = to_lvar_addr(lvar_names, lvar_name)
    print(f"  cp reg_a [bp:{disp}]")

def _gen_set(fn_arg_names, lvar_names, dest, expr):
    gen_expr(fn_arg_names, lvar_names, expr)
    src_val = "reg_a"

    if dest in lvar_names:
        disp = to_lvar_addr(lvar_names, dest)
        print(f"  cp {src_val} [bp:{disp}]")
    else:
        raise not_yet_impl("dest", dest)

def gen_set(fn_arg_names, lvar_names, stmt):
    dest = stmt[1]
    expr = stmt[2]

    _gen_set(fn_arg_names, lvar_names, dest, expr)

def gen_return(_, lvar_names, stmt_rest):
    retval = stmt_rest[0]
    gen_expr([], lvar_names, retval)

def gen_while(fn_arg_names, lvar_names, rest):
    global g_label_id

    cond_expr = rest[0]
    body = rest[1]

    g_label_id += 1
    label_id = g_label_id

    label_begin = f"while_{label_id}"
    label_end = f"end_while_{label_id}"
    label_true = f"true_{label_id}"

    print("")

    print(f"label {label_begin}")

    gen_expr(fn_arg_names, lvar_names, cond_expr)

    print(f"  cp 0 reg_b")
    print(f"  compare")

    print(f"  jump_eq {label_end}")

    gen_stmts(fn_arg_names, lvar_names, body)
    print(f"  jump {label_begin}")
    print(f"label {label_end}")
    print("")

def gen_case(fn_arg_names, lvar_names, when_clauses):
    global g_label_id

    g_label_id += 1
    label_id = g_label_id

    when_idx = -1

    label_end = f"end_case_{label_id}"
    label_when_head = f"when_{label_id}"
    label_end_when_head = f"end_when_{label_id}"

    for when_clause in when_clauses:
        when_idx += 1
        cond = when_clause[0]
        rest = when_clause[1:]
        print(f"  # 条件 {label_id}_{when_idx}: {cond}")

        gen_expr(fn_arg_names, lvar_names, cond)

        print(f"  cp 0 reg_b")
        print(f"  compare")
        print(f"  jump_eq {label_end_when_head}_{when_idx}")

        gen_stmts(fn_arg_names, lvar_names, rest)

        print(f"  jump {label_end}")

        print(f"label {label_end_when_head}_{when_idx}")

    print(f"label {label_end}")

def gen_vm_comment(comment):
    print("  _cmt " + comment.replace(" ", "~"))

def gen_debug(comment):
    print("  _debug")

def gen_stmt(fn_arg_names, lvar_names, stmt):
    stmt_head = stmt[0]
    stmt_rest = stmt[1:]

    if stmt_head == "call":
        gen_call(fn_arg_names, lvar_names, stmt)
    elif stmt_head == "call_set":
        gen_call_set(fn_arg_names, lvar_names, stmt)
    elif stmt_head == "set":
        gen_set(fn_arg_names, lvar_names, stmt)
    elif stmt_head == "return":
        gen_return(fn_arg_names, lvar_names, stmt_rest)
    elif stmt_head == "case":
        gen_case(fn_arg_names, lvar_names, stmt_rest)
    elif stmt_head == "while":
        gen_while(fn_arg_names, lvar_names, stmt_rest)
    elif stmt_head == "_cmt":
        gen_vm_comment(stmt_rest[0])
    elif stmt_head == "_debug":
        gen_debug()
    else:
        raise not_yet_impl("stmt_head", stmt_head)

def gen_stmts(fn_arg_names, lvar_names, stmts):
    for stmt in stmts:
        gen_stmt(fn_arg_names, lvar_names, stmt)

def gen_var(fn_arg_names, lvar_names, stmt):
    print("  sub_sp 1")
    if len(stmt) == 3:
        dest = stmt[1]
        expr = stmt[2]
        _gen_set(fn_arg_names, lvar_names, dest, expr)

def gen_func_def(rest):
    fn_name = rest[0]
    fn_arg_names = rest[1]
    body = rest[2]

    print("")
    print(f"label {fn_name}")
    asm_prologue()

    print("")
    print("  # 関数の処理本体")

    lvar_names = []

    for stmt in body:
        stmt_head = stmt[0]
        stmt_rest = stmt[1:]

        if stmt_head == "var":
            lvar_names.append(stmt_rest[0])
            gen_var(fn_arg_names, lvar_names, stmt)
        else:
            gen_stmt(fn_arg_names, lvar_names, stmt)

    print("")
    asm_epilogue()
    print("  ret")

def gen_top_stmts(rest):
    for stmt in rest:
        stmt_head = stmt[0]
        stmt_rest = stmt[1:]

        if stmt_head == "func":
            gen_func_def(stmt_rest)
        else:
            raise not_yet_impl("stmt_head", stmt_head)

def gen_builtin_set_vram():
    print(f"")
    print(f"label set_vram")
    asm_prologue()

    print(f"  set_vram [bp:2] [bp:3]") # vram_addr value

    asm_epilogue()
    print(f"  ret")

def gen_builtin_get_vram():
    print(f"")
    print(f"label get_vram")
    asm_prologue()

    print(f"  get_vram [bp:2] reg_a") # vram_addr dest

    asm_epilogue()
    print(f"  ret")

def codegen(tree):
    print("  call main")
    print("  exit")

    head = tree[0]
    rest = tree[1:]

    gen_top_stmts(rest)

    print("#>builtins")
    gen_builtin_set_vram()
    gen_builtin_get_vram()
    print("#<builtins")

# --------------------------------

src = read_file(sys.argv[1])

tree = json.loads(src)

codegen(tree)
