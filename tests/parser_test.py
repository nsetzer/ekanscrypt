#! cd .. && python3 -m ekanscrypt.parser_test

import unittest

from ekanscrypt.token import Token
from ekanscrypt.lexer import lexer
from ekanscrypt.parser import parser
from ekanscrypt.util import edit_distance

from ekanscrypt.exception import ParseError

def tokcmp(a, b):
    if a is None:
        return False
    if b is None:
        return False

    _, tok1 = a
    _, tok2 = b

    return tok1.type == tok2.type and tok1.value == tok2.value

def parsecmp(expected, actual, debug=False):

    a = sum([a.flatten() for a in actual], [])
    b = sum([b.flatten() for b in expected], [])

    seq, cor, sub, ins, del_ = edit_distance(a, b, tokcmp)

    error_count = sub + ins + del_
    if error_count > 0 or debug:
        print("\n--- %-50s | --- %-.50s" % ("    HYP", "    REF"))
        for a, b in seq:
            c = ' ' if tokcmp(a, b) else '|'
            if not a:
                a = (0, None)
            if not b:
                b = (0, None)
            print("%3d %-50r %s %3d %-.50r" % (a[0], a[1], c, b[0], b[1]))
    return error_count

class ParserTestCase(unittest.TestCase):

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

        tokens = [
            Token(Token.T_TEXT, 1, 1, 'x'),
            Token(Token.T_SPECIAL2, 1, 3, '='),
            Token(Token.T_SPECIAL1, 1, 7, '('),
            Token(Token.T_NUMBER, 1, 7, '1'),
            Token(Token.T_SPECIAL2, 1, 9, '+'),
            Token(Token.T_NUMBER, 1, 13, '2'),
            Token(Token.T_SPECIAL1, 1, 7, ')'),
        ]

        label_x = Token(Token.S_LABEL, 1, 0, "x")
        const_1 = Token(Token.S_NUMBER, 1, 0, "1")
        const_2 = Token(Token.S_NUMBER, 1, 0, "2")
        operator_assign1 = Token(Token.S_OPERATOR2, 1, 0, "=")
        operator_add = Token(Token.S_OPERATOR2, 1, 0, "+")

        operator_assign1.children = [label_x, operator_add]
        operator_add.children = [const_1, const_2]

        expected = [operator_assign1]

        actual = list(parser(tokens))

        self.assertFalse(parsecmp(expected, actual, False))

    def test_001_basic_expr_2(self):

        tokens = [
            Token(Token.T_TEXT, 1, 1, 'print'),
            Token(Token.T_SPECIAL1, 1, 7, '('),
            Token(Token.T_TEXT, 1, 7, 'abc'),
            Token(Token.T_SPECIAL1, 1, 9, ','),
            Token(Token.T_NUMBER, 1, 13, '123'),
            Token(Token.T_SPECIAL1, 1, 7, ')'),
        ]

        label_abc = Token(Token.S_LABEL, 1, 0, "abc")
        const_123 = Token(Token.S_NUMBER, 1, 0, "123")
        label_print = Token(Token.S_LABEL, 1, 0, "print")
        operator_call = Token(Token.S_CALL_FUNCTION, 1, 0, "")
        operator_call.children = [label_print, label_abc, const_123]

        expected = [operator_call]

        actual = list(parser(tokens))

        self.assertFalse(parsecmp(expected, actual, False))

    def test_001_basic_expr_3(self):

        tokens = [
            Token(Token.T_SPECIAL1, 1, 7, '{'),
              Token(Token.T_TEXT, 1, 7, 'a'),
                Token(Token.T_SPECIAL1, 1, 7, '('),
                Token(Token.T_TEXT, 1, 7, 'b'),
                  Token(Token.T_SPECIAL1, 1, 7, '('),
                  Token(Token.T_SPECIAL1, 1, 7, ')'),
                Token(Token.T_SPECIAL1, 1, 7, ')'),
            Token(Token.T_SPECIAL1, 1, 7, '}'),
        ]

        operator_call1 = Token(Token.S_CALL_FUNCTION, 1, 0, "")
        operator_call2 = Token(Token.S_CALL_FUNCTION, 1, 0, "")
        operator_call2.children=[Token(Token.S_LABEL, 1, 7, 'b')]
        operator_call1.children=[Token(Token.S_LABEL, 1, 7, 'a'), operator_call2]

        expected = [operator_call1]

        actual = list(parser(tokens))

        self.assertFalse(parsecmp(expected, actual, False))

    def test_001_basic_expr_4(self):

        tokens = [
            Token(Token.T_TEXT, 1, 1, 'f'),
            Token(Token.T_SPECIAL1, 1, 3, '('),
            Token(Token.T_SPECIAL1, 1, 7, ')'),
            Token(Token.T_SPECIAL1, 1, 9, '.'),
            Token(Token.T_TEXT, 1, 13, 'a'),
        ]

        label_a = Token(Token.S_ATTR_LABEL, 1, 7, 'a')
        operator_call1 = Token(Token.S_CALL_FUNCTION, 1, 0, "")
        operator_call1.children=[Token(Token.S_LABEL, 1, 7, 'f')]

        label_attr = Token(Token.S_ATTR, 1, 0, ".")
        label_attr.children=[operator_call1, label_a]

        expected = [label_attr]

        actual = list(parser(tokens))

        self.assertFalse(parsecmp(expected, actual, False))

    def test_001_basic_expr_5(self):

        tokens = [
            Token(Token.T_TEXT, 1, 7, 'a'),
            Token(Token.T_SPECIAL1, 1, 7, '('),
            Token(Token.T_SPECIAL1, 1, 7, ')'),
            Token(Token.T_SPECIAL2, 1, 7, '+'),
            Token(Token.T_TEXT, 1, 7, 'b'),
            Token(Token.T_SPECIAL1, 1, 7, '('),
            Token(Token.T_SPECIAL1, 1, 7, ')'),
        ]

        operator_call1 = Token(Token.S_CALL_FUNCTION, 1, 0, "")
        operator_call1.children=[Token(Token.S_LABEL, 1, 7, 'a')]
        operator_call2 = Token(Token.S_CALL_FUNCTION, 1, 0, "")
        operator_call2.children=[Token(Token.S_LABEL, 1, 7, 'b')]
        operator_add = Token(Token.S_OPERATOR2, 1, 0, "+")
        operator_add.children=[operator_call1, operator_call2]

        expected = [operator_add]

        actual = list(parser(tokens))

        self.assertFalse(parsecmp(expected, actual, False))

    def test_001_basic_expr_6(self):
        """
        parsing newlines as optional semicolons works,
        unclear if this is a needed feature
        """

        tokens = [
            Token(Token.T_NUMBER, 1, 7, '1'),
            Token(Token.T_SPECIAL2, 1, 9, '+'),
            Token(Token.T_NEWLINE, 1, 9, '\n'),
            Token(Token.T_NUMBER, 1, 13, '2'),
        ]

        const_1 = Token(Token.S_NUMBER, 1, 0, "1")
        const_2 = Token(Token.S_NUMBER, 1, 0, "2")
        operator_add = Token(Token.S_OPERATOR2, 1, 0, "+")

        operator_add.children = [const_1, const_2]

        expected = [operator_add]

        actual = list(parser(tokens))

        self.assertFalse(parsecmp(expected, actual, False))

    def test_001_basic_expr_7(self):

        tokens = list(lexer("x + - 1"))

        operator_add = Token(Token.S_OPERATOR2, 1, 3, '+')
        label_x = Token(Token.S_LABEL, 1, 1, 'x')
        operator_neg = Token(Token.S_PREFIX, 1, 5, '-')
        const_1 = Token(Token.S_NUMBER, 1, 6, '1')

        operator_neg.children = [const_1]
        operator_add.children = [label_x, operator_neg]

        actual = list(parser(tokens))
        expected = [operator_add]

    def test_001_basic_expr_8(self):

        tokens = list(lexer("; - 1"))

        operator_neg = Token(Token.S_PREFIX, 1, 5, '-')
        const_1 = Token(Token.S_NUMBER, 1, 6, '1')

        operator_neg.children = [const_1]

        actual = list(parser(tokens))
        expected = [operator_neg]

        self.assertFalse(parsecmp(expected, actual, False))

    def test_001_basic_expr_9(self):

        tokens = list(lexer("x + ++ y"))

        operator_add = Token(Token.S_OPERATOR2, 1, 3, '+')
        label_x = Token(Token.S_LABEL, 1, 1, 'x')
        operator_fix = Token(Token.S_PREFIX, 1, 5, '++')
        label_y = Token(Token.S_LABEL, 1, 6, 'y')

        operator_fix.children = [label_y]
        operator_add.children = [label_x, operator_fix]

        actual = list(parser(tokens))
        expected = [operator_add]
        self.assertFalse(parsecmp(expected, actual, False))

    def test_001_basic_expr_10(self):

        tokens = list(lexer("x + y ++"))

        operator_add = Token(Token.S_OPERATOR2, 1, 3, '+')
        label_x = Token(Token.S_LABEL, 1, 1, 'x')
        operator_fix = Token(Token.S_POSTFIX, 1, 5, '++')
        label_y = Token(Token.S_LABEL, 1, 6, 'y')

        operator_fix.children = [label_y]
        operator_add.children = [label_x, operator_fix]

        actual = list(parser(tokens))
        expected = [operator_add]
        self.assertFalse(parsecmp(expected, actual, False))

    def test_001_basic_expr_11(self):

        tokens = list(lexer("f(x)"))

        operator_call = Token(Token.S_CALL_FUNCTION, 1, 1, '')
        label_f = Token(Token.S_LABEL, 1, 1, 'f')
        label_x = Token(Token.S_LABEL, 1, 3, 'x')

        operator_call.children = [label_f, label_x]

        actual = list(parser(tokens))
        expected = [operator_call]
        self.assertFalse(parsecmp(expected, actual, False))

    def test_001_basic_expr_12(self):

        tokens = list(lexer("f()()"))

        operator_call1 = Token(Token.S_CALL_FUNCTION, 1, 1, '')
        operator_call2 = Token(Token.S_CALL_FUNCTION, 1, 1, '')
        label_f = Token(Token.S_LABEL, 1, 1, 'f')

        operator_call1.children = [label_f]
        operator_call2.children = [operator_call1]

        actual = list(parser(tokens))
        expected = [operator_call2]
        self.assertFalse(parsecmp(expected, actual, False))

    def test_001_basic_expr_13(self):

        def TOKEN(t,v,*children):
            return Token(getattr(Token,t), 1, 0, v, children)
        tokens = list(lexer("x=y=0"))
        actual = list(parser(tokens))
        expected = [
            TOKEN('S_OPERATOR2', '=',
                TOKEN('S_LABEL', 'x'),
                TOKEN('S_OPERATOR2', '=',
                    TOKEN('S_LABEL', 'y'),
                    TOKEN('S_NUMBER', '0')))
        ]
        self.assertFalse(parsecmp(expected, actual, False))

    def test_001_basic_expr_14(self):

        def TOKEN(t,v,*children):
            return Token(getattr(Token,t), 1, 0, v, children)
        tokens = list(lexer("x as y"))
        actual = list(parser(tokens))
        expected = [
            TOKEN('S_OPERATOR2', 'as',
                TOKEN('S_LABEL', 'x'),
                TOKEN('S_LABEL', 'y'))
        ]
        self.assertFalse(parsecmp(expected, actual, False))

    def test_001_basic_expr_15(self):

        def TOKEN(t,v,*children):
            return Token(getattr(Token,t), 1, 0, v, children)
        tokens = list(lexer("x in y"))
        actual = list(parser(tokens))
        expected = [
            TOKEN('S_OPERATOR2', 'in',
                TOKEN('S_LABEL', 'x'),
                TOKEN('S_LABEL', 'y'))
        ]
        self.assertFalse(parsecmp(expected, actual, False))

    def test_001_basic_expr_16(self):

        def TOKEN(t,v,*children):
            return Token(getattr(Token,t), 1, 0, v, children)
        tokens = list(lexer("x not in y"))
        actual = list(parser(tokens))
        expected = [
            TOKEN('S_OPERATOR2', 'not in',
                TOKEN('S_LABEL', 'x'),
                TOKEN('S_LABEL', 'y'))
        ]
        self.assertFalse(parsecmp(expected, actual, False))

    def test_001_build_map_expr_1(self):

        tokens = list(lexer("x = {0:1,2:3}"))

        operator_assign = Token(Token.S_OPERATOR2, 1, 3, '=')
        label_x = Token(Token.S_LABEL, 1, 1, 'x')
        build_map = Token(Token.S_BUILD, 1, 4, 'MAP')
        const_0 = Token(Token.S_NUMBER, 1, 6, '0')
        const_1 = Token(Token.S_NUMBER, 1, 8, '1')
        const_2 = Token(Token.S_NUMBER, 1, 10, '2')
        const_3 = Token(Token.S_NUMBER, 1, 12, '3')

        build_map.children = [const_0,const_1,const_2,const_3,]
        operator_assign.children = [label_x, build_map]

        actual = list(parser(tokens))
        expected = [operator_assign]
        self.assertFalse(parsecmp(expected, actual, False))

    def test_001_build_set_expr_1(self):


        operator_assign = Token(Token.S_OPERATOR2, 1, 3, '=')
        label_x = Token(Token.S_LABEL, 1, 1, 'x')
        build_map = Token(Token.S_BUILD, 1, 4, 'SET')
        const_0 = Token(Token.S_NUMBER, 1, 6, '0')
        const_1 = Token(Token.S_NUMBER, 1, 8, '1')
        const_2 = Token(Token.S_NUMBER, 1, 10, '2')
        const_3 = Token(Token.S_NUMBER, 1, 12, '3')

        build_map.children = [const_0,const_1,const_2,const_3,]
        operator_assign.children = [label_x, build_map]

        tokens = list(lexer("x = {0,1,2,3}"))
        actual = list(parser(tokens))
        expected = [operator_assign]
        self.assertFalse(parsecmp(expected, actual, False))

    def test_001_subscr_expr_1(self):

        tokens = list(lexer("m[0]"))

        label_m = Token(Token.S_LABEL, 1, 1, 'm')
        operator_subscr = Token(Token.S_SUBSCR, 1, 1, '')
        const_0 = Token(Token.S_NUMBER, 1, 3, '0')

        operator_subscr.children = [label_m, const_0]

        actual = list(parser(tokens))
        expected = [operator_subscr]
        self.assertFalse(parsecmp(expected, actual, False))

    def test_001_subscr_expr_2(self):

        tokens = list(lexer("m[0:1]"))

        label_m = Token(Token.S_LABEL, 1, 1, 'm')
        operator_subscr = Token(Token.S_SUBSCR, 1, 1, '')
        operator_slice = Token(Token.S_SLICE, 1, 4, '')
        const_0 = Token(Token.S_NUMBER, 1, 3, '0')
        const_1 = Token(Token.S_NUMBER, 1, 5, '1')

        operator_subscr.children = [label_m, operator_slice]
        operator_slice.children = [const_0, const_1]

        actual = list(parser(tokens))
        expected = [operator_subscr]
        self.assertFalse(parsecmp(expected, actual, False))

    def test_001_subscr_expr_3(self):

        tokens = list(lexer("m[0:1:2]"))

        label_m = Token(Token.S_LABEL, 1, 1, 'm')
        operator_subscr = Token(Token.S_SUBSCR, 1, 1, '')
        operator_slice = Token(Token.S_SLICE, 1, 4, '')
        const_0 = Token(Token.S_NUMBER, 1, 3, '0')
        const_1 = Token(Token.S_NUMBER, 1, 5, '1')
        const_2 = Token(Token.S_NUMBER, 1, 5, '2')

        operator_subscr.children = [label_m, operator_slice]
        operator_slice.children = [const_0, const_1, const_2]

        actual = list(parser(tokens))
        expected = [operator_subscr]
        self.assertFalse(parsecmp(expected, actual, False))

    def test_001_subscr_expr_4(self):

        tokens = list(lexer("m[:1]"))

        label_m = Token(Token.S_LABEL, 1, 1, 'm')
        operator_subscr = Token(Token.S_SUBSCR, 1, 1, '')
        operator_slice = Token(Token.S_SLICE, 1, 4, '')
        const_1 = Token(Token.S_NUMBER, 1, 5, '1')
        label_p = Token(Token.S_NONE)

        operator_subscr.children = [label_m, operator_slice]
        operator_slice.children = [label_p, const_1]

        actual = list(parser(tokens))
        expected = [operator_subscr]
        self.assertFalse(parsecmp(expected, actual, False))

    def test_001_subscr_expr_5(self):

        tokens = list(lexer("m[1:]"))

        label_m = Token(Token.S_LABEL, 1, 1, 'm')
        operator_subscr = Token(Token.S_SUBSCR, 1, 1, '')
        operator_slice = Token(Token.S_SLICE, 1, 4, '')
        const_1 = Token(Token.S_NUMBER, 1, 5, '1')
        label_p = Token(Token.S_NONE)

        operator_subscr.children = [label_m, operator_slice]
        operator_slice.children = [const_1, label_p]

        actual = list(parser(tokens))
        expected = [operator_subscr]
        self.assertFalse(parsecmp(expected, actual, False))

    def test_001_advanced_expr_1(self):

        tokens = list(lexer("while true break"))

        label_w = Token(Token.S_WHILE, 1, 5, 'while')
        label_t = Token(Token.S_TRUE, 1, 10, 'true')
        label_b = Token(Token.S_BREAK, 1, 15, 'break')

        label_w.children = [label_t, label_b]
        actual = list(parser(tokens))
        expected = [label_w]

        self.assertFalse(parsecmp(expected, actual, False))

    def test_001_advanced_expr_2(self):

        tokens = list(lexer("while false continue 2"))

        label_w = Token(Token.S_WHILE, 1, 5, 'while')
        label_t = Token(Token.S_FALSE, 1, 10, 'false')
        label_c = Token(Token.S_CONTINUE, 1, 15, 'continue')
        label_n = Token(Token.S_NUMBER, 1, 15, '2')

        label_c.children = [label_n]
        label_w.children = [label_t, label_c]
        actual = list(parser(tokens))
        expected = [label_w]

        self.assertFalse(parsecmp(expected, actual, False))

    def xtest_001_advanced_expr_3(self):

        tokens = list(lexer("for x in range(7) {print(x)}"))

        tok_call1 = Token(Token.S_CALL_FUNCTION, 1, 13, '')
        tok_call2 = Token(Token.S_CALL_FUNCTION, 1, 23, '')
        tok_for = Token(Token.S_FOREACH, 1, 3, 'for')
        tok_x =  Token(Token.S_LABEL, 1, 5, 'x')
        tok_range = Token(Token.S_LABEL, 1, 13, 'range')
        tok_print = Token(Token.S_LABEL, 1, 23, 'print')
        tok_7 = Token(Token.S_NUMBER, 1, 15, '7')

        tok_call1.children = [tok_range, tok_7]
        tok_call2.children = [tok_print, tok_x]
        tok_for.children = [tok_x, tok_call1, tok_call2]

        actual = list(parser(tokens))
        expected = [tok_for]

        self.assertFalse(parsecmp(expected, actual, False))

    def test_001_advanced_expr_4a(self):


        def TOKEN(t,v,*children):
            return Token(getattr(Token,t), 1, 0, v, children)

        asf = TOKEN('S_LAMBDA', '',
            TOKEN('S_LAMBDA_NAMELIST', '',
                TOKEN('S_OPERATOR2', '=',
                    TOKEN('S_LABEL', 'a', ),
                    TOKEN('S_NUMBER', '0', )),
                TOKEN('S_OPERATOR2', '=',
                    TOKEN('S_LABEL', 'b', ),
                    TOKEN('S_NUMBER', '0', ))),
            TOKEN('S_LAMBDA_CLOSURE', '', ),
                TOKEN('S_OPERATOR2', '=',
                    TOKEN('S_TUPLE', ',',
                        TOKEN('S_LABEL', 'a', ),
                        TOKEN('S_LABEL', 'b', )),
                    TOKEN('S_TUPLE', ',',
                        TOKEN('S_LABEL', 'b', ),
                        TOKEN('S_LABEL', 'a', ))))

        tokens = list(lexer("(a=0,b=0)=>{a,b=b,a}"))
        actual = list(parser(tokens))
        expected = [asf]
        self.assertFalse(parsecmp(expected, actual, False))

    def test_001_advanced_expr_4c(self):

        def TOKEN(t,v,*children):
            return Token(getattr(Token,t), 1, 0, v, children)

        asf = TOKEN('S_CALL_FUNCTION', '',
            TOKEN('S_LABEL', 'f', ),
            TOKEN('S_OPERATOR2', '=',
                TOKEN('S_LABEL', 'a', ),
                TOKEN('S_NUMBER', '0', )),
            TOKEN('S_OPERATOR2', '=',
                TOKEN('S_LABEL', 'b', ),
                TOKEN('S_NUMBER', '1', )))

        tokens = list(lexer("f(a=0,b=1)"))
        actual = list(parser(tokens))
        expected = [asf]
        self.assertFalse(parsecmp(expected, actual, False))

    def test_005_lambda_3(self):
        """
        f = () => {x=0; return () => {x += 1}}

        # f=()=>{k=1;g=()=>{k=k+1;return k;};return g;}; h=f(); print(h(),h());
        # f=(k)=>{return ()=>{k=k+1;return k;}}; g=f(); print(g(),g());

        test that closures are generated properly in nested context
        this function returns a function which increments a variable
        from a parent scope. multiple calls will return successive values
        while a new call to the top level function returns a new context
        """
        def TOKEN(t,v,*children):
            return Token(getattr(Token,t), 1, 0, v, children)
        asf = [
            TOKEN('S_OPERATOR2', '=',
            TOKEN('S_LABEL', 'f', ),
            TOKEN('S_LAMBDA', '',
                TOKEN('S_LAMBDA_NAMELIST', '', ),
                TOKEN('S_LAMBDA_CLOSURE', '', ),
                TOKEN('S_BLOCK', '{closure}',
                    TOKEN('S_CLOSURE', '',
                        TOKEN('S_REFERENCE', 'x', )),
                    TOKEN('S_BLOCK', '{}',
                        TOKEN('S_OPERATOR2', '=',
                            TOKEN('S_LABEL', 'x', ),
                            TOKEN('S_NUMBER', '0', )),
                        TOKEN('S_RETURN', 'return',
                            TOKEN('S_LAMBDA', '',
                                TOKEN('S_LAMBDA_NAMELIST', '', ),
                                TOKEN('S_LAMBDA_CLOSURE', '',
                                    TOKEN('S_REFERENCE', 'x', )),
                                TOKEN('S_OPERATOR2', '+=',
                                    TOKEN('S_REFERENCE', 'x', ),
                                    TOKEN('S_NUMBER', '1', ))))))))
        ]

        tokens = list(lexer("f = () => {x=0; return () => {x += 1}}"))
        actual = list(parser(tokens))
        self.assertFalse(parsecmp(asf, actual, False))

    def test_005_lambda_4(self):

        def TOKEN(t,v,*children):
            return Token(getattr(Token,t), 1, 0, v, children)

        tokens = list(lexer("()=>{}()"))
        actual = list(parser(tokens))
        expected = [
            TOKEN('S_CALL_FUNCTION', '()',
                TOKEN('S_LAMBDA', '',
                    TOKEN('S_LAMBDA_NAMELIST', ''),
                    TOKEN('S_LAMBDA_CLOSURE', ''),
                    TOKEN('S_BUILD', 'SET')))
        ]

        self.assertFalse(parsecmp(expected, actual, False))

    def test_005_shell_1(self):

        tokens = list(lexer("exec cat \"/tmp/file\""))
        actual = list(parser(tokens))
        expected = [
            Token(Token.S_EXEC_PROCESS, 1, 4, 'exec',
                [
                    Token(Token.S_LABEL, 1, 8, 'Proc',
                        [Token(Token.S_STRING, 1, 8, 'cat'),
                        Token(Token.S_STRING, 1, 19, '/tmp/file')])
                ]
            )
        ]

        self.assertFalse(parsecmp(expected, actual, False))

    def test_005_shell_2(self):

        tokens = list(lexer("exec cat |> exec grep"))
        actual = list(parser(tokens))
        expected = [
            Token(Token.S_EXEC_PROCESS, 1, 4, '|>',
                [
                    Token(Token.S_EXEC_PROCESS, 1, 4, 'exec',
                        [Token(Token.S_LABEL, 1, 8, 'Proc'),
                         Token(Token.S_STRING, 1, 8, 'grep')]),
                    Token(Token.S_CALL_FUNCTION, 1, 4, '',
                        [Token(Token.S_EXEC_PROCESS, 1, 4, 'exec',
                            [Token(Token.S_LABEL, 1, 8, 'Proc'),
                             Token(Token.S_STRING, 1, 8, 'cat')])]
                    )
                ]
            )
        ]

        self.assertFalse(parsecmp(expected, actual, False))

    def test_005_shell_3(self):

        def TOKEN(t,v,*children):
            return Token(getattr(Token,t), 1, 0, v, children)

        tokens = list(lexer("exec true 1>2 2>&stdout"))
        actual = list(parser(tokens))
        expected = [
            TOKEN('S_EXEC_PROCESS', 'exec',
                TOKEN('S_LABEL', 'Proc'),
                TOKEN('S_STRING', 'true'),
                TOKEN('S_CALL_FUNCTION', '',
                    TOKEN('S_ATTR', '',
                        TOKEN('S_LABEL', 'Proc'),
                        TOKEN('S_ATTR_LABEL', 'Redirect')),
                    TOKEN('S_NUMBER', '1'),
                    TOKEN('S_STRING', '1'),
                    TOKEN('S_STRING', '2')),
                TOKEN('S_CALL_FUNCTION', '',
                    TOKEN('S_ATTR', '',
                        TOKEN('S_LABEL', 'Proc'),
                        TOKEN('S_ATTR_LABEL', 'Redirect')),
                    TOKEN('S_NUMBER', '1'),
                    TOKEN('S_STRING', '2'),
                    TOKEN('S_STRING', '&stdout')))
        ]

        self.assertFalse(parsecmp(expected, actual, False))

    def test_006_comprehension_2(self):

        def TOKEN(t,v,*children):
            return Token(getattr(Token,t), 1, 0, v, children)

        tokens = list(lexer("x = [a for a in b if a]"))
        actual = list(parser(tokens))
        expected = [
            TOKEN('S_OPERATOR2', '=',
                TOKEN('S_LABEL', 'x'),
                TOKEN('S_LIST_COMPREHENSION', '',
                    TOKEN('S_KEYWORD', 'for',
                        TOKEN('S_LABEL', 'a'),
                        TOKEN('S_LABEL', 'b'),
                        TOKEN('S_KEYWORD', 'if',
                            TOKEN('S_LABEL', 'a'))),
                    TOKEN('S_LABEL', 'a')))
        ]

        self.assertFalse(parsecmp(expected, actual, False))

    def test_006_comprehension_3(self):

        def TOKEN(t,v,*children):
            return Token(getattr(Token,t), 1, 0, v, children)

        # TODO FAIL: lexer("x = {(a:b) for a,b in b if a}")
        # TODO PASS: lexer("x = {a:b for (a,b) in b if a}")
        tokens = list(lexer("x = {a:b for a,b in b if a}"))
        actual = list(parser(tokens))
        expected = [
            TOKEN('S_OPERATOR2', '=',
                TOKEN('S_LABEL', 'x'),
                TOKEN('S_DICT_COMPREHENSION', '',
                    TOKEN('S_KEYWORD', 'for',
                        TOKEN('S_TUPLE', ',',
                            TOKEN('S_LABEL', 'a'),
                            TOKEN('S_LABEL', 'b')),
                        TOKEN('S_LABEL', 'b'),
                        TOKEN('S_KEYWORD', 'if',
                            TOKEN('S_LABEL', 'a'))),
                    TOKEN('S_SLICE', '',
                        TOKEN('S_LABEL', 'a'),
                        TOKEN('S_LABEL', 'b'))))
        ]

        self.assertFalse(parsecmp(expected, actual, False))


    def test_007_var_1(self):

        def TOKEN(t,v,*children):
            return Token(getattr(Token,t), 1, 0, v, children)

        tokens = list(lexer("var x = 7"))
        actual = list(parser(tokens))
        expected = [
            TOKEN('S_OPERATOR2', '=',
                TOKEN('S_LABEL', 'x'),
                TOKEN('S_NUMBER', '7'))
        ]

        self.assertFalse(parsecmp(expected, actual, False))

    def test_007_assignment_1(self):

        def TOKEN(t,v,*children):
            return Token(getattr(Token,t), 1, 0, v, children)

        tokens = list(lexer("a.b->c = 1"))
        actual = list(parser(tokens))

        #expected = [
        #    TOKEN('S_OPERATOR2', '=',
        #        TOKEN('S_SUBSCR', '->',
        #            TOKEN('S_ATTR', '.',
        #                TOKEN('S_LABEL', 'a'),
        #                TOKEN('S_ATTR_LABEL', 'b')),
        #            TOKEN('S_STRING', 'c')),
        #        TOKEN('S_NUMBER', '1'))
        #]

        expected = [
            TOKEN('S_OPERATOR2', '=',
                TOKEN('S_CALL_FUNCTION', '->',
                    TOKEN('S_LABEL', '__es_drill__',
                        TOKEN('S_ATTR', '.',
                            TOKEN('S_LABEL', 'a'),
                            TOKEN('S_ATTR_LABEL', 'b')),
                        TOKEN('S_STRING', 'c'))),
                TOKEN('S_NUMBER', '1'))
        ]


        self.assertFalse(parsecmp(expected, actual, False))

    def test_007_string_2(self):

        def TOKEN(t,v,*children):
            return Token(getattr(Token,t), 1, 0, v, children)

        tokens = list(lexer("'s1' 's2'"))
        actual = list(parser(tokens))
        expected = [
            TOKEN('S_STRING', 's1s2')
        ]

        self.assertFalse(parsecmp(expected, actual, False))

    def test_007_transform_1(self):

        def TOKEN(t,v,*children):
            return Token(getattr(Token,t), 1, 0, v, children)

        tokens = list(lexer("x is y"))
        actual = list(parser(tokens))
        expected = [
            TOKEN('S_OPERATOR2', 'is',
                TOKEN('S_LABEL', 'x'),
                TOKEN('S_LABEL', 'y'))
        ]

        self.assertFalse(parsecmp(expected, actual, False))

    def test_007_transform_2(self):

        def TOKEN(t,v,*children):
            return Token(getattr(Token,t), 1, 0, v, children)

        tokens = list(lexer("x is not y"))
        actual = list(parser(tokens))
        expected = [
            TOKEN('S_OPERATOR2', 'is not',
                TOKEN('S_LABEL', 'x'),
                TOKEN('S_LABEL', 'y'))
        ]

        self.assertFalse(parsecmp(expected, actual, False))

    def test_007_transform_3(self):

        def TOKEN(t,v,*children):
            return Token(getattr(Token,t), 1, 0, v, children)

        tokens = list(lexer("not y"))
        actual = list(parser(tokens))
        expected = [
            TOKEN('S_PREFIX', '!',
                TOKEN('S_LABEL', 'y'))
        ]

        self.assertFalse(parsecmp(expected, actual, False))

    def test_007_transform_3_json(self):

        def TOKEN(t,v,*children):
            return Token(getattr(Token,t), 1, 0, v, children)

        tokens = list(lexer("[true, false, nan, infinity, null]"))
        actual = list(parser(tokens))
        expected = [
            TOKEN('S_BUILD', 'LIST',
                TOKEN('S_TRUE', 'true'),
                TOKEN('S_FALSE', 'false'),
                TOKEN('S_NAN', 'nan'),
                TOKEN('S_INFINITY', 'infinity'),
                TOKEN('S_NULL', 'null'))
        ]

        self.assertFalse(parsecmp(expected, actual, False))

    def test_007_transform_4_python(self):

        def TOKEN(t,v,*children):
            return Token(getattr(Token,t), 1, 0, v, children)

        tokens = list(lexer("[True, False, None]"))
        actual = list(parser(tokens))
        expected = [
            TOKEN('S_BUILD', 'LIST',
                TOKEN('S_TRUE', 'True'),
                TOKEN('S_FALSE', 'False'),
                TOKEN('S_NULL', 'None'))
        ]

        self.assertFalse(parsecmp(expected, actual, False))

    def test_008_with_1(self):

        def TOKEN(t,v,*children):
            return Token(getattr(Token,t), 1, 0, v, children)

        tokens = list(lexer("with a {return}"))
        actual = list(parser(tokens))
        expected = [
            TOKEN('S_WITH', 'with',
                TOKEN('S_LABEL', 'a'),
                TOKEN('S_RETURN', 'return'))
        ]

        self.assertFalse(parsecmp(expected, actual, False))

    def test_008_with_2(self):

        def TOKEN(t,v,*children):
            return Token(getattr(Token,t), 1, 0, v, children)

        tokens = list(lexer("with a=b {return}"))
        actual = list(parser(tokens))
        expected = [
            TOKEN('S_WITH', 'with',
                TOKEN('S_OPERATOR2', '=',
                    TOKEN('S_LABEL', 'a'),
                    TOKEN('S_LABEL', 'b')),
                TOKEN('S_RETURN', 'return'))
        ]

        self.assertFalse(parsecmp(expected, actual, False))

    def test_008_with_3(self):

        def TOKEN(t,v,*children):
            return Token(getattr(Token,t), 1, 0, v, children)

        tokens = list(lexer("with (a=b) {return}"))
        actual = list(parser(tokens))
        expected = [
            TOKEN('S_WITH', 'with',
                TOKEN('S_OPERATOR2', '=',
                    TOKEN('S_LABEL', 'a'),
                    TOKEN('S_LABEL', 'b')),
                TOKEN('S_RETURN', 'return'))
        ]

        self.assertFalse(parsecmp(expected, actual, False))

    def test_009_branch_1(self):

        def TOKEN(t,v,*children):
            return Token(getattr(Token,t), 1, 0, v, children)

        tokens = list(lexer("if a b"))
        actual = list(parser(tokens))
        expected = [
            TOKEN('S_BRANCH', 'if',
                TOKEN('S_LABEL', 'a'),
                TOKEN('S_LABEL', 'b'),
                TOKEN('S_NONE', ''))
        ]

        self.assertFalse(parsecmp(expected, actual, False))

    def test_009_branch_2(self):

        def TOKEN(t,v,*children):
            return Token(getattr(Token,t), 1, 0, v, children)

        tokens = list(lexer("if a==0 b"))
        actual = list(parser(tokens))
        expected = [
            TOKEN('S_BRANCH', 'if',
                TOKEN('S_OPERATOR2', '==',
                    TOKEN('S_LABEL', 'a'),
                    TOKEN('S_NUMBER', '0')),
                TOKEN('S_LABEL', 'b'),
                TOKEN('S_NONE', ''))
        ]

        self.assertFalse(parsecmp(expected, actual, False))

    def test_009_branch_3(self):

        def TOKEN(t,v,*children):
            return Token(getattr(Token,t), 1, 0, v, children)

        tokens = list(lexer("if (a==0) b"))
        actual = list(parser(tokens))
        expected = [
            TOKEN('S_BRANCH', 'if',
                TOKEN('S_OPERATOR2', '==',
                    TOKEN('S_LABEL', 'a'),
                    TOKEN('S_NUMBER', '0')),
                TOKEN('S_LABEL', 'b'),
                TOKEN('S_NONE', ''))
        ]

        self.assertFalse(parsecmp(expected, actual, False))

    def test_009_branch_4(self):

        def TOKEN(t,v,*children):
            return Token(getattr(Token,t), 1, 0, v, children)

        tokens = list(lexer("if a b else c"))
        actual = list(parser(tokens))
        expected = [
            TOKEN('S_BRANCH', 'if',
                TOKEN('S_LABEL', 'a'),
                TOKEN('S_LABEL', 'b'),
                TOKEN('S_LABEL', 'c'))
        ]

        self.assertFalse(parsecmp(expected, actual, False))

    def test_009_branch_5(self):

        def TOKEN(t,v,*children):
            return Token(getattr(Token,t), 1, 0, v, children)

        tokens = list(lexer("if a b else if c d"))
        actual = list(parser(tokens))
        expected = [
            TOKEN('S_BRANCH', 'if',
                TOKEN('S_LABEL', 'a'),
                TOKEN('S_LABEL', 'b'),
                TOKEN('S_BRANCH', 'if',
                    TOKEN('S_LABEL', 'c'),
                    TOKEN('S_LABEL', 'd'),
                    TOKEN('S_NONE', '')))
        ]

        self.assertFalse(parsecmp(expected, actual, False))

    def test_009_branch_6(self):

        def TOKEN(t,v,*children):
            return Token(getattr(Token,t), 1, 0, v, children)

        tokens = list(lexer("if a b else if c d else e"))
        actual = list(parser(tokens))
        expected = [
            TOKEN('S_BRANCH', 'if',
                TOKEN('S_LABEL', 'a'),
                TOKEN('S_LABEL', 'b'),
                TOKEN('S_BRANCH', 'if',
                    TOKEN('S_LABEL', 'c'),
                    TOKEN('S_LABEL', 'd'),
                    TOKEN('S_LABEL', 'e')))
        ]

        self.assertFalse(parsecmp(expected, actual, False))

    def test_010_foreach_1(self):

        def TOKEN(t,v,*children):
            return Token(getattr(Token,t), 1, 0, v, children)

        tokens = list(lexer("for a in b {return}"))
        actual = list(parser(tokens))
        expected = [
            TOKEN('S_FOREACH', 'for',
                TOKEN('S_LABEL', 'a'),
                TOKEN('S_LABEL', 'b'),
                TOKEN('S_RETURN', 'return'))
        ]

        self.assertFalse(parsecmp(expected, actual, False))

    def test_010_foreach_2(self):

        def TOKEN(t,v,*children):
            return Token(getattr(Token,t), 1, 0, v, children)

        tokens = list(lexer("for (a,b) in c {return}"))
        actual = list(parser(tokens))
        expected = [
            TOKEN('S_FOREACH', 'for',
                TOKEN('S_TUPLE', ',',
                    TOKEN('S_LABEL', 'a'),
                    TOKEN('S_LABEL', 'b')),
                TOKEN('S_LABEL', 'c'),
                TOKEN('S_RETURN', 'return'))
        ]

        self.assertFalse(parsecmp(expected, actual, False))

    def test_010_foreach_3(self):

        def TOKEN(t,v,*children):
            return Token(getattr(Token,t), 1, 0, v, children)

        tokens = list(lexer("for ((a,b) in c) {return}"))
        actual = list(parser(tokens))
        expected = [
            TOKEN('S_FOREACH', 'for',
                TOKEN('S_TUPLE', ',',
                    TOKEN('S_LABEL', 'a'),
                    TOKEN('S_LABEL', 'b')),
                TOKEN('S_LABEL', 'c'),
                TOKEN('S_RETURN', 'return'))
        ]

        self.assertFalse(parsecmp(expected, actual, False))

    def test_011_tuple_1(self):

        def TOKEN(t,v,*children):
            return Token(getattr(Token,t), 1, 0, v, children)

        tokens = list(lexer("(a,(b,(c,d)),e) = (1,(2,(3,4)),5)"))
        actual = list(parser(tokens))
        expected = [
            TOKEN('S_OPERATOR2', '=',
                TOKEN('S_TUPLE', ',',
                    TOKEN('S_LABEL', 'a'),
                    TOKEN('S_TUPLE', ',',
                        TOKEN('S_LABEL', 'b'),
                        TOKEN('S_TUPLE', ',',
                            TOKEN('S_LABEL', 'c'),
                            TOKEN('S_LABEL', 'd'))),
                    TOKEN('S_LABEL', 'e')),
                TOKEN('S_TUPLE', ',',
                    TOKEN('S_NUMBER', '1'),
                    TOKEN('S_TUPLE', ',',
                        TOKEN('S_NUMBER', '2'),
                        TOKEN('S_TUPLE', ',',
                            TOKEN('S_NUMBER', '3'),
                            TOKEN('S_NUMBER', '4'))),
                    TOKEN('S_NUMBER', '5')))
        ]

        self.assertFalse(parsecmp(expected, actual, False))

    def test_012_import_1(self):

        def TOKEN(t,v,*children):
            return Token(getattr(Token,t), 1, 0, v, children)

        tokens = list(lexer("import abc"))
        actual = list(parser(tokens))

        expected = [
            TOKEN('S_IMPORT', 'abc',
                TOKEN('S_NUMBER', '0'),
                TOKEN('S_STRING', 'abc'),
                TOKEN('S_TUPLE', ''))
        ]

        self.assertFalse(parsecmp(expected, actual, False))

    def test_012_import_2(self):

        def TOKEN(t,v,*children):
            return Token(getattr(Token,t), 1, 0, v, children)

        tokens = list(lexer("import .abc"))
        actual = list(parser(tokens))

        expected = [
            TOKEN('S_IMPORT', 'abc',
                TOKEN('S_NUMBER', '1'),
                TOKEN('S_STRING', 'abc'),
                TOKEN('S_TUPLE', ''))
        ]

        self.assertFalse(parsecmp(expected, actual, False))

    def test_012_import_3(self):

        def TOKEN(t,v,*children):
            return Token(getattr(Token,t), 1, 0, v, children)

        tokens = list(lexer("from abc import def"))
        actual = list(parser(tokens))

        expected = [
            TOKEN('S_IMPORT', 'abc',
                TOKEN('S_NUMBER', '0'),
                TOKEN('S_STRING', 'abc'),
                TOKEN('S_TUPLE', '',
                    TOKEN('S_LABEL', 'def')))
        ]

        self.assertFalse(parsecmp(expected, actual, False))

    def test_012_import_4(self):

        def TOKEN(t,v,*children):
            return Token(getattr(Token,t), 1, 0, v, children)

        tokens = list(lexer("from .abc import def as ghi"))
        actual = list(parser(tokens))

        expected = [
            TOKEN('S_IMPORT', 'abc',
                TOKEN('S_NUMBER', '1'),
                TOKEN('S_STRING', 'abc'),
                TOKEN('S_TUPLE', '',
                    TOKEN('S_OPERATOR2', 'as',
                        TOKEN('S_LABEL', 'def'),
                        TOKEN('S_LABEL', 'ghi'))))
        ]

        self.assertFalse(parsecmp(expected, actual, False))

    def test_012_import_5(self):

        def TOKEN(t,v,*children):
            return Token(getattr(Token,t), 1, 0, v, children)

        tokens = list(lexer("from .abc import a, b, c"))
        actual = list(parser(tokens))

        expected = [
            TOKEN('S_IMPORT', 'abc',
                TOKEN('S_NUMBER', '1'),
                TOKEN('S_STRING', 'abc'),
                TOKEN('S_TUPLE', '',
                    TOKEN('S_LABEL', 'a'),
                    TOKEN('S_LABEL', 'b'),
                    TOKEN('S_LABEL', 'c')))
        ]

        self.assertFalse(parsecmp(expected, actual, False))

    def test_012_optional_1(self):

        def TOKEN(t,v,*children):
            return Token(getattr(Token,t), 1, 0, v, children)

        tokens = list(lexer("a?.b"))
        actual = list(parser(tokens))

        expected = [
            TOKEN('S_OPTIONAL_ATTR', '?.',
                TOKEN('S_LABEL', 'a'),
                TOKEN('S_ATTR_LABEL', 'b'))
        ]

        self.assertFalse(parsecmp(expected, actual, False))

    def test_013_objects_1(self):

        def TOKEN(t,v,*children):
            return Token(getattr(Token,t), 1, 0, v, children)
        tokens = list(lexer("()"))
        actual = list(parser(tokens))
        expected = [TOKEN('S_BUILD', 'TUPLE')]
        self.assertFalse(parsecmp(expected, actual, False))

    def test_013_objects_2(self):

        def TOKEN(t,v,*children):
            return Token(getattr(Token,t), 1, 0, v, children)
        tokens = list(lexer("[]"))
        actual = list(parser(tokens))
        expected = [TOKEN('S_BUILD', 'LIST')]
        self.assertFalse(parsecmp(expected, actual, False))

    def test_013_objects_3(self):

        def TOKEN(t,v,*children):
            return Token(getattr(Token,t), 1, 0, v, children)
        tokens = list(lexer("{}"))
        actual = list(parser(tokens))
        expected = [TOKEN('S_BUILD', 'SET')]
        self.assertFalse(parsecmp(expected, actual, False))

    def test_013_objects_4(self):

        def TOKEN(t,v,*children):
            return Token(getattr(Token,t), 1, 0, v, children)
        tokens = list(lexer("{:}"))
        actual = list(parser(tokens))
        expected = [TOKEN('S_BUILD', 'MAP')]
        self.assertFalse(parsecmp(expected, actual, False))

    def test_013_objects_5(self):

        def TOKEN(t,v,*children):
            return Token(getattr(Token,t), 1, 0, v, children)
        tokens = list(lexer("(0,)"))
        actual = list(parser(tokens))
        expected = [TOKEN('S_TUPLE', ',', Token(Token.S_NUMBER, 1, 1, '0'))]
        self.assertFalse(parsecmp(expected, actual, False))

    def test_013_objects_6(self):

        def TOKEN(t,v,*children):
            return Token(getattr(Token,t), 1, 0, v, children)
        tokens = list(lexer("[0]"))
        actual = list(parser(tokens))
        expected = [TOKEN('S_BUILD', 'LIST', Token(Token.S_NUMBER, 1, 1, '0'))]
        self.assertFalse(parsecmp(expected, actual, False))

    def test_013_objects_7(self):

        def TOKEN(t,v,*children):
            return Token(getattr(Token,t), 1, 0, v, children)
        tokens = list(lexer("{0,}"))
        actual = list(parser(tokens))
        expected = [TOKEN('S_BUILD', 'SET', Token(Token.S_NUMBER, 1, 1, '0'))]
        self.assertFalse(parsecmp(expected, actual, False))

    def test_013_objects_8(self):

        def TOKEN(t,v,*children):
            return Token(getattr(Token,t), 1, 0, v, children)
        tokens = list(lexer("{0:1}"))
        actual = list(parser(tokens))
        expected = [TOKEN('S_BUILD', 'MAP',
                Token(Token.S_NUMBER, 1, 1, '0'),
                Token(Token.S_NUMBER, 1, 1, '1'))]
        self.assertFalse(parsecmp(expected, actual, False))

    def test_013_objects_9(self):

        def TOKEN(t,v,*children):
            return Token(getattr(Token,t), 1, 0, v, children)

        tokens = list(lexer("[1,2,3][:]"))
        actual = list(parser(tokens))

        expected = [
            TOKEN('S_SUBSCR', '',
                TOKEN('S_BUILD', 'LIST',
                    TOKEN('S_NUMBER', '1'),
                    TOKEN('S_NUMBER', '2'),
                    TOKEN('S_NUMBER', '3')),
                TOKEN('S_SLICE', ''))
        ]

        self.assertFalse(parsecmp(expected, actual, False))



    def test_013_switch_1(self):

        def TOKEN(t,v,*children):
            return Token(getattr(Token,t), 1, 0, v, children)

        tokens = list(lexer("""
            switch (expr) {
                case (v2)
                case (v1) {
                    break
                }
                default {
                    break
                }
            }
        """))
        actual = list(parser(tokens))

        expected = [
            TOKEN('S_SWITCH', 'switch',
                TOKEN('S_LABEL', 'expr'),
                TOKEN('S_SWITCH_CASE', 'case',
                    TOKEN('S_LABEL', 'v2')),
                TOKEN('S_SWITCH_CASE', 'case',
                    TOKEN('S_LABEL', 'v1'),
                    TOKEN('S_BREAK', 'break')),
                TOKEN('S_SWITCH_DEFAULT', 'default',
                    TOKEN('S_BREAK', 'break')))
        ]

        self.assertFalse(parsecmp(expected, actual, False))

    def test_013_switch_2(self):

        def TOKEN(t,v,*children):
            return Token(getattr(Token,t), 1, 0, v, children)

        tokens = list(lexer("""
            switch (expr) {
                default
                case (v1) {
                    break
                }
            }
        """))
        actual = list(parser(tokens))

        expected = [
            TOKEN('S_SWITCH', 'switch',
                TOKEN('S_LABEL', 'expr'),
                TOKEN('S_SWITCH_DEFAULT', 'default'),
                TOKEN('S_SWITCH_CASE', 'case',
                    TOKEN('S_LABEL', 'v1'),
                    TOKEN('S_BREAK', 'break')))
        ]

        self.assertFalse(parsecmp(expected, actual, False))

    def test_013_dowhile_1(self):

        def TOKEN(t,v,*children):
            return Token(getattr(Token,t), 1, 0, v, children)

        tokens = list(lexer("do{break}while(expr);"))
        actual = list(parser(tokens))

        expected = [
            TOKEN('S_DO_WHILE', 'do',
                TOKEN('S_BREAK', 'break'),
                TOKEN('S_LABEL', 'expr'))
        ]

        self.assertFalse(parsecmp(expected, actual, False))

    # TODO: [a for a in range(3)] -> [1,2,3]
    # TODO: [[a for a in range(3)]] -> [[1,2,3]]
    # TODO: ()=>{}() -> build and call lambda
    # TODO: ()=>{}()() -> build lambda call, call return value
    # TODO: [1,2,3] vs [(1,2,3)]

class ParserErrorTestCase(unittest.TestCase):

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
        with self.assertRaises(ParseError):
            parser(list(lexer("a % ")))

        with self.assertRaises(ParseError):
            parser(list(lexer(" % b")))

        with self.assertRaises(ParseError):
            parser(list(lexer(";a%;")))

        with self.assertRaises(ParseError):
            parser(list(lexer(";%b;")))

        with self.assertRaises(ParseError):
            parser(list(lexer("(a%)")))

        with self.assertRaises(ParseError):
            parser(list(lexer("(%b)")))

    def test_001_basic_expr_2(self):
        with self.assertRaises(ParseError):
            parser(list(lexer("else")))

def main():
    unittest.main()

if __name__ == '__main__':
    main()
