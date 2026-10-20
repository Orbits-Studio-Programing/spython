# spython

spython is a small, interpreted programming language with a Python-like feel.
It currently supports variables, arithmetic, strings, booleans, lists, functions,
conditionals, loops, and `print`.

## Run a program

Requires Python 3.10 or newer. Run a `.spy` file with:

```sh
python3 spython.py examples/hello.spy
```

## Syntax

```spython
let base = 10;

fn add(value) {
	return base + value;
}

let count = 0;
while (count < 3) {
	print(add(count));
	count = count + 1;
}

if (count == 3) {
	print("done");
}

let values = [10, 20, 30];
print(values[1]);
values[1] = 25;
print(values);
```

Statements end with semicolons. Blocks use braces. Variables declared inside a
block are local to that block, while assignments update the nearest existing
variable. `true`, `false`, and `null` are built-in values. `//` and `#` start
comments. Lists support zero-based indexing, nested access, and indexed
assignment; negative indexes count from the end. Strings can be indexed to get
a one-character string.

Run the test suite with:

```sh
python3 -m unittest
```