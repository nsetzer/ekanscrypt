#! cd .. && python3 -m tests.compiler_test

"""
code(argcount, posonlyargcount, kwonlyargcount, nlocals, stacksize,
 |        flags, codestring, constants, names, varnames, filename, name,
 |        firstlineno, lnotab[, freevars[, cellvars]])

S_FOREACH<1,3,'for'>
  S_LABEL<1,5,'i'>
  S_BUILD<1,6,'LIST'>
    S_NUMBER<1,8,'1'>
    S_NUMBER<1,10,'2'>
    S_NUMBER<1,12,'3'>
  S_CALL_FUNCTION<1,20,''>
    S_LABEL<1,20,'print'>
    S_LABEL<1,22,'i'>

 0    LOAD_GLOBAL 0
  2    GET_ITER
  4    FOR_ITER 12
  6    STORE_FAST 0
  8    LOAD_GLOBAL 1
 10    LOAD_FAST 0
 12    CALL_FUNCTION 1
 14    POP_TOP
 16    JUMP_ABSOLUTE 4
 18    LOAD_CONST 0
 20    RETURN_VALUE

 0    SETUP_LOOP 26
  2    LOAD_GLOBAL 0
  4    GET_ITER
  6    FOR_ITER 18
  8    UNPACK_SEQUENCE 2
 10    STORE_FAST 0
 12    STORE_FAST 1
 14    LOAD_GLOBAL 1
 16    LOAD_FAST 0
 18    LOAD_FAST 1
 20    CALL_FUNCTION 2
 22    POP_TOP
 24    JUMP_ABSOLUTE 6
 26    POP_BLOCK
 28    LOAD_CONST 0
 30    RETURN_VALUE

"""
import sys
import unittest

import dis
from ekanscrypt.token import Token
from ekanscrypt.compiler import dump, compiler
from ekanscrypt.lexer import lexer
from ekanscrypt.parser import parser
from ekanscrypt.util import edit_distance

from bytecode import ConcreteInstr, ConcreteBytecode

VERSION = sys.version_info[:2]

def opcmp(op1, op2):
    if op1 is None:
        return False
    if op2 is None:
        return False
    return op1.name == op2.name and op1.arg == op2.arg

def opstr(op):
    if op.require_arg():
        return "%s:%s" % (op.name, op.arg)
    else:
        return op.name

def discmp(bc_expected, bc_actual, debug=False):

    seq, cor, sub, ins, del_ = edit_distance(bc_expected, bc_actual, opcmp)
    error_count = sub + ins + del_
    if error_count > 0 or debug:
        print("\ncor: %d, sub: %d ins: %d del: %d" % (cor, sub, ins, del_))

        print(dir(bc_expected))
        for name in ["consts", "names", "varnames", "argcount", "freevars", "cellvars"]:
            print("%s:" % name)
            print("    ", getattr(bc_expected, name))
            print("    ", getattr(bc_actual, name))

        print("\n--- %-38s | --- %-38s" % (
            "HYP (%d)" % len(bc_actual),
            "REF (%d)" % len(bc_expected))
        )

        lsize = 0
        rsize = 0
        for a, b in seq:
            sa = opstr(a) if a is not None else "    DEL"
            sb = opstr(b) if b is not None else "    INS"
            c = ' ' if opcmp(a, b) else "|"
            print("%3d %-38s %s %3d %-38s" % (lsize, sa, c, rsize, sb))
            lsize += a.size if a else 0
            rsize += b.size if b else 0

    return error_count

class CompilerTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        pass

    @classmethod
    def tearDownClass(cls):
        pass

    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    def test_001_basic_expr_1(self):

        def test():
            x = 1
            x = x + 2

        bc_expected = ConcreteBytecode.from_code(test.__code__)

        label_x = Token(Token.S_LABEL, 1, 0, "x")
        const_1 = Token(Token.S_NUMBER, 1, 0, "1")
        const_2 = Token(Token.S_NUMBER, 1, 0, "2")
        operator_assign1 = Token(Token.S_OPERATOR2, 1, 0, "=")
        operator_assign2 = Token(Token.S_OPERATOR2, 1, 0, "=")
        operator_add = Token(Token.S_OPERATOR2, 1, 0, "+")

        operator_assign1.children = [label_x, const_1]
        operator_add.children = [label_x, const_2]
        operator_assign2.children = [label_x, operator_add]

        asf = [operator_assign1, operator_assign2]

        expr = compiler(asf)

        self.assertFalse(discmp(bc_expected, expr.bc, False))

    def test_001_basic_expr_2(self):

        def test():
            x=1
            x.y = 2

        bc_expected = ConcreteBytecode.from_code(test.__code__)

        label_x = Token(Token.S_LABEL, 1, 0, "x")
        label_y = Token(Token.S_LABEL, 1, 0, "y")
        const_1 = Token(Token.S_NUMBER, 1, 0, "1")
        const_2 = Token(Token.S_NUMBER, 1, 0, "2")
        operator_assign1 = Token(Token.S_OPERATOR2, 1, 0, "=")
        operator_assign2 = Token(Token.S_OPERATOR2, 1, 0, "=")
        operator_getattr = Token(Token.S_ATTR, 1, 0, ".")

        operator_getattr.children = [label_x, label_y]
        operator_assign1.children = [label_x, const_1]
        operator_assign2.children = [operator_getattr, const_2]

        asf = [operator_assign1, operator_assign2]

        expr = compiler(asf)

        self.assertFalse(discmp(bc_expected, expr.bc, False))

    def test_001_basic_expr_3(self):

        def test():
            x=1
            x[0] = 2

        bc_expected = ConcreteBytecode.from_code(test.__code__)

        label_x = Token(Token.S_LABEL, 1, 0, "x")
        label_y = Token(Token.S_LABEL, 1, 0, "x")
        const_0 = Token(Token.S_NUMBER, 1, 0, "0")
        const_1 = Token(Token.S_NUMBER, 1, 0, "1")
        const_2 = Token(Token.S_NUMBER, 1, 0, "2")
        operator_assign1 = Token(Token.S_OPERATOR2, 1, 0, "=")
        operator_assign2 = Token(Token.S_OPERATOR2, 1, 0, "=")
        operator_setattr = Token(Token.S_SUBSCR, 1, 0, "")

        operator_setattr.children = [label_x, const_0]
        operator_assign1.children = [label_x, const_1]
        operator_assign2.children = [operator_setattr, const_2]

        asf = [operator_assign1, operator_assign2]

        expr = compiler(asf)

        self.assertFalse(discmp(bc_expected, expr.bc, False))

    def test_001_basic_expr_4(self):

        def test():
            return 7

        bc_expected = ConcreteBytecode.from_code(test.__code__)

        label_r = Token(Token.S_RETURN, 1, 0, "")
        const_7 = Token(Token.S_NUMBER, 1, 0, "7")

        label_r.children = [const_7]

        asf = [label_r]

        expr = compiler(asf)

        self.assertFalse(discmp(bc_expected, expr.bc, False))

    def test_001_basic_expr_5(self):

        def test():
            a=0
            a.b

        bc_expected = ConcreteBytecode.from_code(test.__code__)

        operator_assign1 = Token(Token.S_OPERATOR2, 1, 0, "=")

        label_attr = Token(Token.S_ATTR, 1, 0, ".")
        label_a = Token(Token.S_LABEL, 1, 0, "a")
        label_b = Token(Token.S_LABEL, 1, 0, "b")
        const_0 = Token(Token.S_NUMBER, 1, 0, "0")

        operator_assign1.children = [label_a, const_0]
        label_attr.children = [label_a, label_b]

        asf = [operator_assign1, label_attr]

        expr = compiler(asf)

        self.assertFalse(discmp(bc_expected, expr.bc, False))

    def test_002_build_expr_list_1(self):

        def test():
            x=[1,2,3]

        bc_expected = ConcreteBytecode.from_code(test.__code__)

        label_x = Token(Token.S_LABEL, 1, 0, "x")
        const_1 = Token(Token.S_NUMBER, 1, 0, "1")
        const_2 = Token(Token.S_NUMBER, 1, 0, "2")
        const_3 = Token(Token.S_NUMBER, 1, 0, "3")
        build_list = Token(Token.S_BUILD, 1, 0, "LIST")

        operator_assign1 = Token(Token.S_OPERATOR2, 1, 0, "=")

        build_list.children = [const_1, const_2, const_3]
        operator_assign1.children = [label_x, build_list]

        asf = [operator_assign1]

        expr = compiler(asf)

        self.assertFalse(discmp(bc_expected, expr.bc, False))

    def test_002_build_expr_map_1(self):

        # 3.6 added BUILD_CONST_KEY_MAP
        # which will optimize certain types of maps
        # this will cause some comparisons to fail

        def test():
            y=1
            x={y:1, 2:3}

        bc_expected = ConcreteBytecode.from_code(test.__code__)

        label_x = Token(Token.S_LABEL, 1, 0, "x")
        label_y = Token(Token.S_LABEL, 1, 0, "y")
        const_0 = Token(Token.S_NUMBER, 1, 0, "0")
        const_1 = Token(Token.S_NUMBER, 1, 0, "1")
        const_2 = Token(Token.S_NUMBER, 1, 0, "2")
        const_3 = Token(Token.S_NUMBER, 1, 0, "3")
        build_map = Token(Token.S_BUILD, 1, 0, "MAP")

        operator_assign1 = Token(Token.S_OPERATOR2, 1, 0, "=")
        operator_assign2 = Token(Token.S_OPERATOR2, 1, 0, "=")

        operator_assign1.children = [label_y, const_1]
        build_map.children = [label_y, const_1, const_2, const_3]
        operator_assign2.children = [label_x, build_map]

        asf = [operator_assign1, operator_assign2]

        expr = compiler(asf)

        self.assertFalse(discmp(bc_expected, expr.bc, False))

    def test_003_advanced_expr_1(self):

        def test():
            x = 1
            print(x)

        bc_expected = ConcreteBytecode.from_code(test.__code__)

        label_x = Token(Token.S_LABEL, 1, 0, "x")
        const_1 = Token(Token.S_NUMBER, 1, 0, "1")
        label_print = Token(Token.S_LABEL, 1, 0, "print")
        operator_assign1 = Token(Token.S_OPERATOR2, 1, 0, "=")
        operator_call = Token(Token.S_CALL_FUNCTION, 1, 0, "")

        operator_assign1.children = [label_x, const_1]
        operator_call.children = [label_print, label_x]

        asf = [operator_assign1, operator_call]

        expr = compiler(asf)

        self.assertFalse(discmp(bc_expected, expr.bc, False))

    def test_004_subscr_expr_1(self):

        def test():
            x = []
            x[:1]

        bc_expected = ConcreteBytecode.from_code(test.__code__)

        label_x = Token(Token.S_LABEL, 1, 0, "x")
        const_0 = Token(Token.S_NONE, 1, 0, "")
        const_1 = Token(Token.S_NUMBER, 1, 0, "1")
        operator_build = Token(Token.S_BUILD, 1, 0, "LIST")
        operator_subscr = Token(Token.S_SUBSCR, 1, 0, "")
        operator_slice = Token(Token.S_SLICE, 1, 0, "")
        operator_assign = Token(Token.S_OPERATOR2, 1, 0, "=")

        operator_assign.children = [label_x, operator_build]
        operator_slice.children = [const_0, const_1]
        operator_subscr.children = [label_x, operator_slice]

        asf = [operator_assign, operator_subscr]

        expr = compiler(asf)

        self.assertFalse(discmp(bc_expected, expr.bc, False))

    def xxx_test_003_advanced_expr_2(self):

        def test():
            x = 1
            y = x[0:1:2]

        bc_expected = ConcreteBytecode.from_code(test.__code__)

        label_x = Token(Token.S_LABEL, 1, 0, "x")
        const_1 = Token(Token.S_NUMBER, 1, 0, "1")
        const_2 = Token(Token.S_NUMBER, 1, 0, "2")
        operator_assign1 = Token(Token.S_OPERATOR2, 1, 0, "=")
        operator_assign2 = Token(Token.S_OPERATOR2, 1, 0, "=")
        operator_add = Token(Token.S_OPERATOR2, 1, 0, "+")

        operator_assign1.children = [label_x, const_1]
        operator_add.children = [label_x, const_2]
        operator_assign2.children = [label_x, operator_add]

        asf = [operator_assign1, operator_assign2]

        expr = compiler(asf)

        self.assertFalse(discmp(bc_expected, expr.bc, False))

    def xtest_004_ctrl_if_1(self):

        def test():
            x = 1
            if x:
                x = 2

        bc_expected = ConcreteBytecode.from_code(test.__code__)

        label_x = Token(Token.S_LABEL, 1, 0, "x")
        const_1 = Token(Token.S_NUMBER, 1, 0, "1")
        const_2 = Token(Token.S_NUMBER, 1, 0, "2")
        operator_assign1 = Token(Token.S_OPERATOR2, 1, 0, "=")
        operator_assign2 = Token(Token.S_OPERATOR2, 1, 0, "=")
        operator_if = Token(Token.S_BRANCH, 1, 0, "")

        operator_assign1.children = [label_x, const_1]
        operator_assign2.children = [label_x, const_2]
        operator_if.children = [label_x, operator_assign2, None]

        asf = [operator_assign1, operator_if]

        expr = compiler(asf)

        self.assertFalse(discmp(bc_expected, expr.bc, False))

    @unittest.skip("too many variables")
    def test_004_ctrl_for_2(self):

        def test():
            try:
                print()
            except Exception as e:
                print()
            finally:
                print()

        bc_expected = ConcreteBytecode.from_code(test.__code__)

        dump(bc_expected)

        self.fail()

    def test_004_trycatch_1(self):

        def test():
            try:
                print()
            except a as b:
                print()
            finally:
                print()

        text = r"try print() catch a as b print() finally print()"
        tokens = list(lexer(text))
        asf = parser(tokens)
        expr = compiler(asf)

        # the different compilers disagree on global/name
        bc_expected = ConcreteBytecode.from_code(test.__code__)
        for idx, op in enumerate(bc_expected):
            if op.name == 'LOAD_GLOBAL':
                if op.arg == 1:
                    bc_expected[idx] = ConcreteInstr('LOAD_NAME', op.arg)

        self.assertFalse(discmp(bc_expected, expr.bc, False))

    def test_004_trycatch_2(self):

        def test():
            try:
                print()
            except a as b:
                print()
            except c as d:
                print()
            finally:
                print()

        text = r"try print() catch a as b print() catch c as d print() finally print()"
        tokens = list(lexer(text))
        asf = parser(tokens)
        expr = compiler(asf)

        # the different compilers disagree on global/name
        bc_expected = ConcreteBytecode.from_code(test.__code__)
        for idx, op in enumerate(bc_expected):
            if op.name == 'LOAD_GLOBAL':
                if op.arg == 1 or op.arg == 2:
                    bc_expected[idx] = ConcreteInstr('LOAD_NAME', op.arg)

        self.assertFalse(discmp(bc_expected, expr.bc, False))

    def test_004_trycatch_3(self):

        def test():
            try:
                print()
            except a as b:
                print()

        text = r"try print() catch a as b print()"
        tokens = list(lexer(text))
        asf = parser(tokens)
        expr = compiler(asf)

        # the different compilers disagree on global/name
        bc_expected = ConcreteBytecode.from_code(test.__code__)
        for idx, op in enumerate(bc_expected):
            if op.name == 'LOAD_GLOBAL':
                if op.arg == 1 or op.arg == 2:
                    bc_expected[idx] = ConcreteInstr('LOAD_NAME', op.arg)
        bc_expected.pop()
        bc_expected.pop()
        expr.bc.pop()
        expr.bc.pop()
        bc_expected.append(ConcreteInstr("NOP"))

        self.assertFalse(discmp(bc_expected, expr.bc, False))

    def test_004_trycatch_4(self):

        def test():
            try:
                print()
            finally:
                print()

        text = r"try print() finally print()"
        tokens = list(lexer(text))
        asf = parser(tokens)
        expr = compiler(asf)

        # the different compilers disagree on global/name
        bc_expected = ConcreteBytecode.from_code(test.__code__)
        for idx, op in enumerate(bc_expected):
            if op.name == 'LOAD_GLOBAL':
                if op.arg == 1 or op.arg == 2:
                    bc_expected[idx] = ConcreteInstr('LOAD_NAME', op.arg)
        bc_expected.pop()
        bc_expected.pop()
        expr.bc.pop()
        expr.bc.pop()

        self.assertFalse(discmp(bc_expected, expr.bc, False))

    def test_004_with_1(self):

        def test():
            with a:
                a

        text = r"with a {a}"
        tokens = list(lexer(text))
        asf = parser(tokens)
        expr = compiler(asf)

        # the different compilers disagree on global/name
        bc_expected = ConcreteBytecode.from_code(test.__code__)
        for idx, op in enumerate(bc_expected):
            if op.name == 'LOAD_GLOBAL':
                bc_expected[idx] = ConcreteInstr('LOAD_NAME', op.arg)

        self.assertFalse(discmp(bc_expected, expr.bc, False))

    @unittest.skip("too many variables")
    def test_004_with_2(self):

        def test():
            with a as b:
                a

        text = r"with b=a {a}"
        tokens = list(lexer(text))
        asf = parser(tokens)
        expr = compiler(asf)

        # the different compilers disagree on global/name
        bc_expected = ConcreteBytecode.from_code(test.__code__)
        for idx, op in enumerate(bc_expected):
            if op.name == 'LOAD_GLOBAL':
                bc_expected[idx] = ConcreteInstr('LOAD_NAME', op.arg)

        self.assertFalse(discmp(bc_expected, expr.bc, False))

    @unittest.skip("too many variables")
    def test_004_ctrl_while_1(self):

        def test():
            x = 0
            while x < 2:
                x = x + 1

        bc_expected = ConcreteBytecode.from_code(test.__code__)

        label_x = Token(Token.S_LABEL, 1, 0, "x")
        const_0 = Token(Token.S_NUMBER, 1, 0, "0")
        const_1 = Token(Token.S_NUMBER, 1, 0, "1")
        const_2 = Token(Token.S_NUMBER, 1, 0, "2")
        operator_assign1 = Token(Token.S_OPERATOR2, 1, 0, "=")
        operator_test = Token(Token.S_OPERATOR2, 1, 0, "<")
        operator_add = Token(Token.S_OPERATOR2, 1, 0, "+")
        operator_expr = Token(Token.S_OPERATOR2, 1, 0, "=")
        operator_while = Token(Token.S_WHILE, 1, 0, "")

        operator_assign1.children = [label_x, const_0]
        operator_add.children = [label_x, const_1]
        operator_expr.children = [label_x, operator_add]
        operator_test.children = [label_x, const_2]
        operator_while.children = [operator_test, operator_expr]

        asf = [operator_assign1, operator_while]

        expr = compiler(asf)

        # this test is dependent on python version
        # 3.8 removed SETUP_LOOP
        # for 3.7 and older, modify the expected output
        i = 0
        while i < len(bc_expected):
            if bc_expected[i].name == 'SETUP_LOOP':
                del bc_expected[i]
            if bc_expected[i].name == 'POP_BLOCK':
                del bc_expected[i]
            if bc_expected[i].name == 'POP_JUMP_IF_FALSE':
                bc_expected[i].arg = 20
            i += 1

        self.assertFalse(discmp(bc_expected, expr.bc, False))
        result = expr.execute()
        self.assertEqual(result, 1)

    @unittest.skip("too many variables")
    def test_004_ctrl_for_1(self):

        def test():
            for x in range(5):
                print(x)

        bc_expected = ConcreteBytecode.from_code(test.__code__)

        dump(bc_expected)

        self.assertFail()

    def xxxtest_lambda(self):

        def test():
            f = lambda x : x + 1
            f(0)

        g = lambda x: x +1
        bc_expected = ConcreteBytecode.from_code(g.__code__)
        print(" >>>>>>>>>>>>>>>>>>")
        self.assertFalse(discmp(bc_expected, bc_expected, True))
        print(" >>>>>>>>>>>>>>>>>>")

    @unittest.skip("fixme")
    def test_005_lambda_1(self):

        """
        f = x => x + 1
        return f(2)
        """

        bc_expected = ConcreteBytecode()
        bc_expected.names = []
        bc_expected.varnames = []
        bc_expected.consts = [None]
        bc_expected.extend([
            ConcreteInstr('LOAD_CONST', 1),
            ConcreteInstr('LOAD_CONST', 2),
            ConcreteInstr('MAKE_FUNCTION', 0),
            ConcreteInstr('STORE_FAST', 0),
            ConcreteInstr('LOAD_FAST', 0),
            ConcreteInstr('LOAD_CONST', 3),
            ConcreteInstr('CALL_FUNCTION', 1),
            ConcreteInstr('RETURN_VALUE')
        ])

        label_print = Token(Token.S_LABEL, 1, 0, "print")
        label_x = Token(Token.S_LABEL, 1, 0, "x")
        label_f = Token(Token.S_LABEL, 1, 0, "f")
        operator_lambda = Token(Token.S_LAMBDA, 1, 0, "1")
        const_2 = Token(Token.S_NUMBER, 1, 0, "2")
        const_1 = Token(Token.S_NUMBER, 1, 0, "1")
        operator_assign1 = Token(Token.S_OPERATOR2, 1, 0, "=")
        operator_assign2 = Token(Token.S_OPERATOR2, 1, 0, "=")
        operator_add = Token(Token.S_OPERATOR2, 1, 0, "+")

        closure = Token(Token.S_LAMBDA_CLOSURE, 1, 0, "")
        closure.children = []

        namelist = Token(Token.S_LAMBDA_NAMELIST, 1, 0, "")
        namelist.children = [label_x]

        operator_call = Token(Token.S_CALL_FUNCTION, 1, 0, "")

        operator_add.children = [label_x, const_1]
        operator_lambda.children = [namelist, closure, operator_add]
        operator_assign1.children = [label_f, operator_lambda]
        operator_call.children = [label_f, const_2]

        operator_return = Token(Token.S_RETURN, 1, 0, "")
        operator_return.children = [operator_call]

        asf = [operator_assign1, operator_return]

        #print()
        #print(operator_assign1.toString(True))
        #print(operator_return.toString(True))

        expr = compiler(asf)
        self.assertFalse(discmp(bc_expected, expr.bc, False))

        self.assertEqual(expr.execute(), 3)

    @unittest.skip("x")
    def test_005_lambda_2(self):
        """
        f=(x)=>{if(x>1){return f(x-1);}else{return 0;}};f(2);
        """

        def TOK(t,v,*children):
            return Token(getattr(Token,t), 1, 0, v, children)

        asf = [
            TOK('S_CLOSURE','',
                TOK('S_REFERENCE','f')
            ),
            TOK('S_OPERATOR2','=',
                TOK('S_REFERENCE','f'),
                TOK('S_LAMBDA','=>',
                    TOK('S_LAMBDA_NAMELIST','',
                        TOK('S_LABEL','x')
                    ),
                    TOK('S_LAMBDA_CLOSURE','',
                        TOK('S_REFERENCE','f')
                    ),
                    TOK('S_BLOCK','{}',
                        TOK('S_BRANCH','if',
                            TOK('S_OPERATOR2','>',
                                TOK('S_LABEL','x'),
                                TOK('S_NUMBER','1')
                            ),
                            TOK('S_BLOCK','{}',
                                TOK('S_RETURN','return',
                                    TOK('S_CALL_FUNCTION','',
                                        TOK('S_REFERENCE','f'),
                                        TOK('S_OPERATOR2','-',
                                            TOK('S_LABEL','x'),
                                            TOK('S_NUMBER','1')
                                        )
                                    )
                                )
                            ),
                            TOK('S_BLOCK','{}',
                                TOK('S_RETURN','return',
                                    TOK('S_NUMBER','0')
                                )
                            )
                        )
                    )
                )
            ),
            TOK('S_CALL_FUNCTION','',
                TOK('S_REFERENCE', 'f'),
                TOK('S_NUMBER', '2')
            )
        ]

        expr = compiler(asf)

        # validate that the main body was compiled correctly

        bc_expected = ConcreteBytecode()
        bc_expected.names = []
        bc_expected.varnames = []
        bc_expected.consts = []
        bc_expected.cellvars = ['f']
        bc_expected.extend([
            ConcreteInstr('LOAD_CLOSURE',0),
            ConcreteInstr('BUILD_TUPLE',1),
            ConcreteInstr('LOAD_CONST',1),
            ConcreteInstr('LOAD_CONST',2),
            ConcreteInstr('MAKE_FUNCTION',8),
            ConcreteInstr('STORE_DEREF',0),
            ConcreteInstr('LOAD_DEREF',0),
            ConcreteInstr('LOAD_CONST',3),
            ConcreteInstr('CALL_FUNCTION',1),
            ConcreteInstr('POP_TOP'),
            ConcreteInstr('LOAD_CONST',0),
            ConcreteInstr('RETURN_VALUE'),
        ])

        self.assertFalse(discmp(bc_expected, expr.bc, False))

        # validate that the lambda was compiled correctly
        bc_expected = ConcreteBytecode()
        bc_expected.names = []
        bc_expected.varnames = []
        bc_expected.consts = []
        bc_expected.cellvars = []
        bc_expected.freevars = ['f']
        bc_expected.extend([
            ConcreteInstr('LOAD_FAST',0),
            ConcreteInstr('LOAD_CONST',1),
            ConcreteInstr('COMPARE_OP',4),
            ConcreteInstr('POP_JUMP_IF_FALSE',20),
            ConcreteInstr('LOAD_DEREF',0),
            ConcreteInstr('LOAD_FAST',0),
            ConcreteInstr('LOAD_CONST',1),
            ConcreteInstr('BINARY_SUBTRACT'),
            ConcreteInstr('CALL_FUNCTION',1),
            ConcreteInstr('RETURN_VALUE'),
            ConcreteInstr('LOAD_CONST',2),
            ConcreteInstr('RETURN_VALUE'),
        ])

        bc_lambda = ConcreteBytecode.from_code(expr.bc.consts[1])
        self.assertFalse(discmp(bc_expected, bc_lambda, False))

        self.assertEqual(expr.execute(), None)

    def test_005_lambda_3(self):
        """
        f = () => {x=0; return () => {x += 1}}

        """
        def TOK(t,v,*children):
            return Token(getattr(Token,t), 1, 0, v, children)

        asf = [
            TOK('S_OPERATOR2',"=",
                TOK('S_LABEL', "f"),
                TOK('S_LAMBDA', "=>",
                    TOK('S_LAMBDA_NAMELIST',""),
                    TOK('S_LAMBDA_CLOSURE',""),
                    TOK('S_BLOCK',"{closure}",
                        TOK('S_CLOSURE',"",
                            TOK('S_REFERENCE',"x"),
                        ),
                        TOK('S_BLOCK',"{}",
                            TOK('S_OPERATOR2',"=",
                                TOK('S_LABEL',"x"),
                                TOK('S_NUMBER',"0")
                            ),
                            TOK('S_RETURN',"return",
                                TOK('S_LAMBDA',"=>",
                                    TOK('S_LAMBDA_NAMELIST',""),
                                    TOK('S_LAMBDA_CLOSURE',"",
                                        TOK('S_REFERENCE',"x")
                                    ),
                                    TOK('S_OPERATOR2',"+=",
                                        TOK('S_LABEL',"x"),
                                        TOK('S_NUMBER',"1")
                                    )
                                )
                            )
                        )
                    )
                )
            ),

            # print 1 then 1 because the context is recreated
            TOK('S_CALL_FUNCTION','',
                TOK('S_LABEL', 'print'),
                TOK('S_CALL_FUNCTION','',
                    TOK('S_CALL_FUNCTION','',
                        TOK('S_LABEL', 'f')
                    )
                )
            ),
            TOK('S_CALL_FUNCTION','',
                TOK('S_LABEL', 'print'),
                TOK('S_CALL_FUNCTION','',
                    TOK('S_CALL_FUNCTION','',
                        TOK('S_LABEL', 'f')
                    )
                )
            )
        ]

        expr = compiler(asf)

        # expr.execute()

    def xfailed_test_006_for_break2(self):

        text = r"for(i:seq1){for(j:seq2){print(0);continue 2;print(0);break 2;print(0);}}"
        tokens = list(lexer(text))
        asf = parser(tokens)
        bc_expected = ConcreteBytecode()
        bc_expected.names = []
        bc_expected.varnames = []
        bc_expected.consts = [None]
        bc_expected.extend([
            ConcreteInstr('LOAD_NAME',0),
            ConcreteInstr('GET_ITER'),
            ConcreteInstr('FOR_ITER',42),
            ConcreteInstr('STORE_FAST',0),
            ConcreteInstr('LOAD_NAME',1),
            ConcreteInstr('GET_ITER'),
            ConcreteInstr('FOR_ITER',32),
            ConcreteInstr('STORE_FAST',1),
            ConcreteInstr('LOAD_GLOBAL',2),
            ConcreteInstr('LOAD_CONST',1),
            ConcreteInstr('CALL_FUNCTION',1),
            ConcreteInstr('POP_TOP'),
            ConcreteInstr('JUMP_ABSOLUTE',9999),
            ConcreteInstr('LOAD_GLOBAL',2),
            ConcreteInstr('LOAD_CONST',1),
            ConcreteInstr('CALL_FUNCTION',1),
            ConcreteInstr('POP_TOP'),
            ConcreteInstr('JUMP_ABSOLUTE',9999),
            ConcreteInstr('LOAD_GLOBAL',2),
            ConcreteInstr('LOAD_CONST',1),
            ConcreteInstr('CALL_FUNCTION',1),
            ConcreteInstr('POP_TOP'),
            ConcreteInstr('JUMP_ABSOLUTE',12),
            # from continue 2
            ConcreteInstr('POP_TOP'),
            ConcreteInstr('JUMP_ABSOLUTE',9999),
            # from break 2
            ConcreteInstr('POP_TOP'),
            ConcreteInstr('JUMP_ABSOLUTE',9999),
            # end of inner loop
            ConcreteInstr('JUMP_ABSOLUTE',4),
            # from continue 2.1
            ConcreteInstr('POP_TOP'),
            ConcreteInstr('JUMP_ABSOLUTE',9999),
            # from break 2.1
            ConcreteInstr('POP_TOP'),
            ConcreteInstr('JUMP_ABSOLUTE',9999),
            ConcreteInstr('LOAD_CONST',0),
            ConcreteInstr('RETURN_VALUE'),
        ])
        expr = compiler(asf)
        self.assertFalse(discmp(bc_expected, expr.bc, False))

class CompilerRegressionTestCase(unittest.TestCase):
    """
    test all of the basic syntax and verify the
    bytecode produced has not changed

    goal is 80% test coverage of lexer, parser, compiler
    by this testcase alone
    """

    @classmethod
    def setUpClass(cls):
        pass

    @classmethod
    def tearDownClass(cls):
        pass

    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    def test_010_unary_1(self):

        text = r"x = ~1"
        tokens = list(lexer(text))
        asf = parser(tokens)
        bc_expected = ConcreteBytecode()
        bc_expected.names = []
        bc_expected.varnames = []
        bc_expected.consts = [None]
        bc_expected.extend([
            ConcreteInstr('LOAD_CONST', 1),
            ConcreteInstr('UNARY_INVERT'),
            ConcreteInstr('STORE_FAST', 0),
        ])
        expr = compiler(asf)
        expr.bc.pop()
        expr.bc.pop()
        self.assertFalse(discmp(bc_expected, expr.bc, False))

    def test_010_unary_2(self):

        text = r"x = +1"
        tokens = list(lexer(text))
        asf = parser(tokens)
        bc_expected = ConcreteBytecode()
        bc_expected.names = []
        bc_expected.varnames = []
        bc_expected.consts = [None]
        bc_expected.extend([
            ConcreteInstr('LOAD_CONST', 1),
            ConcreteInstr('UNARY_POSITIVE'),
            ConcreteInstr('STORE_FAST', 0),
        ])
        expr = compiler(asf)
        expr.bc.pop()
        expr.bc.pop()
        self.assertFalse(discmp(bc_expected, expr.bc, False))

    def test_010_unary_3(self):

        text = r"x = -1"
        tokens = list(lexer(text))
        asf = parser(tokens)
        bc_expected = ConcreteBytecode()
        bc_expected.names = []
        bc_expected.varnames = []
        bc_expected.consts = [None]
        bc_expected.extend([
            ConcreteInstr('LOAD_CONST', 1),
            ConcreteInstr('UNARY_NEGATIVE'),
            ConcreteInstr('STORE_FAST', 0),
        ])
        expr = compiler(asf)
        expr.bc.pop()
        expr.bc.pop()
        self.assertFalse(discmp(bc_expected, expr.bc, False))

    def test_010_unary_4(self):

        text = r"f(*x)"
        tokens = list(lexer(text))
        asf = parser(tokens)
        bc_expected = ConcreteBytecode()
        bc_expected.names = []
        bc_expected.varnames = []
        bc_expected.consts = [None]
        bc_expected.extend([
            ConcreteInstr('LOAD_NAME', 0),
            ConcreteInstr('LOAD_NAME', 1),
            ConcreteInstr('CALL_FUNCTION_EX', 0),
            ConcreteInstr('POP_TOP'),
        ])
        expr = compiler(asf)
        expr.bc.pop()
        expr.bc.pop()
        self.assertFalse(discmp(bc_expected, expr.bc, False))

    def test_010_unary_5(self):

        text = r"f(**x)"
        tokens = list(lexer(text))
        asf = parser(tokens)
        bc_expected = ConcreteBytecode()
        bc_expected.names = []
        bc_expected.varnames = []
        bc_expected.consts = [None]
        bc_expected.extend([
            ConcreteInstr('LOAD_NAME', 0),
            ConcreteInstr('BUILD_TUPLE', 0),
            ConcreteInstr('LOAD_NAME', 1),
            ConcreteInstr('CALL_FUNCTION_EX', 1),
            ConcreteInstr('POP_TOP'),
        ])
        expr = compiler(asf)
        expr.bc.pop()
        expr.bc.pop()
        self.assertFalse(discmp(bc_expected, expr.bc, False))

    def test_010_unary_fix_1(self):

        text = r"_= ++x"
        tokens = list(lexer(text))
        asf = parser(tokens)
        bc_expected = ConcreteBytecode()
        bc_expected.names = []
        bc_expected.varnames = []
        bc_expected.consts = [None]
        bc_expected.extend([
            ConcreteInstr('LOAD_NAME', 0),
            ConcreteInstr('LOAD_CONST', 1),
            ConcreteInstr('BINARY_ADD'),
            ConcreteInstr('DUP_TOP'),
            ConcreteInstr('STORE_NAME', 0),
            ConcreteInstr('STORE_FAST', 0),
        ])
        expr = compiler(asf)
        expr.bc.pop()
        expr.bc.pop()
        self.assertFalse(discmp(bc_expected, expr.bc, False))

    def test_010_unary_fix_2(self):

        text = r"_= x++"
        tokens = list(lexer(text))
        asf = parser(tokens)
        bc_expected = ConcreteBytecode()
        bc_expected.names = []
        bc_expected.varnames = []
        bc_expected.consts = [None]
        bc_expected.extend([
            ConcreteInstr('LOAD_NAME', 0),
            ConcreteInstr('DUP_TOP'),
            ConcreteInstr('LOAD_CONST', 1),
            ConcreteInstr('BINARY_ADD'),
            ConcreteInstr('STORE_NAME', 0),
            ConcreteInstr('STORE_FAST', 0),
        ])
        expr = compiler(asf)
        expr.bc.pop()
        expr.bc.pop()
        self.assertFalse(discmp(bc_expected, expr.bc, False))

    def test_010_binary_1(self):

        text = r"x < y"
        tokens = list(lexer(text))
        asf = parser(tokens)
        bc_expected = ConcreteBytecode()
        bc_expected.names = []
        bc_expected.varnames = []
        bc_expected.consts = [None]
        bc_expected.extend([
            ConcreteInstr('LOAD_NAME', 0),
            ConcreteInstr('LOAD_NAME', 1),
            ConcreteInstr('COMPARE_OP', 0),
            ConcreteInstr('POP_TOP'),
        ])
        expr = compiler(asf)
        expr.bc.pop()
        expr.bc.pop()
        self.assertFalse(discmp(bc_expected, expr.bc, False))

    def test_010_binary_2(self):

        text = r"x === y"
        tokens = list(lexer(text))
        asf = parser(tokens)
        bc_expected = ConcreteBytecode()
        bc_expected.names = []
        bc_expected.varnames = []
        bc_expected.consts = [None]
        bc_expected.extend([
            ConcreteInstr('LOAD_NAME', 0),
            ConcreteInstr('LOAD_NAME', 1),
            ConcreteInstr('COMPARE_OP', 8),
            ConcreteInstr('POP_TOP'),
        ])
        expr = compiler(asf)
        expr.bc.pop()
        expr.bc.pop()
        self.assertFalse(discmp(bc_expected, expr.bc, False))

    def test_010_binary_3(self):

        text = r"x !== y"
        tokens = list(lexer(text))
        asf = parser(tokens)
        bc_expected = ConcreteBytecode()
        bc_expected.names = []
        bc_expected.varnames = []
        bc_expected.consts = [None]
        bc_expected.extend([
            ConcreteInstr('LOAD_NAME', 0),
            ConcreteInstr('LOAD_NAME', 1),
            ConcreteInstr('COMPARE_OP', 9),
            ConcreteInstr('POP_TOP'),
        ])
        expr = compiler(asf)
        expr.bc.pop()
        expr.bc.pop()
        self.assertFalse(discmp(bc_expected, expr.bc, False))

    def test_010_binary_4(self):

        text = r"x * y"
        tokens = list(lexer(text))
        asf = parser(tokens)
        bc_expected = ConcreteBytecode()
        bc_expected.names = []
        bc_expected.varnames = []
        bc_expected.consts = [None]
        bc_expected.extend([
            ConcreteInstr('LOAD_NAME', 0),
            ConcreteInstr('LOAD_NAME', 1),
            ConcreteInstr('BINARY_MULTIPLY'),
            ConcreteInstr('POP_TOP'),
        ])
        expr = compiler(asf)
        expr.bc.pop()
        expr.bc.pop()
        self.assertFalse(discmp(bc_expected, expr.bc, False))

    def test_010_binary_5(self):

        text = r"x *= y"
        tokens = list(lexer(text))
        asf = parser(tokens)
        bc_expected = ConcreteBytecode()
        bc_expected.names = []
        bc_expected.varnames = []
        bc_expected.consts = [None]
        bc_expected.extend([
            ConcreteInstr('LOAD_NAME', 0),
            ConcreteInstr('LOAD_NAME', 1),
            ConcreteInstr('BINARY_MULTIPLY'),
            ConcreteInstr('STORE_NAME', 0),
            ConcreteInstr('LOAD_NAME', 0),
            ConcreteInstr('POP_TOP'),
        ])
        expr = compiler(asf)
        expr.bc.pop()
        expr.bc.pop()
        self.assertFalse(discmp(bc_expected, expr.bc, False))

    def test_010_binary_5(self):

        text = r"a=b=0"
        tokens = list(lexer(text))
        asf = parser(tokens)
        bc_expected = ConcreteBytecode()
        bc_expected.names = []
        bc_expected.varnames = []
        bc_expected.consts = [None]
        bc_expected.extend([
            ConcreteInstr('LOAD_CONST', 1),
            ConcreteInstr('DUP_TOP'),
            ConcreteInstr('STORE_FAST', 0),
            ConcreteInstr('STORE_FAST', 1),
        ])
        expr = compiler(asf)
        expr.bc.pop()
        expr.bc.pop()
        self.assertFalse(discmp(bc_expected, expr.bc, False))

    def test_010_optional_1(self):

        text = r"a?.b"
        tokens = list(lexer(text))
        asf = parser(tokens)
        bc_expected = ConcreteBytecode()
        bc_expected.names = []
        bc_expected.varnames = []
        bc_expected.consts = [None]
        bc_expected.extend([
            ConcreteInstr('LOAD_NAME', 0),
            ConcreteInstr('DUP_TOP'),
            ConcreteInstr('LOAD_CONST', 0),
            ConcreteInstr('COMPARE_OP', 8),
            ConcreteInstr('POP_JUMP_IF_TRUE', 12),
            ConcreteInstr('LOAD_ATTR', 1),
            ConcreteInstr('NOP'),
        ])
        expr = compiler(asf)
        expr.bc.pop()
        expr.bc.pop()
        self.assertFalse(discmp(bc_expected, expr.bc, False))

    def test_010_optional_2(self):

        text = r"a?.()"
        tokens = list(lexer(text))
        asf = parser(tokens)
        bc_expected = ConcreteBytecode()
        bc_expected.names = []
        bc_expected.varnames = []
        bc_expected.consts = [None]
        bc_expected.extend([
            ConcreteInstr('LOAD_NAME', 0),
            ConcreteInstr('DUP_TOP'),
            ConcreteInstr('LOAD_CONST', 0),
            ConcreteInstr('COMPARE_OP', 8),
            ConcreteInstr('POP_JUMP_IF_TRUE', 12),
            ConcreteInstr('CALL_FUNCTION', 0),
            ConcreteInstr('NOP'),
            ConcreteInstr('POP_TOP'),
        ])
        expr = compiler(asf)
        expr.bc.pop()
        expr.bc.pop()
        self.assertFalse(discmp(bc_expected, expr.bc, False))

    def test_010_optional_3(self):

        text = r"a?.[]"
        tokens = list(lexer(text))
        asf = parser(tokens)
        bc_expected = ConcreteBytecode()
        bc_expected.names = []
        bc_expected.varnames = []
        bc_expected.consts = [None]
        bc_expected.extend([
            ConcreteInstr('LOAD_NAME', 0),
            ConcreteInstr('DUP_TOP'),
            ConcreteInstr('LOAD_CONST', 0),
            ConcreteInstr('COMPARE_OP', 8),
            ConcreteInstr('POP_JUMP_IF_TRUE', 12),
            ConcreteInstr('BINARY_SUBSCR'),
            ConcreteInstr('NOP'),
            ConcreteInstr('POP_TOP'),
        ])
        expr = compiler(asf)
        expr.bc.pop()
        expr.bc.pop()
        self.assertFalse(discmp(bc_expected, expr.bc, False))

    def test_010_yield_1(self):

        text = r"() => {yield x}"
        tokens = list(lexer(text))
        asf = parser(tokens)
        bc_expected = ConcreteBytecode()
        bc_expected.names = []
        bc_expected.varnames = []
        bc_expected.consts = [None]
        bc_expected.extend([
            ConcreteInstr('LOAD_NAME', 0),
            ConcreteInstr('YIELD_VALUE'),
            ConcreteInstr('LOAD_CONST', 0),
            ConcreteInstr('RETURN_VALUE'),
        ])
        expr = compiler(asf)

        bc_actual = ConcreteBytecode.from_code(expr.bc.consts[1])
        self.assertFalse(discmp(bc_expected, bc_actual, False))

    def test_010_yield_2(self):

        text = r"() => {yield from [1,2,3]}"
        tokens = list(lexer(text))
        asf = parser(tokens)
        bc_expected = ConcreteBytecode()
        bc_expected.names = []
        bc_expected.varnames = []
        bc_expected.consts = [None]
        bc_expected.extend([
            ConcreteInstr('LOAD_CONST', 1),
            ConcreteInstr('LOAD_CONST', 2),
            ConcreteInstr('LOAD_CONST', 3),
            ConcreteInstr('BUILD_LIST', 3),
            ConcreteInstr('GET_YIELD_FROM_ITER'),
            ConcreteInstr('LOAD_CONST', 0),
            ConcreteInstr('YIELD_FROM'),
            ConcreteInstr('POP_TOP'),
            ConcreteInstr('LOAD_CONST', 0),
            ConcreteInstr('RETURN_VALUE'),
        ])
        expr = compiler(asf)

        bc_actual = ConcreteBytecode.from_code(expr.bc.consts[1])
        self.assertFalse(discmp(bc_expected, bc_actual, False))

    def test_010_number_1(self):

        text = r"x=nan"
        tokens = list(lexer(text))
        asf = parser(tokens)
        bc_expected = ConcreteBytecode()
        bc_expected.names = []
        bc_expected.varnames = []
        bc_expected.consts = [None]
        bc_expected.extend([
            ConcreteInstr('LOAD_GLOBAL', 0),
            ConcreteInstr('STORE_FAST', 0),
            ConcreteInstr('LOAD_CONST', 0),
            ConcreteInstr('RETURN_VALUE'),
        ])
        expr = compiler(asf)

        self.assertFalse(discmp(bc_expected, expr.bc, False))

    def test_010_number_2(self):

        text = r"x=true"
        tokens = list(lexer(text))
        asf = parser(tokens)
        bc_expected = ConcreteBytecode()
        bc_expected.names = []
        bc_expected.varnames = []
        bc_expected.consts = [None]
        bc_expected.extend([
            ConcreteInstr('LOAD_GLOBAL', 0),
            ConcreteInstr('STORE_FAST', 0),
            ConcreteInstr('LOAD_CONST', 0),
            ConcreteInstr('RETURN_VALUE'),
        ])
        expr = compiler(asf)

        self.assertFalse(discmp(bc_expected, expr.bc, False))

    def test_010_number_3(self):

        text = r"x=false"
        tokens = list(lexer(text))
        asf = parser(tokens)
        bc_expected = ConcreteBytecode()
        bc_expected.names = []
        bc_expected.varnames = []
        bc_expected.consts = [None]
        bc_expected.extend([
            ConcreteInstr('LOAD_GLOBAL', 0),
            ConcreteInstr('STORE_FAST', 0),
            ConcreteInstr('LOAD_CONST', 0),
            ConcreteInstr('RETURN_VALUE'),
        ])
        expr = compiler(asf)

        self.assertFalse(discmp(bc_expected, expr.bc, False))

    def test_010_number_4(self):

        text = r"x=null"
        tokens = list(lexer(text))
        asf = parser(tokens)
        bc_expected = ConcreteBytecode()
        bc_expected.names = []
        bc_expected.varnames = []
        bc_expected.consts = [None]
        bc_expected.extend([
            ConcreteInstr('LOAD_GLOBAL', 0),
            ConcreteInstr('STORE_FAST', 0),
            ConcreteInstr('LOAD_CONST', 0),
            ConcreteInstr('RETURN_VALUE'),
        ])
        expr = compiler(asf)

        self.assertFalse(discmp(bc_expected, expr.bc, False))

    def test_010_gstring_1(self):

        text = r"g'*'"
        tokens = list(lexer(text))
        asf = parser(tokens)
        bc_expected = ConcreteBytecode()
        bc_expected.names = []
        bc_expected.varnames = []
        bc_expected.consts = [None]
        bc_expected.extend([
            ConcreteInstr('LOAD_GLOBAL', 0),
            ConcreteInstr('LOAD_CONST', 1),
            ConcreteInstr('CALL_FUNCTION', 1),
            ConcreteInstr('POP_TOP'),
            ConcreteInstr('LOAD_CONST', 0),
            ConcreteInstr('RETURN_VALUE'),
        ])
        expr = compiler(asf)

        self.assertFalse(discmp(bc_expected, expr.bc, False))

    def test_010_fstring_1(self):

        text = r"f'.'"
        tokens = list(lexer(text))
        asf = parser(tokens)
        bc_expected = ConcreteBytecode()
        bc_expected.names = []
        bc_expected.varnames = []
        bc_expected.consts = [None]
        bc_expected.extend([
            ConcreteInstr('LOAD_GLOBAL', 0),
            ConcreteInstr('LOAD_CONST', 1),
            ConcreteInstr('CALL_FUNCTION', 1),
            ConcreteInstr('POP_TOP'),
            ConcreteInstr('LOAD_CONST', 0),
            ConcreteInstr('RETURN_VALUE'),
        ])
        expr = compiler(asf)

        self.assertFalse(discmp(bc_expected, expr.bc, False))

    def test_010_rstring_1(self):

        text = r"r'.'"
        tokens = list(lexer(text))
        asf = parser(tokens)
        bc_expected = ConcreteBytecode()
        bc_expected.names = []
        bc_expected.varnames = []
        bc_expected.consts = [None]
        bc_expected.extend([
            ConcreteInstr('LOAD_GLOBAL', 0),
            ConcreteInstr('LOAD_CONST', 1),
            ConcreteInstr('CALL_FUNCTION', 1),
            ConcreteInstr('POP_TOP'),
            ConcreteInstr('LOAD_CONST', 0),
            ConcreteInstr('RETURN_VALUE'),
        ])
        expr = compiler(asf)

        self.assertFalse(discmp(bc_expected, expr.bc, False))

    def test_010_attr_1(self):

        text = r"a.b=0"
        tokens = list(lexer(text))
        asf = parser(tokens)
        bc_expected = ConcreteBytecode()
        bc_expected.names = []
        bc_expected.varnames = []
        bc_expected.consts = [None]
        bc_expected.extend([
            ConcreteInstr('LOAD_CONST', 1),
            ConcreteInstr('LOAD_NAME', 0),
            ConcreteInstr('STORE_ATTR', 1),
            ConcreteInstr('LOAD_CONST', 0),
            ConcreteInstr('RETURN_VALUE'),
        ])
        expr = compiler(asf)

        self.assertFalse(discmp(bc_expected, expr.bc, False))

    def test_010_call_1(self):

        text = r"f()"
        tokens = list(lexer(text))
        asf = parser(tokens)
        bc_expected = ConcreteBytecode()
        bc_expected.names = []
        bc_expected.varnames = []
        bc_expected.consts = [None]
        bc_expected.extend([
            ConcreteInstr('LOAD_NAME', 0),
            ConcreteInstr('CALL_FUNCTION', 0),
            ConcreteInstr('POP_TOP'),
        ])
        expr = compiler(asf)
        expr.bc.pop()
        expr.bc.pop()

        self.assertFalse(discmp(bc_expected, expr.bc, False))

    def test_010_call_2(self):

        text = r"f(a, *x)"
        tokens = list(lexer(text))
        asf = parser(tokens)
        bc_expected = ConcreteBytecode()
        bc_expected.names = []
        bc_expected.varnames = []
        bc_expected.consts = [None]
        bc_expected.extend([
            ConcreteInstr('LOAD_NAME', 0),
            ConcreteInstr('LOAD_NAME', 1),
            ConcreteInstr('BUILD_TUPLE', 1),
            ConcreteInstr('LOAD_NAME', 2),
            ConcreteInstr('BUILD_TUPLE_UNPACK_WITH_CALL', 2),
            ConcreteInstr('CALL_FUNCTION_EX', 0),
            ConcreteInstr('POP_TOP'),
        ])
        expr = compiler(asf)
        expr.bc.pop()
        expr.bc.pop()

        self.assertFalse(discmp(bc_expected, expr.bc, False))

    def test_010_call_3(self):

        text = r"f(a=0, **x)"
        tokens = list(lexer(text))
        asf = parser(tokens)
        bc_expected = ConcreteBytecode()
        bc_expected.names = []
        bc_expected.varnames = []
        bc_expected.consts = [None]
        bc_expected.extend([
            ConcreteInstr('LOAD_NAME', 0),
            ConcreteInstr('BUILD_TUPLE', 0),
            ConcreteInstr('LOAD_CONST', 1),
            ConcreteInstr('LOAD_CONST', 2),
            ConcreteInstr('BUILD_MAP', 1),
            ConcreteInstr('LOAD_NAME', 1),
            ConcreteInstr('BUILD_MAP_UNPACK_WITH_CALL', 2),
            ConcreteInstr('CALL_FUNCTION_EX', 1),
            ConcreteInstr('POP_TOP'),
        ])
        expr = compiler(asf)
        expr.bc.pop()
        expr.bc.pop()

        self.assertFalse(discmp(bc_expected, expr.bc, False))

    def test_010_call_4(self):

        text = r"f(a=0)"
        tokens = list(lexer(text))
        asf = parser(tokens)
        bc_expected = ConcreteBytecode()
        bc_expected.names = []
        bc_expected.varnames = []
        bc_expected.consts = [None]
        bc_expected.extend([
            ConcreteInstr('LOAD_NAME', 0),
            ConcreteInstr('LOAD_CONST', 2),
            ConcreteInstr('LOAD_CONST', 1),
            ConcreteInstr('BUILD_TUPLE', 1),
            ConcreteInstr('CALL_FUNCTION_KW', 1),
            ConcreteInstr('POP_TOP'),
        ])
        expr = compiler(asf)
        expr.bc.pop()
        expr.bc.pop()

        self.assertFalse(discmp(bc_expected, expr.bc, False))

    def test_010_import_1(self):

        text = r"import abc"
        tokens = list(lexer(text))
        asf = parser(tokens)
        bc_expected = ConcreteBytecode()
        bc_expected.names = []
        bc_expected.varnames = []
        bc_expected.consts = [None]
        bc_expected.extend([
            ConcreteInstr('LOAD_CONST', 1),
            ConcreteInstr('LOAD_CONST', 0),
            ConcreteInstr('IMPORT_NAME', 0),
            ConcreteInstr('DUP_TOP'),
            ConcreteInstr('STORE_NAME', 0),
            ConcreteInstr('LOAD_CONST', 0),
            ConcreteInstr('RETURN_VALUE'),
        ])
        expr = compiler(asf)

        self.assertFalse(discmp(bc_expected, expr.bc, False))

    def test_010_import_2(self):

        text = r"from abc import def"
        tokens = list(lexer(text))
        asf = parser(tokens)
        bc_expected = ConcreteBytecode()
        bc_expected.names = []
        bc_expected.varnames = []
        bc_expected.consts = [None]
        bc_expected.extend([
            ConcreteInstr('LOAD_CONST', 1),
            ConcreteInstr('LOAD_CONST', 2),
            ConcreteInstr('BUILD_TUPLE', 1),
            ConcreteInstr('IMPORT_NAME', 0),
            ConcreteInstr('IMPORT_FROM', 1),
            ConcreteInstr('STORE_FAST', 0),
            ConcreteInstr('DUP_TOP'),
            ConcreteInstr('STORE_NAME', 0),
            ConcreteInstr('LOAD_CONST', 0),
            ConcreteInstr('RETURN_VALUE'),
        ])
        expr = compiler(asf)

    def test_010_import_3(self):

        text = r"from abc import def as xyz"
        tokens = list(lexer(text))
        asf = parser(tokens)
        bc_expected = ConcreteBytecode()
        bc_expected.names = []
        bc_expected.varnames = []
        bc_expected.consts = [None]
        bc_expected.extend([
            ConcreteInstr('LOAD_CONST', 1),
            ConcreteInstr('LOAD_CONST', 2),
            ConcreteInstr('BUILD_TUPLE', 1),
            ConcreteInstr('IMPORT_NAME', 0),
            ConcreteInstr('IMPORT_FROM', 1),
            ConcreteInstr('STORE_FAST', 0),
            ConcreteInstr('DUP_TOP'),
            ConcreteInstr('STORE_NAME', 0),
            ConcreteInstr('LOAD_CONST', 0),
            ConcreteInstr('RETURN_VALUE'),
        ])
        expr = compiler(asf)

        self.assertFalse(discmp(bc_expected, expr.bc, False))

    def test_010_class_1(self):

        text = r"class A() {;}"
        tokens = list(lexer(text))
        asf = parser(tokens)
        bc_expected = ConcreteBytecode()
        bc_expected.names = []
        bc_expected.varnames = []
        bc_expected.consts = [None]
        bc_expected.extend([
            ConcreteInstr('LOAD_BUILD_CLASS'),
            ConcreteInstr('LOAD_CONST', 1),
            ConcreteInstr('LOAD_CONST', 2),
            ConcreteInstr('MAKE_FUNCTION', 0),
            ConcreteInstr('LOAD_CONST', 3),
            ConcreteInstr('LOAD_NAME', 0),
            ConcreteInstr('CALL_FUNCTION', 3),
            ConcreteInstr('STORE_FAST', 0),
            ConcreteInstr('LOAD_CONST', 0),
            ConcreteInstr('RETURN_VALUE'),
        ])
        expr = compiler(asf)

        self.assertFalse(discmp(bc_expected, expr.bc, False))

    def test_010_lambda_1(self):

        text = r"f()=>{return}"
        tokens = list(lexer(text))
        asf = parser(tokens)
        bc_expected = ConcreteBytecode()
        bc_expected.names = []
        bc_expected.varnames = []
        bc_expected.consts = [None]
        bc_expected.extend([
            ConcreteInstr('LOAD_CONST', 0),
            ConcreteInstr('RETURN_VALUE'),
        ])
        expr = compiler(asf)
        expr.bc.pop()
        expr.bc.pop()

        code = expr.bc.consts[1]
        bc = ConcreteBytecode.from_code(code)

        self.assertFalse(discmp(bc_expected, bc, False))

    def test_010_lambda_2(self):

        text = r"f(x, *y)=>{return y}"
        tokens = list(lexer(text))
        asf = parser(tokens)
        bc_expected = ConcreteBytecode()
        bc_expected.names = []
        bc_expected.varnames = []
        bc_expected.consts = [None]
        bc_expected.extend([
            ConcreteInstr('LOAD_FAST', 1),
            ConcreteInstr('RETURN_VALUE'),
        ])
        expr = compiler(asf)
        expr.bc.pop()
        expr.bc.pop()

        code = expr.bc.consts[1]
        bc = ConcreteBytecode.from_code(code)

        self.assertFalse(discmp(bc_expected, bc, False))

    def test_010_lambda_3(self):

        text = r"f(x=a, **y)=>{return y}"
        tokens = list(lexer(text))
        asf = parser(tokens)
        bc_expected = ConcreteBytecode()
        bc_expected.names = []
        bc_expected.varnames = []
        bc_expected.consts = [None]
        bc_expected.extend([
            ConcreteInstr('LOAD_FAST', 1),
            ConcreteInstr('RETURN_VALUE'),
        ])
        expr = compiler(asf)
        expr.bc.pop()
        expr.bc.pop()

        code = expr.bc.consts[1]
        bc = ConcreteBytecode.from_code(code)

        self.assertFalse(discmp(bc_expected, bc, False))

    def test_010_comprehension_list_1(self):

        text = r"[a for a in b]"
        tokens = list(lexer(text))
        asf = parser(tokens)
        bc_expected = ConcreteBytecode()
        bc_expected.names = []
        bc_expected.varnames = []
        bc_expected.consts = [None]
        bc_expected.extend([
            ConcreteInstr('BUILD_LIST', 0),
            ConcreteInstr('LOAD_NAME', 0),
            ConcreteInstr('GET_ITER'),
            ConcreteInstr('FOR_ITER', 8),
            ConcreteInstr('STORE_FAST', 0),
            ConcreteInstr('LOAD_FAST', 0),
            ConcreteInstr('LIST_APPEND', 2),
            ConcreteInstr('JUMP_ABSOLUTE', 6),
            ConcreteInstr('NOP'),
            ConcreteInstr('LOAD_CONST', 0),
            ConcreteInstr('RETURN_VALUE'),
        ])
        expr = compiler(asf)

        self.assertFalse(discmp(bc_expected, expr.bc, False))

    def test_010_comprehension_set_1(self):

        text = r"{a for a in b}"
        tokens = list(lexer(text))
        asf = parser(tokens)
        bc_expected = ConcreteBytecode()
        bc_expected.names = []
        bc_expected.varnames = []
        bc_expected.consts = [None]
        bc_expected.extend([
            ConcreteInstr('BUILD_SET', 0),
            ConcreteInstr('LOAD_NAME', 0),
            ConcreteInstr('GET_ITER'),
            ConcreteInstr('FOR_ITER', 8),
            ConcreteInstr('STORE_FAST', 0),
            ConcreteInstr('LOAD_FAST', 0),
            ConcreteInstr('SET_ADD', 2),
            ConcreteInstr('JUMP_ABSOLUTE', 6),
            ConcreteInstr('NOP'),
            ConcreteInstr('LOAD_CONST', 0),
            ConcreteInstr('RETURN_VALUE'),
        ])
        expr = compiler(asf)

        self.assertFalse(discmp(bc_expected, expr.bc, False))

    def test_010_comprehension_list_2(self):

        text = r"[a for a in b if a]"
        tokens = list(lexer(text))
        asf = parser(tokens)
        bc_expected = ConcreteBytecode()
        bc_expected.names = []
        bc_expected.varnames = []
        bc_expected.consts = [None]
        bc_expected.extend([
            ConcreteInstr('BUILD_LIST', 0),
            ConcreteInstr('LOAD_NAME', 0),
            ConcreteInstr('GET_ITER'),
            ConcreteInstr('FOR_ITER', 14),
            ConcreteInstr('STORE_FAST', 0),
            ConcreteInstr('LOAD_FAST', 0),
            ConcreteInstr('POP_JUMP_IF_FALSE', 18),
            ConcreteInstr('LOAD_FAST', 0),
            ConcreteInstr('LIST_APPEND', 2),
            ConcreteInstr('NOP'),
            ConcreteInstr('JUMP_ABSOLUTE', 6),
            ConcreteInstr('NOP'),
            ConcreteInstr('LOAD_CONST', 0),
            ConcreteInstr('RETURN_VALUE'),
        ])
        expr = compiler(asf)

        self.assertFalse(discmp(bc_expected, expr.bc, False))

    def test_010_comprehension_dict_1(self):

        text = r"{k:v for k, v in b}"
        tokens = list(lexer(text))
        asf = parser(tokens)
        bc_expected = ConcreteBytecode()
        bc_expected.names = []
        bc_expected.varnames = []
        bc_expected.consts = [None]
        bc_expected.extend([
            ConcreteInstr('BUILD_MAP', 0),
            ConcreteInstr('LOAD_NAME', 0),
            ConcreteInstr('GET_ITER'),
            ConcreteInstr('FOR_ITER', 14),
            ConcreteInstr('UNPACK_SEQUENCE', 2),
            ConcreteInstr('STORE_FAST', 0),
            ConcreteInstr('STORE_FAST', 1),
            ConcreteInstr('LOAD_FAST', 1 if VERSION < (3, 8) else 0),
            ConcreteInstr('LOAD_FAST', 0 if VERSION < (3, 8) else 1),
            ConcreteInstr('MAP_ADD', 2),
            ConcreteInstr('JUMP_ABSOLUTE', 6),
            ConcreteInstr('NOP'),
            ConcreteInstr('LOAD_CONST', 0),
            ConcreteInstr('RETURN_VALUE'),
        ])
        expr = compiler(asf)

        self.assertFalse(discmp(bc_expected, expr.bc, False))

    def test_010_branch_1(self):

        text = r"if a b"
        tokens = list(lexer(text))
        asf = parser(tokens)
        bc_expected = ConcreteBytecode()
        bc_expected.names = []
        bc_expected.varnames = []
        bc_expected.consts = [None]
        bc_expected.extend([
            ConcreteInstr('LOAD_NAME', 1),
            ConcreteInstr('POP_JUMP_IF_FALSE', 8),
            ConcreteInstr('LOAD_NAME', 0),
            ConcreteInstr('POP_TOP'),
            ConcreteInstr('NOP'),
            ConcreteInstr('LOAD_CONST', 0),
            ConcreteInstr('RETURN_VALUE'),
        ])
        expr = compiler(asf)

        self.assertFalse(discmp(bc_expected, expr.bc, False))

    def test_010_branch_2(self):

        text = r"if a b else c"
        tokens = list(lexer(text))
        asf = parser(tokens)
        bc_expected = ConcreteBytecode()
        bc_expected.names = []
        bc_expected.varnames = []
        bc_expected.consts = [None]
        bc_expected.extend([
            ConcreteInstr('LOAD_NAME', 2),
            ConcreteInstr('POP_JUMP_IF_FALSE', 10),
            ConcreteInstr('LOAD_NAME', 0),
            ConcreteInstr('POP_TOP'),
            ConcreteInstr('JUMP_ABSOLUTE', 14),
            ConcreteInstr('LOAD_NAME', 1),
            ConcreteInstr('POP_TOP'),
            ConcreteInstr('NOP'),
            ConcreteInstr('LOAD_CONST', 0),
            ConcreteInstr('RETURN_VALUE'),
        ])
        expr = compiler(asf)

        self.assertFalse(discmp(bc_expected, expr.bc, False))

    def test_010_branch_3(self):

        text = r"a && b"
        tokens = list(lexer(text))
        asf = parser(tokens)
        bc_expected = ConcreteBytecode()
        bc_expected.names = []
        bc_expected.varnames = []
        bc_expected.consts = [None]
        bc_expected.extend([
            ConcreteInstr('LOAD_NAME', 0),
            ConcreteInstr('JUMP_IF_FALSE_OR_POP', 6),
            ConcreteInstr('LOAD_NAME', 1),
            ConcreteInstr('NOP'),
            ConcreteInstr('POP_TOP'),

        ])
        expr = compiler(asf)
        expr.bc.pop()
        expr.bc.pop()

        self.assertFalse(discmp(bc_expected, expr.bc, False))

    def test_010_branch_4(self):

        text = r"a || b"
        tokens = list(lexer(text))
        asf = parser(tokens)
        bc_expected = ConcreteBytecode()
        bc_expected.names = []
        bc_expected.varnames = []
        bc_expected.consts = [None]
        bc_expected.extend([
            ConcreteInstr('LOAD_NAME', 0),
            ConcreteInstr('JUMP_IF_TRUE_OR_POP', 6),
            ConcreteInstr('LOAD_NAME', 1),
            ConcreteInstr('NOP'),
            ConcreteInstr('POP_TOP'),

        ])
        expr = compiler(asf)
        expr.bc.pop()
        expr.bc.pop()

        self.assertFalse(discmp(bc_expected, expr.bc, False))

    def test_010_foreach_1(self):

        text = r"for a in b a"
        tokens = list(lexer(text))
        asf = parser(tokens)
        bc_expected = ConcreteBytecode()
        bc_expected.names = []
        bc_expected.varnames = []
        bc_expected.consts = [None]
        bc_expected.extend([
            ConcreteInstr('LOAD_NAME', 0),
            ConcreteInstr('GET_ITER'),
            ConcreteInstr('FOR_ITER', 10),
            ConcreteInstr('STORE_FAST', 0),
            ConcreteInstr('LOAD_FAST', 0),
            ConcreteInstr('POP_TOP'),
            ConcreteInstr('JUMP_ABSOLUTE', 4),
            ConcreteInstr('POP_TOP'),
            ConcreteInstr('NOP'),
            ConcreteInstr('LOAD_CONST', 0),
            ConcreteInstr('RETURN_VALUE'),
        ])
        expr = compiler(asf)

        self.assertFalse(discmp(bc_expected, expr.bc, False))

    def test_010_while_1(self):

        text = r"while a break"
        tokens = list(lexer(text))
        asf = parser(tokens)
        bc_expected = ConcreteBytecode()
        bc_expected.names = []
        bc_expected.varnames = []
        bc_expected.consts = [None]
        bc_expected.extend([
            ConcreteInstr('LOAD_NAME', 0),
            ConcreteInstr('POP_JUMP_IF_FALSE', 8),
            ConcreteInstr('JUMP_ABSOLUTE', 8),
            ConcreteInstr('JUMP_ABSOLUTE', 0),
            ConcreteInstr('NOP'),
            ConcreteInstr('LOAD_CONST', 0),
            ConcreteInstr('RETURN_VALUE'),
        ])
        expr = compiler(asf)

        self.assertFalse(discmp(bc_expected, expr.bc, False))

    def test_010_exec_1(self):

        text = r"exec true"
        tokens = list(lexer(text))
        asf = parser(tokens)
        bc_expected = ConcreteBytecode()
        bc_expected.names = []
        bc_expected.varnames = []
        bc_expected.consts = [None]
        bc_expected.extend([
            ConcreteInstr('LOAD_GLOBAL', 0),
            ConcreteInstr('LOAD_CONST', 1),
            ConcreteInstr('CALL_FUNCTION', 1),
            ConcreteInstr('LOAD_ATTR', 1),
            ConcreteInstr('CALL_FUNCTION', 0),
            ConcreteInstr('POP_TOP'),
        ])
        expr = compiler(asf)
        expr.bc.pop()
        expr.bc.pop()

        self.assertFalse(discmp(bc_expected, expr.bc, False))

    def test_010_exec_2(self):

        text = r"exec true |> exec false"
        tokens = list(lexer(text))
        asf = parser(tokens)
        bc_expected = ConcreteBytecode()
        bc_expected.names = []
        bc_expected.varnames = []
        bc_expected.consts = [None]
        bc_expected.extend([
            ConcreteInstr('LOAD_GLOBAL', 0),
            ConcreteInstr('LOAD_CONST', 1),
            ConcreteInstr('CALL_FUNCTION', 1),
            ConcreteInstr('LOAD_GLOBAL', 0),
            ConcreteInstr('LOAD_CONST', 2),
            ConcreteInstr('CALL_FUNCTION', 1),
            ConcreteInstr('CALL_FUNCTION', 0),
            ConcreteInstr('CALL_FUNCTION', 1),
            ConcreteInstr('LOAD_GLOBAL', 1),
            ConcreteInstr('ROT_TWO'),
            ConcreteInstr('CALL_FUNCTION', 1),
            ConcreteInstr('POP_TOP'),
        ])
        expr = compiler(asf)
        expr.bc.pop()
        expr.bc.pop()

        self.assertFalse(discmp(bc_expected, expr.bc, False))

    def test_010_trycatch(self):

        text = r"try {raise Exception()} catch Exception as e {raise}"
        tokens = list(lexer(text))
        asf = parser(tokens)
        bc_expected = ConcreteBytecode()
        bc_expected.names = []
        bc_expected.varnames = []
        bc_expected.consts = [None]
        i1 = 'SETUP_EXCEPT' if VERSION < (3, 8) else 'SETUP_FINALLY'
        i2 = ('LOAD_CONST',0) if VERSION < (3, 8) else ('BEGIN_FINALLY',)
        bc_expected.extend([

            ConcreteInstr(i1,10),
            ConcreteInstr('LOAD_NAME',0),
            ConcreteInstr('CALL_FUNCTION',0),
            ConcreteInstr('RAISE_VARARGS',1),
            ConcreteInstr('POP_BLOCK'),
            ConcreteInstr('JUMP_FORWARD',36),
            ConcreteInstr('DUP_TOP'),
            ConcreteInstr('LOAD_NAME',0),
            ConcreteInstr('COMPARE_OP',10),
            ConcreteInstr('POP_JUMP_IF_FALSE',46),
            ConcreteInstr('POP_TOP'),
            ConcreteInstr('STORE_FAST',0),
            ConcreteInstr('POP_TOP'),
            ConcreteInstr('SETUP_FINALLY',6),
            ConcreteInstr('RAISE_VARARGS',0),
            ConcreteInstr('POP_BLOCK'),
            ConcreteInstr(*i2),
            ConcreteInstr('LOAD_CONST',0),
            ConcreteInstr('STORE_FAST',0),
            ConcreteInstr('DELETE_FAST',0),
            ConcreteInstr('END_FINALLY'),
            ConcreteInstr('POP_EXCEPT'),
            ConcreteInstr('JUMP_FORWARD',2),
            ConcreteInstr('END_FINALLY'),
            ConcreteInstr('NOP'),
        ])
        expr = compiler(asf)
        expr.bc.pop()
        expr.bc.pop()

        self.assertFalse(discmp(bc_expected, expr.bc, False))

    # f=()=>{yield 0}; g=()=>{yield from f()}; print([x for x in g()])

    # try {print(0)} catch Exception as b {print(1)} finally {print(2)}
    # print 0, 2
    # try {raise Exception()} catch Exception as b {print(1)} finally {print(2)}
    # prints 1, 2

def main():
    unittest.main()

if __name__ == '__main__':
    main()
