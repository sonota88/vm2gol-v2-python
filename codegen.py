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

def concat_alines(a, b):
    for x in b:
        a.append(x)

    return a

def not_yet_impl(k, v):
    return Exception(f"{k} ({v})")

# --------------------------------

g_label_id = 0

def to_fn_arg_addr(fn_arg_names, fn_arg_name):
    i = fn_arg_names.index(fn_arg_name)
    return f"[bp+{i+2}]"

def to_lvar_addr(lvar_names, lvar_name):
    i = lvar_names.index(lvar_name)
    return f"[bp-{i+1}]"

def _match_vram_addr(s):
    pattern = r"vram\[(\d+)\]"

    if re.match(pattern, s):
        m = re.match(pattern, s)
        return m.group(1)
    else:
        return None

def _match_vram_ref(s):
    pattern = r"vram\[([a-z_][a-z0-9_]*)\]"

    if re.match(pattern, s):
        m = re.match(pattern, s)
        return m.group(1)
    else:
        return None

# --------------------------------

def _codegen_exp_push(fn_arg_names, lvar_names, val):
    alines = []
    push_arg = None

    if type(val) == int:
        push_arg = val
    elif type(val) == str:
        if val in fn_arg_names:
            push_arg = to_fn_arg_addr(fn_arg_names, val)
        elif val in lvar_names:
            push_arg = to_lvar_addr(lvar_names, val)
        else:
            raise not_yet_impl("todo", val)
    elif type(val) == list:
        alines = concat_alines(
            alines,
            codegen_exp(fn_arg_names, lvar_names, val)
        )
        push_arg = "reg_a"
    else:
        raise not_yet_impl("todo", val)

    alines.append(f"  push {push_arg}")

    return alines

def _codegen_exp_add():
    alines = []

    alines.append("  pop reg_b")
    alines.append("  pop reg_a")
    alines.append("  add_ab")

    return alines

def _codegen_exp_mult():
    alines = []

    alines.append("  pop reg_b")
    alines.append("  pop reg_a")
    alines.append("  mult_ab")

    return alines

def _codegen_exp_eq():
    global g_label_id

    alines = []

    g_label_id += 1
    label_id = g_label_id

    label_end = f"end_eq_{label_id}"
    label_then = f"then_{label_id}"

    alines.append(f"  pop reg_b")
    alines.append(f"  pop reg_a")

    alines.append(f"  compare")
    alines.append(f"  jump_eq {label_then}")

    alines.append(f"  set_reg_a 0")
    alines.append(f"  jump {label_end}")

    alines.append(f"label {label_then}")
    alines.append(f"  set_reg_a 1")

    alines.append(f"label {label_end}")

    return alines

def _codegen_exp_neq():
    global g_label_id

    alines = []

    g_label_id += 1
    label_id = g_label_id

    label_end = f"end_neq_{label_id}"
    label_then = f"then_{label_id}"

    alines.append(f"  pop reg_b")
    alines.append(f"  pop reg_a")

    alines.append(f"  compare")
    alines.append(f"  jump_eq {label_then}")

    alines.append(f"  set_reg_a 1")
    alines.append(f"  jump {label_end}")

    alines.append(f"label {label_then}")
    alines.append(f"  set_reg_a 0")

    alines.append(f"label {label_end}")

    return alines

def codegen_exp(fn_arg_names, lvar_names, exp):
    global g_label_id

    alines = []
    operator = exp[0]
    args = exp[1:]

    arg_l = args[0]
    arg_r = args[1]

    alines = concat_alines(
        alines,
        _codegen_exp_push(fn_arg_names, lvar_names, arg_l)
    )

    alines = concat_alines(
        alines,
        _codegen_exp_push(fn_arg_names, lvar_names, arg_r)
    )

    if operator == "+":
        alines = concat_alines(alines, _codegen_exp_add())
    elif operator == "*":
        alines = concat_alines(alines, _codegen_exp_mult())
    elif operator == "eq":
        alines = concat_alines(alines, _codegen_exp_eq())
    elif operator == "neq":
        alines = concat_alines(alines, _codegen_exp_neq())
    else:
        raise not_yet_impl("todo", operator)

    return alines

def _codegen_call_push_fn_arg(fn_arg_names, lvar_names, fn_arg):
    alines = []

    if type(fn_arg) == int:
        alines.append(f"  push {fn_arg}")
    elif type(fn_arg) == str:
        if fn_arg in fn_arg_names:
            addr = to_fn_arg_addr(fn_arg_names, fn_arg)
            alines.append(f"  push {addr}")
        elif fn_arg in lvar_names:
            addr = to_lvar_addr(lvar_names, fn_arg)
            alines.append(f"  push {addr}")
        else:
            raise not_yet_impl("fn_arg", fn_arg)
    else:
        raise not_yet_impl("fn_arg", fn_arg)

    return alines

def codegen_call(fn_arg_names, lvar_names, stmt_rest):
    alines = []

    fn_name = stmt_rest[0]
    fn_args = stmt_rest[1:] or []

    for fn_arg in reversed(fn_args):
        alines = concat_alines(
            alines,
            _codegen_call_push_fn_arg(fn_arg_names, lvar_names, fn_arg)
        )

    alines = concat_alines(
        alines,
        codegen_comment(f"call  {fn_name}")
    )
    alines.append(f"  call {fn_name}")
    alines.append(f"  add_sp {len(fn_args)}")

    return alines

def codegen_call_set(fn_arg_names, lvar_names, stmt_rest):
    alines = []

    lvar_name = stmt_rest[0]
    fn_temp = stmt_rest[1]

    fn_name = fn_temp[0]
    fn_args = fn_temp[1:]

    for fn_arg in reversed(fn_args):
        alines = concat_alines(
            alines,
            _codegen_call_push_fn_arg(fn_arg_names, lvar_names, fn_arg)
        )

    alines = concat_alines(
        alines,
        codegen_comment(f"call_set  {fn_name}")
    )
    alines.append(f"  call {fn_name}")
    alines.append(f"  add_sp {len(fn_args)}")

    lvar_addr = to_lvar_addr(lvar_names, lvar_name)
    alines.append(f"  cp reg_a {lvar_addr}")
    
    return alines

def codegen_set(fn_arg_names, lvar_names, rest):
    alines = []
    dest = rest[0]
    exp = rest[1]

    src_val = None

    if type(exp) == int:
        src_val = exp
    elif type(exp) == list:
        alines = concat_alines(
            alines,
            codegen_exp(fn_arg_names, lvar_names, exp)
        )
        src_val = "reg_a"
    elif type(exp) == str:
        if exp in fn_arg_names:
            src_val = to_fn_arg_addr(fn_arg_names, exp)
        elif exp in lvar_names:
            src_val = to_lvar_addr(lvar_names, exp)
        elif _match_vram_addr(exp):
            vram_addr = _match_vram_addr(exp)
            alines.append(f"  get_vram {vram_addr} reg_a")
            src_val = "reg_a"
        elif _match_vram_ref(exp):
            var_name = _match_vram_ref(exp)
            if var_name in lvar_names:
                lvar_addr = to_lvar_addr(lvar_names, var_name)
                alines.append(f"  get_vram {lvar_addr} reg_a")
            else:
                raise not_yet_impl("exp", exp)

            src_val = "reg_a"
        else:
            raise not_yet_impl("exp", exp)
    else:
        raise not_yet_impl("exp", exp)

    if _match_vram_addr(dest):
        vram_addr = _match_vram_addr(dest)
        alines.append(f"  set_vram {vram_addr} {src_val}")
    elif _match_vram_ref(dest):
        vram_ref = _match_vram_ref(dest)
        if vram_ref in lvar_names:
            addr = to_lvar_addr(lvar_names, vram_ref)
            alines.append(f"  set_vram {addr} {src_val}")
        else:
            raise not_yet_impl("dest", dest)
    elif dest in lvar_names:
        lvar_addr = to_lvar_addr(lvar_names, dest)
        alines.append(f"  cp {src_val} {lvar_addr}")
    else:
        raise not_yet_impl("dest", dest)

    return alines

def codegen_return(_, lvar_names, stmt_rest):
    alines = []

    retval = stmt_rest[0]

    if type(retval) == int:
        alines.append(f"  set_reg_a {retval}")
    elif type(retval) == str:
        if _match_vram_ref(retval):
            var_name = _match_vram_ref(retval)
            if var_name in lvar_names:
                lvar_addr = to_lvar_addr(lvar_names, var_name)
                alines.append(f"  get_vram {lvar_addr} reg_a")
            else:
                raise not_yet_impl("retval", retval)
        elif retval in lvar_names:
            lvar_addr = to_lvar_addr(lvar_names, retval)
            alines.append(f"  cp {lvar_addr} reg_a")
        else:
            raise not_yet_impl("retval", retval)

    else:
        raise not_yet_impl("retval", retval)

    return alines

def codegen_while(fn_arg_names, lvar_names, rest):
    global g_label_id
    alines = []
    cond_exp = rest[0]
    body = rest[1]

    g_label_id += 1
    label_id = g_label_id

    label_begin = f"while_{label_id}"
    label_end = f"end_while_{label_id}"
    label_true = f"true_{label_id}"

    alines.append("")

    alines.append(f"label {label_begin}")

    alines = concat_alines(
        alines,
        codegen_exp(fn_arg_names, lvar_names, cond_exp)
    )

    alines.append(f"  set_reg_b 1")
    alines.append(f"  compare")

    alines.append(f"  jump_eq {label_true}")

    alines.append(f"  jump {label_end}")

    alines.append(f"label {label_true}")

    alines = concat_alines(
        alines,
        codegen_stmts(fn_arg_names, lvar_names, body)
    )
    alines.append(f"  jump {label_begin}")
    alines.append(f"label {label_end}")
    alines.append("")

    return alines

def codegen_case(fn_arg_names, lvar_names, when_blocks):
    global g_label_id

    alines = []
    g_label_id += 1
    label_id = g_label_id

    when_idx = -1
    then_bodies = []

    label_end = f"end_case_{label_id}"
    label_when_head = f"when_{label_id}"

    for when_block in when_blocks:
        when_idx += 1
        cond = when_block[0]
        rest = when_block[1:]
        cond_head = cond[0]
        cond_rest = cond[1:]
        alines.append(f"  # 条件 {label_id}_{when_idx}: {cond}")

        if cond_head == "eq":
            alines = concat_alines(
                alines,
                codegen_exp(fn_arg_names, lvar_names, cond)
            )

            alines.append(f"  set_reg_b 1")
            alines.append(f"  compare")
            alines.append(f"  jump_eq {label_when_head}_{when_idx}")

            then_alines = [f"label {label_when_head}_{when_idx}"]
            then_alines = concat_alines(
                then_alines,
                codegen_stmts(fn_arg_names, lvar_names, rest)
            )
            then_alines.append(f"  jump {label_end}")
            then_bodies.append(then_alines)
        else:
            raise not_yet_impl("cond_head", cond_head)

    alines.append(f"  jump {label_end}")

    for then_alines in then_bodies:
        alines = concat_alines(
            alines,
            then_alines
        )

    alines.append(f"label {label_end}")

    return alines

def codegen_comment(comment):
    return ["  _cmt " + comment.replace(" ", "~")]

def codegen_stmt(fn_arg_names, lvar_names, stmt):
    alines = []

    stmt_head = stmt[0]
    stmt_rest = stmt[1:]

    if stmt_head == "call":
        alines = concat_alines(
            alines,
            codegen_call(fn_arg_names, lvar_names, stmt_rest)
        )
    elif stmt_head == "call_set":
        alines = concat_alines(
            alines,
            codegen_call_set(fn_arg_names, lvar_names, stmt_rest)
        )
    elif stmt_head == "var":
        lvar_names.append(stmt_rest[0])
        alines.append("  sub_sp 1")
        if len(stmt_rest) == 2:
            alines = concat_alines(
                alines,
                codegen_set(fn_arg_names, lvar_names, stmt_rest)
            )
    elif stmt_head == "set":
        alines = concat_alines(
            alines,
            codegen_set(fn_arg_names, lvar_names, stmt_rest)
        )

    elif stmt_head == "return":
        alines = concat_alines(
            alines,
            codegen_return(fn_arg_names, lvar_names, stmt_rest)
        )
    elif stmt_head == "case":
        alines = concat_alines(
            alines,
            codegen_case(fn_arg_names, lvar_names, stmt_rest)
        )
    elif stmt_head == "while":
        alines = concat_alines(
            alines,
            codegen_while(fn_arg_names, lvar_names, stmt_rest)
        )
    elif stmt_head == "_cmt":
        alines = concat_alines(
            alines,
            codegen_comment(stmt_rest[0])
        )
    else:
        raise not_yet_impl("stmt_head", stmt_head)

    return alines

def codegen_stmts(fn_arg_names, lvar_names, stmts):
    alines = []

    for stmt in stmts:
        alines = concat_alines(
            alines,
            codegen_stmt(fn_arg_names, lvar_names, stmt)
        )

    return alines

def codegen_func_def(rest):
    alines = []

    fn_name = rest[0]
    fn_arg_names = rest[1]
    body = rest[2]

    alines.append("")
    alines.append(f"label {fn_name}")
    alines.append("  push bp")
    alines.append("  cp sp bp")

    alines.append("")
    alines.append("  # 関数の処理本体")

    lvar_names = []

    alines = concat_alines(
        alines,
        codegen_stmts(fn_arg_names, lvar_names, body)
    )

    alines.append("")
    alines.append("  cp bp sp")
    alines.append("  pop bp")
    alines.append("  ret")

    return alines

def codegen_top_stmts(rest):
    alines = []

    for stmt in rest:
        stmt_head = stmt[0]
        stmt_rest = stmt[1:]

        if stmt_head == "func":
            alines = concat_alines(
                alines,
                codegen_func_def(stmt_rest)
            )
        elif stmt_head == "_cmt":
            alines = concat_alines(
                alines,
                codegen_comment(stmt_rest[0])
            )
        else:
            raise not_yet_impl("stmt_head", stmt_head)

    return alines

def codegen(tree):
    alines = []

    alines.append("  call main")
    alines.append("  exit")

    head = tree[0]
    rest = tree[1:]

    alines = concat_alines(
        alines,
        codegen_top_stmts(rest)
    )

    return alines

# --------------------------------

src = read_file(sys.argv[1])

tree = json.loads(src)

alines = codegen(tree)

for aline in alines:
    print(aline)
