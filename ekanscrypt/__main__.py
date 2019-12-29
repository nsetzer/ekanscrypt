
import os
import sys
import argparse
import logging

from .import loader

from .program import Program, Namespace
from .repl import Repl

import faulthandler; faulthandler.enable()
from .exception import TokenError, format_generic

def parse_args(argv):
    program, *argvalues = argv
    args = Namespace()
    args.verbose = 0
    args.positional = []
    args.evaluate = None
    args.module = None
    args.node = None

    opts1 = {
        "-n": ("node", str),
        "-m": ("module", str),
        "-e": ("evaluate", str),
    }
    opts2 = {
        "--node": ("node", str),
        "--module": ("module", str),
        "--evaluate": ("evaluate", str),
    }

    while argvalues:
        arg = argvalues.pop(0)

        if arg == "-h" or arg == '--help':
            sys.stdout.write("Usage:\n")
            sys.stdout.write("  %s [-v] -[V] [-h|--help] [-n|--node] [-m|--module [-e|--evaluate]\n" % program)
            sys.exit(1)

        elif arg == "-V":
            sys.stdout.write("ekanscrypt 0.0.0\n")
            sys.exit(1)

        elif arg.startswith("-v"):
            args.verbose += len(arg[1:])

        elif arg in opts1:
            target, type_ = opts1[arg]
            value = argvalues.pop(0)
            setattr(args, target, type_(value))

        elif arg in opts2:
            target, type_ = opts2[arg]
            if '=' in arg:
                value = arg.split('=', 1)[-1]
            else:
                value = argvalues.pop(0)
            setattr(args, target, type_(value))

        else:
            args.positional.append(arg)

    return args

def main():

    log_parser = logging.getLogger("ekanscrypt.parser")
    log_proc = logging.getLogger("ekanscrypt.proc")

    args = parse_args(sys.argv)

    # TODO:
    #  0: error only
    #  1: warning runtime (i.e. proc)
    #  2: info runtime, warning compile time
    #  3: info all
    if args.verbose > 1:
        log_parser.setLevel(logging.INFO)
        log_proc.setLevel(logging.INFO)
    elif args.verbose == 1:
        pass
    else:
        log_parser.setLevel(logging.ERROR)
        log_proc.setLevel(logging.ERROR)

    program = Program()

    if args.evaluate:
        path = "<string>"
        text = args.evaluate
        unit = program.compile_text(path, text)
        unit.function_body()
    elif args.module:

        sys.argv = [args.module] + args.positional
        mod = __import__(args.module)
        mod_path = args.module.split(".")
        for name in mod_path[1:]:
            mod = getattr(mod, name)
        if hasattr(mod, 'main'):
            main = exports['main']
            if main.__code__.co_argcount == 1:
                exports['main'](sys.argv)
            else:
                exports['main']()

    elif args.node:

        sys.argv = [args.node] + args.positional
        sys.exit(program.execute_node(args.node, args.positional))

    elif args.positional:

        try:

            sys.argv = args.positional

            if args.positional[0] == "-":
                text = sys.stdin.read()
                path = "<string>"
                unit = program.compile_text(path, text)
            else:
                path = args.positional[0]
                text = None
                unit = program.compile(path)

            exports = unit.function_body()

            if 'main' in exports:
                main = exports['main']
                if main.__code__.co_argcount == 1:
                    exports['main'](sys.argv)
                else:
                    exports['main']()

        except TokenError as e:
            if os.path.exists(path) and not text:
                text = open(path).read()
            e.format(path, text)
        except Exception as e:
            format_generic(*sys.exc_info())

    else:
        repl = Repl()
        repl.main()

if __name__ == '__main__':
    main()
