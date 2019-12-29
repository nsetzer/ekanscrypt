
"""
Implementation of an L(N) (look-ahead-by-N) Lexer

A base class and implementation of an Ekanscrypt Lexer.
Given a sequence of characters produce a sequence of tokens.

The output is relativley simple compared to the complexity of the parser.
The output is either one of:
    Text: an alpha numeric sequence starting with a non-digit character
    Number: Text that starts with a decimal digit
    Special: A special character. this is further divided into two groups
             Special1: characters that never combine with other characters
             Special2: characters that may combine with other characters
             Special2 are almost always binary operators

Import and Exec keywords cause the lexer to change modes and parse
a slightly differnt grammar than the standard parser.

"""
from .token import Token
from .exception import LexError
import logging

# special characters that never combine with other characters
chset_special1 = "{}[](),~;:"
# special characters that may combine with other special characters
chset_special2 = "+-*/&|^=<>%!@"
# digits in a decimal number, digits that always begin a number
chset_number_base  = "0123456789"
# characters that may exist in a number, either:
#   int, oct, hex, float, imaginary
# this includes all possible and many impossible combinations
# the compiler will determine if the token is valid
chset_number  = "0123456789nxob_.jtgmkABCDEFabcdef"

# the number of characters to read for a string encoding
char_len = {'o': 3, 'x': 2, 'u': 4, 'U': 8}
# the base used to convert a string to a single character
char_base = {'o': 8, 'x': 16, 'u': 16, 'U': 16}


# symbols for operators that have length 1
operators1 = set("+-~*@&^|!?:.,;")

# operators composed of 2 or more special characters
# except for = and ==, which prefix match ===
# used to break longers strings of special characters into valid operators
operators2 = {
    "+=", "-=", "*=", "**=", "/=", "//=", "%=", "@=", "|=", "&=", "^=", ">>=", "<<=",
    "<", "<=", ">", ">=", "!=", "===", "!==",
    "&&",
    "||",
    "=>",
    "|>",
    "<<", ">>",
    "++", "--",
    "->", "=>", "?."
}

# the set of all valid operators for this language
# if an operator is not in this list, then it is a syntax error
operators3 = operators1 | operators2 | set(["=", "=="])

def char_reader(f):
    # convert a file like object into a character generator
    buf = f.read(1024)
    while buf:
        for c in buf:
            yield c
        buf = f.read(1024)

class LexerBase(object):
    """
    base class for a generic look-ahead-by-N lexer
    """
    def __init__(self,):
        super(LexerBase, self).__init__()

    def _init(self, seq, default_type):

        # the line of the most recently consumed character
        self._line = 1
        # the column of the line of the most recently consumed character
        self._index = -1

        self._default_type = default_type
        # the type of the current token
        self._type = default_type
        # the value of the current token
        self._tok = ""
        # the line where the current token began
        self._initial_line = -1
        # the column of the current line where the token began
        self._initial_index = -1
        # list of characters read from the input stream, but not consumed
        self._peek_char = []
        # the last token successfully pushed
        self._prev_token = None

        # define an iterator (generator) which
        # yields individual (utf-8) characters from
        # either an open file or an existing iterable
        if hasattr(seq, 'read'):
            self.g = char_reader(seq)
        else:
            self.g = seq.__iter__()

        self.tokens = []

    def _getch_impl(self):
        """ read one character from the input stream"""
        c = next(self.g)

        if c == '\n':
            self._line += 1
            self._index = -1
        else:
            self._index += 1
        return c

    def _getch(self):
        """ return the next character """
        if self._peek_char:
            c = self._peek_char.pop(0)
        else:
            c = self._getch_impl()
        return c

    def _getstr(self, n):
        """ return the next N characters """

        s = ''
        try:
            for i in range(n):
                s += self._getch()
        except StopIteration:
            return None
        return s

    def _peekch(self):
        """ return the next character, do not advance the iterator """

        if not self._peek_char:
            self._peek_char.append(self._getch_impl())
        return self._peek_char[0]

    def _peekstr(self, n):
        """ return the next N characters, do not advance the iterator """
        while len(self._peek_char) < n:
            self._peek_char.append(self._getch_impl())
        return ''.join(self._peek_char[:n])

    def _putch(self, c):
        """ append a character to the current token """

        if self._initial_line < 0:
            self._initial_line = self._line
            self._initial_index = self._index
        self._tok += c

    def _push_endl(self):
        """ push an end of line token """
        self.tokens.append(Token(
            Token.T_NEWLINE,
            self._line,
            0,
            "")
        )
        self._type = self._default_type
        self._initial_line = -1
        self._initial_index = -1
        self._tok = ""

    def _push(self):
        """ push a new token """

        self._prev_token = Token(
            self._type,
            self._initial_line,
            self._initial_index,
            self._tok
        )
        self.tokens.append(self._prev_token)
        self._type = self._default_type
        self._initial_line = -1
        self._initial_index = -1
        self._tok = ""

    def _maybe_push(self):
        """ push a new token if there is a token to push """
        if self._tok:
            self._push()

    def _error(self, message):

        token = Token(self._type, self._initial_line, self._initial_index, "")
        return LexError(token, message)

class Lexer(LexerBase):
    """
    read tokens from a file or string
    """
    def __init__(self):
        super(Lexer, self).__init__()

    def lex(self, seq):

        self._init(seq, Token.T_TEXT)

        error = 0
        try:
            self._lex()
        except StopIteration:
            error = 1

        if error:
            tok = Token("", self._line, self._index, "")
            raise LexError(tok, "Unexpected End of Sequence")

        return self.tokens

    def _lex(self):

        while True:

            try:
                c = self._getch()
            except StopIteration:
                break

            if c == '\n':
                self._maybe_push()
                self._push_endl()

            elif c == '#':
                self._lex_comment()

            elif c == '\\':
                c = self._peekch()
                if c != '\n':
                    raise self._error("expected newline")
                self._getch()  # consume the newline

            elif c == '\'' or c == '\"':
                self._lex_string(c)

            elif c in chset_special1:
                self._maybe_push()
                self._putch(c)
                self._type = Token.T_SPECIAL1
                self._push()

            elif c in chset_special2:
                self._maybe_push()
                self._putch(c)
                self._lex_special2()

            elif c == '?':

                self._maybe_push()
                self._putch(c)
                try:
                    nc = self._peekch()
                except StopIteration:
                    nc = None

                if nc and nc == '.':
                    self._putch(self._getch())
                    self._type = Token.T_SPECIAL2
                    self._push()
                else:
                    self._type = Token.T_SPECIAL1
                    self._push()

            elif c == '.':
                self._maybe_push()
                self._putch(c)
                try:
                    nc = self._peekch()
                except StopIteration:
                    nc = None

                if nc and nc in chset_number_base:
                    self._lex_number()
                else:
                    self._type = Token.T_SPECIAL1
                    self._push()

            elif not self._tok and c in chset_number_base:
                self._maybe_push()
                self._putch(c)
                self._lex_number()

            elif c == ' ' or c == '\t':
                is_exec = self._tok == 'exec'
                # from has two different meanings depending on if 'yield' comes before it
                # or if 'import' comes after it
                is_yield = self._prev_token and self._prev_token.type == Token.T_TEXT and self._prev_token.value == 'yield'
                is_import = not is_yield and (self._tok == 'import' or self._tok == 'from')

                self._maybe_push()
                if is_exec:
                    self._lex_exec()
                if is_import:
                    self._lex_import()
            else:
                self._putch(c)

        self._maybe_push()

    def _lex_special2(self):

        self._type = Token.T_SPECIAL2

        while True:
            try:
                c = self._peekch()
            except StopIteration:
                break

            if c in chset_special2:
                self._putch(self._getch())
                self._maybe_push_op()
            else:
                self._maybe_push()
                self._type = Token.T_TEXT
                break

    def _lex_string(self, string_terminal):
        """ read a string from the stream, terminated by the given character"""

        if self._tok == "f":
            self._type = Token.T_FORMAT_STRING
            self._tok = ""
        elif self._tok == "b":
            self._tok = ""
            self._type = Token.T_BYTE_STRING
        elif self._tok == "r":
            self._tok = ""
            self._type = Token.T_REGEX_STRING
        elif self._tok == "g":
            self._tok = ""
            self._type = Token.T_GLOB_STRING
        else:
            self._maybe_push()
            self._type = Token.T_STRING

        escape = False

        while True:
            try:
                c = self._getch()
            except StopIteration:
                c = None

            if c is None:
                raise self._error("unterminated string")

            elif c == "\n":
                raise self._error("unterminated string")

            elif escape:
                if c == "\\":
                    self._putch(c)
                elif c == string_terminal:
                    self._putch(c)
                elif c == "a":
                    self._putch('\a')
                elif c == "b":
                    self._putch('\b')
                elif c == "f":
                    self._putch('\f')
                elif c == "n":
                    self._putch('\n')
                elif c == "r":
                    self._putch('\r')
                elif c == "t":
                    self._putch('\t')
                elif c == "v":
                    self._putch('\v')
                elif c in char_len:
                    # decode \o000 \x00 \u0000 \U00000000
                    s = self._getstr(char_len[c])
                    if s is None:
                        raise self._error("unexpected end of sequence")

                    error = 0

                    try:
                        self._putch(chr(int(s, char_base[c])))
                    except ValueError:
                        error = 1

                    if error:
                        raise self._error("invalid encoding '\\%s%s'" % (c, s))
                # TODO: python also supports a \N{...} sequence
                else:
                    self._putch(c)
                escape = False
            elif c == '\\':
                escape = True
            elif c == string_terminal:
                # allow pushing empty strings
                if not self._tok:
                    self._initial_line = self._line
                    self._initial_index = self._index
                self._push()
                break
            else:
                self._putch(c)

    def _lex_number(self):
        """ read a number from the stream """

        self._type = Token.T_NUMBER

        while True:
            try:
                c = self._peekch()
            except StopIteration:
                break

            if c in chset_number:
                self._putch(self._getch())
            else:
                self._push()
                break

    def _lex_comment(self):
        """ read a comment and produce no token """

        while True:
            try:
                c = self._getch()
            except StopIteration:
                break

            if c == '\n':
                self._push_endl()
                break

    def _lex_exec(self):
        """ use a different strategy to generate tokens from a process exec line

        """

        while True:
            try:
                c = self._getch()
            except StopIteration:
                break

            if c == '#':
                self._lex_comment()
                break

            elif c == '\\':
                c = self._peekch()
                if c != '\n':
                    raise self._error("expected newline")
                self._getch()  # consume the newline

            elif c == '\n':
                self._maybe_push()
                self._push_endl()
                break

            elif c == '$':
                self._lex_substitution()

            elif c in ',;)]}':
                self._maybe_push()
                self._putch(c)
                self._type = Token.T_SPECIAL1
                self._push()
                break

            elif c == '<':
                self._maybe_push()
                self._putch(c)
                self._type = Token.T_SPECIAL2
                try:
                    nc = self._peekch()
                except StopIteration:
                    break

                if nc == '<':
                    self._putch(self._getch())
                self._push()

            elif c == '>':
                self._maybe_push()
                self._putch(c)
                self._type = Token.T_SPECIAL2
                try:
                    nc = self._peekch()
                except StopIteration:
                    break

                if nc == '>':
                    self._putch(self._getch())
                self._push()

            elif c == '|':
                self._maybe_push()
                self._putch(c)
                self._type = Token.T_SPECIAL2
                try:
                    nc = self._peekch()
                except StopIteration:
                    break

                if nc == '>':
                    self._putch(self._getch())
                    break
                else:
                    raise self._error("unexpected operator")

            elif c == '\'' or c == '\"':
                self._lex_string(c)

            #elif not self._tok and c in chset_number_base:
            #    self._maybe_push()
            #    self._putch(c)
            #    self._lex_integer()

            elif c == ' ' or c == '\t':
                self._maybe_push()
            else:
                self._putch(c)

    def _lex_import(self):
        """ use a different strategy to generate tokens from an import statement

        """

        while True:
            try:
                c = self._getch()
            except StopIteration:
                break

            if c == '#':
                self._lex_comment()
                break

            elif c == '\\':
                c = self._peekch()
                if c != '\n':
                    raise self._error("expected newline")
                self._getch()  # consume the newline

            elif c == '\n':
                self._maybe_push()
                self._push_endl()
                break

            elif c in ';)]}':
                self._maybe_push()
                self._putch(c)
                self._type = Token.T_SPECIAL1
                self._push()
                break

            elif c == ' ' or c == '\t' or c == ',':
                self._maybe_push()

            else:
                self._putch(c)

    def _lex_substitution(self):
        """ read a variable substitution, i.e. ${varname} """

        self._type = Token.T_SUBSTITUTION
        self._initial_line = self._line
        self._initial_index = self._index

        try:
            c = self._getch()
        except StopIteration:
            c = None

        if c != '{':
            raise self._error("invalid substitution")

        while True:
            try:
                c = self._getch()
            except StopIteration:
                c = None

            if not c or c in '#;\n':
                raise self._error("unexpected end of substitution")

            if c == '}':
                self._push()
                break
            else:
                self._putch(c)

    def _maybe_push_op(self):
        if self._tok and self._tok in operators2:
            self._push()
            self._type = Token.T_SPECIAL2

def lexer(seq):
    return Lexer().lex(seq)

def main():  # pragma: no cover
    import sys

    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) != 2:
        print("usage: %s path" % sys.argv[0])
        sys.exit(1)

    path = sys.argv[1]
    if path == '-':
        text = sys.stdin.read()
    else:
        with open(path, "r") as src:
            text = src.read()

    try:
        for tok in lexer(text):
            print(tok.toString(0))

    except TokenError as e:
        e.format(path, text)

if __name__ == '__main__': # pragma: no cover
    main()