



# Language Documentation : Basic Types

## None Type

Both the keyword 'None' and 'null' represent the python None Type to better support JSON

```python
    x = None
    if (x === null) { # compare identity
        print("x is null")
    }
```

## Boolean Types

The capitalized and lowercase form of True and False are valid

```python

    true === True
    false === False
```

## String Constants

Like python, strings constants are quoted utf-8 sequences, using either
double or single quotes.

```python
    "abc"
    "\""
    '\''
    "\o000"
    "\x00"
    "\u0000"
    "\U00000000"

    g"*.md"   # UNIX glob string
    b"abc"    # byte array
    f"{abc}"  # format string
    r"^.+$"   # regex string
```

## Numerical Constants

Numbers are processed in the standard way for python, with an extension for SI-like suffixes and can use an underscore as a separator
```python
    123 == 123            #
    3.14 == 3.14          #
    0x123 == 291          # base 16
    0o123 == 83           # base 8
    0o123 == 27           # base 4
    0b101 == 5            # base 2
    1k == 1000            #
    1m == 1000000         #
    1g == 1000000000      #
    1t == 1000000000000   #
    1kb == 1024           # 1KiB
    1mb == 1048576        # 1MiB
    1gb == 1073741824     # 1GiB
    1tb == 1099511627776  # 1TiB
    3.14k == 3140.0
    1_234 == 1234
    123_456.789 == 123456.789
    3e1 == 30.0
    3e+1 == 30.0
    3e-1 == 0.3
    1j == 1j              # imaginary
    1.1kj == 1100j        # imaginary

    nan == float("nan")
    infinity == float("inf")
```

Hexadecimal floats and doubles are also supported
```python
    0f4048f5c3 == 3.140000104904175
    0f40091eb851eb851f == 3.14
```

## Operators

### Logical Operators

```python

    x && y # and, return y if x is true else x
    x || y # or, return x if x is true else y
    ! x    # not, return True if x is True else False
    not x  #
```
### Unary Operators

```python
    + x  # unary positive
    - x  # unary negative
    ~ x  # bitwise not

    x++, ++x # postfix, prefix increment
    x--, --x # postfix, prefix decrement

    *x # unpack sequence in the context of a function call
    **x # unpack mapping in the context of a function call

```

### Arithmetic Binary Operators

```python

    x + y  # add y to x
    x - y  # subtract y from x
    x * y
    x / y
    x // y
    x % y
    x ** y
    x @ y

```
### Bitwise Binary Operators

```python
    x & y # and
    x | y # or
    x ^ y # xor
    x >> y # right shift
    x << y # left shift
```

### Comparison

```python
    x < y
    x <= y
    x > y
    x >= y
    x == y
    x === y     # identity, equal; python "is"
    x !== y     # identity, not equal; python "is not"
    x is y      # identity, equal
    x is not y  # identity, not equal
```

### Contains

```python
    x in y
    x not in y
```

### Assignment

Assignment operators return a value equal to the value of the rhs, allowing for operator chaining `a=b=c=0`

```python
    x = y
    x += y
    x -= y
    x *= y
    x /= y
    x //= y
    x %= y
    x **= y
    x @= y

```

### Other

see [New Operators](NewOperators.md) and [Process Execution](Exec.md) for more information

```python
    x |> y  # process pipe, see below
    x -> y  # property drill equivalent to python x["y"]
    x?.y    # optional chaining
```

### Sequences and Mapping

```python

()      # empty tuple
(1,)    # tuple

[]      # empty list
[1]     # list

{}      # empty set
{1,}    # set

{:}     # empty dict
{0:1}   # dict
```
