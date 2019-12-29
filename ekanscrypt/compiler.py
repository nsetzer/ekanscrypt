#! cd .. && python3 -m pythonscrypt.compiler
# https://bytecode.readthedocs.io/en/latest/usage.html
# https://docs.python.org/3/library/dis.html
# https://docs.python.org/3.8/library/types.html

from .token import Token

import dis
import types
import sys
from collections import defaultdict
import opcode as _opcode
from .objects.io import EkanscryptIo
from .objects.proc import EkanscryptProc
from .util import parseNumber, es_glob, es_format, es_regex
from .exception import CompilerError, format_generic
from .bytecode import dump, calcsize, \
    ConcreteBytecode2, \
    BytecodeInstr, BytecodeJumpInstr, \
    BytecodeRelJumpInstr, BytecodeContinueInstr, BytecodeBreakInstr

from  . import builtins
import faulthandler; faulthandler.enable()

import logging
log = logging.getLogger("ekanscrypt.compiler")

#CO_OPTIMIZED=1
#CO_NEWLOCALS=2
#CO_VARARGS=4
#CO_VARKEYWORDS=8
#CO_NESTED=16
#CO_GENERATOR=32
#CO_NOFREE=64
#CO_COROUTINE=128
#CO_ITERABLE_COROUTINE=256
#CO_ASYNC_GENERATOR=512
mod_dict = globals()
for val, key in dis.COMPILER_FLAG_NAMES.items():
    mod_dict['CO_' + key] = val

class Expression(object):

    CF_MODULE    = 1
    CF_REPL      = 2
    CF_NO_FAST   = 4

    def __init__(self, name="__main__", filename="<string>", globals=None, flags=0):
        super(Expression, self).__init__()

        if not isinstance(name, str):
            raise TypeError(name)
        if not isinstance(filename, str):
            raise TypeError(filename)

        self.globals = Expression.defaultGlobals()

        self.flags = flags
        self.module_globals = set()
        if globals:
            self.globals.update(globals)

        self.bc = ConcreteBytecode2()
        self.bc.name = name
        self.bc.filename = filename
        self.bc.names = []
        self.bc.varnames = []
        self.bc.consts = [None]
        self.depth = 0
        self.namedex = {}

        self.next_label = 0

    @staticmethod
    def defaultGlobals():
        globals_ = {
            'print': print,
            'eprint': builtins.es_print,
            "io": EkanscryptIo(),
            "True": True,
            "False": False,
            "None": None,
            "nan": float('nan'),
            "infinity": float("inf"),
            "Proc": EkanscryptProc,
            "__es_communicate__": EkanscryptProc.communicate,
            '__es_glob__': es_glob,
            '__es_format__': es_format,
            '__es_regex__': es_regex,
            '__es_drill__': builtins.es_drill,
            'range': range,
            '__spec__': __spec__, # for import
            '__loader__': __loader__, # for import
            '__builtins__': __builtins__, # for import
            'globals': globals,
            'locals': locals,
        }
        return globals_

    def execute(self):
        rv = self.function_body()

    def dump(self):
        if self.bc:
            dump(self.bc)
        print("%20s: %s" % ("mod_globals", ', '.join(self.module_globals)))

    def compile(self, asf, name=None):
        last_index = len(asf) - 1
        for index, ast in enumerate(asf):
            production = self.flags&Expression.CF_REPL and last_index == index and ast.type !=  Token.S_EXEC_PROCESS
            instr = self._compile(ast, production=production)
            try:
                self.bc.extend(instr)
            except ValueError:
                raise
            if production:
                self.module_globals.add("_")
                self.bc.extend(self._compile_store(Token(Token.S_LABEL, 1, 0, "_")))
        self._finalize()

        stacksize = calcsize(self.bc)
        code = self.bc.to_code(stacksize)
        self.function_body = types.FunctionType(code, self.globals, self.bc.name)

    def _make_label(self):
        self.next_label += 1
        return self.next_label

    def _finalize(self):

        retry = True
        again = False
        attempts = 0
        while retry:
            attempts += 1
            if attempts > 10:
                sys.stderr.write("ekanscrypt compiler warning: finalize attempt %d\n" % attempts)
            if attempts > 20:
                raise CompilerError(Token("", 1, 0, ""), "failed to finalize")

            # walk the list of instructions, build the map
            # for computing the absolute jumps
            # lbl -> pos
            src = {}
            # lbl -> list-of-index
            tgt = defaultdict(list)
            # index -> pos
            map = [0]*len(self.bc)

            pos = 0
            for index, op in enumerate(self.bc):
                if not isinstance(op, BytecodeInstr):
                    raise TypeError(op)
                if op._es_target:
                    tgt[op._es_target].append(index)
                for lbl in op._es_labels:
                    src[lbl] = pos
                map[index] = pos
                pos += op.size

            retry = False
            for lbl, tgts in tgt.items():
                for index in tgts:
                    op = self.bc[index]
                    size = op.size
                    op.finalize(map[index], src[lbl])
                    new_size = op.size
                    # if the size is different the jump targets
                    # will need to be recalculated
                    # keep processing the whole list since
                    # it is possible that will minimize the number
                    # of loops
                    if size != new_size:
                        retry = True

            if again is False and retry is False:
                again = True
                retry = True

        if len(self.bc):
            lineno = self.bc[-1].lineno
        else:
            lineno = 1

        if self.flags&Expression.CF_REPL or self.flags&Expression.CF_MODULE:
            instr = []
            for name in sorted(self.module_globals):
                tok1 = Token(Token.S_STRING, lineno, 0, name)
                tok2 = Token(Token.S_LABEL, lineno, 0, name)
                instr.extend(self._compile_load(tok1))
                instr.extend(self._compile_load(tok2))
            instr.append(BytecodeInstr("BUILD_MAP", len(self.module_globals), lineno=lineno))
            instr.append(BytecodeInstr('RETURN_VALUE', lineno=lineno))
            self.bc.extend(instr)

        elif not len(self.bc) or self.bc[-1].name != 'RETURN_VALUE':
            self.bc.append(BytecodeInstr('LOAD_CONST', 0, lineno=lineno))
            self.bc.append(BytecodeInstr('RETURN_VALUE', lineno=lineno))

        lineno = 1
        for op in self.bc:
            if op.lineno and op.lineno > lineno:
                lineno = op.lineno
            elif op.lineno is None or op.lineno < lineno:
                op.lineno = lineno

    def _token2index_name(self, tok, load=False):

        try:
            index = self.bc.names.index(tok.value)
            #print('label', 'NAME', "load_" if load else "store", index, tok.value)
            return 'NAME', index
        except ValueError:
            index = len(self.bc.names)
            self.bc.names.append(tok.value)
            #print('label', 'NAME', "load_" if load else "store", index, tok.value)
            return 'NAME', index

    def _token2index_fast(self, tok, load=False):

        if self.flags&Expression.CF_NO_FAST:
            # no import inside a class? or fallback to name?
            raise CompilerError(tok, "probably shouldnt do this")

        try:
            index = self.bc.varnames.index(tok.value)
            #print('label', 'FAST', "load_" if load else "store", index, tok.value)
            return 'FAST', index
        except ValueError:
            index = len(self.bc.varnames)
            #print('label', 'FAST', "load_" if load else "store", index, tok.value)
            self.bc.varnames.append(tok.value)
            return 'FAST', index

    def _token2index(self, tok, load=False):

        # TODO: likely depracted
        if tok.type == Token.S_REFERENCE:
            # return index such that:
            #  co_cellvars[i] = tok.value
            #  or
            #  co_freevars[i - len(co_cellvars)] = tok.value

            if tok.value in self.bc.freevars:
                return "DEREF", len(self.bc.cellvars) + self.bc.freevars.index(tok.value)

            if tok.value in self.bc.cellvars:
                return 'DEREF', self.bc.cellvars.index(tok.value)

            #if tok.value in self.globals or \
            #   tok.value in self.module_globals:
            #    index = self.bc.names.index(tok.value)
            #    return 'GLOBAL', index

            #index = len(self.bc.freevars)
            #self.bc.freevars.append(tok.value)
            #return "DEREF", index
            raise ValueError("%s %s" % (self.depth, tok))

        if tok.type == Token.S_BYTE_STRING:
            value = tok.value.encode("utf-8")
            if value not in self.bc.consts:
                index = len(self.bc.consts)
                self.bc.consts.append(value)
            else:
                index = self.bc.consts.index(value)
            return 'CONST', index

        elif tok.type in [Token.S_STRING, Token.S_GLOB_STRING, Token.S_FORMAT_STRING, Token.S_REGEX_STRING]:
            if tok.value not in self.bc.consts:
                self.bc.consts.append(tok.value)
            index = self.bc.consts.index(tok.value)
            return 'CONST', index

        elif tok.type == Token.S_NUMBER:
            # TODO: may need to cache string repr for floats
            # no guarantee  "3.14" will always equal "3.14" after
            # conversion or that two different strings wont map
            # to the same constant
            value = parseNumber(tok)
            if value not in self.bc.consts:
                self.bc.consts.append(value)
            index = self.bc.consts.index(value)
            return 'CONST', index

        elif tok.type == Token.S_LABEL:

            if not load and (self.flags&Expression.CF_REPL or self.flags&Expression.CF_MODULE):
                self.module_globals.add(tok.value)


            if self.flags&Expression.CF_NO_FAST and not load:

                pass
            else:
                if tok.value in self.bc.freevars:
                    index = len(self.bc.cellvars) + self.bc.freevars.index(tok.value)
                    #print('label', 'DEREF', "load_" if load else "store", index, tok.value)
                    return "DEREF", index

                if tok.value in self.bc.cellvars:
                    index = self.bc.cellvars.index(tok.value)
                    #print('label', 'DEREF', "load_" if load else "store", index, tok.value)
                    return 'DEREF', index

            #tok.value in self.module_globals or \
            #   (not load and self.module):

            if tok.value in self.globals:

                try:
                    index = self.bc.names.index(tok.value)
                    #print('label', 'GLOBAL', "load_" if load else "store", index, tok.value)
                    return 'GLOBAL', index
                except ValueError:
                    index = len(self.bc.names)
                    if load:
                        log.debug('read from unassigned global: %s' % tok.value)
                    # keep track of labels the program is adding.
                    #if tok.value not in self.globals:
                    #    self.module_globals.add(tok.value)
                    self.bc.names.append(tok.value)
                    #print('label', 'GLOBAL', "load_" if load else "store", index, tok.value)
                    return 'GLOBAL', index

            if not self.flags&Expression.CF_NO_FAST:
                try:
                    index = self.bc.varnames.index(tok.value)
                    #print('label', 'FAST', "load_" if load else "store", index, tok.value)
                    return 'FAST', index
                except ValueError:
                    pass

            try:
                index = self.bc.names.index(tok.value)
                #print('label', 'NAME', "load_" if load else "store", index, tok.value)
                return 'NAME', index
            except ValueError:
                pass

            if load or self.flags&Expression.CF_NO_FAST:
                #log.warning('read %s from names: %s' % (tok.type, tok.value))
                index = len(self.bc.names)
                self.bc.names.append(tok.value)
                #print('label', 'NAME', "load_" if load else "store", index, tok.value)
                return 'NAME', index
            else:
                index = len(self.bc.varnames)
                self.bc.varnames.append(tok.value)
                #print('label', 'FAST', "load_" if load else "store", index, tok.value)
                return 'FAST', index

        elif tok.type == Token.S_ATTR_LABEL:
            try:
                index = self.bc.names.index(tok.value)
                return 'NAME', index
            except ValueError:
                index = len(self.bc.names)
                self.bc.names.append(tok.value)
                return 'NAME', index

        elif tok.type in [Token.S_TRUE]:
            if not load:
                raise CompilerError(tok, "cannot assign to %s" % tok.value)
            try:
                index = self.bc.names.index("True")
                return 'GLOBAL', index
            except ValueError:
                index = len(self.bc.names)
                self.bc.names.append("True")
                return 'GLOBAL', index

        elif tok.type in [Token.S_FALSE]:
            if not load:
                raise CompilerError(tok, "cannot assign to %s" % tok.value)
            try:
                index = self.bc.names.index('False')
                return 'GLOBAL', index
            except ValueError:
                index = len(self.bc.names)
                self.bc.names.append('False')
                return 'GLOBAL', index

        elif tok.type in [Token.S_NULL]:
            if not load:
                raise CompilerError(tok, "cannot assign to %s" % tok.value)
            try:
                index = self.bc.names.index('None')
                return 'GLOBAL', index
            except ValueError:
                index = len(self.bc.names)
                self.bc.names.append('None')
                return 'GLOBAL', index

        elif tok.type in [Token.S_NAN, Token.S_INFINITY]:
            if not load:
                raise CompilerError(tok, "cannot assign to %s" % tok.value)
            if tok.value in self.globals:
                try:
                    index = self.bc.names.index(tok.value)
                    return 'GLOBAL', index
                except ValueError:
                    index = len(self.bc.names)
                    self.bc.names.append(tok.value)
                    return 'GLOBAL', index
            raise Exception("not found %s" % tok)

        # raise ValueError("unable to index")
        raise CompilerError(tok, "unable to index %s (%s)" % (tok.type, tok.value))

    def _compile(self, tok, production=True):

        if tok.type == Token.S_CLOSURE:
            if production:
                raise ValueError()
            return self._compile_closure(tok)
        if tok.type == Token.S_BRANCH:
            return self._compile_branch(tok, production)
        elif tok.type == Token.S_WHILE:
            return self._compile_while(tok, production)
        elif tok.type == Token.S_FOREACH:
            return self._compile_foreach(tok, production)
        elif tok.type == Token.S_SWITCH:
            return self._compile_switch(tok, production)
        elif tok.type == Token.S_WITH:
            return self._compile_with(tok, production)
        elif tok.type == Token.S_CALL_FUNCTION:
            return self._compile_call_function(tok, production)
        elif tok.type == Token.S_EXEC_PROCESS:
            return self._compile_exec(tok, production)
        elif tok.type == Token.S_SUBSCR:
            return self._compile_subscr(tok, production)
        elif tok.type == Token.S_SLICE:
            return self._compile_slice(tok, production)
        elif tok.type == Token.S_PREFIX:
            return self._compile1(tok)
        elif tok.type == Token.S_OPERATOR1:
            return self._compile1(tok, production)
        elif tok.type == Token.S_OPERATOR2:
            return self._compile2(tok, production)
        elif tok.type == Token.S_ATTR:
            return self._compile_attr(tok, production)
        elif tok.type in [Token.S_BUILD, Token.S_TUPLE]:
            return self._compile_build(tok, production)
        elif tok.type == Token.S_CLASS:
            return self._compile_class(tok, production)
        elif tok.type == Token.S_CLASS_INIT:
            return self._compile_class_init(tok, production)
        elif tok.type == Token.S_CLASS_INIT2:
            return self._compile_class_init2(tok, production)
        elif tok.type == Token.S_LAMBDA:
            return self._compile_lambda(tok, production)
        elif tok.type == Token.S_BLOCK:
            return self._compile_block(tok, production)
        elif tok.type == Token.S_RETURN:
            return self._compile_return(tok, production)
        elif tok.type in [Token.S_NUMBER,
                          Token.S_STRING,
                          Token.S_BYTE_STRING,
                          Token.S_LABEL,
                          Token.S_REFERENCE,
                          Token.S_TRUE,
                          Token.S_FALSE,
                          Token.S_NAN,
                          Token.S_INFINITY,
                          Token.S_NULL]:
            kind, index = self._token2index(tok, True)
            instr = [BytecodeInstr('LOAD_' + kind, index, lineno=tok.line)]
            if not production:
                instr.append(BytecodeInstr("POP_TOP"))
            return instr
        elif tok.type == Token.S_FORMAT_STRING:
            return self._compile_fstring(tok, production)
        elif tok.type == Token.S_GLOB_STRING:
            return self._compile_gstring(tok, production)
        elif tok.type == Token.S_REGEX_STRING:
            return self._compile_rstring(tok, production)
        elif tok.type == Token.S_NONE:
            if production:
                return [BytecodeInstr('LOAD_CONST', 0)]
            return []
        elif tok.type == Token.S_CONTINUE:
            if production:
                raise ValueError(tok)
            return self._compile_continue(tok)
        elif tok.type == Token.S_BREAK:
            if production:
                raise ValueError(tok)
            return self._compile_break(tok)
        elif tok.type == Token.S_POSTFIX:
            return self._compile_postfix(tok, production)
        elif tok.type == Token.S_LIST_COMPREHENSION:
            return self._compile_list_comprehension(tok)
        elif tok.type == Token.S_SET_COMPREHENSION:
            return self._compile_set_comprehension(tok)
        elif tok.type == Token.S_DICT_COMPREHENSION:
            return self._compile_dict_comprehension(tok)
        elif tok.type == Token.S_OPTIONAL_ATTR:
            return self._compile_optional(tok)
        elif tok.type == Token.S_IMPORT:
            return self._compile_import(tok)
        elif tok.type == Token.S_YIELD:
            return self._compile_yield(tok, production)
        elif tok.type == Token.S_YIELD_FROM:
            return self._compile_yield_from(tok, production)
        elif tok.type == Token.S_TRYCATCH:
            return self._compile_trycatch_3_7(tok, production)
            #if sys.version_info >= (3, 8):
            #    return self._compile_trycatch_3_8(tok, production)
            #else:
            #    return []
        elif tok.type == Token.S_RAISE:
            return self._compile_raise(tok, production)
        else:
            raise CompilerError(tok, "not implemented: %s" % tok)

    def _compile_postfix(self, tok, production=True):

        if tok.type !=  Token.S_POSTFIX:
            raise ValueError(str(tok))

        unop2 = {
            "++": "BINARY_ADD",
            "--": "BINARY_SUBTRACT"
        }

        instr = []

        if tok.value in unop2:
            # TODO: obvious optimization on load/store here
            # this only works correctly for x++, a.b++ will work, but not optimally
            # will need to correctly update module_globals
            instr_store = self._compile_store(tok.children[0])
            instr.extend(self._compile_load(tok.children[0]))
            if production and instr_store:
                instr.append(BytecodeInstr('DUP_TOP', lineno=tok.line))
            instr.extend(self._compile_load(Token(Token.S_NUMBER, tok.line, tok.index, "1")))
            instr.append(BytecodeInstr(unop2[tok.value], lineno=tok.line))
            instr.extend(instr_store)
        else:
            raise NotImplementedError(str(tok))

        return instr

    def _compile_call_function(self, tok, production=True):
        """ implement all forms of calling a function

        f()
            call a function with no arguments

        f(a,b,c)
            call a function using positional arguments

        f(a=0,b=1,c=2)
            call a function using keyword arguments

        f?.()
            call the function f if f is not None else return the value of f
        """
        if tok.type != Token.S_CALL_FUNCTION:
            raise ValueError()

        instr = []

        pos_count = 0
        pos_instr = []
        kwarg_count = 0
        kwarg_instr = []
        kwarg_names = []

        varpos_count = 0
        varpos_instr = []
        varkwarg_count = 0
        varkwarg_instr = []

        # load the function
        tokf = tok.children[0]
        optional = False
        if tokf.type == Token.S_OPTIONAL_ATTR and len(tokf.children) == 1:
            optional = True
            tokf = tokf.children[0]

        instr.extend(self._compile_load(tokf))

        nop = None
        if optional:
            lbl = self._make_label()
            instr.append(BytecodeInstr('DUP_TOP'))
            instr.append(BytecodeInstr("LOAD_CONST", 0))
            instr.append(BytecodeInstr("COMPARE_OP", dis.cmp_op.index('is')))
            instr.append(BytecodeJumpInstr("POP_JUMP_IF_TRUE", lbl))

            nop = BytecodeInstr("NOP")
            nop.add_label(lbl)

        # load the arguments
        disable_pos = False
        disable_kwa = False
        for child in tok.children[1:]:


            if child.type == Token.S_PREFIX and child.value in ('*', '**'):
                # keyword arguments
                if child.value == '*':
                    disable_pos = True
                    varpos_instr.extend(self._compile_load(child.children[0]))
                    varpos_count += 1

                if child.value == '**':
                    disable_pos = True
                    varkwarg_instr.extend(self._compile_load(child.children[0]))
                    varkwarg_count += 1

            elif child.type == Token.S_OPERATOR2 and child.value == "=":
                # keyword arguments

                lhs, rhs = child.children
                if lhs.type != Token.S_LABEL:
                    raise CompilerError(lhs, "expected label")

                try:
                    index = self.bc.consts.index(lhs.value)
                except ValueError:
                    index = len(self.bc.consts)
                    self.bc.consts.append(lhs.value)

                kwarg_instr.append(self._compile_load(rhs))
                kwarg_names.append(BytecodeInstr('LOAD_CONST', index))

                kwarg_count += 1

            else:
                # positional arguments
                if disable_pos:
                    raise CompilerError(child, "positional argument after *")

                if kwarg_count > 0:
                    raise CompilerError(child, "positional after keyword argument")

                pos_instr.extend(self._compile_load(child))
                pos_count += 1

        instr.extend(pos_instr)

        if varpos_count > 0 or varkwarg_count > 0:
            if pos_count > 0:
                instr.append(BytecodeInstr('BUILD_TUPLE', pos_count))

            if varpos_count > 0:
                instr.extend(varpos_instr)

            # merge argument tuples if there are more than 1
            n1 = varpos_count + (1 if pos_count > 0 else 0)
            n2 = varkwarg_count + (1 if kwarg_count > 0 else 0)
            if n1 > 1:
                instr.append(BytecodeInstr('BUILD_TUPLE_UNPACK_WITH_CALL', n1))

            if n1 == 0 and n2 > 0:
                instr.append(BytecodeInstr('BUILD_TUPLE', 0))

            # build a map out of all arguments name=value pairs
            if kwarg_count > 0:
                for instrs, name in zip(kwarg_instr, kwarg_names):
                    instr.append(name)
                    instr.extend(instrs)
                instr.append(BytecodeInstr('BUILD_MAP', kwarg_count))


            if varkwarg_count > 0:
                instr.extend(varkwarg_instr)

            # merge argument dicts if there are more than 1

            if n2 > 1:
                instr.append(BytecodeInstr('BUILD_MAP_UNPACK_WITH_CALL', n2))

            flags = 0x01 if (varkwarg_count + kwarg_count) > 0 else 0x00
            instr.append(BytecodeInstr('CALL_FUNCTION_EX', flags))

        elif kwarg_count > 0:

            for instrs in kwarg_instr:
                instr.extend(instrs)
            instr.extend(kwarg_names)
            instr.append(BytecodeInstr('BUILD_TUPLE', kwarg_count))
            instr.append(BytecodeInstr('CALL_FUNCTION_KW', pos_count + kwarg_count))
        else:
            instr.append(BytecodeInstr('CALL_FUNCTION', pos_count))

        if optional:
            instr.append(nop)

        if not production:
            instr.append(BytecodeInstr('POP_TOP', lineno=tok.line))

        return instr

    def _compile_exec(self, tok, production=True):
        """
        a function is a token with 1 or more children

        the first child is the label or expr for the function to call
        the remaining children are the positional arguments
        """
        if tok.type != Token.S_EXEC_PROCESS:
            raise ValueError()

        instr = []

        for child in tok.children:
            instr.extend(self._compile_load(child))

        instr.append(BytecodeInstr('CALL_FUNCTION', len(tok.children) - 1, lineno=tok.line))

        if not production:
            # an exec keyword not consumed needs to be run
            # the process pipe is more complicated
            #
            if tok.value == "exec":
                attr = "run2"
                try:
                    index = self.bc.names.index(attr)
                except ValueError:
                    index = len(self.bc.names)
                    self.bc.names.append(attr)

                instr.append(BytecodeInstr('LOAD_ATTR', index, lineno=tok.line))
                instr.append(BytecodeInstr('CALL_FUNCTION', 0, lineno=tok.line))
                instr.append(BytecodeInstr('POP_TOP', lineno=tok.line))
            else:
                attr = "__es_communicate__"
                try:
                    index = self.bc.names.index(attr)
                except ValueError:
                    index = len(self.bc.names)
                    self.bc.names.append(attr)
                instr.append(BytecodeInstr('LOAD_GLOBAL', index, lineno=tok.line))
                instr.append(BytecodeInstr('ROT_TWO', lineno=tok.line))
                instr.append(BytecodeInstr('CALL_FUNCTION', 1, lineno=tok.line))
                instr.append(BytecodeInstr('POP_TOP', lineno=tok.line))

        return instr

    def _compile1(self, tok, production=True):
        """
        compile a unary expression
        """

        if tok.type not in [Token.S_OPERATOR1, Token.S_PREFIX]:
            raise ValueError(str(tok))

        if len(tok.children) != 1:
            # TODO: should explicitly transform this in the parser
            #if tok.value == "()":
            #    return [BytecodeInstr("BUILD_TUPLE", 0)]
            raise CompilerError(tok, "empty operator %d %s" % (tok.line, tok.index))

        instr = []

        unop = {
            "+": "UNARY_POSITIVE",
            "-": "UNARY_NEGATIVE",
            "!": "UNARY_NOT",
            "~": "UNARY_INVERT",
        }

        unop2 = {
            "++": "BINARY_ADD",
            "--": "BINARY_SUBTRACT"
        }

        if tok.value in unop:
            instr.extend(self._compile_load(tok.children[0]))
            instr.append(BytecodeInstr(unop[tok.value], lineno=tok.line))

            if not production:
                instr.append(BytecodeInstr('POP_TOP', lineno=tok.line))

        elif tok.value in unop2:
            # TODO: obvious optimization on load/store here
            # this only works correctly for x++, a.b++ will work, but not optimally
            # will need to correctly update module_globals

            n = 0
            token = tok
            while token.type == Token.S_PREFIX:
                if token.value == "++":
                    n += 1
                    token = token.children[0]
                elif token.value == "--":
                    n -= 1
                    token = token.children[0]
                else:
                    break

            token_load = token

            while token.type == Token.S_POSTFIX:
                if token.value == "++":
                    token = token.children[0]
                elif token.value == "--":
                    token = token.children[0]
                else:
                    break

            instr_store = self._compile_store(token)
            instr.extend(self._compile_load(token_load))
            instr.extend(self._compile_load(Token(Token.S_NUMBER, tok.line, tok.index, str(n))))
            instr.append(BytecodeInstr('BINARY_ADD', lineno=tok.line))
            if production and instr_store:
                instr.append(BytecodeInstr('DUP_TOP', lineno=tok.line))
            instr.extend(instr_store)

        else:
            raise NotImplementedError(str(tok))

        return instr

    def _compile2(self, tok, production=True):
        """
        compile a binary expression
        """

        if tok.type != Token.S_OPERATOR2:
            raise ValueError(str(tok))

        if len(tok.children) != 2:
            raise ValueError(str(tok))

        instr = []

        binop = {
            "+": "BINARY_ADD",
            "*": "BINARY_MULTIPLY",
            "@": "BINARY_MATRIX_MULTIPLY",
            "//": "BINARY_FLOOR_DIVIDE",
            "/": "BINARY_TRUE_DIVIDE",
            "%": "BINARY_MODULO",
            "-": "BINARY_SUBTRACT",
            "**": "BINARY_POWER",
            "<<": "BINARY_LSHIFT",
            ">>": "BINARY_RSHIFT",
            "&": "BINARY_AND",
            "^": "BINARY_XOR",
            "|": "BINARY_OR",
        }

        binop_store = {
            "+=": "BINARY_ADD",
            "*=": "BINARY_MULTIPLY",
            "@=": "BINARY_MATRIX_MULTIPLY",
            "//=": "BINARY_FLOOR_DIVIDE",
            "/=": "BINARY_TRUE_DIVIDE",
            "%=": "BINARY_MODULO",
            "-=": "BINARY_SUBTRACT",
            "**=": "BINARY_POWER",
            "<<=": "BINARY_LSHIFT",
            ">>=": "BINARY_RSHIFT",
            "&=": "BINARY_AND",
            "^=": "BINARY_XOR",
            "|=": "BINARY_OR",
        }

        if tok.value == "=":
            instr.extend(self._compile_load(tok.children[1]))
            if production:
                instr.append(BytecodeInstr('DUP_TOP', lineno=tok.line))

            instr.extend(self._compile_store(tok.children[0]))

        elif tok.value == "&&":
            lhs = self._compile_load(tok.children[0])
            rhs = self._compile_load(tok.children[1])
            lbl = self._make_label()
            op = BytecodeJumpInstr("JUMP_IF_FALSE_OR_POP", lbl)
            nop = BytecodeInstr("NOP")
            nop.add_label(lbl)

            instr.extend(lhs)
            instr.append(op)
            instr.extend(rhs)
            instr.append(nop)

            if not production:
                instr.append(BytecodeInstr('POP_TOP'))
            return instr

        elif tok.value == "||":
            lhs = self._compile_load(tok.children[0])
            rhs = self._compile_load(tok.children[1])
            lbl = self._make_label()
            op = BytecodeJumpInstr("JUMP_IF_TRUE_OR_POP", lbl)
            nop = BytecodeInstr("NOP")
            nop.add_label(lbl)

            instr.extend(lhs)
            instr.append(op)
            instr.extend(rhs)
            instr.append(nop)

            if not production:
                instr.append(BytecodeInstr('POP_TOP'))
            return instr

        elif tok.value in dis.cmp_op:
            instr.extend(self._compile_load(tok.children[0]))
            instr.extend(self._compile_load(tok.children[1]))
            instr.append(BytecodeInstr('COMPARE_OP', dis.cmp_op.index(tok.value), lineno=tok.line))

            if not production:
                instr.append(BytecodeInstr('POP_TOP'))

        elif tok.value == "===":
            instr.extend(self._compile_load(tok.children[0]))
            instr.extend(self._compile_load(tok.children[1]))
            instr.append(BytecodeInstr('COMPARE_OP', dis.cmp_op.index("is"), lineno=tok.line))

            if not production:
                instr.append(BytecodeInstr('POP_TOP'))

        elif tok.value == "!==":
            instr.extend(self._compile_load(tok.children[0]))
            instr.extend(self._compile_load(tok.children[1]))
            instr.append(BytecodeInstr('COMPARE_OP', dis.cmp_op.index("is not"), lineno=tok.line))

            if not production:
                instr.append(BytecodeInstr('POP_TOP', lineno=tok.line))

        elif tok.value in binop:
            instr.extend(self._compile_load(tok.children[0]))
            instr.extend(self._compile_load(tok.children[1]))
            instr.append(BytecodeInstr(binop[tok.value]))

            if not production:
                instr.append(BytecodeInstr('POP_TOP', lineno=tok.line))

        elif tok.value in binop_store:
            # TODO: there is an optimization on lhs to be done
            instr.extend(self._compile_load(tok.children[0]))
            instr.extend(self._compile_load(tok.children[1]))
            instr.append(BytecodeInstr(binop_store[tok.value], lineno=tok.line))
            #if production:
            #    instr.append(BytecodeInstr('DUP_TOP', lineno=tok.line))
            instr.extend(self._compile_store(tok.children[0]))
            # TODO: the DUP_TOP was removed to duplicate
            # some python logic
            instr.extend(self._compile_load(tok.children[0]))

            if not production:
                instr.append(BytecodeInstr('POP_TOP'))

        else:
            raise NotImplementedError(str(tok))

        return instr

    def _compile_attr(self, tok, production=True):

        if tok.type != Token.S_ATTR:
            raise ValueError(str(tok))

        instr = []

        expr, attr = tok.children
        instr.extend(self._compile_load(expr))

        kind, index = self._token2index_name(attr, load=True)

        instr.append(BytecodeInstr('LOAD_ATTR', index, lineno=tok.line))

        if not production:
            instr.append(BytecodeInstr('POP_TOP', lineno=tok.line))

        return instr

    def _compile_build(self, tok, production=True):

        if tok.type not in [Token.S_BUILD, Token.S_TUPLE]:
            raise ValueError(str(tok))

        #if tok.value == "MAP" and len(tok.children) % 2 == 1:
        #    raise ValueError(str(tok))

        instr = []

        for child in tok.children:
            if child.type == Token.S_PREFIX and child.value in ('*', '**'):
                raise CompilerError(child, "not implemented")
            instr.extend(self._compile_load(child))

        if tok.type == Token.S_TUPLE:
            count = len(tok.children)
            kind = "BUILD_TUPLE"
        elif tok.value == "MAP":
            count = len(tok.children) // 2
            kind = 'BUILD_MAP'
        else:
            count = len(tok.children)
            kind = 'BUILD_' + tok.value

        instr.append(BytecodeInstr(kind, count, lineno=tok.line))

        if not production:
            instr.append(BytecodeInstr('POP_TOP', lineno=tok.line))

        return instr

    def _compile_branch(self, tok, production=True):

        br_e = tok.children[0]
        br_t = tok.children[1]
        br_f = tok.children[2]

        if br_t:
            instr_t = self._compile(br_t, production)
        elif production:
            instr_t = [BytecodeInstr('LOAD_CONST', 0, lineno=tok.line)]
        else:
            instr_t = []

        if br_f:
            instr_f = self._compile(br_f, production)
        elif production:
            instr_f = [BytecodeInstr('LOAD_CONST', 0, lineno=tok.line)]
        else:
            instr_f = []

        instr = self._compile_load(br_e)

        nop = BytecodeInstr('NOP')

        if instr_f:
            lbl_branch1 = self._make_label()
            lbl_branch2 = self._make_label()
            instr.append(BytecodeJumpInstr('POP_JUMP_IF_FALSE', lbl_branch1))
            instr.extend(instr_t)
            instr.append(BytecodeJumpInstr('JUMP_ABSOLUTE', lbl_branch2))
            instr.extend(instr_f)
            instr.append(nop)

            instr_f[0].add_label(lbl_branch1)
            nop.add_label(lbl_branch2)
        else:
            lbl_branch1 = self._make_label()
            instr.append(BytecodeJumpInstr('POP_JUMP_IF_FALSE', lbl_branch1))
            instr.extend(instr_t)
            instr.append(nop)

            nop.add_label(lbl_branch1)

        return instr

    def _compile_while(self, tok, production=True):

        if tok.type != Token.S_WHILE:
            raise ValueError(str(tok))

        test = tok.children[0]
        expr = tok.children[1]

        lbl_continue = self._make_label()
        lbl_break = self._make_label()

        instr_test = self._compile_load(test)
        instr_expr = self._compile(expr, False)

        instr_test[0].add_label(lbl_continue)
        instr = instr_test[:]

        jmp1 = BytecodeJumpInstr('POP_JUMP_IF_FALSE', lbl_break)
        instr.append(jmp1)

        instr.extend(instr_expr)
        jmp = BytecodeJumpInstr('JUMP_ABSOLUTE', lbl_continue)
        instr.append(jmp)
        nop = BytecodeInstr("NOP")
        nop.add_label(lbl_break)
        instr.append(nop)

        for op in instr_expr:
            if isinstance(op, (BytecodeContinueInstr, BytecodeBreakInstr)):
                op.update(lbl_continue, lbl_break)

        if production:
            # recompile because the labels tainted the old instr
            instr.extend(self._compile_load(test))
        return instr

    def _compile_foreach(self, tok, production=True):

        if tok.type != Token.S_FOREACH:
            raise ValueError(str(tok))

        tgt, seq, expr = tok.children

        instr_seq = self._compile_load(seq)

        lbl_continue = self._make_label()
        lbl_break = self._make_label()
        lbl_done = self._make_label()

        instr_expr = []

        instr_expr.extend(self._compile_store(tgt))
        #if tgt.type == Token.S_LABEL:
        #    kind, index = self._token2index(tgt)
        #    instr_expr.append(BytecodeInstr('STORE_' + kind, index, lineno=tok.line))
        #else:
        #    # TODO: refactor to _compile_store :: tuple unpacking
        #    # TODO: assert namelist
        #    instr_expr.append(BytecodeInstr('UNPACK_SEQUENCE', len(tgt.children), lineno=tok.line))
        #    for label in tgt.children:
        #        kind, index = self._token2index(label)
        #        instr_expr.append(BytecodeInstr('STORE_' + kind, index, lineno=tok.line))
        instr_expr.extend(self._compile(expr, False))

        # an instruction target to continue the loop for the next iteration
        jmp = BytecodeJumpInstr('JUMP_ABSOLUTE', lbl_continue)

        # an instruction target to jump to to break out of the loop
        instr_break = BytecodeInstr('POP_TOP', lineno=tok.line)
        instr_break.add_label(lbl_break)

        instr_expr.append(jmp)
        instr_expr.append(instr_break)

        offset = sum([op.size for op in instr_expr])

        get_iter = BytecodeInstr('GET_ITER', lineno=tok.line)
        for_iter = BytecodeRelJumpInstr('FOR_ITER', lbl_done, lineno=tok.line)
        for_iter.add_label(lbl_continue)

        for op in instr_expr:
            if isinstance(op, (BytecodeContinueInstr, BytecodeBreakInstr)):
                op.update(lbl_continue, lbl_break)

        nop = BytecodeInstr('NOP')
        nop.add_label(lbl_done)

        instr = []
        instr.extend(instr_seq)
        instr.append(get_iter)
        instr.append(for_iter)
        instr.extend(instr_expr)
        instr.append(nop)

        if production:
            instr.append(BytecodeInstr('LOAD_CONST', 0))

        return instr

    def _compile_list_comprehension(self, tok, production=True):

        comp, body = tok.children

        instr = []

        instr.append(BytecodeInstr("BUILD_LIST", 0))
        instr.extend(self._comprehension_for(comp, 1, body, "LIST_APPEND"))

        return instr

    def _compile_set_comprehension(self, tok, production=True):

        comp, body = tok.children


        instr = []

        instr.append(BytecodeInstr("BUILD_SET", 0))
        instr.extend(self._comprehension_for(comp, 1, body, "SET_ADD"))

        return instr

    def _compile_dict_comprehension(self, tok, production=True):

        comp, body = tok.children

        instr = []

        instr.append(BytecodeInstr("BUILD_MAP", 0))
        instr.extend(self._comprehension_for(comp, 1, body, "MAP_ADD"))

        return instr

    def _comprehension_for(self, tok, depth, tok_assign, add_opcode_str):
        """
        a foreach loop dedicated to a comprehension

        tok: the token to compile
        depth: the recursion depth
        tok_assign: a token representing the expression body of a comprehension
        add_opcode_str: opcode for adding an item to an object
        """
        lbl_continue = self._make_label()
        lbl_done = self._make_label()

        instr = self._compile_load(tok.children[1])

        get_iter = BytecodeInstr('GET_ITER', lineno=tok.line)
        for_iter = BytecodeRelJumpInstr('FOR_ITER', lbl_done, lineno=tok.line)
        for_iter.add_label(lbl_continue)
        jmp = BytecodeJumpInstr('JUMP_ABSOLUTE', lbl_continue)

        instr.append(get_iter)
        instr.append(for_iter)
        instr.extend(self._compile_store(tok.children[0]))

        if len(tok.children) == 3:
            tmp = tok.children[2]
            if tmp.value == 'for':
                instr.extend(self._comprehension_for(tmp, depth + 1, tok_assign, add_opcode_str))
            if tmp.value == 'if':
                instr.extend(self._comprehension_if(tmp, depth, tok_assign, add_opcode_str))
        else:
            instr.extend(self._comprehension_assign(depth+1, tok_assign, add_opcode_str))

        instr.append(jmp)
        instr.append(BytecodeInstr('NOP'))
        instr[-1].add_label(lbl_done)

        return instr

    def _comprehension_if(self, tok, depth, tok_assign, add_opcode_str):
        """
        a branch instruction where only the true path can be taken

        tok: the token to compile
        depth: the recursion depth
        tok_assign: a token representing the expression body of a comprehension
        add_opcode_str: opcode for adding an item to an object
        """

        lbl = self._make_label()
        instr = self._compile_load(tok.children[0])

        instr.append(BytecodeJumpInstr('POP_JUMP_IF_FALSE', lbl))

        if len(tok.children) == 2:
            tmp = tok.children[2]
            if tmp.value == 'for':
                instr.extend(self._comprehension_for(tmp, depth + 1, tok_assign, add_opcode_str))
            if tmp.value == 'if':
                instr.extend(self._comprehension_if(tmp, depth, tok_assign, add_opcode_str))
        else:
            instr.extend(self._comprehension_assign(depth+1, tok_assign, add_opcode_str))

        instr.append(BytecodeInstr('NOP'))
        instr[-1].add_label(lbl)

        return instr

    def _comprehension_assign(self, depth, tok_assign, add_opcode_str):
        """

        depth: TOS[-depth] is the stack object to add an element to
        tok_assign: a token representing the expression body which
            computes the value to push to the object at TOS[-depth]
        add_opcode_str: the mechanism by which the item is added
            Python 3 has specific opcodes for list, set, map
        """

        if add_opcode_str == "MAP_ADD" and tok_assign.type != Token.S_SLICE:
            raise CompilerError(tok, "expected slice")

        instr = []

        if add_opcode_str == "MAP_ADD":
            # >= 3.8: dict.__setitem__(TOS1[-i], TOS1, TOS)
            # <= 3.7: dict.__setitem__(TOS1[-i], TOS, TOS1)

            key, val = tok_assign.children

            instr_key = self._compile(key)
            instr_val = self._compile(val)

            if sys.version_info >= (3, 8):
                instr.extend(instr_key)
                instr.extend(instr_val)
            else:
                instr.extend(instr_val)
                instr.extend(instr_key)

            instr.append(BytecodeInstr(add_opcode_str, depth))
        else:
            instr.extend(self._compile(tok_assign))
            instr.append(BytecodeInstr(add_opcode_str, depth))

        return instr

    def _compile_import(self, tok, production=True):

        if tok.type != Token.S_IMPORT:
            raise ValueError(str(tok))

        level, name, fromlist = tok.children
        instr = []

        if name.value not in self.bc.names:
            index = len(self.bc.names)
            self.bc.names.append(name.value)
        else:
            index = self.bc.names.index(name.value)

        instr.extend(self._compile_load(level))

        src_names = []
        dst_names = []
        if len(fromlist.children) == 0:
            instr.append(BytecodeInstr('LOAD_CONST', 0))
        else:

            for child in fromlist.children:
                if child.type == Token.S_LABEL:

                    kind, index = self._token2index(Token(Token.S_STRING, 0, 0, child.value))
                    instr.append(BytecodeInstr('LOAD_' + kind, index))

                    src_names.append(child.value)
                    dst_names.append(child.value)

                    if self.flags&Expression.CF_REPL or self.flags&Expression.CF_MODULE:
                        self.module_globals.add(child.value)

                elif len(child.children) == 2:

                    src, dst = child.children

                    kind, index = self._token2index(Token(Token.S_STRING, 0, 0, src.value))
                    instr.append(BytecodeInstr('LOAD_' + kind, index))

                    src_names.append(src.value)
                    dst_names.append(dst.value)

                    if self.flags&Expression.CF_REPL or self.flags&Expression.CF_MODULE:
                        self.module_globals.add(dst.value)
                else:
                    raise CompilerError(child, "unexpected in import")

            instr.append(BytecodeInstr('BUILD_TUPLE', len(src_names)))

        # TODO: refactor all instances like these into _token2index
        _, index = self._token2index_name(Token(Token.S_LABEL, 0, 0, name.value), load=True)
        instr.append(BytecodeInstr('IMPORT_NAME', index))

        for src_name, dst_name in zip(src_names, dst_names):
            src_kind, src_index = self._token2index_name(Token(Token.S_LABEL, 0, 0, src_name), load=True)
            dst_kind, dst_index = self._token2index_fast(Token(Token.S_LABEL, 0, 0, dst_name), load=False)
            instr.append(BytecodeInstr('IMPORT_FROM', src_index))
            instr.append(BytecodeInstr('STORE_' + dst_kind, dst_index))

        #instr.append(BytecodeInstr('BUILD_TUPLE', 0))
        # mod_name = name.value.split(".")[0]
        mod_name = tok.value

        # TODO: refactor all instances like these into _token2index

        # TODO: this uncovered a bug int _token2index
        # can't have a name and varname that are the same
        # need to record how a name was used, and warn
        # when a conflict is found on name/fast
        # record: other/name/fast

        #if mod_name not in self.bc.names:
        #    index = len(self.bc.names)
        #    self.bc.names.append(mod_name)
        #else:
        #    index = self.bc.names.index(mod_name)


        # store name or deref (load is true to force using name and not fast)
        kind, index = self._token2index(Token(Token.S_LABEL, name.line, name.index, mod_name), load=True)
        if production:
            instr.append(BytecodeInstr('DUP_TOP'))
        instr.append(BytecodeInstr('STORE_' + kind, index))

        if self.flags&Expression.CF_REPL or self.flags&Expression.CF_MODULE:
            self.module_globals.add(mod_name)

        #instr.extend(self._compile_load(Token(Token.S_LABEL, tok.line, tok.index, '__import__')))
        #instr.extend(self._compile_load(name))
        #instr.extend(self._compile_load(Token(Token.S_LABEL, tok.line, tok.index, 'globals')))
        #instr.append(BytecodeInstr('CALL_FUNCTION', 0))
        #instr.extend(self._compile_load(Token(Token.S_LABEL, tok.line, tok.index, 'locals')))
        #instr.append(BytecodeInstr('CALL_FUNCTION', 0))
        #instr.append(BytecodeInstr('BUILD_TUPLE', 0))
        #instr.extend(self._compile_load(level))
        #instr.append(BytecodeInstr('CALL_FUNCTION', 5))

        mod_name = name.value.split(".")[0]

        #if not mod_name and len(fromlist.children) == 0:
        #    raise CompilerError(name, "invalid import")

        #if not production:
        #    # TODO: process fromlist or store module
        #    instr.append(BytecodeInstr('POP_TOP'))
        #else:
        #    instr.append(BytecodeInstr('POP_TOP'))

        return instr

    def _compile_with(self, tok, production):

        # with expr : a, expr : b, expr : c { body }
        # [expr, slice, or tuple-of-slices], body

        if tok.type != Token.S_WITH:
            raise ValueError(str(tok))

        expr, body = tok.children

        setup_instr = []
        cleanup_instr = []
        body_instr = self._compile(body, False)

        labels = []
        exprs = []

        if expr.type == Token.S_TUPLE:
            for child in expr.children:
                #if child.type != Token.S_SLICE:
                #    raise CompilerError(child, "expected slice in tuple")
                if child.type != Token.S_SLICE:
                    labels.append(None)
                    exprs.append(child.children[0])
                else:
                    labels.append(child.children[0])
                    exprs.append(child.children[1])

        elif expr.type == Token.S_SLICE:
            labels.append(expr.children[0])
            exprs.append(expr.children[1])
        else:
            labels.append(None)
            exprs.append(expr)

        for lbl, exp in zip(labels, exprs):

            lbl_cleanup = self._make_label()
            setup_instr.extend(self._compile_load(exp))
            setup_instr.append(BytecodeRelJumpInstr('SETUP_WITH', lbl_cleanup, lineno=tok.line))
            if lbl is None:
                setup_instr.append(BytecodeInstr('POP_TOP', lineno=tok.line))
            else:
                kind, index = self._token2index(lbl)
                setup_instr.append(BytecodeInstr('STORE_' + kind, index, lineno=tok.line))

            cleanup_instr.append(BytecodeInstr('POP_BLOCK', lineno=tok.line))
            if sys.version_info >= (3, 8):
                cleanup_instr.append(BytecodeInstr('BEGIN_FINALLY', lineno=tok.line))
            else:
                cleanup_instr.append(BytecodeInstr('LOAD_CONST', 0, lineno=tok.line))

            cleanup_instr.append(BytecodeInstr('WITH_CLEANUP_START', lineno=tok.line))
            cleanup_instr[-1].add_label(lbl_cleanup)

            cleanup_instr.append(BytecodeInstr('WITH_CLEANUP_FINISH', lineno=tok.line))
            cleanup_instr.append(BytecodeInstr('END_FINALLY', lineno=tok.line))





        instr = []

        instr.extend(setup_instr)
        instr.extend(body_instr)
        instr.extend(cleanup_instr)

        if production:
            instr.append(BytecodeInstr('LOAD_CONST', 0))

        return instr

    def _compile_class(self, tok, production):
        """
             0 LOAD_BUILD_CLASS          |
             2 LOAD_CLOSURE            0 | cellvar: 'mycls'
             4 BUILD_TUPLE             1 |
             6 LOAD_CONST              1 |   const: <mycls:D:\Storage\public\code\python\ekanscrypt\ekanscrypt\compiler_test.py>
             8 LOAD_CONST              2 |   const: 'mycls'
            10 MAKE_FUNCTION           8 |
            12 LOAD_CONST              2 |   const: 'mycls'
            14 LOAD_GLOBAL             0 |  global: 'list'
            16 LOAD_GLOBAL             1 |  global: 'int'
            18 CALL_FUNCTION           4 |
            20 STORE_DEREF             0 | cellvar: 'mycls'
            22 LOAD_CONST              0 |   const: None
            24 RETURN_VALUE              |
        """

        paramlist, body = tok.children
        instr = []
        instr.append(BytecodeInstr('LOAD_BUILD_CLASS'))
        instr.extend(self._compile_lambda(body, expr_flags=Expression.CF_NO_FAST))
        instr.extend(self._compile_load(Token(Token.S_STRING, tok.line, tok.index, tok.value)))
        count = 0
        if len(paramlist.children)==0:
            instr.extend(self._compile_load(Token(Token.S_LABEL, tok.line, tok.index, 'object')))
            count = 1
        else:
            for param in paramlist.children:
                instr.extend(self._compile_load(param))
                count += 1
        instr.append(BytecodeInstr('CALL_FUNCTION', count + 2))
        if production:
            instr.append(BytecodeInstr('DUP_TOP', count + 2))
        instr.extend(self._compile_store(Token(Token.S_LABEL, tok.line, tok.index, tok.value)))
        return instr

    def _compile_class_init(self, tok, production=True):

        instr = []
        instr.extend(self._compile_load(Token(Token.S_LABEL, tok.line, tok.index, '__name__')))
        instr.extend(self._compile_store(Token(Token.S_LABEL, tok.line, tok.index, '__module__')))
        # TODO: qual name
        qualname = self.bc.name + "." + tok.value
        instr.extend(self._compile_load(Token(Token.S_STRING, tok.line, tok.index, qualname)))
        instr.extend(self._compile_store(Token(Token.S_LABEL, tok.line, tok.index, '__qualname__')))

        return instr

    def _compile_class_init2(self, tok, production=True):

        # 20 LOAD_CLOSURE            0 | cellvar: '__class__'
        # 22 DUP_TOP                   |
        # 24 STORE_NAME              4 |    name: '__classcell__'
        # 26 RETURN_VALUE              |

        instr = []
        _, index = self._token2index(Token(Token.S_REFERENCE, tok.line, tok.index, '__class__'), True)
        instr.append(BytecodeInstr('LOAD_CLOSURE', index))
        instr.append(BytecodeInstr('DUP_TOP'))
        instr.extend(self._compile_store(Token(Token.S_LABEL, tok.line, tok.index, '__classcell__')))
        instr.append(BytecodeInstr('RETURN_VALUE'))

        return instr

    def _compile_closure(self, tok):

        for child in tok.children:
            if self.flags&Expression.CF_REPL or self.flags&Expression.CF_MODULE:
                self.module_globals.add(child.value)
            self.bc.cellvars.append(child.value)
        return []

    def _compile_lambda(self, tok, production=True, expr_flags=0):

        if not tok.value:
            lambda_qualified_name = 'Anonymous_%d_%d_%d' % (
                tok.line, tok.index, self.depth)

        else:
            lambda_qualified_name = tok.value

        if not expr_flags&Expression.CF_NO_FAST:
            lambda_qualified_name = 'lambda.' + lambda_qualified_name
        else:
            lambda_qualified_name = lambda_qualified_name

        lambda_qualified_name = self.bc.name + "." + lambda_qualified_name

        namelist = tok.children[0]
        closure = tok.children[1]
        block = tok.children[2]

        subexpr = Expression(lambda_qualified_name, self.bc.filename, flags=expr_flags)
        subexpr.depth += 1

        disable_positional = False
        disable_keyword = False
        pos_kwarg_instr = []
        pos_kwarg_count = 0
        extra_args = [] # *args or **kwargs
        argcount = 0
        for argname in namelist.children:
            if argname.type == Token.S_PREFIX and argname.value in ('*', '**'):

                if argname.value == '*':
                    disable_positional = True
                    extra_args.append(argname.children[0].value)
                    subexpr.bc.flags |= CO_VARARGS

                if argname.value == '**':
                    disable_keyword = True
                    disable_positional = True
                    extra_args.append(argname.children[0].value)
                    subexpr.bc.flags |= CO_VARKEYWORDS

            elif argname.type == Token.S_LABEL:
                if disable_positional:
                    raise CompilerError(argname, "positional after keyword argument")
                subexpr.bc.varnames.append(argname.value)
                argcount += 1

            elif argname.type == Token.S_OPERATOR2 and argname.value == "=":
                if disable_keyword:
                    raise CompilerError(argname, "positional after keyword argument")
                pos_kwarg_count += 1
                lhs, rhs = argname.children
                if lhs.type != Token.S_LABEL:
                    raise CompilerError(lhs, "expected label")
                pos_kwarg_instr.extend(self._compile_load(rhs))
                subexpr.bc.varnames.append(lhs.value)
                disable_positional = True
                argcount += 1
            else:
                raise CompilerError(argname, "unexpected argument")

        subexpr.bc.varnames.extend(extra_args)

        closure_instr = []
        closure_count = 0

        # TODO: CF_NO_FAST is really 'CF_CLASS_BODY'
        if self.flags&Expression.CF_NO_FAST:
            label = Token(Token.S_REFERENCE, tok.line, tok.index, '__class__')
            kind, index = self._token2index(label, True)
            subexpr.bc.freevars.append(label.value)
            closure_instr.append(BytecodeInstr('LOAD_CLOSURE', index, lineno=tok.line))
            closure_count += 1

        for label in closure.children:
            kind, index = self._token2index(label, True)
            subexpr.bc.freevars.append(label.value)
            closure_instr.append(BytecodeInstr('LOAD_CLOSURE', index, lineno=tok.line))
            closure_count += 1

        # Note: this may set subexpr.flags CO_GENERATOR
        subexpr.bc.extend(subexpr._compile(block, True))
        if len(subexpr.bc) and subexpr.bc[-1].name != 'RETURN_VALUE':
                subexpr.bc.append(BytecodeInstr('RETURN_VALUE', lineno=tok.line))
        subexpr.bc.argcount = argcount
        subexpr._finalize()

        index_code = len(self.bc.consts)
        stacksize = calcsize(subexpr.bc)
        try:
            code = subexpr.bc.to_code(stacksize)
        except Exception as e:
            #subexpr.bc.to_code_debug()
            subexpr.dump()
            raise e

        self.bc.consts.append(code)

        index_name = len(self.bc.consts)
        self.bc.consts.append(lambda_qualified_name)

        instr = []

        kwarg_count = 0
        flg = 0

        if pos_kwarg_count:
            # push positional or kwarg arguments tuple
            instr.extend(pos_kwarg_instr)
            instr.append(BytecodeInstr('BUILD_TUPLE', pos_kwarg_count, lineno=tok.line))
            flg |= 0x01

        if False:
            # push kwarg only arguments tuple
            flg |= 0x02

        if False:
            # push annotated dictionary
            flg |= 0x04

        if closure_instr:
            # push the closure context
            instr.extend(closure_instr)
            instr.append(BytecodeInstr('BUILD_TUPLE', closure_count, lineno=tok.line))
            flg |= 0x08

        instr.append(BytecodeInstr('LOAD_CONST', index_code, lineno=tok.line))
        instr.append(BytecodeInstr('LOAD_CONST', index_name, lineno=tok.line))

        instr.append(BytecodeInstr('MAKE_FUNCTION', flg, lineno=tok.line))

        if not expr_flags&Expression.CF_NO_FAST and tok.value:
            instr.append(BytecodeInstr('DUP_TOP', lineno=tok.line))
            kind, index = self._token2index(Token(Token.S_LABEL, tok.line, tok.index, tok.value))
            instr.append(BytecodeInstr('STORE_' + kind, index, lineno=tok.line))

        return instr

    def _compile_block(self, tok, production=True):
        """
        compile a sequence of nodes, such that the last node
        may or may not produce some value
        """
        if tok.type != Token.S_BLOCK:
            raise ValueError(str(tok))

        instr = []

        for child in tok.children[:-1]:
            instr.extend(self._compile(child, False))

        if len(tok.children) == 0:
            if production:
                instr.append(BytecodeInstr('LOAD_CONST', 0, lineno=tok.line))
        else:
            instr.extend(self._compile(tok.children[-1], production))

        return instr

    def _compile_trycatch_3_7(self, tok, production=True):

        """

        this implementation is valid for python 3.7, 3.8
            first child: expr body
            chlid 2 - n : catch block
            last child, optional finally block
            TOKEN('S_TRYCATCH', 'try',
                TOKEN('S_CALL_FUNCTION', '',
                    TOKEN('S_LABEL', 'print')),
                TOKEN('S_KEYWORD', 'catch',
                    TOKEN('S_OPERATOR2', 'as',
                        TOKEN('S_LABEL', 'a'),
                        TOKEN('S_LABEL', 'b')),
                    TOKEN('S_BUILD', 'SET')),
                TOKEN('S_KEYWORD', 'catch',
                    TOKEN('S_OPERATOR2', 'as',
                        TOKEN('S_LABEL', 'x'),
                        TOKEN('S_LABEL', 'y')),
                    TOKEN('S_BUILD', 'SET')),
                TOKEN('S_KEYWORD', 'finally',
                    TOKEN('S_BUILD', 'SET')))
        """

        CMP_IDX = dis.cmp_op.index('exception match')

        lbl_catch = self._make_label()
        instr = []

        tok_body = tok.children[0]
        toklst_catch = tok.children[1:]
        tok_finally = None
        if toklst_catch[-1].type == Token.S_KEYWORD and toklst_catch[-1].value == 'finally':
            tok_finally = toklst_catch.pop()

        lbllst_catch = [self._make_label() for i in toklst_catch]
        lbllst_catch.append(self._make_label())

        lbl_finally = self._make_label()

        instr_finally = []
        if tok_finally:
            instr_finally.extend(self._compile(tok_finally.children[0], production=False))
        if len(instr_finally) == 0:
            instr_finally.append(BytecodeInstr("NOP"))
        if tok_finally and toklst_catch:
            tgt = self._make_label()
            instr_finally[0].add_label(tgt)
            instr.append(BytecodeRelJumpInstr('SETUP_FINALLY', tgt))

        if sys.version_info >= (3, 8):
            instr.append(BytecodeRelJumpInstr('SETUP_FINALLY', lbllst_catch[0]))
        else:
            if toklst_catch:
                instr.append(BytecodeRelJumpInstr('SETUP_EXCEPT', lbllst_catch[0]))
            else:
                instr.append(BytecodeRelJumpInstr('SETUP_FINALLY', lbllst_catch[0]))

        instr.extend(self._compile(tok_body, production=False))

        if toklst_catch:
            instr.append(BytecodeInstr('POP_BLOCK'))
            instr.append(BytecodeRelJumpInstr('JUMP_FORWARD', lbl_finally))

            for i, token in enumerate(toklst_catch):
                token_test, token_body = token.children
                lhs, rhs = token_test.children
                op = BytecodeInstr('DUP_TOP')
                instr.append(op)
                op.add_label(lbllst_catch[i])
                instr.extend(self._compile_load(lhs))

                instr.append(BytecodeInstr('COMPARE_OP', CMP_IDX))
                instr.append(BytecodeJumpInstr('POP_JUMP_IF_FALSE', lbllst_catch[i+1]))
                instr.append(BytecodeInstr('POP_TOP'))
                kind, index = self._token2index(rhs, load=False)
                instr.append(BytecodeInstr('STORE_' + kind, index))
                instr.append(BytecodeInstr('POP_TOP'))
                tgt = self._make_label()
                instr.append(BytecodeRelJumpInstr('SETUP_FINALLY', tgt))
                instr.extend(self._compile(token_body, production=False))
                instr.append(BytecodeInstr('POP_BLOCK'))
                if sys.version_info >= (3, 8):
                    instr.append(BytecodeInstr('BEGIN_FINALLY'))
                else:
                    instr.append(BytecodeInstr('LOAD_CONST', 0))
                instr.append(BytecodeInstr('LOAD_CONST', 0))
                instr[-1].add_label(tgt)
                instr.append(BytecodeInstr('STORE_' + kind, index))
                instr.append(BytecodeInstr('DELETE_' + kind, index))
                instr.append(BytecodeInstr('END_FINALLY'))
                instr.append(BytecodeInstr('POP_EXCEPT'))
                instr.append(BytecodeRelJumpInstr('JUMP_FORWARD', lbl_finally))

            instr.append(BytecodeInstr('END_FINALLY'))
            instr[-1].add_label(lbllst_catch[-1])

        if tok_finally:
            instr.append(BytecodeInstr('POP_BLOCK'))

            instr[-1].add_label(lbl_finally)
            if sys.version_info >= (3, 8):
                instr.append(BytecodeInstr('BEGIN_FINALLY'))
            else:
                instr.append(BytecodeInstr('LOAD_CONST', 0))
            if not toklst_catch:
                instr_finally[0].add_label(lbllst_catch[-1])
            instr.extend(instr_finally)
            instr.append(BytecodeInstr('END_FINALLY'))
        else:
            instr.append(BytecodeInstr('NOP'))
            instr[-1].add_label(lbl_finally)

        return instr

    def _compile_return(self, tok, production=True):

        if tok.type != Token.S_RETURN:
            raise ValueError(str(tok))

        #if len(tok.children) != 1: # TODO maybe allow 0 for None?
        #    raise ValueError(str(tok))

        #if production:
        #    raise CompilerError(tok, "return cannot produce a value")

        if self.flags&Expression.CF_MODULE:
            raise CompilerError(tok, "return in global scope")

        instr = []
        if len(tok.children) == 0:
            instr.append(BytecodeInstr('LOAD_CONST', 0, lineno=tok.line))
        else:
            instr.extend(self._compile_load(tok.children[0]))
        instr.append(BytecodeInstr('RETURN_VALUE', lineno=tok.line))

        return instr

    def _compile_raise(self, tok, production=True):

        # TODO: support RAISE with argc=2
        if tok.type != Token.S_RAISE:
            raise ValueError(str(tok))

        argc = len(tok.children)

        if self.flags&Expression.CF_MODULE:
            raise CompilerError(tok, "return in global scope")

        instr = []
        argc = 0
        if len(tok.children) == 1:
            instr.extend(self._compile_load(tok.children[0]))
            argc = 1

        instr.append(BytecodeInstr('RAISE_VARARGS', argc, lineno=tok.line))

        if production:
            instr.append(BytecodeInstr('LOAD_CONST', 0))

        return instr

    def _compile_continue(self, tok):
        counter = 1
        if tok.children:
            counter = parseNumber(tok.children[0])
            if not isinstance(counter, int):
                raise CompilerError(tok.children[0], "expected integer")
        return [BytecodeContinueInstr(tok, counter)]

    def _compile_break(self, tok):
        counter = 1
        if tok.children:
            counter = parseNumber(tok.children[0])
            if not isinstance(counter, int):
                raise CompilerError(tok.children[0], "expected integer")
        return [BytecodeBreakInstr(tok, counter)]

    def _compile_switch(self, tok, production=True):

        test, *rest = tok.children
        CMP_IDX = dis.cmp_op.index('==')

        instr = []
        instr_body = []
        instr_default = []

        # load the primary expression, the result will be compared
        # using == to all case statements.
        instr.extend(self._compile_load(test))

        # if this case falls through, next_label is the place to jump to
        # to handle the next case
        next_label = None
        # if all cases fall through, this is the instruction to jump to
        default_tgt = None

        lbl_break = self._make_label()

        for case in rest:

            if case.type == Token.S_SWITCH_CASE:

                tgt = self._make_label()
                case_value, case_body = case.children
                instr.append(BytecodeInstr('DUP_TOP'))
                if next_label:
                    instr[-1].add_label(next_label)
                instr.extend(self._compile_load(case_value))
                instr.append(BytecodeInstr('COMPARE_OP', CMP_IDX))
                next_label = self._make_label()
                instr.append(BytecodeJumpInstr('POP_JUMP_IF_FALSE', next_label))
                instr.append(BytecodeInstr('POP_TOP'))
                instr.append(BytecodeRelJumpInstr('JUMP_FORWARD', tgt))

                tmp = self._compile(case_body, production=False)
                if not tmp:
                    tmp = [BytecodeInstr('NOP')]
                tmp[0].add_label(tgt)
                instr_body.extend(tmp)
            elif case.type == Token.S_SWITCH_DEFAULT:
                case_body = case.children[0]
                if default_tgt:
                    raise CompilerError(case, 'multiple default targets')
                instr.append(BytecodeInstr('NOP'))
                if next_label:
                    instr[-1].add_label(next_label)
                    next_label = None

                default_tgt = self._make_label()
                tmp = self._compile(case_body, production=False)
                if not tmp:
                    tmp = [BytecodeInstr('NOP')]
                tmp[0].add_label(default_tgt)
                instr_body.extend(tmp)

            else:
                raise CompilerError(case, "expected keyword case or default")

        # if there was no default given, the default case should just break
        if not default_tgt:
            default_tgt = lbl_break

        # in the default case pop top and jump to the
        # default block if there is one
        instr.append(BytecodeInstr('POP_TOP'))
        instr.append(BytecodeRelJumpInstr('JUMP_FORWARD', default_tgt))

        if next_label:
            instr[-1].add_label(next_label)
        instr.extend(instr_body)
        instr.append(BytecodeInstr('NOP'))
        instr[-1].add_label(lbl_break)

        # fix the break keywords that resolve in this scope
        # continue is not supported, so don't update those and
        # therefore use zero as the first argument here
        for op in instr:
            if isinstance(op, BytecodeBreakInstr):
                op.update(0, lbl_break)



        return instr

    def _compile_subscr(self, tok, production=True):
        """

        subscr{expr, index0, [index1, index2]}
        """

        if tok.type != Token.S_SUBSCR:
            raise ValueError(str(tok))

        instr = []

        ############
        # load the function
        tokf = tok.children[0]
        optional = False
        if tokf.type == Token.S_OPTIONAL_ATTR and len(tokf.children) == 1:
            optional = True
            tokf = tokf.children[0]
        instr.extend(self._compile_load(tokf))

        nop = None
        if optional:
            lbl = self._make_label()
            instr.append(BytecodeInstr('DUP_TOP'))
            instr.append(BytecodeInstr("LOAD_CONST", 0))
            instr.append(BytecodeInstr("COMPARE_OP", dis.cmp_op.index('is')))
            instr.append(BytecodeJumpInstr("POP_JUMP_IF_TRUE", lbl))

            nop = BytecodeInstr("NOP")
            nop.add_label(lbl)

        ############

        # load subscr args
        for child in tok.children[1:]:
            instr.extend(self._compile_load(child))

        instr.append(BytecodeInstr('BINARY_SUBSCR', lineno=tok.line))

        if optional:
            instr.append(nop)

        if not production:
            instr.append(BytecodeInstr('POP_TOP', lineno=tok.line))

        return instr

    def _compile_slice(self, tok, production=True):
        """

        """

        if tok.type != Token.S_SLICE:
            raise ValueError(str(tok))

        instr = []

        count = 0
        if len(tok.children) == 0:
            count = 2
            instr.append(BytecodeInstr('LOAD_CONST', 0))
            instr.append(BytecodeInstr('LOAD_CONST', 0))
        else:
            for child in tok.children:
                instr.extend(self._compile_load(child))
                count += 1

        instr.append(BytecodeInstr('BUILD_SLICE', count, lineno=tok.line))

        if not production:
            instr.append(BytecodeInstr('POP_TOP', lineno=tok.line))

        return instr

    def _compile_gstring(self, tok, production=True):

        if tok.type != Token.S_GLOB_STRING:
            raise ValueError(str(tok))

        instr = []

        # load function
        kind, index = self._token2index(Token(Token.S_LABEL, 1, 0, "__es_glob__"))
        instr.append(BytecodeInstr('LOAD_' + kind, index, lineno=tok.line))
        # load argument
        kind, index = self._token2index(tok, True)
        instr.append(BytecodeInstr('LOAD_' + kind, index, lineno=tok.line))
        instr.append(BytecodeInstr('CALL_FUNCTION', 1))
        if not production:
            instr.append(BytecodeInstr('POP_TOP', lineno=tok.line))

        return instr

    def _compile_fstring(self, tok, production=True):

        if tok.type != Token.S_FORMAT_STRING:
            raise ValueError(str(tok))

        instr = []

        # load function
        kind, index = self._token2index(Token(Token.S_LABEL, 1, 0, "__es_format__"))
        instr.append(BytecodeInstr('LOAD_' + kind, index, lineno=tok.line))
        # load argument
        kind, index = self._token2index(tok, True)
        instr.append(BytecodeInstr('LOAD_' + kind, index, lineno=tok.line))
        instr.append(BytecodeInstr('CALL_FUNCTION', 1))
        if not production:
            instr.append(BytecodeInstr('POP_TOP', lineno=tok.line))

        return instr

    def _compile_rstring(self, tok, production=True):

        if tok.type != Token.S_REGEX_STRING:
            raise ValueError(str(tok))

        instr = []

        # load function
        kind, index = self._token2index(Token(Token.S_LABEL, 1, 0, "__es_regex__"))
        instr.append(BytecodeInstr('LOAD_' + kind, index, lineno=tok.line))
        # load argument
        kind, index = self._token2index(tok, True)
        instr.append(BytecodeInstr('LOAD_' + kind, index, lineno=tok.line))
        instr.append(BytecodeInstr('CALL_FUNCTION', 1))
        if not production:
            instr.append(BytecodeInstr('POP_TOP', lineno=tok.line))

        return instr

    def _compile_optional(self, tok, production=True):
        """ implement optional chaining operator

        examples:
            a?.b

        return `a.b` as long as a is not None else return `a`
        """

        if len(tok.children) != 2:
            raise CompilerError(tok, "invalid operator")
        instr = []
        lhs = self._compile_load(tok.children[0])
        attr = tok.children[1]
        try:
            index = self.bc.names.index(attr.value)
        except ValueError:
            index = len(self.bc.names)
            self.bc.names.append(attr.value)
        rhs = [BytecodeInstr('LOAD_ATTR', index, lineno=tok.line)]

        lbl = self._make_label()
        nop = BytecodeInstr("NOP")
        nop.add_label(lbl)

        instr.extend(lhs)
        instr.append(BytecodeInstr('DUP_TOP'))
        instr.append(BytecodeInstr("LOAD_CONST", 0))
        # TODO: 'is' or '==': equals would allow users to override behavior
        instr.append(BytecodeInstr("COMPARE_OP", dis.cmp_op.index('is')))
        instr.append(BytecodeJumpInstr("POP_JUMP_IF_TRUE", lbl))
        instr.extend(rhs)
        instr.append(nop)
        if not production:
            instr.append(BytecodeInstr('POP_TOP', lineno=tok.line))

        return instr

    def _compile_yield(self, tok, production=True):

        if tok.type != Token.S_YIELD:
            raise ValueError(str(tok))

        if self.flags&Expression.CF_MODULE:
            raise CompilerError(tok, "yield in global scope")

        self.bc.flags |= CO_GENERATOR

        instr = self._compile_load(tok.children[0])
        instr.append(BytecodeInstr('YIELD_VALUE'))

        if production:
            instr.append(BytecodeInstr('LOAD_CONST', 0))

        return instr

    def _compile_yield_from(self, tok, production=True):

        if tok.type != Token.S_YIELD_FROM:
            raise ValueError(str(tok))

        if self.flags&Expression.CF_MODULE:
            raise CompilerError(tok, "yield in global scope")

        self.bc.flags |= CO_GENERATOR

        instr = self._compile_load(tok.children[0])
        instr.append(BytecodeInstr('GET_YIELD_FROM_ITER'))
        # TODO: this load const appears in 3.7/3.8 but not sure why
        instr.append(BytecodeInstr('LOAD_CONST', 0))
        instr.append(BytecodeInstr('YIELD_FROM'))
        instr.append(BytecodeInstr('POP_TOP'))

        if production:
            instr.append(BytecodeInstr('LOAD_CONST', 0))
        return instr

    def _compile_store(self, tok):
        """ compile the token to store TOS """
        if tok.type == Token.S_TUPLE:
            n = len(tok.children)
            instr = [BytecodeInstr('UNPACK_SEQUENCE', n, lineno=tok.line)]

            for child in tok.children:
                instr.extend(self._compile_store(child))
            return instr
        elif tok.type == Token.S_SUBSCR:
            instr = self._compile_load(tok.children[0])
            instr.extend(self._compile_load(tok.children[1]))
            instr.append(BytecodeInstr('STORE_SUBSCR', lineno=tok.line))
            return instr
        #elif tok.type == Token.S_OPERATOR2 and tok.value == ".":
        #    # TODO: is this unreachable now?
        #    instr = self._compile_load(tok.children[0])
        #    # TODO: may need special index method option
        #    _, index = self._token2index(tok.children[1], True)
        #    instr.append(BytecodeInstr('STORE_ATTR', index, lineno=tok.line))
        #    return instr
        elif tok.type == Token.S_ATTR:
            instr = self._compile_load(tok.children[0])
            # TODO: may need special index method option
            _, index = self._token2index(tok.children[1], True)
            instr.append(BytecodeInstr('STORE_ATTR', index, lineno=tok.line))
            return instr
        else:
            kind, index = self._token2index(tok, False)
            if kind == 'CONST':
                return []
            return [BytecodeInstr('STORE_' + kind, index, lineno=tok.line)]

    def _compile_load(self, tok):
        """ compile the token and store expression result on TOS

        helper function to signal intent, mirror _compile_store
        """
        return self._compile(tok, True)

def compiler(asf, filename="<string>"):

    expr = Expression("__main__", filename)

    expr.compile(asf)

    return expr

def main():  # pragma: no cover
    import sys
    from .lexer import lexer
    from .parser import parser
    from .exception import TokenError

    # tokens = lexer(r"f=(x)=>{if(x>1){return f(x-1);}else{return 0;}};f(2);")
    #tokens = lexer("f = () => {return io;}; print(f().stdout)")
    # text = "x=[]"

    # text = "a = (x) => x+1; b = (x) => a(x); b(0)"
    text = None
    path = "<string>"

    xtext = """
        f = () => {x=0; return () => {x += 1}}
        g = f()
        print(f()())
        print(f()())
        print(g())
        print(g())
        print(g())
    """

    if text is None:
        path = sys.argv[1]
        # path = "samples/fibonachi.es"
        # path = "samples/mergesort.es"
        # path = "samples/json.es"
        # path = "samples/objects.es"
        if path == '-':
            text = sys.stdin.read()
        else:
            with open(path, "r") as src:
                text = src.read()
    try:
        tokens = list(lexer(text))
        c2 = Token.count
        asf = parser(tokens)
        c3 = Token.count
        #for tok in asf:
        #    print(tok.toString(True))
        expr = compiler(asf, path)
        c4 = Token.count

        print(expr)
        expr.dump()

        sys.stdout.write("Tokens: %d %d %d\n" % (c2 ,c3 ,c4))
        sys.stdout.write("\nOutput of %s\n" % path)
        sys.stdout.write("=" * 79 + "\n")
        expr.execute()
        sys.stdout.write("=" * 79 + "\n")
    except TokenError as e:
        e.format(path, text)
    except Exception as e:
        format_generic(*sys.exc_info())

if __name__ == '__main__':  # pragma: no cover
    main()

