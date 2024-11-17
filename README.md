This is a port of the compiler part of [vm2gol-v2 (Ruby version)](https://github.com/sonota88/vm2gol-v2).

素朴な自作言語のコンパイラをPythonに移植した  
https://memo88.hatenablog.com/entry/2020/08/19/065056

```sh
  $ LANG=C wc -l mrcl_{lexer,parser,codegen}.py lib/common.py
   75 mrcl_lexer.py
  369 mrcl_parser.py
  327 mrcl_codegen.py
   44 lib/common.py
  815 total

  $ cat mrcl_{lexer,parser,codegen}.py lib/common.py | grep -v '^ *#' | wc -l
808
```

```
  $ python3 -V
Python 3.10.6
```

```
git clone --recursive https://github.com/sonota88/vm2gol-v2-python.git
cd vm2gol-v2-python

./docker.sh build

./test.sh all
```


# Compile and run game of life

```
./run_game_of_life.sh
```
