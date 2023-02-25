This is a port of the compiler part of [vm2gol-v2 (Ruby version)](https://github.com/sonota88/vm2gol-v2).

素朴な自作言語のコンパイラをPythonに移植した  
https://memo88.hatenablog.com/entry/2020/08/19/065056

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
