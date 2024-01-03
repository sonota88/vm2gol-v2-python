#!/bin/bash

asm_file=z_game_of_life.asm
exe_file=z_game_of_life.exe.txt

# compile
cat test_common/compile/27.mrcl \
  | python3 mrcl_lexer.py \
  | python3 mrcl_parser.py \
  | python3 mrcl_codegen.py \
  > $asm_file

# assemble
cat $asm_file | python3 mrcl_asm.py \
  > $exe_file

# run on VM
python3 mrcl_vm.py $exe_file

# or to run step by step
# STEP= python3 mrcl_vm.py $exe_file
