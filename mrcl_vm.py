import json
import os
import re
import sys

from lib.common import file_read, p_e, puts_e

COLOR_RESET = "\033[m"
COLOR_RED   = "\033[0;31m"
COLOR_BLUE  = "\033[0;34m"

class Memory:
    MAIN_DUMP_WIDTH = 10

    def __init__(self, stack_size):
        self.main = []
        self.stack = [0] * stack_size
        self.vram = [0] * 50

    def dump_main(self, pc):
        work_insns = []
        i = 0
        while i < len(self.main):
            if pc - self.MAIN_DUMP_WIDTH < i < pc + self.MAIN_DUMP_WIDTH:
                insn = self.main[i]
                work_insns.append({ "addr": i, "insn": insn })
            i += 1

        lines = []
        for work_insn in work_insns:
            head = None
            if work_insn["addr"] == pc:
                head = "pc =>"
            else:
                head = "     "

            opcode = work_insn["insn"][0]

            color = None
            if opcode in ["exit", "call", "ret", "jmp", "je"]:
                color = COLOR_RED
            elif opcode in ["_cmt", "_debug"]:
                color = COLOR_BLUE
            else:
                color = ""

            indent = None
            if opcode == "label":
              indent = ""
            else:
              indent = "  "

            lines.append(
                "{} {:0=2} {}{}{}{}".format(
                    head,
                    work_insn["addr"],
                    color,
                    indent,
                    work_insn["insn"],
                    COLOR_RESET
                )
            )
        return "\n".join(lines)

    def dump_stack(self, sp, bp):
        lines = []
        i = 0
        while i < len(self.stack):
            x = self.stack[i]
            addr = i

            head = None
            if addr == sp:
                if sp == bp:
                    head = "sp bp => "
                else:
                    head = "sp    => "
            elif addr == bp:
                head = "   bp => "
            else:
                head = "         "

            if sp - 8 <= addr <= sp + 8:
                lines.append(head + f"{i} {x}")
            i += 1

        return "\n".join(lines)

    def dump_vram(self):
        lines = []
        y = 0
        while y < 5:
            x = 0
            cols = []
            while x < 5:
                i = y * 5 + x
                val = self.vram[i]
                if val == 1:
                    cols.append("@")
                else:
                    cols.append(".")
                x += 1
            lines.append("".join(cols))
            y += 1

        return "\n".join(lines)

class Vm:
    FLAG_TRUE = 1
    FLAG_FALSE = 0

    def __init__(self, mem, stack_size):
        self.mem = mem

        self.pc = 0
        self.reg_a = 0
        self.reg_b = 0
        self.zf = self.FLAG_FALSE
        self.sp = stack_size - 1
        self.bp = stack_size - 1
        self.step = 0
        self.debug = False

    # TODO
    #   def test?
    #     ENV.key?("TEST")
    #   end

    def set_sp(self, addr):
        if addr < 0:
            raise Exception("stack overflow")

        self.sp = addr

    def load_program_file(self, path):
        src = file_read(path)
        lines = src.split("\n")
        insns = []
        for line in lines:
            if line.startswith("["):
                insns.append(json.loads(line))
        self.load_program(insns)

    def load_program(self, insns):
        self.mem.main = insns

    def execute(self):
        insn = self.mem.main[self.pc]
        opcode = insn[0]

        if opcode == "exit":
            return True
        elif opcode == "mov":
            self.insn_mov()
            self.pc += 1
        elif opcode == "add":
            self.insn_add()
            self.pc += 1
        elif opcode == "mul":
            self.insn_mul()
            self.pc += 1
        elif opcode == "cmp":
            self.insn_cmp()
            self.pc += 1
        elif opcode == "label":
            self.pc += 1
        elif opcode == "jmp":
            self.insn_jmp()
        elif opcode == "je":
            self.insn_je()
        elif opcode == "call":
            self.insn_call()
        elif opcode == "ret":
            self.insn_ret()
        elif opcode == "push":
            self.insn_push()
            self.pc += 1
        elif opcode == "pop":
            self.insn_pop()
            self.pc += 1
        elif opcode == "set_vram":
            self.insn_set_vram()
            self.pc += 1
        elif opcode == "get_vram":
            self.insn_get_vram()
            self.pc += 1
        elif opcode == "_cmt":
            self.pc += 1

        # TODO
        #     when "_debug"   then insn__debug()   ; @pc += 1

        else:
            raise Exception(f"unknown opcode ({opcode})")

        return False

    def start(self):
        # TODO if not test?
        self.dump()
        input("Press enter key to start")
        # end if

        while True:
            self.step += 1

            do_exit = self.execute()
            if do_exit:
                return

            # TODO if not test?
            if os.getenv("STEP") != None or self.debug:
                self.dump()
                input()
            else:
                if self.step % 10 == 0:
                    self.dump()
            # end if

    def dump_reg(self):
        return f"reg_a({self.reg_a}) reg_b({self.reg_b})"

    def dump(self):
        print(f"""
================================
{self.step}: {self.dump_reg()} zf({self.zf})
---- memory (main) ----
{self.mem.dump_main(self.pc)}
---- memory (stack) ----
{self.mem.dump_stack(self.sp, self.bp)}
---- memory (vram) ----
{self.mem.dump_vram()}
        """)

    def is_mem_ref(self, arg):
        return re.match(r"mem:", arg)

    def calc_indirect_addr(self, mem_str):
        _, base_str, disp_str = mem_str.split(":")
        base = self.get_val(base_str)
        return base + int(disp_str)

    def get_val(self, arg):
        if type(arg) == int:
            return arg
        elif type(arg) == str:
            if arg == "reg_a":
                return self.reg_a
            elif arg == "reg_b":
                return self.reg_b
            elif arg == "bp":
                return self.bp
            elif arg == "sp":
                return self.sp
            elif self.is_mem_ref(arg):
                addr = self.calc_indirect_addr(arg)
                return self.mem.stack[addr]
            else:
                raise Exception(f"unsupported ({arg})")
        else:
            raise Exception(f"unsupported ({arg})")

    def set_val(self, dest, val):
        if dest == "reg_a":
            self.reg_a = val
        elif dest == "reg_b":
            self.reg_b = val
        elif dest == "bp":
            self.bp = val
        elif dest == "sp":
            self.set_sp(val)
        elif self.is_mem_ref(dest):
            addr = self.calc_indirect_addr(dest)
            self.mem.stack[addr] = val
        else:
            raise Exception(f"unsupported ({dest})")

    def insn_add(self):
        arg_dest = self.mem.main[self.pc][1]
        arg_src = self.mem.main[self.pc][2]

        dest_val = self.get_val(arg_dest)
        src_val = self.get_val(arg_src)

        self.set_val(arg_dest, dest_val + src_val)

    def insn_mul(self):
        arg_src = self.mem.main[self.pc][1]

        dest_val = self.reg_a
        src_val = self.get_val(arg_src)

        self.set_val("reg_a", dest_val * src_val)

    def insn_mov(self):
        arg_dest = self.mem.main[self.pc][1]
        arg_src  = self.mem.main[self.pc][2]

        src_val = self.get_val(arg_src)
        self.set_val(arg_dest, src_val)
    def insn_cmp(self):
        if self.reg_a == self.reg_b:
            self.zf = self.FLAG_TRUE
        else:
            self.zf = self.FLAG_FALSE

    def insn_jmp(self):
        jump_dest = self.mem.main[self.pc][1]
        self.pc = jump_dest

    def insn_je(self):
        if self.zf == self.FLAG_TRUE:
            jump_dest = self.mem.main[self.pc][1]
            self.pc = jump_dest
        else:
            self.pc += 1

    def insn_call(self):
        self.set_sp(self.sp - 1)
        self.mem.stack[self.sp] = self.pc + 1
        next_addr = self.mem.main[self.pc][1]
        self.pc = next_addr

    def insn_ret(self):
        ret_addr = self.mem.stack[self.sp]
        self.pc = ret_addr
        self.set_sp(self.sp + 1)

    def insn_push(self):
        arg = self.mem.main[self.pc][1]

        val_to_push = self.get_val(arg)

        self.set_sp(self.sp - 1)
        self.mem.stack[self.sp] = val_to_push

    def insn_pop(self):
        arg = self.mem.main[self.pc][1]
        val = self.mem.stack[self.sp]

        self.set_val(arg, val)

        self.set_sp(self.sp + 1)

    def insn_set_vram(self):
        arg_vram = self.mem.main[self.pc][1]
        arg_val = self.mem.main[self.pc][2]

        src_val = self.get_val(arg_val)

        if type(arg_vram) == int:
            self.mem.vram[arg_vram] = src_val
        elif self.is_mem_ref(arg_vram):
            stack_addr = self.calc_indirect_addr(arg_vram)
            vram_addr = self.mem.stack[stack_addr]
            self.mem.vram[vram_addr] = src_val
        else:
          raise Exception(f"unsupported ({arg_vram})")

    def insn_get_vram(self):
        arg_vram = self.mem.main[self.pc][1]
        arg_dest = self.mem.main[self.pc][2]

        vram_addr = self.get_val(arg_vram)
        val = self.mem.vram[vram_addr]

        self.set_val(arg_dest, val)

    # TODO
    #   def insn__debug
    #     @debug = true
    #   end

if __name__ == "__main__":
    exe_file = sys.argv[1]
    print(exe_file)

    stack_size = 50
    mem = Memory(stack_size)
    vm = Vm(mem, stack_size)
    vm.load_program_file(exe_file)

    vm.start()
    vm.dump()
    puts_e("exit")
