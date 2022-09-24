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

RUNNER_CMD=python

run_lex() {
  local infile="$1"; shift

  $RUNNER_CMD mrcl_lexer.py $infile
}

run_parse() {
  local infile="$1"; shift

  $RUNNER_CMD mrcl_parser.py $infile
}

run_codegen() {
  local infile="$1"; shift

  $RUNNER_CMD mrcl_codegen.py $infile
}

# --------------------------------

setup() {
  mkdir -p ./z_tmp
}

postproc() {
  local stage="$1"; shift

  if [ "$ERRS" = "" ]; then
    echo "${stage}: ok"
  else
    echo "----"
    echo "FAILED: ${ERRS}" | sed -e 's/,/\n  /g'
    exit 1
  fi
}

# --------------------------------

test_compile_nn() {
  local nn="$1"; shift

  echo "test_${nn}"

  local exp_file="${TEST_DIR}/compile/exp_${nn}.vga.txt"

  run_lex ${TEST_DIR}/compile/${nn}.vg.txt > $TEMP_TOKENS_FILE
  run_parse $TEMP_TOKENS_FILE > $TEMP_VGT_FILE
  if [ $? -ne 0 ]; then
    ERRS="${ERRS},${nn}_parse"
    return
  fi

  run_codegen $TEMP_VGT_FILE | tr "'" '"'> $TEMP_VGA_FILE
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

test_compile() {
  ns=

  if [ $# -eq 1 ]; then
    ns="$1"
  else
    ns="$(seq 1 11)"
  fi

  for n in $ns; do
    test_compile_nn $(printf "%02d" $n)
  done

  if [ "$ERRS" = "" ]; then
    echo "ok"
  else
    echo "----"
    echo "FAILED: ${ERRS}"
  fi
}

# --------------------------------

main() {
  setup

  local cmd="$1"; shift
  case $cmd in
    compile | c* )  #task: Run compile tests
      test_compile "$@"
      postproc "compile"

  ;; * )
      echo "Tasks:"
      grep '#task: ' $0 | grep -v grep
      ;;
  esac
}

# --------------------------------

main "$@"
