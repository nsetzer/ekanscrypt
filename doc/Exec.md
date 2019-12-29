


## Execute Shell Commands

The `exec` keyword is used to launch a subprocess. The arguments are the
list of strings after the keyword up until a semicolon, newline or process pipe operator ("|>") are found.

    exec cat "/tmp/file"

variable substition can be done with `${name}` syntax. The named entity must be
a string, or a list of strings.

```javascript
    args = ["-v", "-e", "pattern"]
    file = "./README.md"
    exec grep ${args} ${file}
```

is equivalent to the following bash syntax:

```bash
grep -v -e pattern /tmp/file
```

### Running an Interactive (sub) shell

the following launches bash redirecting stdout to the terminal
```bash
ekans -e 'exec bash 1>"/dev/stdout"'
```

the following runs the bash command redirecting stdout to the terminal
and prints the exit status when bash exits.


```bash
ekans -e 'print((exec bash 1>"/dev/stdout").run())'

```

### listing open files

On Linux, the following will list open file descriptors (of the child process ls)

```bash
exec ls -l /proc/self/fd
````

It can be rewritten as:

``` javascript
    for name in io.listdir('/proc/self/fd') {
        print(name, io.path.realpath('/proc/self/fd/' + name))
    };
```


## Process Pipe Operator

the operator `a |> b` is functionally equivalent to `b(a())`

When combined with shell execution, the output of one command can be chained
with the next command. Interprocess communication is done using Pipes.

    exec cat "/tmp/file" |> exec grep "-v" "-e" foo

The following pairs of lines are equivalent

```python
    exec cat "README.md" |> exec rev

    Proc.communicate(Proc("rev")(Proc("cat", "README.md")))
```

When assigning to a variable, the process is not run automatically, allowing you a chance to read the output into a variable

```python
    proc = exec cat "README.md" |> exec rev
    returncode, stdout, stderr = proc.run()

    proc = Proc("rev")(Proc("cat", "README.md"))
    returncode, stdout, stderr = proc.run()
```

Run the process in the background and collect results
```python
    proc = exec cat "README.md" |> exec rev
    ticket = proc.run_background()
    #... do something else while the task runs
    ticket.wait()
```

# Inspect member processes

```python
    proc = exec 'false' |> exec 'true'
    print(proc.run());
    print(proc.returncode, proc);
    print(proc._parent.returncode, proc._parent);
    print(proc._parent._parent);

    # output
    (0, b'', b'')
    0 Proc<'true'>
    1 Proc<'false'>
    None
```
