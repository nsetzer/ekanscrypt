#! cd .. && python3 -m pythonscrypt.compiler

"""

TODO: unify S_TUPLE, S_BUILD:TUPLE

TODO: label tagging
    e.g. var x; => Token(Token.S_LABEL, 1, 0, 'x:1')
    then all x in the current scope get renamed to 'x:1'
    a tagged label is also local (fast) scope
    if `var x` is given a second time, the new label tag is 'x:2'
    a tag of 0 indicates no tag, meaning x could come from the global scope

TODO: tag rhs of dot operator as S_ATTR instead of S_LABEL
closures should always see label as varnames

Abstract-Syntax-Tree (AST) a tree made of Tokens
Abstract-Syntax-Forest (ASF) is a list of AST nodes

Basic Token Types
    Label     : alpha numeric sequence
    String    : utf-8 sequence
    Bytes     : byte sequence
    Operator  : sequence of special characters
    Keyword   : a Label reserved by the parser
    Semicolon : explicit end of expression
    Newline   : conditional end of expression

Expr
    - any token

Block
    - Expr
    - a Bracketed list of Expr

NameList
    - Label
    - Parenthetical grouping of Labels

NameAssign
    - Label, Operator(=), Expr

ParamList
    - Label
    - Parenthetical grouping of Labels or NameAssign

Closure
    - Parenthetical grouping of Labels

Lambda
    - ParamList, Closure, Expr

Branch
    - Keyword(if), True Expr, False Expr
    - Test Expr, True Expr, False Expr

While
    - keyword(while), Expr, Block
    - Test Expr, Block

DoWhile
    - Keyword(do), Block, keyword(while), Expr
    - Test Expr, Block

ForEach
    for label : expr
    for namelist : expr

Return
    - Keyowrd(return), Expr
    - Expr


- a block of comma separated slices is a map/object
- a block with a single slice is a map/object
- a block of comma separated nodes-that-are-not-slices is a set

|> cat file |> grep foo
Proc("grep foo", Proc("cat file", null))

"""
# https://docs.python.org/3/reference/expressions.html#operator-precedence

from .token import Token
from .exception import ParseError, TokenError
import logging
log = logging.getLogger("ekanscrypt.parser")
from .util import prefix_count

keywords = [
        #"new",
        #"int8", "int16", "int32", "int64",
        #"float32", "float64","boolean","void",
        "true", "false", "null", "nan", "infinity",
        "import", "from", "as",
        "if", "else",
        "switch", "case", "default", "return",
        "while", "do", "for", "break", "continue", "with", "in",
        "try", "catch", "finally", "raise",
        "class", "static", "const", "final", "var",
        "yield",
        "exec",
    ]

def isCallable(tok):
    return tok.type == Token.S_LABEL or \
        tok.type == Token.S_ATTR or \
        tok.type == Token.S_OPTIONAL_ATTR or \
        tok.type == Token.S_SUBSCR or \
        tok.type == Token.S_CALL_FUNCTION

def isOperator(tok, value):
    return tok.type in [Token.S_OPERATOR1, Token.S_OPERATOR2] and tok.value == value

def isExecTerminal(tok):
    return (tok.type == Token.S_OPERATOR1 and (
            tok.value == ";" or tok.value == "," or tok.value == ")"
            or tok.value == "}" or tok.value == "]")) or \
        (tok.type == Token.S_OPERATOR2 and tok.value == "|>") or \
        (tok.type == Token.S_NEWLINE)

def isImportTerminal(tok):
    return (tok.type == Token.S_OPERATOR1 and (
            tok.value == ";" or tok.value == ")"
            or tok.value == "}" or tok.value == "]")) or \
        (tok.type == Token.S_NEWLINE)

def isComparable(token, operators):
    return token.type == Token.S_MCMP or (token.type == Token.S_OPERATOR2 and token.value in operators)

def isParenthetical(parent):
    if not parent:
        return False

    return ((parent.type == Token.S_OPERATOR1 and parent.value == "()") or \
            (parent.type == Token.S_CALL_FUNCTION) or \
            (parent.type == Token.S_BUILD)
           )

def peek_token(tokens, token, index, direction):
    """
    return the token that would be returned by consume
    """

    j = index + direction
    while 0 <= j < len(tokens):
        tok1 = tokens[j]
        if tok1.type == Token.S_OPERATOR1 and tok1.value == ";":
            break
        elif tok1.type == Token.S_OPERATOR1 and tok1.value == ",":
            break
        elif tok1.type == Token.S_NEWLINE:
            j += direction
        else:
            return tokens[j]
    return None

def consume(tokens, token, index, direction, maybe=False):

    index_tok1 = index + direction
    while 0 <= index_tok1 < len(tokens):
        tok1 = tokens[index_tok1]

        if tok1.type == Token.S_OPERATOR1 and tok1.value == ";":
            break
        elif tok1.type == Token.S_OPERATOR1 and tok1.value == ",":
            break
        elif tok1.type == Token.S_NEWLINE:
            tokens.pop(index_tok1)
        else:
            return tokens.pop(index_tok1)

    if maybe:
        return None

    side = "rhs" if direction > 0 else "lhs"
    raise ParseError(token, "missing token on %s" % side)

def collect(tokens, i, open, close):

    initial = tokens[i]
    final = initial
    stack = []
    while i < len(tokens):
        token = tokens[i]
        if token.type in [Token.S_OPERATOR1, Token.S_OPERATOR2] and token.value == open:
            if len(stack) == 0:
                token.value = open + close
                i += 1
            else:
                stack[0].children.append(tokens.pop(i))
            stack.append(token)

        elif token.type in [Token.S_OPERATOR1, Token.S_OPERATOR2] and token.value == close:
            stack.pop()
            if len(stack) == 0:
                tokens.pop(i)

                tok1 = None
                if i-1 >= 0:
                    tok1 = tokens[i-1]

                tok2 = None
                if i-2 >= 0:
                    tok2 = tokens[i-2]

                if tok1 and tok1.value == "()":
                    if tok2 and isCallable(tok2):
                        tok1.type = Token.S_CALL_FUNCTION
                        tok1.value = ""
                        toki = Token(Token.I_ARGS, 0, 0, "")
                        toki.children = tok1.children
                        tok1.children = [tokens.pop(i-2), toki]
                        final = toki

                    #tok1.children.insert(0, Token(Token.S_OPERATOR1, 0, 0, ";"))
                    #tok1.children.insert(0, tokens.pop(i-2))
                elif tok1 and tok1.value == "[]":
                    if tok2 and (isCallable(tok2) or tok2.type == Token.S_BUILD):
                        tok1.type = Token.S_SUBSCR
                        tok1.value = ""
                        # TODO: this insert is a hack
                        toki = Token(Token.I_ARGS, 0, 0, "")
                        toki.children = tok1.children
                        tok1.children = [tokens.pop(i-2), toki]
                        final = toki
                        #tok1.children.insert(0, Token(Token.S_OPERATOR1, 0, 0, ";"))
                        #tok1.children.insert(0, tokens.pop(i-2))
                    else:
                        tok1.type = Token.S_BUILD
                        tok1.value = "LIST"
                elif tok1 and tok1.value == "{}":
                    tok1.type = Token.S_BLOCK
                break;
            else:
                stack[0].children.append(tokens.pop(i))
        elif stack:
            stack[0].children.append(tokens.pop(i))
        else:
            i += 1

    if len(stack) > 0:

        raise ParseError(initial, "Unterminated %s" % open)

    return final

def collect_var(tokens, i):

    token = tokens[i]
    tok1 = consume(tokens, token, i, 1)
    token.children.append(tok1)
    token.type = Token.S_DEFINE_VAR

def collect_final(tokens, i):

    token = tokens[i]
    tok1 = consume(tokens, token, i, 1)
    token.children.append(tok1)
    token.type = Token.S_DEFINE_FINAL

def collect_static(tokens, i):

    token = tokens[i]
    tok1 = consume(tokens, token, i, 1)
    token.children.append(tok1)
    token.type = Token.S_DEFINE_STATIC

def collect_branch(tokens, i):

    token = tokens[i]
    tok1 = tokens.pop(i+1)
    tok2 = tokens.pop(i+1)
    token.children = [tok1, tok2]
    token.type = Token.S_BRANCH

    j = i + 1
    if j < len(tokens) and tokens[j].type == Token.S_KEYWORD and tokens[j].value == "else":
        tok3 = tokens.pop(j) # pop else
        tok4 = tokens[j]

        if tok4.type == Token.S_KEYWORD and tok4.value == "if":
            collect_branch(tokens, j)

        token.children.append(tokens.pop(j))
    else:
        token.children.append(Token(Token.S_NONE,0,0,""))

def collect_trycatch(tokens, i):

    token = tokens[i]
    token.children.append(consume(tokens, tokens[i], i, 1))

    k = i + 1
    while k < len(tokens) and tokens[k].type == Token.S_KEYWORD and tokens[k].value == 'catch':
        tok1 = consume(tokens, tokens[i], i, 1)
        tok1.children.append(consume(tokens, tokens[i], i, 1))
        tok1.children.append(consume(tokens, tokens[i], i, 1))
        token.children.append(tok1)

    k = i + 1
    if k < len(tokens) and tokens[k].type == Token.S_KEYWORD and tokens[k].value == 'finally':
        tok1 = consume(tokens, tokens[i], i, 1)
        tok1.children.append(consume(tokens, tokens[i], i, 1))
        token.children.append(tok1)

    token.type = Token.S_TRYCATCH

    if len(token.children) < 2:
        raise ParseError(token, "missing catch or finally block")

def collect_raise(tokens, i):
    token = tokens[i]
    tok1 = consume(tokens, token, i, 1, True)
    if tok1:
        token.children = [tok1]
    token.type = Token.S_RAISE

def collect_switch(tokens, i):

    # collect expression
    token = tokens[i]
    token.children.append(consume(tokens, tokens[i], i, 1))
    body = consume(tokens, tokens[i], i, 1)


    if body.type != Token.S_BLOCK:
        raise ParseError(body, "expected block")
    token.children.extend(body.children)
    token.type = Token.S_SWITCH

def collect_case(tokens, i):

    token = tokens[i]
    token.children.append(consume(tokens, tokens[i], i, 1))
    tok1 = peek_token(tokens, tokens[i], i, 1)
    if tok1 and tok1.type == Token.S_KEYWORD and tok1.value in ('case', 'default'):
        pass
    else:
        token.children.append(consume(tokens, tokens[i], i, 1))
    token.type = Token.S_SWITCH_CASE

def collect_default(tokens, i):

    token = tokens[i]
    tok1 = peek_token(tokens, tokens[i], i, 1)
    if tok1 and tok1.type == Token.S_KEYWORD and tok1.value in ('case', 'default'):
        pass
    else:
        token.children.append(consume(tokens, tokens[i], i, 1))
    token.type = Token.S_SWITCH_DEFAULT

def collect_dowhile(tokens, i):

    token = tokens[i]

    # collect body
    token.children.append(consume(tokens, tokens[i], i, 1))
    # collect while
    keyword = consume(tokens, tokens[i], i, 1)
    if keyword.type != Token.S_KEYWORD or keyword.value != "while":
        raise ParseError(keyword, "expected keyword while")
    # collect test
    token.children.append(consume(tokens, tokens[i], i, 1))

    token.type = Token.S_DO_WHILE

def collect_while(tokens, i):

    token = tokens[i]
    token.children.append(consume(tokens, tokens[i], i, 1))
    token.children.append(consume(tokens, tokens[i], i, 1))
    token.type = Token.S_WHILE

def collect_comprehension(tokens, i, form):

    tok_body = consume(tokens, tokens[i], i, -1)

    _typ = Token.S_LIST_COMPREHENSION
    if form == 3:
        _typ = Token.S_DICT_COMPREHENSION
    if form == 4:
        _typ = Token.S_SET_COMPREHENSION

    tok_comp = Token(_typ, 1, 0, "")

    current = tok_comp
    while len(tokens):

        tok = tokens[0]

        if tok.type != Token.S_KEYWORD:
            raise ParseError(tok, "unexpected symbol in comprehension")

        if tok.value == "for":
            rhs = consume(tokens, tok, 0, 1)
            # TODO: test that rhs is not a slice
            tmp = tokens.pop(0)
            if not isOperator(rhs, "in"):
                raise ParseError(rhs, "expected 'in'")
            lbl, seq = rhs.children
            tok.children.append(lbl)
            tok.children.append(seq)
            current.children.append(tok)
            current = tok

        elif tok.value == "if":
            rhs = consume(tokens, tok, 0, 1)
            tokens.pop(0)
            tok.children.append(rhs)
            current.children.append(tok)
            current = tok

        else:
            raise ParseError(tok, "unexpected keyword in comprehension")

    tok_comp.children.append(tok_body)
    tokens.insert(0, tok_comp)
    return tok_comp

def collect_foreach_impl(tokens, i):

    token = tokens[i]

    tok_slice = consume(tokens, token, i, 1)
    if tok_slice.type == Token.S_OPERATOR1 and tok_slice.value == "()" and len(tok_slice.children) == 1:
        tok_slice = tok_slice.children[0]
    if not isOperator(tok_slice, "in"):
        raise ParseError(tok, "expected 'in'")
    if len(tok_slice.children) != 2:
        raise ParseError(tok_slice, "invalid expression")
    tok_slice.type = "fixme"
    tok_slice.value = ""

    token.type = Token.S_FOREACH
    token.children.extend(tok_slice.children)
    token.children.append(consume(tokens, token, i, 1))

def collect_foreach(tokens, i, parent):

    token = tokens[i]

    # guess if the form of this for keyword is a comprehension or a foreach loop
    tok0 = peek_token(tokens, token, i, -1)
    valid = parent and i == 1 and len(tokens) > 2 and tok0

    # can't have a comprehension with a semicolon
    if valid:
        for tok in tokens:
            if tok.type == Token.S_OPERATOR1 and token.value == ';':
                valid = False
                break;

    form = 0
    if valid:
        if parent.type == Token.S_OPERATOR1 and parent.value == '()':
            form = 1  # generator
        elif parent.type == Token.S_CALL_FUNCTION:
            form = 1  # generator
        elif parent.type == Token.S_BUILD and parent.value == 'LIST':
            form = 2  # list
        elif parent.type == Token.S_BLOCK:
            if tokens[0].type == Token.S_SLICE:
                form = 3  # dictionary
            else:
                form = 4  # set

    if form:
        tok = collect_comprehension(tokens, i, form)
        if form == 2:
            # S_LIST_COMPREHENSION always has aparent BUIld_LIST
            # which must be replaced
            parent.type = tok.type
            parent.value = tok.value
            parent.line = tok.line
            parent.index = tok.index
            parent.children = tok.children
    else:
        collect_foreach_impl(tokens, i)

def collect_with(tokens, i):

    token = tokens[i]

    # expr can be an expr, operator=, of tuple of expr-or-slice
    tok_expr = consume(tokens, token, i, 1)
    if tok_expr.type == Token.S_OPERATOR1 and tok_expr.value == "()":
        if len(tok_expr.children) == 1:
            tok_expr = tok_expr.children[0]
        else:
            raise ParseError(tok_expr, "expected label or operator=")

    token.children.append(tok_expr)
    # body
    token.children.append(consume(tokens, token, i, 1))
    token.type = Token.S_WITH

def collect_return(tokens, i):
    token = tokens[i]
    tok1 = consume(tokens, token, i, 1, True)
    if tok1:
        token.children = [tok1]
    token.type = Token.S_RETURN

def collect_break_continue(tokens, i):

    rhs = consume(tokens, tokens[i], i, 1, True)
    if rhs is not None:
        if rhs.type != Token.S_NUMBER:
            raise ParseError(rhs, "Unexpected symbol after %s" % tokens[i].value)
        tokens[i].children.append(rhs)
    if tokens[i].value == "continue":
        tokens[i].type = Token.S_CONTINUE
    else:
        tokens[i].type = Token.S_BREAK

def collect_yield(tokens, i):

    token = tokens[i]
    if token.type != Token.S_KEYWORD:
        raise ValueError(token.type)

    tok1 = consume(tokens, tokens[i], i, 1)

    if tok1.type == Token.S_KEYWORD and tok1.value == "from":
        tok2 = consume(tokens, tokens[i], i, 1)

        token.children.append(tok2)
        token.type = Token.S_YIELD_FROM
    else:
        token.children.append(tok1)
        token.type = Token.S_YIELD

def collect_class(tokens, i):
    """
    expect:
        class label paramlist expr
        class functioncall expr
    output:
        S_CLASS(label){
            S_CLASS_PARAMLIST(){...paramlist}
            S_LAMBDA(){
                S_LAMBDA_NAMELIST(){}
                S_LAMBDA_CLOSURE(){}
                S_BLOCK(){
                    S_CLASS_INIT(label)
                    ...expr
                }
            }
        }
    note:
        the grouping stage will convert the token sequence
            label paramlist
        into a function call, which will need to be unpacked.
    """

    token = tokens[i]
    if token.type != Token.S_KEYWORD:
        raise ValueError(token.type)

    tokens.pop(i)
    tok_lst = tokens[i]
    tok_lbl = tok_lst.children.pop(0)
    tok_exp = consume(tokens, tokens[i], i, 1)

    tok_blk = Token(Token.S_BLOCK,
        tok_exp.line, tok_exp.index, "")
    tok_int = Token(Token.S_CLASS_INIT,
        tok_exp.line, tok_exp.index, tok_lbl.value)
    tok_int2 = Token(Token.S_CLASS_INIT2,
        tok_exp.line, tok_exp.index, tok_lbl.value)
    tok_closure2 = Token(Token.S_CLOSURE, tok_exp.line, tok_exp.index, "")
    tok_closure2.children = [Token(Token.S_REFERENCE, tok_exp.line, tok_exp.index, "__class__")]
    tok_blk.children = [tok_closure2, tok_int, tok_exp, tok_int2]
    tok_lst.type = Token.S_CLASS_PARAMLIST
    tok_lbl.type = Token.S_CLASS
    tok_lambda = Token(Token.S_LAMBDA, tok_exp.line, tok_exp.index, 'cls.' + tok_lbl.value)
    tok_closure = Token(Token.S_LAMBDA_CLOSURE, tok_exp.line, tok_exp.index, "")
    tok_lambda.children = [
        Token(Token.S_LAMBDA_NAMELIST, tok_exp.line, tok_exp.index, ""),
        tok_closure,
        tok_blk
    ]
    tok_lbl.children = [tok_lst, tok_lambda]
    tokens[i] = tok_lbl

def visit_transform(parent, tokens, index, operators, precedence):

    token = tokens[index]

    if token.type == Token.T_TEXT:
        if token.value == "true" or token.value == 'True':
            token.type = Token.S_TRUE
        elif token.value == "false" or token.value == 'False':
            token.type = Token.S_FALSE
        elif token.value == "nan":
            token.type = Token.S_NAN
        elif token.value == "infinity":
            token.type = Token.S_INFINITY
        elif token.value == "null" or token.value == 'None':
            token.type = Token.S_NULL
        elif token.value == "as":
            token.type = Token.S_OPERATOR2
        elif token.value == "is":
            # is followed by not is a single operator
            if index + 1 < len(tokens) and \
                tokens[index+1].type == Token.T_TEXT and \
                tokens[index+1].value == "not":
                token.value += " not"
                tokens.pop(index + 1)
            token.type = Token.S_OPERATOR2
        elif token.value == "in":
            token.type = Token.S_OPERATOR2
        elif token.value == "not":
            if index + 1 < len(tokens) and \
                tokens[index+1].type == Token.T_TEXT and \
                tokens[index+1].value == "in":
                token.value = "not in"
                token.type = Token.S_OPERATOR2
                tokens.pop(index + 1)
            else:
                token.type = Token.S_OPERATOR1
                token.value = "!"
        elif token.value in keywords:
            token.type = Token.S_KEYWORD
        else:
            token.type = Token.S_LABEL
    if token.type == Token.T_NUMBER:
        token.type = Token.S_NUMBER
    if token.type == Token.T_SPECIAL1:
        token.type = Token.S_OPERATOR1
    if token.type == Token.T_SPECIAL2:
        token.type = Token.S_OPERATOR2
    if token.type == Token.T_STRING:
        token.type = Token.S_STRING
    if token.type == Token.T_BYTE_STRING:
        token.type = Token.S_BYTE_STRING
    if token.type == Token.T_REGEX_STRING:
        token.type = Token.S_REGEX_STRING
    if token.type == Token.T_GLOB_STRING:
        token.type = Token.S_GLOB_STRING
    if token.type == Token.T_FORMAT_STRING:
        token.type = Token.S_FORMAT_STRING
    if token.type == Token.T_NEWLINE:
        token.type = Token.S_NEWLINE

    return 1

def visit_string(parent, tokens, index, operators, precedence):
    token = tokens[index]

    if token.type != Token.S_STRING:
        return 1

    while index < len(tokens) - 1:
        tok1 = tokens[index+1]
        if tok1.type == Token.S_STRING:
            token.value += tokens.pop(index+1).value
        else:
            break

    return 1

def _transform_exec(token):

    token.type = Token.S_EXEC_PROCESS

    i = 0

    while i < len(token.children):
        tok = token.children[i]
        if tok.type == Token.S_LABEL:
            tok.type = Token.S_STRING
        elif tok.type == Token.T_SUBSTITUTION:
            tok.type = Token.S_LABEL
        elif tok.type == Token.S_OPERATOR2:
            if tok.value != ">" and tok.value != ">>":
                raise ParseError(tok, "invalid operator in exec statement")
        elif tok.type not in (Token.S_STRING, Token.S_FORMAT_STRING, Token.S_GLOB_STRING, Token.S_BYTE_STRING, Token.S_NUMBER):
            tok.type = Token.S_STRING
        i += 1

    i = 0
    while i < len(token.children):
        tok = token.children[i]

        # TODO: flip lhs/rhs if < or << is given
        if tok.type == Token.S_OPERATOR2 and tok.value in [">", ">>"]:
            rhs = consume(token.children, token, i, 1)
            lhs = consume(token.children, token, i, -1)
            mode = {">":"1", ">>":"2"}[tok.value]

            tokm = Token(Token.S_NUMBER, tok.line, tok.index, mode)
            tok1 = Token(Token.S_ATTR, tok.line, tok.index, "")
            tok1.children = [
                Token(Token.S_LABEL, tok.line, tok.index, "Proc"),
                Token(Token.S_ATTR_LABEL, tok.line, tok.index, "Redirect")
            ]
            tok2 = Token(Token.S_CALL_FUNCTION, tok.line, tok.index, "")
            tok2.children = [tok1, tokm, lhs, rhs]
            token.children[i-1] = tok2

        else:
            i += 1

    tok_proc = Token(Token.S_LABEL, token.line, token.index, "Proc")
    token.children.insert(0, tok_proc)

def visit_exec(parent, tokens, index, operators, precedence):

    token = tokens[index]
    if token.type == Token.S_KEYWORD and token.value in operators:
        k = index + 1
        while k < len(tokens):
            if not isExecTerminal(tokens[k]):
                rhs = consume(tokens, token, index, 1)
                token.children.append(rhs)
            else:
                break;
        if len(token.children) == 0:
            raise ParseError(token, "exec with no arguments")
        _transform_exec(token)
    return 1

def visit_import(parent, tokens, index, operators, precedence):

    token = tokens[index]

    if token.type == Token.S_KEYWORD and token.value in operators:

        # the from list for import
        tok1 = Token(Token.S_TUPLE, token.line, token.index, "")
        # the level for import
        tok2 = Token(Token.S_NUMBER, token.line, token.index, "")

        if token.value == 'from':

            if index - 1 >= 0 and tokens[index-1].type == Token.S_KEYWORD and tokens[index-1].value == 'yield':
                return 1

            name = consume(tokens, token, index, 1)
            imp = consume(tokens, token, index, 1)

            k = index + 1
            while k < len(tokens):
                if tokens[k].value == "as":
                    raise ParseError(tokens[k], "unexpected keyword")
                elif not isImportTerminal(tokens[k]):
                    rhs = consume(tokens, token, index, 1)
                    if index+2 < len(tokens) and tokens[index+1].value == 'as':
                        tmp = consume(tokens, token, index, 1)
                        tmp.children = [rhs, consume(tokens, token, index, 1)]
                        tok1.children.append(tmp)
                    else:
                        tok1.children.append(rhs)

                else:
                    break;
        elif token.value == "import":
            name = consume(tokens, token, index, 1)

        c = prefix_count(name.value, '.')
        tok2.value = str(c)
        name.value = name.value[c:]
        name.type = Token.S_STRING

        token.type = Token.S_IMPORT
        token.value = name.value.split('.')[0]
        token.children = [tok2, name, tok1]

    return 1

def visit_proc_pipe(parent, tokens, index, operators, precedence):
    token = tokens[index]

    if token.type != token.S_OPERATOR2 or token.value not in operators:
        return 1

    rhs = consume(tokens, token, index, 1)
    lhs = consume(tokens, token, index, -1)
    # flip the order
    token.children.append(rhs)
    # insert a call function as needed EXEC_PROCESS
    # is a special form of call function
    if lhs.type == Token.S_EXEC_PROCESS and lhs.value == "|>":
        token.children.append(lhs)
    else:
        token.children.append(Token(Token.S_CALL_FUNCTION, 0, 0, "", [lhs]))
    token.type = Token.S_EXEC_PROCESS

    return 0

def visit_semicolon(parent, tokens, index, operators, precedence):

    token = tokens[index]
    if token.type in [Token.S_NEWLINE]:
        tokens.pop(index)
        return 0

    elif token.type in [Token.S_OPERATOR1, Token.S_OPERATOR2] and token.value in operators:
        tokens.pop(index)
        return 0

    return 1

def visit_break(parent, tokens, index, operators, precedence):
    token = tokens[index]
    if token.value == "continue" or token.value == "break":
        collect_break_continue(tokens, index)
    return 1

def visit_keyword(parent, tokens, index, operators, precedence):
    token = tokens[index]

    if token.type != Token.S_KEYWORD or token.value not in operators:
        return 1

    if token.value == "var":
        collect_var(tokens, index)

    if token.value == "final":
        collect_final(tokens, index)

    if token.value == "static":
        collect_static(tokens, index)

    elif token.value == "if":
        collect_branch(tokens, index)

    elif token.value == "else":
        raise ParseError(token, "else without matching if")

    elif token.value == "do":
        collect_dowhile(tokens, index)

    elif token.value == "while":
        collect_while(tokens, index)

    elif token.value == "switch":
        collect_switch(tokens, index)

    elif token.value == "default":
        collect_default(tokens, index)

    elif token.value == "case":
        collect_case(tokens, index)

    elif token.value == "return":
        collect_return(tokens, index)

    elif token.value == "for":
        collect_foreach(tokens, index, parent)

    elif token.value == "with":
        collect_with(tokens, index)

    elif token.value == "try":
        collect_trycatch(tokens, index)

    elif token.value == "catch":
        raise ParseError(token, "unexpected catch without matching try")

    elif token.value == "finally":
        raise ParseError(token, "unexpected finally without matching try")

    elif token.value == "raise":
        collect_raise(tokens, index)

    elif token.value == "yield":
        collect_yield(tokens, index)

    elif token.value == "from":
        raise ParseError(token, "unexpected from without matching yield")

    elif token.value == "class":
        collect_class(tokens, index)

    return 1

def visit_grouping(parent, tokens, index, operators, precedence):
    token = tokens[index]

    if token.value not in operators or token.type not in (Token.S_OPERATOR1, Token.S_OPERATOR2):
        return 1

    # TODO: blocks are probably best grouped right to left
    # while . ?. and -> are best grouped right to left
    pairs = {
        "(": ")",
        "[": "]",
        "{": "}",
    }

    if token.value in pairs:
        next_token = collect(tokens, index, token.value, pairs[token.value])
        next_tokens = next_token.children if next_token else token.children
        group(next_tokens, precedence, token)
        return 0  # TODO: explain this return value

    elif token.value == "->":
        # subscript operator
        if index + 1 < len(tokens):
            rhs = tokens[index+1]
            # expectation is string or number
            # TODO: figure out what should happen for these edge cases
            if rhs.type == Token.S_OPERATOR1 and rhs.value in pairs:
                raise ParseError(rhs, "illegal after ->")
        rhs = consume(tokens, token, index, 1)
        lhs = consume(tokens, token, index, -1)

        if rhs.type == Token.S_LABEL:
            rhs.type = Token.S_STRING
        elif rhs.type != Token.S_NUMBER:
            # TODO: maybe some of these we can handle
            raise ParseError(rhs, "nothing is wrong, just a weird edge case")

        # alternative implementation, which does not use __es_drill__:
        # token.children.append(lhs)
        # token.children.append(rhs)
        # token.type = Token.S_SUBSCR

        token.children.append(Token(Token.S_LABEL, token.line, token.index, '__es_drill__'))
        token.children.append(lhs)
        token.children.append(rhs)
        token.type = Token.S_CALL_FUNCTION

        return 0

    elif token.value == ".":
        # attribute operator
        rhs = consume(tokens, token, index, 1)
        lhs = consume(tokens, token, index, -1)
        token.children.append(lhs)
        token.children.append(rhs)
        token.type = Token.S_ATTR
        rhs.type = Token.S_ATTR_LABEL
        return 0

    elif token.value == '?.':
        # optional chaining operator
        # a?.b a?.[0] a?.() a->0 a?.->0
        if index + 1 < len(tokens):
            rhs = tokens[index+1]
            if (rhs.type == Token.S_OPERATOR1 and rhs.value in pairs) or (rhs.type == Token.S_OPERATOR2 and rhs.value == '->'):
                rhs = None
            else:
                rhs = consume(tokens, token, index, 1)
                rhs.type = Token.S_ATTR_LABEL
        lhs = consume(tokens, token, index, -1)
        token.children.append(lhs)
        if rhs:
            token.children.append(rhs)
        token.type = Token.S_OPTIONAL_ATTR

        return 0

    return 1

def visit_unary(parent, tokens, index, operators, precedence):
    token = tokens[index]

    if token.type != token.S_OPERATOR2 and token.type != token.S_OPERATOR1:
        return 1

    if token.value not in operators or len(token.children)>0:
        return 1

    # TODO: use peek_token?
    lhs = None
    if 0 <= index-1 < len(tokens):
        lhs = tokens[index-1]

    rhs = None
    if 0 <= index+1 < len(tokens):
        rhs = tokens[index+1]

    valid = False
    dir = 1
    type = Token.S_PREFIX

    # TODO: consider using the parent to decide if NEWLINE should be allowed to break
    #       use peek_token and consume instead

    # attempt prefix if possible
    if lhs is None or lhs.type in [Token.S_OPERATOR1, Token.S_OPERATOR2, Token.S_KEYWORD, Token.S_NEWLINE]:
        valid = True

    # conditionally consume unary operators when they
    # cannot be confused for a binary operator
    if valid:
        token.children.append(consume(tokens, token, index, dir))
        # rename to something other than an operator
        # so that later stages don't process the token
        token.type = type

    return 1

def visit_unary_fix(parent, tokens, index, operators, precedence):
    token = tokens[index]

    if token.type != token.S_OPERATOR2 or token.value not in operators or len(token.children)>0:
        return 1

    lhs = None
    if 0 <= index-1 < len(tokens):
        lhs = tokens[index-1]

    rhs = None
    if 0 <= index+1 < len(tokens):
        rhs = tokens[index+1]

    valid = False
    dir = 1
    type = Token.S_PREFIX

    # prefer POSTFIX when possible
    if lhs and rhs is None or rhs.type in [Token.S_OPERATOR1, Token.S_OPERATOR2, Token.S_KEYWORD, Token.S_NEWLINE]:
        dir = -1
        type = Token.S_POSTFIX
        valid = True

    # attempt prefix if possible
    elif lhs is None or lhs.type in [Token.S_OPERATOR1, Token.S_OPERATOR2, Token.S_KEYWORD, Token.S_NEWLINE]:
        valid = True


    rv = 1
    # conditionally consume unary operators when they
    # cannot be confused for a binary operator
    if valid:
        rv = 0 if dir > 0 else 1
        token.children.append(consume(tokens, token, index, dir))
        # rename to something other than an operator
        # so that later stages don't process the token
        token.type = type
    else:
        print(lhs, rhs)

    print(valid, rv)
    return rv

def visit_binary(parent, tokens, index, operators, precedence):
    token = tokens[index]

    if token.type != token.S_OPERATOR2 or token.value not in operators:
        return 1

    rhs = consume(tokens, token, index, 1)
    lhs = consume(tokens, token, index, -1)
    token.children.append(lhs)
    token.children.append(rhs)

    return 0

def visit_ternary(parent, tokens, index, operators, precedence):
    """
    convert a?b:c into a branch
    """

    token = tokens[index]

    if token.type != token.S_OPERATOR1 or token.value not in operators:
        return 1

    rhs = consume(tokens, token, index, 1)
    lhs = consume(tokens, token, index, -1)
    token.children.append(lhs)
    token.children.extend(rhs.children)
    token.type = Token.S_BRANCH

    return 0

def visit_binary_cmp(parent, tokens, index, operators, precedence):
    """
    comparison binary operators can be chained such that these are equivalent
        (a < b < c)
        ((a < b) && (b < c))


    a three way compare looks like this
    0: load a           | a,
       load b           | a, b,
       dup top          | a, b, b
       rot3             | b, a, b
       cmp_op           | b, r1
       jmp_false:1      | b, r1
       pop_top          | b,
       load c           | b, c
       cmp_op           | r2
       jmp_abs:2        | r2
    1: rot2             | r1, b
       pop_top          | r1
    2: nop              | r1 or r2

    a four way compare looks like this
    0: load a           | a,
       load b           | a, b,
       dup_top          | a, b, b
       rot3             | b, a, b
       cmp_op           | b, r1
       jmp_false:1      | b, r1
       pop_top          | b,
       load c           | b, c
       dup_top          | b, c, c
       rot3             | c, b, c
       cmp_op           | c, r2
       jmp_false:1      | c, r2
       pop_top          | c,
       load d           | c, d
       cmp_op           | r3
       jmp_abs:2        | r3
    1: rot2             | r1, b
       pop_top          | r1
    2: nop              | r1 or r2 or r3

    """
    token = tokens[index]

    if token.type != token.S_OPERATOR2 or token.value not in operators:
        return 1

    rhs = consume(tokens, token, index, 1)
    lhs = consume(tokens, token, index, -1)

    # NOTE: traversal is only ever left to right or right to left
    if lhs.type == Token.S_MCMP:
        token.children.extend(lhs.children)
        token.children.append(Token(Token.S_OPERATOR2, token.line, token.index, token.value))
        token.type = Token.S_MCMP
    elif lhs.type == Token.S_OPERATOR2 and lhs.value in operators:
        token.children.append(lhs.children[0])
        token.children.append(Token(Token.S_OPERATOR2, lhs.line, lhs.index, lhs.value))
        token.children.append(lhs.children[1])
        token.children.append(Token(Token.S_OPERATOR2, token.line, token.index, token.value))
        token.type = Token.S_MCMP
    else:
        token.children.append(lhs)

    if rhs.type == Token.S_MCMP:
        token.children.append(Token(Token.S_OPERATOR2, token.line, token.index, token.value))
        token.children.extend(rhs.children)
        token.type = Token.S_MCMP
    elif rhs.type == Token.S_OPERATOR2 and rhs.value in operators:
        token.children.append(Token(Token.S_OPERATOR2, token.line, token.index, token.value))
        token.children.append(rhs.children[0])
        token.children.append(Token(Token.S_OPERATOR2, rhs.line, rhs.index, rhs.value))
        token.children.append(rhs.children[1])
        token.type = Token.S_MCMP
    else:
        token.children.append(rhs)

    return 0

def visit_binary_slice(parent, tokens, index, operators, precedence):
    """
    add the tokens to the left and right as children of this token
    if no token exists in either direction, build a new None token
    if neither left nor right exist, then this token will have no children
    which will form an empty slice object

    the sequence
        expr : expr
    becomes
        operator:
            expr
            expr
    """
    token = tokens[index]

    if token.type != token.S_OPERATOR1 or token.value not in operators:
        return 1

    rhs = consume(tokens, token, index, 1, True)
    lhs = consume(tokens, token, index, -1, True)

    i = 0

    isEmpty = True
    if lhs:
        token.children.append(lhs)
        isEmpty = False
    else:
        token.children.append(Token(Token.S_NONE))
        i = 1

    if rhs:
        token.children.append(rhs)
        isEmpty = False
    else:
        token.children.append(Token(Token.S_NONE))

    token.type = Token.S_SLICE
    token.value = ""
    if isEmpty:
        token.children = []
    return i

def visit_lambda(parent, tokens, index, operators, precedence):
    """
    the sequence
        paramlist => expr
    becomes
        lambda
            namelist
            closure
            expr
    """
    token = tokens[index]

    if token.type != token.S_OPERATOR2 or token.value not in operators:
        return 1

    rhs = consume(tokens, token, index, 1)
    lhs = consume(tokens, token, index, -1)

    lhs_lbl = None
    if lhs.type == Token.S_CALL_FUNCTION:
        lhs_lbl = lhs.children.pop(0)
        lhs.type = Token.S_OPERATOR1
        lhs.value = "()"

    namelist = Token(Token.S_LAMBDA_NAMELIST, lhs.line, lhs.index, "")
    if lhs.type == Token.S_OPERATOR1 and lhs.value == "()":
        namelist.children = lhs.children
    else:
        # TODO: potentially, when collecting (), check that tok+1 is =>
        # there is probably a way to make '@ f () => {}' work
        if lhs.type != Token.S_LABEL:
            raise ParseError(lhs, "invalid function definition. expected label")
        namelist.children = [lhs]

    closure = Token(Token.S_LAMBDA_CLOSURE, token.line, token.index, "")

    token.type = Token.S_LAMBDA
    token.children = [namelist, closure, rhs]
    if lhs_lbl:
        token.value = lhs_lbl.value
    else:
        token.value = ''

    # a call to the lambda that was just built. why?
    index -= 1
    while index+1 < len(tokens):
        tok1 = tokens[index + 1]
        if tok1.type == Token.S_OPERATOR1 and tok1.value == "()":

            tok0 = tokens.pop(index)

            tok1.children.insert(0, tok0)
            tok1.type = Token.S_CALL_FUNCTION

        else:
            break;


    return 0

def visit_comma_b(parent, tokens, index, operators, precedence):
    token = tokens[index]

    if token.type != token.S_OPERATOR1 or token.value not in operators:
        return 1

    is_parenthetical = isParenthetical(parent)

    i = 0
    if not is_parenthetical:
        rhs = consume(tokens, token, index, 1, True)
        lhs = consume(tokens, token, index, -1)
        token.children.append(lhs)
        if rhs:
            token.children.append(rhs)
        # TODO: still need to hoist a tuple seq
        token.type = Token.I_TUPLE_SEPARATOR
    elif is_parenthetical:
        i = 1
    else:
        raise ParseError(token, "unexpected separator: %s %s %s %s" % (mode, is_parenthetical, parent.type, parent.value))

    return i

def visit_comma_a(parent,tokens, index, operators, precedence):
    token = tokens[index]

    if token.type != token.S_OPERATOR1 or token.value not in operators:
        return 1

    is_parenthetical = isParenthetical(parent)

    i = 0

    if is_parenthetical:
        rhs = consume(tokens, token, index, 1, True)
        lhs = consume(tokens, token, index, -1)
        token.children.append(lhs)
        if rhs:
            token.children.append(rhs)
        token.type = Token.I_TUPLE_SEPARATOR
        #parent.type = Token.S_TUPLE
    elif not is_parenthetical:
        i = 1
    else:
        raise ParseError(token, "unexpected separator: %s %s %s %s" % (mode, is_parenthetical, parent.type, parent.value))

    return i

def visit_decorator(parent, tokens, index, operators, precedence):

    """
    a previous visitor converted the unary form of the '@' symbol

    once function definitions have been visited, this can further transform
    the decorator syntax into a function call.

    the sequence
        @ expr1 expr2
    becomes
        call_function
            expr1
            expr2
    """
    token = tokens[index]
    if token.type != Token.S_PREFIX or token.value != "@":
        return 1

    arg = consume(tokens, token, index, 1)

    token.type = Token.S_CALL_FUNCTION
    token.children.append(arg)

    if arg.type == Token.S_LAMBDA and arg.value:
        tok1 = Token(Token.S_OPERATOR2, token.line, token.index, "=")
        tok2 = Token(Token.S_LABEL, token.line, token.index, arg.value)
        tok1.children = [tok2, token]
        tokens[index] = tok1


    return 1

def visit_dump(parent,tokens, index, operators, precedence):

    logging.info('\n%s', tokens[index].toString(True))
    return 1

# this table defines the operator precedence
# it is sorted from strongest to weakest binding
# that is: grouping is the most important for defining program structure
# while a semicolon, which merely separates expressions is less important
precedence1 = [
    # 1.  rename nodes
    # 2. convert is not into a single token
    (1, visit_transform,     []),
]

"+-~*@&^|!?:"

precedence2 = [
        # TODO: can visit_grouping be split into visit_grouping and visit_attr_ref
        # first pass discovers structure, second pass determines subscription,
        # slicing, function call, attribute reference (in three forms)
        ( 1, visit_grouping,     ["(", "[", "{", "?.", ".", "->"]),
        ( 1, visit_exec,         ["exec"]),
        ( 1, visit_import,       ["from", "import"]),
        ( 1, visit_string,       []),
        (-1, visit_unary,        ["+", "-", "~", "*", "**", "@"]),
        (-1, visit_unary_fix,    ["++", "--"]),
        ( 1, visit_binary,       ["**"]),
        ( 1, visit_binary,       ["*", "@", "/", "//", "%"]),
        ( 1, visit_binary,       ["+", "-"]),
        ( 1, visit_binary,       ["<<", ">>"]),
        ( 1, visit_binary,       ["&"]),
        ( 1, visit_binary,       ["^"]),
        ( 1, visit_binary,       ["|"]),
        ( 1, visit_proc_pipe,    ["|>"]),
        ( 1, visit_binary_cmp,   ["<", "<=", ">", ">=", "==", "!=", "===", "!==", "is", "is not"]),
        (-1, visit_unary,        ["!"]),
        ( 1, visit_binary,       ["&&"]),
        ( 1, visit_binary,       ["||"]),
        (-1, visit_lambda,       ["=>"]),
        ( 1, visit_binary_slice, [":"]),
        ( 1, visit_ternary,      ["?"]),
        ( 1, visit_comma_b,      [","]), # inside anything but a () block
        ( 1, visit_keyword,      ["var", "final", "static"]),
        (-1, visit_binary,       ["in", "not in", "as"]), # needs to be after comma_b, before assignment
        (-1, visit_binary,       ["=", "+=", "-=", "*=", "**=", "/=", "//=", "%=", "@=", "|=", "&=", "^=", ">>=", "<<=",]),
        ( 1, visit_comma_a,      [","]), # inside a () block
        ( 1, visit_break,        ["continue", "break"]),
        ( 1, visit_keyword,      ["if", "else", "for", "do", "while", "switch",
                                  "return", "with", "do", "case", "default",
                                  "try", "catch", "finally", "raise",
                                  "yield", "from",
                                  "class"]),
        ( 1, visit_decorator,    ["@"]),
        ( 1, visit_semicolon,    [";"]),
]

def group(tokens, precedence, parent=None):

    for direction, callback, operators in precedence:

        i = 0
        while i < len(tokens):

            if direction < 0:
                j = len(tokens) - i - 1
            else:
                j = i

            i += callback(parent, tokens, j, operators, precedence)

def walk(token, parent=None):

    i = 0;
    while i < len(token.children):
        tok = token.children[i]

        if tok.type == Token.I_ARGS or (tok.type == Token.S_BUILD and tok.value == "LIST"):
            match = True
            while match:
                match = False
                for j, child in enumerate(tok.children):
                    if child.type == Token.I_TUPLE_SEPARATOR:
                        tok.children = tok.children[:j] + child.children + tok.children[j+1:]
                        match = True
                        break

        walk(tok, token)

        if tok.type == Token.S_OPERATOR1 and tok.value == "()":
            if len(tok.children) == 0:
                tok.type = Token.S_BUILD
                tok.value = "TUPLE"

            elif len(tok.children) == 1:
                if tok.children[0].type ==Token.I_TUPLE_SEPARATOR:
                    token.children[i] = tok.children[0]
                    token.children[i].type = Token.S_TUPLE
                else:
                    token.children[i] = tok.children[0]
        elif tok.type == Token.S_BLOCK and tok.value == "{}":
            if len(tok.children) == 0:
                tok.type = Token.S_BUILD
                tok.value = "SET"
            elif len(tok.children) == 1:
                child = tok.children[0]

                if child.type == Token.S_SLICE:
                    tok.type = Token.S_BUILD
                    tok.value = "MAP"
                    tok.children = child.children

                elif child.type == Token.I_TUPLE_SEPARATOR:
                    token.children[i] = child
                    child.type = Token.S_BUILD
                    if child.children and child.children[0].type != Token.S_SLICE:
                        child.value = "SET"
                    else:
                        child.value = "MAP"
                        # flatten
                        new_children = []
                        for c in child.children:
                            if c.type == Token.S_PREFIX and c.value == "**":
                                new_children.append(c)
                            elif c.type == Token.S_SLICE:
                                new_children.extend(c.children)
                            else:
                                raise ParseError(c, "unexpected map element")

                        child.children = new_children
                else:
                    token.children[i] = child
        elif tok.type == Token.I_ARGS:
            token.children = token.children[:i] + tok.children + token.children[i+1:]
            continue
        elif tok.type == Token.S_SLICE:

            # Hoist Slice operators onto the same plane
            match = True
            while match:
                match = False
                for j, child in enumerate(tok.children):
                    if child.type == Token.S_SLICE:
                        tok.children = tok.children[:j] + child.children + tok.children[j+1:]
                        match = True
                        break
        elif tok.type == Token.I_TUPLE_SEPARATOR:

            match = True
            while match:
                match = False
                for j, child in enumerate(tok.children):
                    if child.type == Token.I_TUPLE_SEPARATOR:
                        tok.children = tok.children[:j] + child.children + tok.children[j+1:]
                        match = True
                        break

        i += 1

def walk2(token, parent=None):

    # Note: this one example demonstrates all shenanigans
    # with operator= operator, and operator()
    # "(1,8,(2,(3,4)),5); [1,2,3]; {1,2,3}; {0:1,2:3}; (a=1,b=2)=>{a,b=b,a}(a=0,b=1); f(1,2); f((1,2));"
    # f(1,2) vs f((1,2))
    i = 0;
    while i < len(token.children):
        tok = token.children[i]

        walk2(tok, token)

        if tok.type == Token.I_TUPLE_SEPARATOR:
            tok.type = Token.S_TUPLE
        elif tok.type == Token.S_LAMBDA_NAMELIST:
            if len(tok.children) == 1 and tok.children[0].type == Token.S_TUPLE:
                tok.children = tok.children[0].children
        # NSETZER 12 4 2019 HERE NOW
        #elif tok.type == Token.S_BUILD:
        #    if len(tok.children) == 1 and tok.children[0].type == Token.S_TUPLE:
        #        tok.children = tok.children[0].children
        i += 1

class Ref(object):

    def __init__(self, label):
        super(Ref, self).__init__()
        self.label = label
        self.final = False
        self._identity = 0

    def identity(self):
        if self._identity > 0:
            return "%s:%d" % (self.label, self._identity)
        return self.label

    def __str__(self):
        return "<*%s>" % (self.identity())

    def __repr__(self):
        return "<*%s>" % (self.identity())

    def clone(self):
        ref = Ref(self.label)
        ref._identity = self._identity + 1
        return ref

class UndefinedRef(Ref):
    def identity(self):
        return self.label

class Scope(object):
    """Scope keeps track of variables that are defined, read, written.
    It is used to discover where variables are defined in one scope
    and used in a child scope, as well as to implement name mangling
    if the same identifier label is used in the same scope in different ways

    # the following should print: "1 5 2"
    a=1; C=()=>{a+=1; var a = 5; return a}; print(a, C(), a)
    In order for that to happen, the function scope of C must have
    access to `a` in the parent scope, while also being able to redefine
    the symbol and assign to a local scope `a`

    TODO: like the var keyword, implement const which disallows 'store' to ref
        const or final?

    """
    def __init__(self, parent=None, noalias=False):
        """
        parent: the parent scope, which may define variables
        noalias: when true, don't name mangle or use vars from parent scopes
                 when defining classes that scope cannot mangle names
        """
        super(Scope, self).__init__()
        self.noalias = noalias
        self.parent = parent
        self.level = 0 if parent is None else parent.level + 1
        # cellvars are identifiers defined in this scope used
        # by a child scope
        self.cellvars = set()
        # freevars are identifiers defined in a parent scope
        # that are used in this or a child scope
        self.freevars = set()
        # vars are identifiers defined in this scope
        # vars are a dict mapping a label to a list-of-refs
        # currently for no good reason
        self.vars = {}

    def define(self, token):
        # i.e. `var x`, `class x(){}`, `import x`
        label = token.value

        # determine if this variable was defined in a parent scope
        old_ref = None
        scope = self
        while scope:
            if label in scope.vars:
                old_ref = scope.vars[label]
            scope = scope.parent

        if old_ref and not self.noalias:
            # define, but give a new identity
            self.vars[label] = old_ref.clone()
        else:
            self.vars[label] = Ref(label)

        ref = self.vars[label]
        #print(self.level, '  ', ' ','DEF', ref.identity() if ref else None)
        token.value = ref.identity()
        return ref

    def _load_store(self, token, load):
        # i.e. `x = 1`
        label = token.value
        ref = None

        # search for the scope the defines this label
        scopes = [self]
        while scopes[-1]:
            if not scopes[-1].noalias:
                if label in scopes[-1].vars:
                    break
            scopes.append(scopes[-1].parent)

        if scopes[-1] is None:

            # not found in an existing scope
            if load:
                # attempting to load an undefined reference
                ref = UndefinedRef(label)
                #print(self.level, '<-', self.level, 'LD_', ref.identity() if ref else None, )
            else:
                # define this reference in this scope
                ref = self.define(token)
        elif scopes[-1] is not self:
            # found in a parent scope
            scope = scopes[-1]

            if self.noalias and not load:
                if label not in self.vars:
                    ref = self.define(token)
                else:
                    ref = self.vars[label]
                    #print(self.level, '<-', self.level, 'LD_' if load else 'STR', ref.identity() if ref else None)
            else:
                ref = scope.vars[label]

                scope.cellvars.add(ref.identity())
                for scope2 in scopes[:-1]:
                    scope2.freevars.add(ref.identity())
                # this is a questionable addition to support
                # a = 1; class A() {a = a}
                # with the current version of _token2index Im not sure why it works
                token.type = Token.S_REFERENCE
                #print(self.level, '<-', scope.level, 'LD_' if load else 'STR', ref.identity() if ref else None)
        else:
            ref = self.vars[label]
            #print(self.level, '<-', self.level, 'LD_', ref.identity() if ref else None)

        if ref is None:
            raise ParseError(token, "error identity")
        token.value = ref.identity()
        return ref

    def load(self, token):
        return self._load_store(token, True)

    def store(self, token):
        return self._load_store(token, False)

def treewalk_varscopes(token, parent_scope=None, noalias=False):
    scope = Scope(parent_scope, noalias)

    if token.type == Token.I_MOD:
        cellvars = Token(Token.S_CLOSURE, token.line, token.index, "")

        for child in token.children:
            treewalk_varscopes_impl(child, scope)

        for label in scope.cellvars:
            cellvars.children.append(Token(Token.S_REFERENCE, token.line, token.index, label))

        if parent_scope is None and len(scope.freevars) > 0:
            raise ParseError("found freevars in module scope: %s" % scope.freevars)

        # TODO: for a module, this is a list of globals
        if len(cellvars.children) > 0:
            token.children.insert(0, cellvars)

    elif token.type == Token.S_LAMBDA:
        cellvars = Token(Token.S_CLOSURE, token.line, token.index, "")
        namelist, freevars, expr = token.children

        if token.value:
            # this function has a name. define that name so that
            # there is a unique identifier that can be used for recursion
            parent_scope.define(token)

        for child in namelist.children:
            if child.type == Token.S_OPERATOR2 and child.value == "=":
                lhs, rhs = child.children
                scope.define(lhs)
                treewalk_varscopes_impl(rhs, parent_scope)
            else:
                scope.define(child)

        # walk the lambda expression in the child scope
        treewalk_varscopes_impl(expr, scope)

        for label in scope.cellvars:
            cellvars.children.append(Token(Token.S_REFERENCE, token.line, token.index, label))
        for label in scope.freevars:
            freevars.children.append(Token(Token.S_REFERENCE, token.line, token.index, label))

        if len(cellvars.children) > 0:
            block = Token(Token.S_BLOCK, token.line, token.index, "{closure}")
            block.children = [cellvars, token.children[2]]
            token.children[2] = block

    #print(">", token.type, token.value)
    #print(" vars", ",".join([v[-1].identity() for v in scope.vars.values()]))
    #print(" cell", ",".join(scope.cellvars))
    #print(" free", ",".join(scope.freevars))

def treewalk_varscopes_impl(token, current_scope):
    # TODO: on define/load/store check identity of return value and update token
    if token.type == Token.S_LABEL:
        # load the contents from an identifier
        ref = current_scope.load(token)

    elif token.type == Token.S_CLASS:
        # define the class name
        current_scope.define(token)
        paramlist, expr = token.children
        for child in paramlist.children:
            if child.type == Token.S_OPERATOR2 and child.value == "=":
                _, rhs = child.children
                # lhs is not a variable in this scope, only process right side
                treewalk_varscopes_impl(rhs, current_scope)
            else:
                treewalk_varscopes_impl(child, current_scope)
        # expr is a lambda, and will produce a new scope...
        # TODO: this next lambda cannot mangle names
        treewalk_varscopes(expr, current_scope, noalias=True)
    elif token.type == Token.S_IMPORT:
        # define the import name
        current_scope.define(token)
        level, name, fromlist = token.children
        # define each element in the from list
        for child in fromlist.children:
            if child.type == Token.S_LABEL:
                current_scope.define(child)
            else:
                lhs, rhs = child.children
                current_scope.define(rhs)
    elif token.type == Token.S_DEFINE_VAR:
        # redefine a variable
        child,= token.children
        current_scope.define(child)

        # replace
        token.type = child.type
        token.value = child.value
        token.line = child.line
        token.index = child.index
        token.children = []
    elif token.type == Token.S_OPERATOR2 and token.value == "=":
        lhs, rhs = token.children
        treewalk_varscopes_impl(rhs, current_scope)
        if lhs.type == Token.S_LABEL:
            current_scope.store(lhs)
            # bit of a hack but rename the function if assigned to a label
            #if rhs.type == Token.S_LAMBDA:
            #    rhs.value = lhs.value
        else:
            treewalk_varscopes_impl(lhs, current_scope)
    elif token.type == Token.S_OPERATOR2:
        if len(token.children) == 2:
            lhs, rhs = token.children
            treewalk_varscopes_impl(rhs, current_scope)
            treewalk_varscopes_impl(lhs, current_scope)
        else:
            # i.e. MCMP{1, <, 2, <, 3}
            for child in token.children:
                treewalk_varscopes_impl(child, current_scope)
    elif token.type == Token.S_CALL_FUNCTION:

        # first child is the function itself
        treewalk_varscopes_impl(token.children[0], current_scope)

        for child in token.children[1:]:
            if child.type == Token.S_OPERATOR2 and child.value == "=":
                _, rhs = child.children
                # lhs is not a variable in this scope, only process right side
                treewalk_varscopes_impl(rhs, current_scope)
            else:
                treewalk_varscopes_impl(child, current_scope)
    elif token.type == Token.S_LAMBDA:
        treewalk_varscopes(token, current_scope)
    else:
        for child in token.children:
            treewalk_varscopes_impl(child, current_scope)

def parser(tokens):

    # first pass transform node types, prepare for second phase
    group(tokens, precedence1)
    # sdcond pass build AST from flat list of nodes
    group(tokens, precedence2)

    mod = Token(Token.I_MOD)
    mod.children = tokens
    walk(mod)
    walk2(mod)

    # after all transformations perform one last walk of the full graph
    # discover variables defined in one scope and used in a child scope
    treewalk_varscopes(mod)

    return tokens

def main():  # pragma: no cover
    import sys
    from .lexer import lexer

    logging.basicConfig(level=logging.INFO)

    path = sys.argv[1]
    if path == '-':
        text = sys.stdin.read()
    else:
        with open(path, "r") as src:
            text = src.read()

    try:
        tokens = list(lexer(text))

        asf = parser(tokens)

        for tok in asf:
            print(tok.toString(2))

    except ParseError as e:
        # dump the ASF generated so far
        for tok in tokens:
            print(tok.toString(True))

        e.format(path, text)
    except TokenError as e:
        e.format(path, text)

if __name__ == '__main__': # pragma: no cover
    main()

