
import sys
import os.path

import time
import struct
import marshal
from importlib.abc import Loader, MetaPathFinder
from importlib.util import spec_from_file_location, MAGIC_NUMBER, cache_from_source
import types

from .program import Namespace
from .compiler import Expression
from .parser import parser
from .lexer import lexer
from .util import Namespace

def save_module(path, co):

    dirpath, _ = os.path.split(path)
    if not os.path.exists(dirpath):
        os.makedirs(dirpath)

    with open(path, "wb") as wb:
        wb.write(MAGIC_NUMBER)
        wb.write(b"\x00\x00\x00\x00")
        wb.write(struct.pack("I", int(time.time())))
        wb.write(b"\x00\x00\x00\x00")
        marshal.dump(co, wb)

def load_module(path):

    with open(path, "rb") as rb:

        magic = rb.read(4)
        if magic != MAGIC_NUMBER:
            raise ImportError("magic number does not match")
        rb.read(4)
        rb.read(4)
        rb.read(4)
        return marshal.load(rb)

def isNewer(source_path, compiled_path):
    return os.stat(source_path).st_mtime > os.stat(compiled_path).st_mtime

class EkanscryptFinder(MetaPathFinder):

    _installed = False
    def find_spec(self, fullname, path, target=None):

        if path is None or path == "":
            path = [os.getcwd()] # top level import --

        if "." in fullname:
            *_, name = fullname.split(".")
        else:
            name = fullname

        for entry in path:

            if os.path.isdir(os.path.join(entry, name)):
                # this module has child modules
                filename = os.path.join(entry, name, "__init__.es")
                submodule_locations = [os.path.join(entry, name)]
            else:
                filename = os.path.join(entry, name + ".es")
                submodule_locations = None

            if not os.path.exists(filename):
                continue

            sys.stderr.write("loader found `%s`\n" % filename)

            return spec_from_file_location(fullname, filename,
                loader=EkanscryptyLoader(filename),
                submodule_search_locations=submodule_locations)

        return None # we don't know how to import this

    @staticmethod
    def install():
        if not EkanscryptFinder._installed:
            print("install loader")
            sys.meta_path.insert(0, EkanscryptFinder())
            EkanscryptFinder._installed = True

class EkanscryptyLoader(Loader):
    def __init__(self, filename):
        self.filename = filename

    def create_module(self, spec):

        cpath = cache_from_source(spec.origin)
        code = None
        mod_fptr = None
        if os.path.exists(cpath) and not isNewer(spec.origin, cpath):
            code = load_module(cpath)
            mod_fptr = types.FunctionType(code, Expression.defaultGlobals(), spec.name)

        if not mod_fptr:
            with open(spec.origin, "r") as src:
                text = src.read()

            globals_ = Expression.defaultGlobals()
            expr = Expression(spec.name, spec.origin, globals=globals_, module=True)
            expr.compile(parser(list(lexer(text))))

            mod_fptr = expr.function_body
            code = mod_fptr.__code__
            save_module(cpath, code)

        mod = types.ModuleType(spec.name)

        mod.__name__ = spec.name
        mod.__file__ = spec.origin
        mod.__cached__ = cpath
        # TODO: set package name
        # https://docs.python.org/3/reference/import.html#__package__
        mod.__package__ = spec.name
        mod.__loader__ = self
        mod.__spec__ = spec

        mod.__body__ = mod_fptr

        return mod

    def exec_module(self, module):

        result = module.__body__()
        delattr(module, '__body__')

        if not isinstance(result, dict):
            raise ImportError("not a proper ES module")

        for name, attr in result.items():
            if not name.startswith("_"):
                setattr(module, name, attr)


EkanscryptFinder.install()