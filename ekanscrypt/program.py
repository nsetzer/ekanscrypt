
import os
import sys
import logging
import argparse

from .lexer import lexer
from .parser import parser
from .compiler import Expression
from .exception import TokenError, format_generic
from .util import prefix_count, Namespace

from .objects.proc import _textstream, EkanscryptProcTextNode

def path_name(name):

    count = prefix_count(name, ".")
    if count > 1:
        path = "../" * (count - 1)
    else:
        path = ""

    path += name.lstrip(".").replace(".", "/")

    path += ".es"

    return path

class Program(object):
    def __init__(self):
        super(Program, self).__init__()

        self.diag = False

    def compile(self, path, globals=None, name=None):

        with open(path, "r") as src:
            text = src.read()

        expr = self.compile_text(path, text, globals=globals, name=name)

        #save_module(path, expr.function_body.__code__)

        return expr

    def _patch_globals(self, globals, path):
        # TODO: move to Expression
        if not globals:
            globals = {}

        if path == "<string>" or not os.path.exists(path):
            script_path = os.getcwd()
        else:
            script_path, _ = os.path.split(path)

        globals['__file__'] = path
        globals['__script_path__'] = script_path

        return globals

    def compile_text(self, path, text, globals=None, name=None, flags=Expression.CF_MODULE):
        asf = parser(list(lexer(text)))

        if name is None:
            name = '__main__'

        if self.diag:
            for ast in asf:
                print(ast.toString(True))

        expr = Expression(name, path, globals=globals, flags=flags)
        expr.compile(asf)

        if self.diag:
            expr.dump()

        return expr

    def execute(self, name):
        pass

    def execute_text(self, text):
        unit = self.compile_text("<string>", text, flags=Expression.CF_REPL)
        return unit.function_body()

    def _execute(self, expr):
        pass

    def import_(self, level, name, script_path):
        """
        level: where to search for the given name
            n==0: absolute import
            n==1: current directory
            n>=2: n-1 parent directory

        name: dotted alpha-numeric string, a file name

        examples:
            level: 2, name 'foo.bar' => '../foo/bar.es'
            level: 0, name os => './os.es'

        absolute imports scan all directories in pythons sys.path
        If no match is found for an *.es file, then the default
        python import is used as a fallback

        return value is a namespce (or module) containing the exported names


        """

        module_name = name.replace(".", "/") + ".es"
        if level == 0:
            search_path = sys.path
        elif level == 1:
            path = "./" + module_name
            search_path = [script_path]
        elif level >= 2:
            path = "../" * (level - 1) + module_name
            search_path = [script_path]

        print(name, path)

        for dir_path in search_path:
            abspath = os.path.abspath(os.path.join(dir_path, path))
            if os.path.exists(abspath):
                unit = self.compile(abspath)
                mod = Namespace(**unit.function_body())
                mod.__name__ = name
                print(mod)
                return mod

    def es_import(self, name, globals=None, locals=None, fromlist=(), level=0):

        path = path_name(name)

        unit = self.compile(path, globals=globals)
        mod = Namespace(**unit.function_body())
        return mod

    def py_import(self, name, globals=None, locals=None, fromlist=(), level=0):
        return __import__(name, globals, locals, fromlist, level)

    def execute_node(self, node, args):
        # python -m ekanscrypt -n nodelib.col -- --col=0 --del=,

        module, function_name = node.rsplit('.')

        mod = __import__(module)
        mod_path = module.split(".")
        for name in mod_path[1:]:
            mod = getattr(mod, name)

        callable = getattr(mod, function_name)

        print(callable)
        # build an argparse from the following information
        argcount = callable.__code__.co_argcount
        argnames = callable.__code__.co_varnames[:argcount]
        argdefaults = callable.__defaults__
        if argdefaults is not None:
            k = len(argnames) - len(argdefaults)
            pos = argnames[:k]
            kwa = argnames[k:]
        else:
            pos = argnames
            kwa = []

        parser2 = argparse.ArgumentParser(description='')
        for arg in pos:
            parser2.add_argument(arg)
        for i, arg in enumerate(kwa):
            parser2.add_argument("--" + arg, default=argdefaults[i])
        args2 = parser2.parse_args()
        print(pos, kwa, argdefaults, args2)

        nd_args = [getattr(args2, arg) for arg in pos]
        nd_kwargs = {arg: getattr(args2, arg) for arg in kwa}

        nd = callable(*nd_args, **nd_kwargs)

        # TODO: wait, _parent, _child should be optional
        stream = Namespace(stdout=sys.stdin.buffer,
            stderr=None, stdin=None,
            wait=lambda: None, _parent=None, _child=None)

        if isinstance(nd, EkanscryptProcTextNode):
            stream = _textstream(stream)
            stream.wait = lambda: None
            stream._parent = None
            stream._child = None

        nd = nd(stream)

        return nd.run2()

    # f = x => y => x + y; add2 = f(2); print(add2(3));

def main():

    parser_log = logging.getLogger("ekanscrypt.parser")
    parser_log.setLevel(logging.ERROR)

    prog = Program()

    mod = prog.es_import("samples.mergesort")

    for name in vars(mod):
        print(name, getattr(mod, name))

    print(mod.mergesort([3,2,1]))

if __name__ == '__main__':
    main()