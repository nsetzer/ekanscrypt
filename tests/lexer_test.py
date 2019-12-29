#! cd .. && python3 -m ekanscrypt.lexer_test

import unittest

from ekanscrypt.token import Token
from ekanscrypt.lexer import lexer
from ekanscrypt.util import edit_distance
from ekanscrypt.exception import LexError

def tokcmp(a, b):
    if a is None:
        return False
    if b is None:
        return False
    return a.type == b.type and a.value == b.value

def lexcmp(expected, actual, debug=False):

    seq, cor, sub, ins, del_ = edit_distance(actual, expected, tokcmp)
    error_count = sub + ins + del_
    if error_count > 0 or debug:
        print("\ncor: %d sub: %d ins: %d del: %d" % (cor, sub, ins, del_))
        print("token error rate:", error_count / len(expected))
        print("\n%-50s | %-.50s" % ("    HYP", "    REF"))
        for a, b in seq:
            c = ' ' if tokcmp(a, b) else '|'
            print("%-50r %s %-.50r" % (a,c,b))
    return error_count

class LexerTestCase(unittest.TestCase):

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

        text = "x = 123 + 3.14"
        expected = [
            Token(Token.T_TEXT, 1, 1, 'x'),
            Token(Token.T_SPECIAL2, 1, 3, '='),
            Token(Token.T_NUMBER, 1, 7, '123'),
            Token(Token.T_SPECIAL2, 1, 9, '+'),
            Token(Token.T_NUMBER, 1, 13, '3.14'),
        ]
        tokens = list (lexer(text))

        self.assertFalse(lexcmp(expected, tokens, False))

    def test_001_basic_expr_2(self):

        # this test was originally marking the 2 in text1 as a label
        text1 = "fib(n-2);"
        text2 = "fib ( n - 2 ) ;"
        expected = [
            Token(Token.T_TEXT, 1, 3, 'fib'),
            Token(Token.T_SPECIAL1, 1, 3, '('),
            Token(Token.T_TEXT, 1, 5, 'n'),
            Token(Token.T_SPECIAL2, 1, 6, '-'),
            Token(Token.T_NUMBER, 1, 7, '2'),
            Token(Token.T_SPECIAL1, 1, 7, ')'),
            Token(Token.T_SPECIAL1, 1, 8, ';'),
        ]
        actual = list (lexer(text1))
        expected = list (lexer(text2))

        self.assertFalse(lexcmp(expected, actual, False))

    def test_001_basic_expr_3(self):

        text = "f().a"
        expected = [
            Token(Token.T_TEXT, 1, 1, 'f'),
            Token(Token.T_SPECIAL1, 1, 3, '('),
            Token(Token.T_SPECIAL1, 1, 7, ')'),
            Token(Token.T_SPECIAL1, 1, 9, '.'),
            Token(Token.T_TEXT, 1, 13, 'a'),
        ]
        tokens = list (lexer(text))

        self.assertFalse(lexcmp(expected, tokens, False))

    def test_001_basic_expr_4(self):

        text = "a &"
        expected = [
            Token(Token.T_TEXT, 1, 1, 'a'),
            Token(Token.T_SPECIAL2, 1, 3, '&'),
        ]
        tokens = list (lexer(text))

        self.assertFalse(lexcmp(expected, tokens, False))

    def test_001_basic_expr_5(self):

        text = "a ."
        expected = [
            Token(Token.T_TEXT, 1, 1, 'a'),
            Token(Token.T_SPECIAL1, 1, 3, '.'),
        ]
        tokens = list (lexer(text))

        self.assertFalse(lexcmp(expected, tokens, False))

    def test_001_basic_expr_6(self):

        text = "x # comment"
        expected = [
            Token(Token.T_TEXT, 1, 1, 'x'),
        ]
        tokens = list (lexer(text))

        self.assertFalse(lexcmp(expected, tokens, False))

    def test_001_basic_expr_7(self):

        text = "x \\t"
        with self.assertRaises(LexError):
            list (lexer(text))


    def test_001_number_int_1(self):

        text = "1"
        expected = [
            Token(Token.T_NUMBER, 1, 1, '1'),
        ]
        tokens = list (lexer(text))

    def test_001_number_float_1(self):

        text = "0.0"
        expected = [
            Token(Token.T_NUMBER, 1, 1, '0.0'),
        ]
        tokens = list (lexer(text))

    def test_001_number_float_2(self):

        text = ".0"
        expected = [
            Token(Token.T_NUMBER, 1, 1, '.0'),
        ]
        tokens = list (lexer(text))

    def test_001_advanced_expr_1(self):

        text = "if (a != b) { return 7 }"
        expected = [
            Token(Token.T_TEXT, 1, 2, 'if'),
            Token(Token.T_SPECIAL1, 1, 3, '('),
            Token(Token.T_TEXT, 1, 5, 'a'),
            Token(Token.T_SPECIAL2, 1, 6, '!='),
            Token(Token.T_TEXT, 1, 10, 'b'),
            Token(Token.T_SPECIAL1, 1, 10, ')'),
            Token(Token.T_SPECIAL1, 1, 12, '{'),
            Token(Token.T_TEXT, 1, 20, 'return'),
            Token(Token.T_NUMBER, 1, 22, '7'),
            Token(Token.T_SPECIAL1, 1, 23, '}'),
        ]
        tokens = list (lexer(text))

        self.assertFalse(lexcmp(expected, tokens, False))

    def test_001_advanced_expr_2(self):

        text = " ( x, y ) => { x + y } (2,3)"
        expected = [
            Token(Token.T_SPECIAL1, 1, 1, '('),
            Token(Token.T_TEXT, 1, 4, 'x'),
            Token(Token.T_SPECIAL1, 1, 4, ','),
            Token(Token.T_TEXT, 1, 7, 'y'),
            Token(Token.T_SPECIAL1, 1, 8, ')'),
            Token(Token.T_SPECIAL2, 1, 12, '=>'),
            Token(Token.T_SPECIAL1, 1, 13, '{'),
            Token(Token.T_TEXT, 1, 16, 'x'),
            Token(Token.T_SPECIAL2, 1, 18, '+'),
            Token(Token.T_TEXT, 1, 20, 'y'),
            Token(Token.T_SPECIAL1, 1, 21, '}'),
            Token(Token.T_SPECIAL1, 1, 23, '('),
            Token(Token.T_NUMBER, 1, 25, '2'),
            Token(Token.T_SPECIAL1, 1, 25, ','),
            Token(Token.T_NUMBER, 1, 27, '3'),
            Token(Token.T_SPECIAL1, 1, 27, ')'),
        ]
        tokens = list (lexer(text))

        self.assertFalse(lexcmp(expected, tokens, False))

    def test_001_newline_1(self):

        text = "x = 1 + \\\n2"

        tokens = list (lexer(text))

        expected = [
            Token(Token.T_TEXT, 1, 1, 'x'),
            Token(Token.T_SPECIAL2, 1, 3, '='),
            Token(Token.T_NUMBER, 1, 5, '1'),
            Token(Token.T_SPECIAL2, 1, 7, '+'),
            Token(Token.T_NUMBER, 2, 1, '2'),
        ]

        self.assertFalse(lexcmp(expected, tokens, False))

    def test_001_newline_2(self):

        text = "x = 1 + \n2"

        tokens = list (lexer(text))

        expected = [
            Token(Token.T_TEXT, 1, 1, 'x'),
            Token(Token.T_SPECIAL2, 1, 3, '='),
            Token(Token.T_NUMBER, 1, 5, '1'),
            Token(Token.T_SPECIAL2, 1, 7, '+'),
            Token(Token.T_NEWLINE, 1, 7, ''),
            Token(Token.T_NUMBER, 2, 1, '2'),
        ]

        self.assertFalse(lexcmp(expected, tokens, False))

    def test_001_string_1(self):
        text = "'abc'"
        expected = [
            Token(Token.T_STRING, 1, 8, 'abc'),
        ]
        tokens = list(lexer(text))
        self.assertFalse(lexcmp(expected, tokens, False))

    def test_001_string_2(self):
        text = "g'abc'"
        expected = [
            Token(Token.T_GLOB_STRING, 1, 8, 'abc'),

        ]
        tokens = list(lexer(text))
        self.assertFalse(lexcmp(expected, tokens, False))

    def test_001_string_3(self):
        text = "'\\a\\b\\f\\n\\r\\t\\v\\[\\\\'"
        expected = [
            Token(Token.T_STRING, 1, 8, '\a\b\f\n\r\t\v[\\'),

        ]
        tokens = list(lexer(text))
        self.assertFalse(lexcmp(expected, tokens, False))

    def test_001_string_32(self):
        text = "'\\\''"
        expected = [
            Token(Token.T_STRING, 1, 8, '\''),

        ]
        tokens = list(lexer(text))
        self.assertFalse(lexcmp(expected, tokens, False))

    def test_001_string_33(self):
        text = '"\\\""'
        expected = [
            Token(Token.T_STRING, 1, 8, '"'),

        ]
        tokens = list(lexer(text))
        self.assertFalse(lexcmp(expected, tokens, False))

    def test_001_string_4(self):
        text = "'\\o123'"
        expected = [
            Token(Token.T_STRING, 1, 8, chr(0o123)),

        ]
        tokens = list(lexer(text))
        self.assertFalse(lexcmp(expected, tokens, False))

    def test_001_string_5(self):
        text = "'\\x61'"
        expected = [
            Token(Token.T_STRING, 1, 8, chr(0x61)),

        ]
        tokens = list(lexer(text))
        self.assertFalse(lexcmp(expected, tokens, False))

    def test_001_string_6(self):
        text = "'\\u0000'"
        expected = [
            Token(Token.T_STRING, 1, 8, '\u0000'),

        ]
        tokens = list(lexer(text))
        self.assertFalse(lexcmp(expected, tokens, False))

    def test_001_string_7(self):
        text = "'\\U00000000'"
        expected = [
            Token(Token.T_STRING, 1, 8, '\U00000000'),

        ]
        tokens = list(lexer(text))
        self.assertFalse(lexcmp(expected, tokens, False))

    def test_001_string_8(self):
        text = "'\\x4"
        with self.assertRaises(LexError):
            tokens = list(lexer(text))

    def test_001_string_9(self):
        text = "'\\xXX'"
        with self.assertRaises(LexError):
            tokens = list(lexer(text))

    def test_001_string_10(self):
        text = "g'*.txt'"
        expected = [
            Token(Token.T_GLOB_STRING, 1, 8, '*.txt'),

        ]
        tokens = list(lexer(text))
        self.assertFalse(lexcmp(expected, tokens, False))

    def test_001_string_10(self):
        text = "b'abc'"
        expected = [
            Token(Token.T_BYTE_STRING, 1, 8, 'abc'),

        ]
        tokens = list(lexer(text))
        self.assertFalse(lexcmp(expected, tokens, False))

    def test_001_string_11(self):
        text = "f'${abc}'"
        expected = [
            Token(Token.T_FORMAT_STRING, 1, 8, '${abc}'),

        ]
        tokens = list(lexer(text))
        self.assertFalse(lexcmp(expected, tokens, False))

    def test_001_string_12(self):
        text = "r'abc'"
        expected = [
            Token(Token.T_REGEX_STRING, 1, 8, 'abc'),

        ]
        tokens = list(lexer(text))
        self.assertFalse(lexcmp(expected, tokens, False))

    def test_001_string_13(self):
        text = "''"
        expected = [
            Token(Token.T_STRING, 1, 8, ''),

        ]
        tokens = list(lexer(text))
        self.assertFalse(lexcmp(expected, tokens, False))

    def test_001_string_14(self):
        text = "'"
        with self.assertRaises(LexError):
            list(lexer(text))

    def test_001_string_15(self):
        text = "'\n"
        with self.assertRaises(LexError):
            list(lexer(text))

    def test_001_script_1(self):

        text = "exec cat ${foo} "
        expected = [
            Token(Token.T_TEXT, 1, 4, 'exec'),
            Token(Token.T_TEXT, 1, 8, 'cat'),
            Token(Token.T_SUBSTITUTION, 1, 12, 'foo'),
        ]
        tokens = list(lexer(text))
        self.assertFalse(lexcmp(expected, tokens, False))

    def test_002_comment_1(self):
        pass

    def test_003_exec_1(self):
        text = "exec true"
        expected = [
            Token(Token.T_TEXT, 1, 4, 'exec'),
            Token(Token.T_TEXT, 1, 8, 'true'),

        ]
        tokens = list(lexer(text))
        self.assertFalse(lexcmp(expected, tokens, False))

    def test_003_exec_2(self):
        text = "exec true # comment"
        expected = [
            Token(Token.T_TEXT, 1, 4, 'exec'),
            Token(Token.T_TEXT, 1, 8, 'true'),

        ]
        tokens = list(lexer(text))
        self.assertFalse(lexcmp(expected, tokens, False))

    def test_003_exec_3(self):
        text = "exec true # comment\n"
        expected = [
            Token(Token.T_TEXT, 1, 4, 'exec'),
            Token(Token.T_TEXT, 1, 8, 'true'),
            Token(Token.T_NEWLINE, 1, 8, ''),
        ]
        tokens = list(lexer(text))
        self.assertFalse(lexcmp(expected, tokens, False))

    def test_003_exec_4(self):
        text = "exec true 1>2"
        expected = [
            Token(Token.T_TEXT, 1, 4, 'exec'),
            Token(Token.T_TEXT, 1, 8, 'true'),
            Token(Token.T_TEXT, 1, 8, '1'),
            Token(Token.T_SPECIAL2, 1, 8, '>'),
            Token(Token.T_TEXT, 1, 8, '2'),
        ]
        tokens = list(lexer(text))
        self.assertFalse(lexcmp(expected, tokens, False))

    def test_003_exec_5(self):
        text = "exec true 1>>2"
        expected = [
            Token(Token.T_TEXT, 1, 4, 'exec'),
            Token(Token.T_TEXT, 1, 8, 'true'),
            Token(Token.T_TEXT, 1, 8, '1'),
            Token(Token.T_SPECIAL2, 1, 8, '>>'),
            Token(Token.T_TEXT, 1, 8, '2'),
        ]
        tokens = list(lexer(text))
        self.assertFalse(lexcmp(expected, tokens, False))

    def test_003_exec_6(self):
        text = "exec true 1<2"
        expected = [
            Token(Token.T_TEXT, 1, 4, 'exec'),
            Token(Token.T_TEXT, 1, 8, 'true'),
            Token(Token.T_TEXT, 1, 8, '1'),
            Token(Token.T_SPECIAL2, 1, 8, '<'),
            Token(Token.T_TEXT, 1, 8, '2'),
        ]
        tokens = list(lexer(text))
        self.assertFalse(lexcmp(expected, tokens, False))

    def test_003_exec_7(self):
        text = "exec true 1<<2"
        expected = [
            Token(Token.T_TEXT, 1, 4, 'exec'),
            Token(Token.T_TEXT, 1, 8, 'true'),
            Token(Token.T_TEXT, 1, 8, '1'),
            Token(Token.T_SPECIAL2, 1, 8, '<<'),
            Token(Token.T_TEXT, 1, 8, '2'),
        ]
        tokens = list(lexer(text))
        self.assertFalse(lexcmp(expected, tokens, False))

    def test_003_exec_8(self):
        text = "(exec true; exec false)"
        expected = [
            Token(Token.T_SPECIAL1, 1, 4, '('),
            Token(Token.T_TEXT, 1, 4, 'exec'),
            Token(Token.T_TEXT, 1, 8, 'true'),
            Token(Token.T_SPECIAL1, 1, 4, ';'),
            Token(Token.T_TEXT, 1, 4, 'exec'),
            Token(Token.T_TEXT, 1, 8, 'false'),
            Token(Token.T_SPECIAL1, 1, 4, ')'),
        ]
        tokens = list(lexer(text))
        self.assertFalse(lexcmp(expected, tokens, False))

    def test_003_exec_9(self):
        text = "exec true\n1"
        expected = [
            Token(Token.T_TEXT, 1, 4, 'exec'),
            Token(Token.T_TEXT, 1, 8, 'true'),
            Token(Token.T_NEWLINE, 1, 4, ''),
            Token(Token.T_NUMBER, 1, 4, '1'),
        ]
        tokens = list(lexer(text))
        self.assertFalse(lexcmp(expected, tokens, False))

    def test_003_exec_10(self):
        text = "exec find /etc -name g'*.cfg'"
        expected = [
            Token(Token.T_TEXT, 1, 4, 'exec'),
            Token(Token.T_TEXT, 1, 8, 'find'),
            Token(Token.T_TEXT, 1, 4, '/etc'),
            Token(Token.T_TEXT, 1, 4, '-name'),
            Token(Token.T_GLOB_STRING, 1, 4, '*.cfg'),
        ]
        tokens = list(lexer(text))
        self.assertFalse(lexcmp(expected, tokens, False))

    def test_003_exec_11(self):
        text = "exec true |> exec true"
        expected = [
            Token(Token.T_TEXT, 1, 4, 'exec'),
            Token(Token.T_TEXT, 1, 8, 'true'),
            Token(Token.T_SPECIAL2, 1, 4, '|>'),
            Token(Token.T_TEXT, 1, 4, 'exec'),
            Token(Token.T_TEXT, 1, 8, 'true'),
        ]
        tokens = list(lexer(text))
        self.assertFalse(lexcmp(expected, tokens, False))

    def test_003_exec_12(self):
        text = "exec ${args}"
        expected = [
            Token(Token.T_TEXT, 1, 4, 'exec'),
            Token(Token.T_SUBSTITUTION, 1, 8, 'args'),
        ]
        tokens = list(lexer(text))
        self.assertFalse(lexcmp(expected, tokens, False))

    def test_003_exec_13(self):
        text = "exec \\\n ${args}"
        expected = [
            Token(Token.T_TEXT, 1, 4, 'exec'),
            Token(Token.T_SUBSTITUTION, 1, 8, 'args'),
        ]
        tokens = list(lexer(text))
        self.assertFalse(lexcmp(expected, tokens, False))

    def test_003_exec_14(self):
        text = "exec ${args#"
        with self.assertRaises(LexError):
            list(lexer(text))

    def test_003_exec_15(self):
        text = "exec ${args"
        with self.assertRaises(LexError):
            list(lexer(text))

    def test_003_exec_16(self):
        text = "exec $"
        with self.assertRaises(LexError):
            list(lexer(text))

    def test_003_exec_17(self):
        text = "exec \\b"
        with self.assertRaises(LexError):
            list(lexer(text))

    def test_003_exec_18(self):
        text = "exec <"
        expected = [
            Token(Token.T_TEXT, 1, 4, 'exec'),
            Token(Token.T_SPECIAL2, 1, 8, '<'),
        ]
        tokens = list(lexer(text))
        self.assertFalse(lexcmp(expected, tokens, False))

    def test_003_exec_19(self):
        text = "exec >"
        expected = [
            Token(Token.T_TEXT, 1, 4, 'exec'),
            Token(Token.T_SPECIAL2, 1, 8, '>'),
        ]
        tokens = list(lexer(text))
        self.assertFalse(lexcmp(expected, tokens, False))

    def test_003_exec_20(self):
        text = "exec |"
        expected = [
            Token(Token.T_TEXT, 1, 4, 'exec'),
            Token(Token.T_SPECIAL2, 1, 8, '|'),
        ]
        tokens = list(lexer(text))
        self.assertFalse(lexcmp(expected, tokens, False))

    def test_003_exec_21(self):
        text = "exec ||"
        with self.assertRaises(LexError):
            list(lexer(text))

    def test_003_import_1(self):
        text = "import abc.def"
        expected = [
            Token(Token.T_TEXT, 1, 4, 'import'),
            Token(Token.T_TEXT, 1, 8, 'abc.def'),
        ]
        tokens = list(lexer(text))
        self.assertFalse(lexcmp(expected, tokens, False))

    def test_003_import_2(self):
        text = "from abc import def"
        expected = [
            Token(Token.T_TEXT, 1, 4, 'from'),
            Token(Token.T_TEXT, 1, 4, 'abc'),
            Token(Token.T_TEXT, 1, 4, 'import'),
            Token(Token.T_TEXT, 1, 8, 'def'),
        ]
        tokens = list(lexer(text))
        self.assertFalse(lexcmp(expected, tokens, False))

    def test_003_import_2(self):
        text = "from abc import def as xyz"
        expected = [
            Token(Token.T_TEXT, 1, 4, 'from'),
            Token(Token.T_TEXT, 1, 4, 'abc'),
            Token(Token.T_TEXT, 1, 4, 'import'),
            Token(Token.T_TEXT, 1, 8, 'def'),
            Token(Token.T_TEXT, 1, 8, 'as'),
            Token(Token.T_TEXT, 1, 8, 'xyz'),
        ]
        tokens = list(lexer(text))
        self.assertFalse(lexcmp(expected, tokens, False))

    def test_003_import_3(self):
        text = "import abc # comment"
        expected = [
            Token(Token.T_TEXT, 1, 4, 'import'),
            Token(Token.T_TEXT, 1, 8, 'abc'),
        ]
        tokens = list(lexer(text))
        self.assertFalse(lexcmp(expected, tokens, False))

    def test_003_import_4(self):
        text = "import abc \n"
        expected = [
            Token(Token.T_TEXT, 1, 4, 'import'),
            Token(Token.T_TEXT, 1, 8, 'abc'),
            Token(Token.T_NEWLINE, 1, 8, ''),
        ]
        tokens = list(lexer(text))
        self.assertFalse(lexcmp(expected, tokens, False))

    def test_003_import_5(self):
        text = "import \\\n abc \n"
        expected = [
            Token(Token.T_TEXT, 1, 4, 'import'),
            Token(Token.T_TEXT, 1, 8, 'abc'),
            Token(Token.T_NEWLINE, 1, 8, ''),
        ]
        tokens = list(lexer(text))
        self.assertFalse(lexcmp(expected, tokens, False))

    def test_003_import_6(self):
        text = "x=(import abc)"
        expected = [
            Token(Token.T_TEXT, 1, 4, 'x'),
            Token(Token.T_SPECIAL2, 1, 4, '='),
            Token(Token.T_SPECIAL1, 1, 4, '('),
            Token(Token.T_TEXT, 1, 4, 'import'),
            Token(Token.T_TEXT, 1, 8, 'abc'),
            Token(Token.T_SPECIAL1, 1, 4, ')'),
        ]
        tokens = list(lexer(text))
        self.assertFalse(lexcmp(expected, tokens, False))

    def test_003_import_7(self):
        text = "import \\b"
        with self.assertRaises(LexError):
            list(lexer(text))

    def test_003_ternary_1(self):
        text = "a?b:c"
        expected = [
            Token(Token.T_TEXT, 1, 4, 'a'),
            Token(Token.T_SPECIAL1, 1, 4, '?'),
            Token(Token.T_TEXT, 1, 4, 'b'),
            Token(Token.T_SPECIAL1, 1, 8, ':'),
            Token(Token.T_TEXT, 1, 8, 'c'),
        ]
        tokens = list(lexer(text))
        self.assertFalse(lexcmp(expected, tokens, False))

    def test_003_ternary_2(self):
        text = "a?"
        expected = [
            Token(Token.T_TEXT, 1, 4, 'a'),
            Token(Token.T_SPECIAL1, 1, 4, '?'),
        ]
        tokens = list(lexer(text))
        self.assertFalse(lexcmp(expected, tokens, False))

    def test_003_optional(self):
        text = "a?.b"
        expected = [
            Token(Token.T_TEXT, 1, 4, 'a'),
            Token(Token.T_SPECIAL2, 1, 4, '?.'),
            Token(Token.T_TEXT, 1, 4, 'b'),
        ]
        tokens = list(lexer(text))
        self.assertFalse(lexcmp(expected, tokens, False))

def main():
    unittest.main()

if __name__ == '__main__':
    main()
