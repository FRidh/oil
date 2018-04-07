#!/bin/bash
#
# Usage:
#   ./test.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

readonly THIS_DIR=$(cd $(dirname $0) && pwd)
readonly OPYC=$THIS_DIR/../bin/opyc

source $THIS_DIR/common.sh

osh-opy() {
  _tmp/oil-opy/bin/osh "$@"
}

oil-opy() {
  _tmp/oil-opy/bin/oil "$@"
}

osh-help() {
  osh-opy --help
}

# TODO: Add compiled with "OPy".
# How will it know?  You can have a special function bin/oil.py:
# def __GetCompilerName__():
#   return "CPython"
#
# If the function name is opy stub, then Opy ret
#
# Or __COMPILER_NAME__ = "CPython"
# The OPy compiler can rewrite this to "OPy".

osh-version() {
  osh-opy --version
}

# TODO:
# - Run with oil.ovm{,-dbg}

# 3/2018 byterun results:
#
# Ran 28 tests, 4 failures
# asdl/arith_parse_test.pyc core/glob_test.pyc core/lexer_gen_test.pyc osh/lex_test.pyc
#

oil-unit() {
  local dir=${1:-_tmp/oil-opy}
  local vm=${2:-cpython}  # byterun or cpython

  pushd $dir

  #$OPYC run core/cmd_exec_test.pyc

  local n=0
  local -a failures=()

  #for t in {build,test,native,asdl,core,osh,test,tools}/*_test.py; do
  for t in {asdl,core,osh}/*_test.pyc; do

    echo $t
    if test $vm = byterun; then

      set +o errexit
      set +o nounset  # for empty array!

      # Note: adding PYTHONPATH screws things up, I guess because it's the HOST
      # interpreter pythonpath.
      $OPYC run $t
      status=$?

      if test $status -ne 0; then
        failures=("${failures[@]}" $t)
      fi
      (( n++ ))

    elif test $vm = cpython; then
      PYTHONPATH=. python $t
      #(( n++ ))

    else
      die "Invalid VM $vm"
    fi
  done
  popd

  if test $vm = byterun; then
    echo "Ran $n tests, ${#failures[@]} failures"
    echo "${failures[@]}"
  fi
}

oil-unit-byterun() {
  oil-unit '' byterun
}

readonly -a FAILED=(
  asdl/arith_parse_test.pyc  # IndexError
  # I believe this is due to:
  # 'TODO: handle generator exception state' in pyvm2.py.  Open bug in
  # byterun.  asdl/tdop.py uses a generator Tokenize() with StopIteration

  # Any bytecode can raise an exception internally.

  core/glob_test.pyc  # unbound method append()
  core/lexer_gen_test.pyc  # ditto
  osh/lex_test.pyc  # ditto
)

oil-byterun-failed() {
  #set +o errexit

  for t in "${FAILED[@]}"; do

    echo
    echo ---
    echo --- $t
    echo ---

    pushd _tmp/oil-opy
    $OPYC run $t
    popd
  done
}

# TODO: byterun/run.sh has this too
byterun-unit() {
  pushd byterun
  for t in test_*.py; do
    echo
    echo "*** $t"
    echo
    PYTHONPATH=. ./$t
  done
}

# Isolated failures.

# File "/home/andy/git/oilshell/oil/bin/../opy/byterun/pyvm2.py", line 288, in manage_block_stack
#   block = self.frame.block_stack[-1]
# IndexError: list index out of range

generator-exception() {
  testdata/generator_exception.py
  ../bin/opyc run testdata/generator_exception.py 
}

generator-exception-diff() {
  rm -f -v testdata/generator_exception.pyc
  testdata/generator_exception.py

  pushd testdata 
  python -c 'import generator_exception'
  popd

  echo ---
  ../bin/opyc compile testdata/generator_exception.py _tmp/ge-opy.pyc

  ../bin/opyc dis testdata/generator_exception.pyc > _tmp/ge-cpython.txt
  ../bin/opyc dis _tmp/ge-opy.pyc > _tmp/ge-opy.txt

  diff -u _tmp/ge-{cpython,opy}.txt
}

# TypeError: unbound method append() must be called with SubPattern instance as
# first argument (got tuple instance instead) 

regex-compile() {
  testdata/regex_compile.py
  echo ---
  ../bin/opyc run testdata/regex_compile.py
}

re-dis() {
  ../bin/opyc dis /usr/lib/python2.7/sre_parse.pyc
}


unit() {
  PYTHONPATH=. "$@"
}

# NOTE: I checked with set -x that it's being run.  It might be nicer to be
# sure with --verison.

export OSH_PYTHON=opy/_tmp/oil-opy/bin/osh

# NOTE: Failures in 'var-num' and 'special-vars' due to $0.  That proves
# we're running the right binary!
spec() {
  local action=${1:-smoke}
  shift

  pushd ..
  # Could also export OSH_OVM
  test/spec.sh $action "$@"
  popd
}

# The way to tickle the 'import' bug.  We need to wrap SOME functions in
# pyobj.Function.  Otherwise it will run too fast!

opy-speed-test() {
  opyc-compile testdata/speed.py _tmp/speed.pyc
  opyc-compile testdata/speed_main.py _tmp/speed_main.pyc

  cp _tmp/speed.pyc _tmp/speed.opyc

  # For logging
  local n=10000
  #local n=10

  # 7 ms
  echo PYTHON
  time python _tmp/speed.opyc $n

  # 205 ms.  So it's 30x slower.  Makes sense.
  echo OPY
  time opyc-run _tmp/speed.opyc $n

  #
  # byterun Import bug regression test!
  #

  # 7 ms
  echo PYTHON
  time python _tmp/speed_main.pyc $n

  # 205 ms.  So it's 30x slower.  Makes sense.
  echo OPY
  time opyc-run _tmp/speed_main.pyc $n
}

"$@"
