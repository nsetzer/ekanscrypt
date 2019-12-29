

class Token(object):
    count = 0

    # tokens as produced by the lexer
    T_UNKNOWN = "T_UNKNOWN"
    T_TEXT = "T_TEXT"
    T_NUMBER = "T_NUMBER"
    T_STRING = "T_STRING"
    T_FORMAT_STRING = "T_FORMAT_STRING"
    T_BYTE_STRING = "T_BYTE_STRING"
    T_REGEX_STRING = "T_REGEX_STRING"
    T_GLOB_STRING = "T_GLOB_STRING"
    T_DOT = "T_DOT"
    T_SPECIAL1 = "T_SPECIAL1"
    T_SPECIAL2 = "T_SPECIAL2"
    T_SEMICOLON = "T_SEMICOLON"
    T_ESCAPE = "T_ESCAPE"
    T_NEWLINE = "T_NEWLINE"
    T_SUBSTITUTION1 = "T_SUBSTITUTION1"
    T_SUBSTITUTION = "T_SUBSTITUTION"

    I_MOD = "I_MOD"
    I_ARGS = "I_ARGS"
    I_TUPLE_SEPARATOR = "I_TUPLE_SEPARATOR"

    # tokens as produced by the parser
    S_ATTR = "S_ATTR"
    S_ATTR_LABEL = "S_ATTR_LABEL" # rhs label of exp 'a.b'
    S_OPTIONAL_ATTR = "S_OPTIONAL_ATTR" # rhs label of exp 'a.b'
    S_KEYWORD = "S_KEYWORD"
    S_STRING = "S_STRING"
    S_FORMAT_STRING = "S_FORMAT_STRING"
    S_REGEX_STRING = "S_REGEX_STRING"
    S_BYTE_STRING = "S_BYTE_STRING"
    S_GLOB_STRING = "S_GLOB_STRING"
    S_NUMBER = "S_NUMBER"
    S_LABEL = "S_LABEL"
    S_OPERATOR1 = "S_OPERATOR1"
    S_OPERATOR2 = "S_OPERATOR2"
    S_NEWLINE = "S_NEWLINE"
    S_CALL_FUNCTION = "S_CALL_FUNCTION"
    S_SUBSCR = "S_SUBSCR"
    S_BUILD = "S_BUILD" # LIST SET MAP
    S_BRANCH = "S_BRANCH" # IF => (EXPR TRUE FALSE)
    S_DEFINE_VAR = "S_DEFINE_VAR"
    S_DEFINE_FINAL = "S_DEFINE_FINAL"
    S_DEFINE_STATIC = "S_DEFINE_STATIC"
    S_CLASS = "S_CLASS"
    S_CLASS_PARAMLIST = "S_CLASS_PARAMLIST"
    S_CLASS_INIT = "S_CLASS_INIT"
    S_CLASS_INIT2 = "S_CLASS_INIT2"
    # a sequence of either label or `label=expr`
    S_LAMBDA = "S_LAMBDA"
    S_LAMBDA_NAMELIST = "S_LAMBDA_NAMELIST" # TODO RENAME PARAMLIST
    S_LAMBDA_CLOSURE = "S_LAMBDA_CLOSURE"
    S_CLOSURE = "S_CLOSURE"
    S_RETURN = "S_RETURN"
    S_EXPR = "S_EXPR" # an expression chain
    S_PASS = "S_PASS"
    S_WHILE = "S_WHILE"
    S_DO_WHILE = "S_DO_WHILE"
    S_SWITCH = "S_SWITCH"
    S_SWITCH_CASE = "S_SWITCH_CASE"
    S_SWITCH_DEFAULT = "S_SWITCH_DEFAULT"
    S_BLOCK = "S_BLOCK"
    S_REFERENCE = "S_REFERENCE" # a LABEL, which references another scope
    S_BREAK = "S_BREAK"
    S_CONTINUE = "S_CONTINUE"
    S_TRUE = "S_TRUE"
    S_FALSE = "S_FALSE"
    S_NAN = "S_NAN"
    S_INFINITY = "S_INFINITY"
    S_NULL = "S_NULL"
    S_FOREACH = "S_FOREACH"
    S_WITH = "S_WITH"
    S_POSTFIX = "S_POSTFIX"
    S_PREFIX = "S_PREFIX"
    S_SLICE = "S_SLICE"
    S_NONE = "S_NONE"
    S_TUPLE = "S_TUPLE"
    S_IMPORT = "S_IMPORT"
    S_TRYCATCH = "S_TRYCATCH"
    S_RAISE = "S_RAISE"
    S_EXEC_PROCESS = "S_EXEC_PROCESS"
    S_LIST_COMPREHENSION = "S_LIST_COMPREHENSION"
    S_DICT_COMPREHENSION = "S_DICT_COMPREHENSION"
    S_SET_COMPREHENSION = "S_SET_COMPREHENSION"
    S_YIELD = "S_YIELD"
    S_YIELD_FROM = "S_YIELD_FROM"
    S_MCMP = "S_MCMP"

    def __init__(self, type, line=0, index=0, value="", children=None):
        Token.count += 1
        super(Token, self).__init__()
        self.type = type
        self.line = line
        self.index = index
        self.value = value
        self.children = children if children is not None else []

    def __str__(self):

        return self.toString(False, 0)

    def __repr__(self):
        return "Token(Token.%s, %r, %r, %r)" % (
            self.type, self.line, self.index, self.value)

    def toString(self, pretty=True, depth=0, pad="  "):
        s = "%s<%s,%s,%r>" % (self.type, self.line, self.index, self.value)

        if pretty==2:

            if len(self.children) == 0:
                s = "\n%sTOKEN(%r, %r)" % ("    " * depth, self.type, self.value)
                return s
            else:
                s = "\n%sTOKEN(%r, %r, " % ("    " * depth, self.type, self.value)
                c = [child.toString(pretty, depth+1) for child in self.children]
                return s + ', '.join(c) + ")"

        elif pretty:
            parts = ["%s%s\n" % (pad * depth, s)]

            for child in self.children:
                parts.append(child.toString(pretty, depth+1))

            return ''.join(parts)

        elif self.children:
            t = ','.join(child.toString(False) for child in self.children)
            return "%s{%s}" % (s, t)
        else:
            return s

    def flatten(self, depth=0):
        items = [(depth,self)]
        for child in self.children:
            items.extend(child.flatten(depth + 1))
        return items

def main():  # pragma: no cover
    tok1 = Token("Parent", 1, 0, "abc")
    tok2 = Token("Child", 1, 0, "def")

    print(tok1)
    print(tok2)

    tok1.children = [tok2]

    print(tok1)
    print(tok1.toString(True))

if __name__ == '__main__':  # pragma: no cover
    main()