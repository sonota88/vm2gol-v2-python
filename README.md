This is a port of the compiler part of [vm2gol-v2 (Ruby version)](https://github.com/sonota88/vm2gol-v2).

素朴な自作言語のコンパイラをPythonに移植した  
https://memo88.hatenablog.com/entry/2020/08/19/065056

```sh
  $ LANG=C wc -l mrcl_{lexer,parser,codegen}.py lib/common.py
   92 mrcl_lexer.py
  390 mrcl_parser.py
  366 mrcl_codegen.py
   19 lib/common.py
  867 total

  $ cat mrcl_{lexer,parser,codegen}.py lib/common.py | grep -v '^ *#' | wc -l
858
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
