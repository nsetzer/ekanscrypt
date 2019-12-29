import os
import sys

def format_generic(exc_type, exc_obj, exc_tb):

    tb = exc_tb
    while tb is not None:

        fpath = tb.tb_frame.f_code.co_filename
        lineno = tb.tb_lineno

        current_line = ""
        ext = os.path.splitext(fpath)[1]
        if os.path.exists(fpath) and ext in [".py", ".es"]:
            with open(fpath, "r") as rf:
                for index, line in enumerate(rf):
                    if index+1 == lineno:
                        current_line = line.replace("\n", "")

        fpath = os.path.relpath(fpath)

        sys.stderr.write("\n%s: %d\n" % (fpath, lineno))
        sys.stderr.write("%s\n" % (current_line))

        tb = tb.tb_next

    sys.stderr.write("\nUnhandled Exception\n%s: %s\n" % (
        exc_type.__name__, exc_obj))

class TokenError(Exception):

    def __init__(self, token, message=None):
        super(TokenError, self).__init__(message)
        self.token = token

    def format(self, path, text):
        lines = text.split("\n")
        l1 = max(0, self.token.line - 2)
        l2 = min(len(lines), self.token.line + 2)
        lines = lines[l1:l2]
        sys.stderr.write("Syntax Error in File %s at line %d column %d\n" % (
            path, self.token.line, self.token.index))
        sys.stderr.write(" %s\n" % self)
        for n, line in zip(range(l1,l2), lines):

            sys.stderr.write(" %4d: %s\n" % (n+1, line))
            if n+1 == self.token.line:
                indicator = " " * (self.token.index)
                sys.stderr.write("       %s^\n" % (indicator))

class LexError(TokenError):
    pass

class ParseError(TokenError):
    pass

class CompilerError(TokenError):
    pass