#!/bin/bash

print_project_dir() {
  local real_path="$(readlink --canonicalize "$0")"
  (
    cd "$(dirname "$real_path")"
    pwd
  )
}

readonly PROJECT_DIR="$(print_project_dir)"
readonly TEST_DIR="${PROJECT_DIR}/test_common"
readonly TEST_COMMON_DIR="${PROJECT_DIR}/test_common"
readonly TEMP_DIR="${PROJECT_DIR}/z_tmp"
readonly TEMP_TOKENS_FILE="${TEMP_DIR}/test.tokens.txt"
readonly TEMP_VGT_FILE="${TEMP_DIR}/test.vgt.json"
readonly TEMP_VGA_FILE="${TEMP_DIR}/test.vga.txt"

readonly MAX_ID_LEX=3
readonly MAX_ID_PARSE=2

ERRS=""

readonly RUNNER_CMD=python

run_test_json() {
  local infile="$1"; shift

  $RUNNER_CMD test/test_json.py $infile
}

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

get_ids() {
  local max_id="$1"; shift

  if [ $# -eq 1 ]; then
    echo "$1"
  else
    seq 1 $max_id
  fi
}

# --------------------------------

test_json_nn() {
  local nn="$1"; shift

  echo "case ${nn}"

  local input_file="${TEST_COMMON_DIR}/json/${nn}.json"
  local temp_json_file="${TEMP_DIR}/test.json"
  local exp_file="${TEST_COMMON_DIR}/json/${nn}.json"

  run_test_json $input_file > $temp_json_file
  if [ $? -ne 0 ]; then
    echo >&2
    echo "json >>$(cat -A $temp_json_file)<<" >&2
    ERRS="${ERRS},${nn}_json"
    return
  fi

  ruby ${TEST_COMMON_DIR}/diff.rb json-fmt $exp_file $temp_json_file
  if [ $? -ne 0 ]; then
    ERRS="${ERRS},json_${nn}_diff"
    return
  fi
}

test_json() {
  # TODO json-fmt が利用可能になったら有効化する
  return

  local ids="$(get_ids $MAX_ID_JSON "$@")"

  for id in $ids; do
    test_json_nn $(printf "%02d" $id)
  done
}

# --------------------------------

test_lex_nn() {
  local nn="$1"; shift

  echo "case ${nn}"

  local input_file="${TEST_COMMON_DIR}/lex/${nn}.vg.txt"
  local temp_tokens_file="${TEMP_DIR}/test.tokens.txt"
  local exp_file="${TEST_COMMON_DIR}/lex/exp_${nn}.txt"

  run_lex $input_file > $temp_tokens_file
  if [ $? -ne 0 ]; then
    ERRS="${ERRS},lex_${nn}_lex"
    return
  fi

  ruby test_common/diff.rb text $exp_file $temp_tokens_file
  if [ $? -ne 0 ]; then
    # meld $exp_file $temp_tokens_file &

    ERRS="${ERRS},lex_${nn}_diff"
    return
  fi
}

test_lex() {
  local ids="$(get_ids $MAX_ID_LEX "$@")"

  for id in $ids; do
    test_lex_nn $(printf "%02d" $id)
  done
}

# --------------------------------

test_parse_nn() {
  local nn="$1"; shift

  echo "case ${nn}"

  local input_file="${TEST_COMMON_DIR}/parse/${nn}.vg.txt"
  local temp_tokens_file="${TEMP_DIR}/test.tokens.txt"
  local temp_vgt_file="${TEMP_DIR}/test.vgt.json"
  local exp_file="${TEST_COMMON_DIR}/parse/exp_${nn}.vgt.json"

  echo "  lex" >&2
  run_lex $input_file > $temp_tokens_file
  if [ $? -ne 0 ]; then
    ERRS="${ERRS},parse_${nn}_lex"
    return
  fi

  echo "  parse" >&2
  run_parse $temp_tokens_file \
    > $temp_vgt_file
  if [ $? -ne 0 ]; then
    ERRS="${ERRS},parse_${nn}_parse"
    return
  fi

  ruby test_common/diff.rb json $exp_file $temp_vgt_file
  if [ $? -ne 0 ]; then
    # meld $exp_file $temp_vga_file &

    ERRS="${ERRS},parse_${nn}_diff"
    return
  fi
}

test_parse() {
  local ids="$(get_ids $MAX_ID_PARSE "$@")"

  for id in $ids; do
    test_parse_nn $(printf "%02d" $id)
  done
}

# --------------------------------

test_compile_nn() {
  local nn="$1"; shift

  echo "test_${nn}"

  local exp_file="${TEST_COMMON_DIR}/compile/exp_${nn}.vga.txt"

  run_lex ${TEST_COMMON_DIR}/compile/${nn}.vg.txt > $TEMP_TOKENS_FILE
  if [ $? -ne 0 ]; then
    ERRS="${ERRS},compile_${nn}_lex"
    return
  fi

  run_parse $TEMP_TOKENS_FILE > $TEMP_VGT_FILE
  if [ $? -ne 0 ]; then
    ERRS="${ERRS},compile_${nn}_parse"
    return
  fi

  run_codegen $TEMP_VGT_FILE | tr "'" '"'> $TEMP_VGA_FILE
  if [ $? -ne 0 ]; then
    ERRS="${ERRS},compile_${nn}_codegen"
    return
  fi

  ruby test_common/diff.rb asm $exp_file $TEMP_VGA_FILE
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
    ns="$(seq 1 27)"
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

test_all() {
  echo "==== json ===="
  test_json
  if [ $? -ne 0 ]; then
    ERRS="${ERRS},all_json"
    return
  fi

  echo "==== lex ===="
  test_lex
  if [ $? -ne 0 ]; then
    ERRS="${ERRS},all_lex"
    return
  fi

  # echo "==== parse ===="
  # test_parse
  # if [ $? -ne 0 ]; then
  #   ERRS="${ERRS},parse"
  #   return
  # fi

  echo "==== compile ===="
  test_compile
  if [ $? -ne 0 ]; then
    ERRS="${ERRS},compile"
    return
  fi
}

# --------------------------------

main() {
  setup

  local cmd="$1"; shift
  case $cmd in
    json | j* )     #task: Run json tests
      test_json "$@"
      postproc "json"

  ;; lex | l* )      #task: Run lex tests
      test_lex "$@"
      postproc "lex"

    # parse | p* )  #task: Run parse tests
    #   test_parse "$@"
    #   postproc "parse"

  ;; compile | c* )  #task: Run compile tests
      test_compile "$@"
      postproc "compile"

  ;; all | a* )     #task: Run all tests
      test_all "$@"
      postproc "all"

  ;; * )
      echo "Tasks:"
      grep '#task: ' $0 | grep -v grep
      ;;
  esac
}

# --------------------------------

main "$@"
