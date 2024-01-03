import json
import re

from lib.common import read_stdin_all, p_e

def parse(src):
    alines = []
    for line in src.split("\n"):
        stripped = line.strip()
        if stripped != "":
            if not stripped.startswith("#"):
                alines.append(stripped.split())
    return alines

def create_label_addr_map(alines):
    map = {}
    addr = 1

    for aline in alines:
        head = aline[0]
        rest = aline[1:]
        if head == "label":
            name = rest[0]
            map[name] = addr
        addr += 1

    return map

def to_machine_code_operand(arg):
    if re.match(r"^\[(.+)\]$", arg):
        m = re.match(r"^\[(.+)\]$", arg)
        return "mem:" + m.group(1)
    elif re.match(r"^-?\d+$", arg):
        return int(arg)
    else:
        return arg

# --------------------------------

src = read_stdin_all()
asm_insns = parse(src)
label_addr_map = create_label_addr_map(asm_insns)

for asm_insn in asm_insns:
    head = asm_insn[0]
    rest = asm_insn[1:]

    insn = [head]
    if head == "label":
        insn.append(rest[0])
    elif head == "jmp" or head == "je" or head == "call":
        label_name = rest[0]

        if label_name in label_addr_map:
            insn.append(label_addr_map[label_name])
        else:
            raise Exception(f"label not found ({label_name})")
    else:
        for arg in rest:
            insn.append(to_machine_code_operand(arg))

    print(json.dumps(insn))
