
# EkanScrypt

![icon](icon.png)

A backwards thinking, JSON compatable, slightly cryptic, scripting language that compiles to Python Bytecode.

Pros:
 - braces
 - multi-line lambda
 - it has a logo!
 - syntax is a superset of JSON
 - execute shell-like-syntax process pipelines
 - optional chaining (x?.y)
 - property drill (x->y)
 - all the /speed/ of python

Cons:
 - see pros!

# Examples

See the samples directory for more detailed examples

```javascript
print("hello world") # print to stdout
eprint("danger!")  # print to stderr

# Execute Process
exec cat 'README.md' |> exec rev

# parse and output JSON natively
json_payload = {
    "fruit": [
        {"type": "apple", "inventory": 1},
        {"type": "orange", "inventory": 2},
    ]
    "vegetables": [
        {"type": "ketchup", "inventory": 3}
    ]
}

# Property Drill

print(json_payload->fruit->0->type) # apple

# Optional Chaining

obj?.push?.(item)

# define functions using =>
add5 = (x) => {
    y = 5
    return x+y
}
print(add5(2))  # prints 7

```

## Documentation

[Basic Types](doc/BasicTypes.md)

[Control Flow](doc/Import.md)

[New Operators](doc/NewOperators.md)

[New Keywords](doc/NewKeywords.md)

[Import Python or Ekanscrypt Modules](doc/Import.md)

[Process Excution](doc/Exec.md)

## Why?

I wanted to learn how Python Bytecode worked, and also how to write
a lexer and parser. After that I wanted to see what could be done
to push the Python VM and experiment with alternative syntax.

## Next Steps

- improved scoping rules, python uses `nonlocal x`, consider the inversion using `new x` or `var x`. or annotate variables that can be used in child scopes using `let` or `var`
- declare labels and function args as const  (const is enforced by parser phase)
- classes