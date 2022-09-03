#!/bin/bash

print_project_dir() {
  local real_path="$(readlink --canonicalize "$0")"
  (
    cd "$(dirname "$real_path")"
    pwd
  )
}

export PROJECT_DIR="$(print_project_dir)"
export TEST_DIR="${PROJECT_DIR}/test"
export TEMP_DIR="${PROJECT_DIR}/z_tmp"
export TEMP_TOKENS_FILE="${TEMP_DIR}/test.tokens.txt"
export TEMP_VGT_FILE="${TEMP_DIR}/test.vgt.json"
export TEMP_VGA_FILE="${TEMP_DIR}/test.vga.txt"

ERRS=""

test_nn() {
  local nn="$1"; shift

  echo "test_${nn}"

  local exp_file="${TEST_DIR}/compile/exp_${nn}.vga.txt"

  python mrcl_lexer.py ${TEST_DIR}/compile/${nn}.vg.txt > $TEMP_TOKENS_FILE
  python mrcl_parser.py $TEMP_TOKENS_FILE > $TEMP_VGT_FILE
  if [ $? -ne 0 ]; then
    ERRS="${ERRS},${nn}_parse"
    return
  fi

  python mrcl_codegen.py $TEMP_VGT_FILE | tr "'" '"'> $TEMP_VGA_FILE
  if [ $? -ne 0 ]; then
    ERRS="${ERRS},${nn}_codegen"
    return
  fi

  ruby test/diff.rb asm $exp_file $TEMP_VGA_FILE
  if [ $? -ne 0 ]; then
    # meld $exp_file $TEMP_VGA_FILE &

    ERRS="${ERRS},${nn}_diff"
    return
  fi
}

# --------------------------------

mkdir -p z_tmp

ns=

if [ $# -eq 1 ]; then
  ns="$1"
else
  ns="$(seq 1 11)"
fi

for n in $ns; do
  test_nn $(printf "%02d" $n)
done

if [ "$ERRS" = "" ]; then
  echo "ok"
else
  echo "----"
  echo "FAILED: ${ERRS}"
fi
