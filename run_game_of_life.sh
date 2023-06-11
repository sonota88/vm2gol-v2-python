#!/bin/bash

if [ -e vm2gol-v2 ]; then
  : # ok
else
  cat <<__MSG >&2
To use assembler and virtual machine, please clone the following repository:
git clone --branch 63 https://github.com/sonota88/vm2gol-v2.git
__MSG
  exit 1
fi

asm_file=game_of_life.asm
exe_file=game_of_life.exe.txt

# compile
cat test_common/compile/27.mrcl \
  | python3 mrcl_lexer.py \
  | python3 mrcl_parser.py \
  | python3 mrcl_codegen.py \
  > $asm_file

# assemble
ruby vm2gol-v2/vgasm.rb $asm_file \
  > $exe_file

# run on VM
ruby vm2gol-v2/vgvm.rb $exe_file

# or to run step by step
# STEP= ruby vm2gol-v2/vgvm.rb $exe_file
