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

def to_fn_arg_addr(fn_arg_names, fn_arg_name):
    i = fn_arg_names.index(fn_arg_name)
    return f"[bp:{i+2}]"

def to_lvar_addr(lvar_names, lvar_name):
    i = lvar_names.index(lvar_name)
    return f"[bp:-{i+1}]"

# --------------------------------

def _codegen_expr_add():
    print("  pop reg_b")
    print("  pop reg_a")
    print("  add_ab")

def _codegen_expr_mult():
    print("  pop reg_b")
    print("  pop reg_a")
    print("  mult_ab")

def _codegen_expr_eq():
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

def _codegen_expr_neq():
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

def codegen_expr(fn_arg_names, lvar_names, expr):
    if type(expr) == int:
        print(f"  cp {expr} reg_a")
    elif type(expr) == str:
        if expr in fn_arg_names:
            cp_src = to_fn_arg_addr(fn_arg_names, expr)
            print(f"  cp {cp_src} reg_a")
        elif expr in lvar_names:
            cp_src = to_lvar_addr(lvar_names, expr)
            print(f"  cp {cp_src} reg_a")
        else:
            raise not_yet_impl("expr", expr)
    elif type(expr) == list:
        _codegen_expr_binary(fn_arg_names, lvar_names, expr)
    else:
        raise Exception("expr", expr)

def _codegen_expr_binary(fn_arg_names, lvar_names, expr):
    global g_label_id

    operator = expr[0]
    args = expr[1:]

    arg_l = args[0]
    arg_r = args[1]

    codegen_expr(fn_arg_names, lvar_names, arg_l)
    print(f"  push reg_a")
    codegen_expr(fn_arg_names, lvar_names, arg_r)
    print(f"  push reg_a")

    if operator == "+":
        _codegen_expr_add()
    elif operator == "*":
        _codegen_expr_mult()
    elif operator == "eq":
        _codegen_expr_eq()
    elif operator == "neq":
        _codegen_expr_neq()
    else:
        raise not_yet_impl("todo", operator)

def codegen_call(fn_arg_names, lvar_names, stmt_rest):
    fn_name = stmt_rest[0]
    fn_args = stmt_rest[1:] or []

    for fn_arg in reversed(fn_args):
        codegen_expr(fn_arg_names, lvar_names, fn_arg)
        print(f"  push reg_a")

    codegen_vm_comment(f"call  {fn_name}")
    print(f"  call {fn_name}")
    print(f"  add_sp {len(fn_args)}")

def codegen_call_set(fn_arg_names, lvar_names, stmt_rest):
    lvar_name = stmt_rest[0]
    fn_temp = stmt_rest[1]

    codegen_call(fn_arg_names, lvar_names, fn_temp)

    lvar_addr = to_lvar_addr(lvar_names, lvar_name)
    print(f"  cp reg_a {lvar_addr}")

def codegen_set(fn_arg_names, lvar_names, rest):
    dest = rest[0]
    expr = rest[1]

    codegen_expr(fn_arg_names, lvar_names, expr)
    src_val = "reg_a"

    if dest in lvar_names:
        lvar_addr = to_lvar_addr(lvar_names, dest)
        print(f"  cp {src_val} {lvar_addr}")
    else:
        raise not_yet_impl("dest", dest)

def codegen_return(_, lvar_names, stmt_rest):
    retval = stmt_rest[0]
    codegen_expr([], lvar_names, retval)

def codegen_while(fn_arg_names, lvar_names, rest):
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

    codegen_expr(fn_arg_names, lvar_names, cond_expr)

    print(f"  cp 1 reg_b")
    print(f"  compare")

    print(f"  jump_eq {label_true}")

    print(f"  jump {label_end}")

    print(f"label {label_true}")

    codegen_stmts(fn_arg_names, lvar_names, body)
    print(f"  jump {label_begin}")
    print(f"label {label_end}")
    print("")

def codegen_case(fn_arg_names, lvar_names, when_clauses):
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

        codegen_expr(fn_arg_names, lvar_names, cond)

        print(f"  cp 1 reg_b")
        print(f"  compare")
        print(f"  jump_eq {label_when_head}_{when_idx}")
        print(f"  jump {label_end_when_head}_{when_idx}")

        print(f"label {label_when_head}_{when_idx}")

        codegen_stmts(fn_arg_names, lvar_names, rest)

        print(f"  jump {label_end}")

        print(f"label {label_end_when_head}_{when_idx}")

    print(f"label {label_end}")

def codegen_vm_comment(comment):
    print("  _cmt " + comment.replace(" ", "~"))

def codegen_stmt(fn_arg_names, lvar_names, stmt):
    stmt_head = stmt[0]
    stmt_rest = stmt[1:]

    if stmt_head == "call":
        codegen_call(fn_arg_names, lvar_names, stmt_rest)
    elif stmt_head == "call_set":
        codegen_call_set(fn_arg_names, lvar_names, stmt_rest)
    elif stmt_head == "set":
        codegen_set(fn_arg_names, lvar_names, stmt_rest)
    elif stmt_head == "return":
        codegen_return(fn_arg_names, lvar_names, stmt_rest)
    elif stmt_head == "case":
        codegen_case(fn_arg_names, lvar_names, stmt_rest)
    elif stmt_head == "while":
        codegen_while(fn_arg_names, lvar_names, stmt_rest)
    elif stmt_head == "_cmt":
        codegen_vm_comment(stmt_rest[0])
    else:
        raise not_yet_impl("stmt_head", stmt_head)

def codegen_stmts(fn_arg_names, lvar_names, stmts):
    for stmt in stmts:
        codegen_stmt(fn_arg_names, lvar_names, stmt)

def codegen_var(fn_arg_names, lvar_names, stmt_rest):
    print("  sub_sp 1")
    if len(stmt_rest) == 2:
        codegen_set(fn_arg_names, lvar_names, stmt_rest)

def codegen_func_def(rest):
    fn_name = rest[0]
    fn_arg_names = rest[1]
    body = rest[2]

    print("")
    print(f"label {fn_name}")
    print("  push bp")
    print("  cp sp bp")

    print("")
    print("  # 関数の処理本体")

    lvar_names = []

    for stmt in body:
        stmt_head = stmt[0]
        stmt_rest = stmt[1:]

        if stmt_head == "var":
            lvar_names.append(stmt_rest[0])
            codegen_var(fn_arg_names, lvar_names, stmt_rest)
        else:
            codegen_stmt(fn_arg_names, lvar_names, stmt)

    print("")
    print("  cp bp sp")
    print("  pop bp")
    print("  ret")

def codegen_top_stmts(rest):
    for stmt in rest:
        stmt_head = stmt[0]
        stmt_rest = stmt[1:]

        if stmt_head == "func":
            codegen_func_def(stmt_rest)
        elif stmt_head == "_cmt":
            codegen_vm_comment(stmt_rest[0])
        else:
            raise not_yet_impl("stmt_head", stmt_head)

def codegen_builtin_set_vram():
    print(f"")
    print(f"label set_vram")
    print(f"  push bp")
    print(f"  cp sp bp")

    print(f"  set_vram [bp:2] [bp:3]") # vram_addr value

    print(f"  cp bp sp")
    print(f"  pop bp")
    print(f"  ret")

def codegen_builtin_get_vram():
    print(f"")
    print(f"label get_vram")
    print(f"  push bp")
    print(f"  cp sp bp")

    print(f"  get_vram [bp:2] reg_a") # vram_addr dest

    print(f"  cp bp sp")
    print(f"  pop bp")
    print(f"  ret")

def codegen(tree):
    print("  call main")
    print("  exit")

    head = tree[0]
    rest = tree[1:]

    codegen_top_stmts(rest)

    print("#>builtins")
    codegen_builtin_set_vram()
    codegen_builtin_get_vram()
    print("#<builtins")

# --------------------------------

src = read_file(sys.argv[1])

tree = json.loads(src)

codegen(tree)
