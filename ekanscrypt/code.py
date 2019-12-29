#! python3 $this
#! python3 -m pip install bytecode

# https://bytecode.readthedocs.io/en/latest/usage.html
# https://docs.python.org/3/library/dis.html
# https://docs.python.org/3.8/library/types.html
from bytecode import dump_bytecode, ConcreteInstr, ConcreteBytecode

import types
# dump_bytecode(bytecode, lineno=False)
# Bytecode.from_code(code)

"""
fn = types.FunctionType(fn.__code__, fn.__globals__, name,
                                fn.__defaults__, fn.__closure__)
"""

def test():
    x = 1
    x = x + 2
    print(x)

bc = ConcreteBytecode.from_code(test.__code__)

def dump(bc):
    for name in dir(bc):
        if name.startswith("_"):
            continue
        s = str(getattr(bc, name))
        if 'method' in s:
            continue
        if 'function' in s:
            continue
        print("%20s: %s" % (name, s))
    dump_bytecode(bc)

# dump(bc)

def old():

    # f = types.FunctionType(bc.to_code(), {}, name='test', argdefs=(1, 2))
    f = types.FunctionType(bc.to_code(), {'x': 5, 'print': print}, name='test')

    dump(bc)
    print(test2.__defaults__)
    print(f.__defaults__)
    print(f.__closure__)
    print(test2.__closure__)
    print(f.__name__)
    print(f(g))
# exec(bc.to_code(), {'x':1, 'y':2})


#bytecode = ConcreteBytecode()
#bytecode.names = ['print']
#bytecode.consts = ['Hello World!', None]
#bytecode.extend([ConcreteInstr("LOAD_NAME", 0),
#                 ConcreteInstr("LOAD_CONST", 0),
#                 ConcreteInstr("CALL_FUNCTION", 1),
#                 ConcreteInstr("POP_TOP"),
#                 ConcreteInstr("LOAD_CONST", 1),
#                 ConcreteInstr("RETURN_VALUE")])
#code = bytecode.to_code()
#exec(code)

def const2index(bc, tok):
    if tok not in bc.consts:
        bc.consts.append(tok)
    index = bc.consts.index(tok)
    return index

def label2index(bc, tok, load=False):

    if tok in bc.globals:
        try:
            index = bc.names.index(tok)
            return '_GLOBAL', index
        except ValueError:
            index = len(bc.names)
            bc.names.append(tok)
            return '_GLOBAL', index

    try:
        index = bc.names.index(tok)
        return '_NAME', index
    except ValueError:
        pass

    try:
        index = bc.varnames.index(tok)
        return '_FAST', index
    except ValueError:
        pass

    if load:
        index = len(bc.names)
        bc.names.append(tok)
        return '_NAME', index
    else:
        index = len(bc.varnames)
        bc.varnames.append(tok)
        return '_FAST', index

def compile_load(bc, arg):
    if isinstance(arg, tuple):
        return compile2(bc, *arg)
    elif isinstance(arg, int):
        index = const2index(bc, arg)
        return [ConcreteInstr('LOAD_CONST', index)]
    elif isinstance(arg, str):
        kind, index = label2index(bc, arg, True)
        return [ConcreteInstr('LOAD' + kind, index)]

def compile_store(bc, arg):

    if isinstance(arg, tuple):
        op, arg0, arg1 = arg
        isntr = compile2(bc, *arg0)
        _, index = label2index(bc, arg1, True)
        instr.append(ConcreteInstr('STORE_ATTR', index))
        return instr
    else:
        kind, index = label2index(bc, arg, False)
        return [ConcreteInstr('STORE' + kind, index)]

def compile2(bc, op, arg0, arg1, production=True):

    instr = []
    """
      0    LOAD_CONST 1
      2    STORE_FAST 1
      4    LOAD_FAST 1
      6    LOAD_CONST 2
      8    BINARY_ADD
     10    STORE_FAST 1
     12    LOAD_GLOBAL 0
     14    LOAD_FAST 1
     16    CALL_FUNCTION 1
     18    POP_TOP
     20    LOAD_CONST 0
     22    RETURN_VALUE
     """

    if op == "=":
        instr.extend(compile_load(bc, arg1))
        instr.extend(compile_store(bc, arg0))

        if production:
            instr.extend(compile_load(bc, arg0))

    elif op == "+":
        instr.extend(compile_load(bc, arg0))
        instr.extend(compile_load(bc, arg1))
        instr.append(ConcreteInstr('BINARY_ADD'))

        if not production:
            instr.append(ConcreteInstr('POP_TOP'))

    elif op == "call":
        instr.extend(compile_load(bc, arg0))
        for pos in arg1:
            instr.extend(compile_load(bc, pos))
        instr.append(ConcreteInstr('CALL_FUNCTION', len(arg1)))

        if not production:
            instr.append(ConcreteInstr('POP_TOP'))

    return instr

def compile(seq):
    bc = ConcreteBytecode()

    #dump(bc)
    bc.names = []
    bc.varnames = []
    bc.consts = [None]
    bc.globals = {'print': print}
    for ast in seq:

        op, arg0, arg1 = ast
        bc.extend(compile2(bc, op, arg0, arg1, production=False))

    # always append return None, it may be unreachable
    bc.append(ConcreteInstr('LOAD_CONST', 0))
    bc.append(ConcreteInstr('RETURN_VALUE'))

    dump(bc)

    f = types.FunctionType(bc.to_code(), bc.globals, name='test')

    return f

def  main():

    seq = [('=', 'x', 1), ('=', 'x', ('+', 'x', 2)), ('call', 'print', [('+', 'x', 7)])]
    f = compile(seq)

    print(f())

if __name__ == '__main__':
    main()