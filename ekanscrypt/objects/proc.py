
import os
import sys
import subprocess
import types
import select
import io
import threading
import traceback
import codecs
import logging
log = logging.getLogger("ekanscrypt.proc")

class _fdfile(object):
    def __init__(self, fd, mode):
        super(_fdfile, self).__init__()
        self.mode = mode
        self.fd = fd
        self.closed = False

    def read(self, n):
        if self.mode != "r":
            raise ValueError(self.mode)
        if self.closed:
            return b""
        return os.read(self.fd, n)

    def write(self, string):
        if self.mode != "w":
            raise ValueError(self.mode)
        try:
            return os.write(self.fd, string)
        except BrokenPipeError:
            sys.stderr.write("write to %d failed 1 (%d)" % (self.fd, len(string)))
        except OSError:
            sys.stderr.write("write to %d failed 2 (%d)" % (self.fd, len(string)))

    def flush():
        pass

    def isatty():
        return False

    def readable():
        return self.mode == "r"

    def seekable():
        return False

    def writable():
        return self.mode == "w"

    def close(self):
        if not self.closed:
            self.closed = True
            return os.close(self.fd)

    def fileno(self):
        return self.fd

    def __repr__(self):
        return "fd<%s,%s>" % (self.fd, self.mode)

class _pipefile(object):
    def __init__(self):
        super(_pipefile, self).__init__()

        self._fd_in_r, self._fd_in_w = os.pipe()
        self.stdin = _fdfile(self._fd_in_w, "w")
        self.stdout = _fdfile(self._fd_in_r, "r")
        self.stderr = None

class _textfile(object):
    def __init__(self):
        super(_textfile, self).__init__()

        writer_factory = codecs.getwriter("utf-8")
        reader_factory = codecs.getreader("utf-8")

        self._fd_in_r, self._fd_in_w = os.pipe()

        self._stdin = _fdfile(self._fd_in_w, "w")
        self._stdout = _fdfile(self._fd_in_r, "r")
        self._stderr = None

        # provide an underlying buffer
        # like sys.stdout.buffer, to allow
        # for directly writing bytes
        self.stdin = writer_factory(self._stdin)
        self.stdin.buffer = self._stdin
        self.stdin.writeline2 = self._writeline
        self.stdout = reader_factory(self._stdout)
        self.stdout.buffer = self._stdout
        self.stdout.readline2 = self._readline2
        self.stderr = None

    def _readline2(self):

        line = self.stdout.readline()
        while line and not line.strip():
            line = self.stdout.readline()
        return line.rstrip("\n")

    def _writeline(self, text):
        self.stdin.write(text)
        self.stdin.write("\n")

class _textstream(object):
    def __init__(self, stream):
        super(_textstream, self).__init__()
        self.stream = stream

        writer_factory = codecs.getwriter("utf-8")
        reader_factory = codecs.getreader("utf-8")

        self.stdin = None
        self.stdout = None
        self.stderr = None

        if self.stream:
            if self.stream.stdin:
                if isinstance(self.stream.stdin, codecs.StreamWriter):
                    self.stdin = self.stream.stdin
                else:
                    self.stdin = writer_factory(self.stream.stdin)
                    self.stdin.buffer = self.stream.stdin
                    self.stdin.writeline2 = self._writeline

            if self.stream.stdout:
                if isinstance(self.stream.stdout, codecs.StreamReader):
                    self.stdout = self.stream.stdout
                else:
                    self.stdout = reader_factory(self.stream.stdout)
                    self.stdout.buffer = self.stream.stdout
                    self.stdout.readline2 = self._readline2

            if self.stream.stderr:
                self.stderr = reader_factory(self.stream.stderr)

    def _readline2(self):

        line = self.stdout.readline()
        while line and not line.strip():
            line = self.stdout.readline()
        return line.rstrip("\n")

    def _writeline(self, text):
        self.stdin.write(text)
        self.stdin.write("\n")

class _ndfile(object):
    """
    provides a natural interface for handling process input/output

    this objects stdin represents a pipeline processes input and
    mimics the api of sys.stdin, while stdout represents the pipeline
    processes output, minmicing the api of syd.stdout
    """
    def __init__(self, src, dst):
        super(_ndfile, self).__init__()

        self.stdin = src.stdout if src else None

        self.stdout = dst.stdin if dst else None
        self._stderr = src.stderr if src else None
        self._stdin = src.stdin if src else None

    def close(self):
        if self.stdin:
            self.stdin.close()

        if self.stdout:
            self.stdout.close()

        if self._stderr:
            self._stderr.close()

        if self._stdin:
            self._stdin.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

class Popen(subprocess.Popen):

    def __repr__(self):
        return "Proc<%s>" % ','.join(repr(r) for r in self.args)

class ProcNodeThread(threading.Thread):
    """docstring for ProcNodeThread"""

    def __init__(self, parent, stream, callback):
        super(ProcNodeThread, self).__init__()
        self.callback = callback
        self.stream = stream
        self.parent = parent

    def run(self):

        try:
            with _ndfile(self.stream, self.parent) as f:
                self.callback(f)

                self.parent.returncode = 0

                #while self.parent._parent and self.parent._parent.returncode is None:
                #    # TODO: still not clear if this is needed
                #    sys.stderr.write("waiting for parent process to finish\n")
                #    time.sleep(0.1)

        except BaseException as e:
            self.parent.returncode = 1
            traceback.print_exc()
            sys.stderr.write("unhandled exception: %s\n" % e)

class EkanscryptProcNode(object):

    _filetype = _pipefile

    def __init__(self, callback=None):
        super().__init__()

        self.callback = callback or self.execute
        self._called = False

        self.pipe = self._filetype()

        # used by communicate api
        self.stdin = self.pipe.stdin
        self.stdout = self.pipe.stdout
        self.stderr = None
        self.returncode = None
        self.thread = None

    def __repr__(self):
        #return "Node<%s,%s,%s>" % (self.stdin, self.stdout, self.stderr)
        return "ProcNode<%s>" % (self.callback.__name__)

    def __call__(self, stream=None):
        if self._called:
            raise RuntimeError("Double call on process")
        self._called = True
        original = stream
        if isinstance(stream, (EkanscryptProcNode, subprocess.Popen)):
            if isinstance(self, EkanscryptProcTextNode):
                stream = _textstream(stream)
        self.thread = ProcNodeThread(self, stream, self.callback)
        self.thread.start()

        self._parent = original
        self._child = None
        if original:
            original._child = self
        return self

    def execute(self, stream):
        # puplic API to implement
        raise NotImplementedError("implement execute")

    def wait(self):
        if self.thread:
            self.thread.join()
        return self.returncode

    def run(self):
        if not self._called:
            self(None)
        # TODO: support text mode output
        if isinstance(self, EkanscryptProcTextNode):
            stdout = io.StringIO()
            stderr = io.StringIO()
        else:
            stdout = io.BytesIO()
            stderr = io.BytesIO()
        returncode = EkanscryptProc.communicate(self, stdout=stdout, stderr=stderr)
        return returncode, stdout.getvalue(), stderr.getvalue()

    def run2(self):
        if not self._called:
            self(None)
        return EkanscryptProc.communicate(self)

    def background(self):
        if not self._called:
            self(None)

        return self

class EkanscryptProcTextNode(EkanscryptProcNode):

    _filetype = _textfile

    def __repr__(self):
        #return "Node<%s,%s,%s>" % (self.stdin, self.stdout, self.stderr)
        return "ProcTextNode<%s>" % (self.callback.__name__)

class BackgroundProc(threading.Thread):
    def __init__(self, proc, target):
        super(BackgroundProc, self).__init__(target=target)
        self.proc = proc

    def wait(self):

        self.join()

        for f in self._open_files:
            f.close()

        return self.proc.proc.returncode

class EkanscryptProcRedirect(object):
    def __init__(self, mode, src, dst):
        super(EkanscryptProcRedirect, self).__init__()
        self.mode = mode # 1 write, 2 append
        try:
            self.src = int(src)
        except Exception as e:
            print("error with redirect", e)
            self.src =src

        if src == '&stdout':
            src = 1

        if src == '&stderr':
            src = 2

        try:
            self.dst = int(dst)
        except Exception as e:
            self.dst =dst

    def __repr__(self):
        return "'%s%s%s'" % (self.src, {1:'>', 2:'>>'}[self.mode], self.dst)

class EkanscryptProc(object):
    def __init__(self, *args):
        super(EkanscryptProc, self).__init__()
        self.args, self.port_mapping = self._build_args(args)
        self._called = False

    def __repr__(self):
        return "Proc(%s)" % (','.join('%r' % r for r in self.args))

    def _build_args(self, args):
        # TODO: the last N arguments can be a tuple of pairs for pipe redirect
        #   (file|pipe, file|pipe)
        # e.g.
        #   ('/tmp/file', 0) -- write /tmp/file into stdin
        #   (1, '/tmp/file') -- write stdout to /tmp/file
        #   (2, 1)           -- write stderr into stdout
        #
        #   1 > '/tmp/data'
        #   2 > '/tmp/data'
        #   2 > 1
        #   1 > '/tmp/data' 2>1  # both to same file
        #   2>1 1>'/tmp/data'    # 2 to stdout, 1 to file
        #   '/tmp/data'>0        # file to stdin
        #   ${label}>0           # variable to file
        #   to suopport variable to file, the language must pass
        #   an open file handle to exec, i.e (2, open('path'))
        #   and a context cannot be used to close it, the
        #   exec process will need to do that...

        port_mapping = {
            0: (1,0),
            1: (1,1),
            2: (1,2),
        }
        # I.E named pipes
        # TODO: special files &stdin, &stdout, &stderr, &nul
        # when the redirect specifies these files
        # instead use the original setting
        # e.g. 1>&stderr 2>stdout or 1>nul or stderr>stdout
        # e.g. stdin<nul

        arglst = []
        for arg in args:
            if isinstance(arg, str):
                arglst.append(arg)
            elif isinstance(arg, list):
                # TODO: check all are strings
                # TODO: enable iterable api
                # TODO: possibly json encode maps?
                for val in arg:
                    arglst.append(str(val))
            elif isinstance(arg, EkanscryptProcRedirect):

                if isinstance(arg.dst, int):
                    if arg.dst == 0:
                        port_mapping[arg.dst] = (1, arg.src)
                    else:
                        port_mapping[arg.src] = port_mapping[arg.dst]
                else:
                    port_mapping[arg.src] = (arg.mode, arg.dst)
                arg.src
            elif callable(arg):
                # TODO: ensure first position
                arglst.append(arg)

        return arglst, port_mapping

    def _open_pipes(self, stream):

        log.info(self.port_mapping)

        _stdin = stream.stdout if hasattr(stream, 'stdout') else None
        _stdout = subprocess.PIPE
        _stderr = None

        literal = {
            1: subprocess.STDOUT,
            2: sys.stderr.fileno(),
        }
        defaults = {
            0: _stdin,
            1: _stdout,
            2: _stderr,
        }

        self.file_mapping = dict(defaults)
        open_files = []

        for src, (mode, dst) in self.port_mapping.items():
            if dst is None:
                continue

            elif isinstance(dst, int):
                if src == 0:
                    if dst != 0:
                        raise RuntimeError("redirect %d to %d is invalid" % (dst, src))
                elif src == dst:
                    # the default is correct
                    pass
                else:  # src != dst, src > 0

                    self.file_mapping[src] = literal[dst]

                log.info(src, ">", dst, defaults[dst])

            elif isinstance(dst, str):
                _x_mode = "rb" if src == 0 else ("wb" if mode == 1 else "ab")
                if dst == '&stdout':
                    dst = 1
                    _f = 1

                elif dst == '&stderr':
                    dst = 2
                    _f = 2

                elif dst not in defaults:
                    log.info("opening", _x_mode, dst)
                    _f = open(dst, _x_mode)
                    open_files.append(_f)
                    defaults[dst] = (_x_mode, _f.fileno())
                    _f = _f.fileno()
                else:
                    _mode, _f = defaults[dst]
                    if _mode != _x_mode:
                        raise RuntimeError("invalid redirect dst file opened for 2 different modes")
                self.file_mapping[src] = _f
        print("proc file mapping", self.file_mapping)
        return open_files

    def __call__(self, stream=None):
        if self._called:
            raise RuntimeError("Double call on process")

        self._called = True

        open_files = self._open_pipes(stream)

        self.proc = Popen(
            self.args,
            stdin=self.file_mapping[0],
            stdout=self.file_mapping[1],
            stderr=self.file_mapping[2],
        )

        self.proc._parent = stream
        self.proc._child = None
        self.proc._open_files = open_files
        if stream:
            stream._child = self.proc

        self.proc.run = self._run
        self.proc.background = self._background

        return self.proc

    def _run(self):
        if not self._called:
            self(None)
        stdout = io.BytesIO()
        stderr = io.BytesIO()
        returncode = EkanscryptProc.communicate(self.proc, stdout=stdout, stderr=stderr)

        return returncode, stdout.getvalue(), stderr.getvalue()

    def run(self):
        return self._run()

    def run2(self):
        if not self._called:
            self(None)
        return EkanscryptProc.communicate(self.proc)

    def _background(self):

        thread = BackgroundProc(self, target=self.run)
        thread.start()

        return thread

    def background(self):
        return self._background()

    @staticmethod
    def Redirect(mode, src, dst):
        return EkanscryptProcRedirect(mode, src, dst)

    Node = EkanscryptProcNode

    TextNode = EkanscryptProcTextNode

    @staticmethod
    def communicate(stream, stdout=None, stderr=None):

        if isinstance(stream, EkanscryptProcNode):

            fds = []
            dst = {}
            src = {}
            if hasattr(stream, 'stdout') and stream.stdout:
                fd = stream.stdout.fileno()
                fds.append(fd)
                if stdout is None:
                    if isinstance(stream, EkanscryptProcTextNode):
                        dst[fd] = sys.stdout
                    else:
                        dst[fd] = sys.stdout.buffer
                else:
                    dst[fd] = stdout

                # wrap the output file in a text reader
                if isinstance(stream, EkanscryptProcTextNode):
                    src[fd] = codecs.getreader("utf-8")(_fdfile(fd, "r"))
                else:
                    src[fd] = _fdfile(fd, "r")

            while True:
                rlist, _, _ = select.select(fds, [], [], 0.5)

                if not rlist:
                    continue

                success = False
                for fd in rlist:
                    #data = os.read(fd, 1024)
                    data = src[fd].read(1024)
                    if len(data) > 0:
                        success = True
                    dst[fd].write(data)

                # TODO: put a ~1minute, ~10 second warning for dev testing
                if not success and stream.returncode is not None:
                    break

            nd = stream
            while nd:
                nd.wait()
                nd = nd._parent

            return stream.returncode

        elif isinstance(stream, subprocess.Popen):

            if stream and stream.stdin:
                stream.stdin.close()

            fds = []
            dst = {}
            if hasattr(stream, 'stdout') and stream.stdout:
                fd = stream.stdout.fileno()
                fds.append(fd)
                if stdout is None:
                    dst[fd] = sys.stdout.buffer
                else:
                    dst[fd] = stdout
            if hasattr(stream, 'stderr') and stream.stderr:
                fd = stream.stderr.fileno()
                fds.append(fd)
                if stderr is None:
                    dst[fd] = sys.stderr.buffer
                else:
                    dst[fd] = stderr

            # its possible there are no files to read from
            while fds:
                try:
                    rlist, _, _ = select.select(fds, [], [], 0.5)

                    if not rlist:
                        if stream.returncode is not None:
                            break
                        continue

                    count = 0
                    for fd in rlist:
                        # TODO: support text mode output somehow...
                        # maybe the encoding argument should be an argument
                        # to this method
                        data = os.read(fd, 1024)
                        count += len(data)
                        dst[fd].write(data)

                    # TODO: put a ~1minute, ~10 second warning for dev testing
                    if count == 0 or stream.returncode is not None:
                        break
                except KeyboardInterrupt:
                    print(stream.stdin)
                    print(stream.stdout)
                    print(stream.stderr)
                    print(stream.returncode)
                    sys.exit(1)

            # TODO: maybe this should wait in reverse
            nd = stream
            while nd:
                nd.wait()
                nd = nd._parent

            return stream.returncode
        elif hasattr(stream, '__call__'):
            stream()
        else:
            raise NotImplementedError(stream)

def process_test():

    # todo: obvious callback case
    # map dst.stdin to obj.stdout
    # map src.stdout to obj.stdin
    #
    def callback1(pipe):
        pipe.stdout.write(b"hello world\n")

    def callback2(pipe):
        data = pipe.stdin.read(1024)
        assert data == b"hello world\n"
        pipe.stdout.write(data)

    def callback3(pipe):
        data = pipe.stdin.read(1024)
        assert data == b"hello world\n"
        pipe.stdout.write(data)

    def callback4(pipe):
        data = pipe.stdin.read(1024)
        assert data == b"hello world\n"
        pipe.stdout.write(data)

    def mkProc1():
        return EkanscryptProc("echo", "hello world")

    def mkProc2():
        return EkanscryptProc("cat", "-")

    def mkProc3():
        return EkanscryptProc("cat", "-")

    def mkProc4():
        return EkanscryptProc("cat", "-")

    def mkNode1():
        return EkanscryptProcNode(callback1)

    def mkNode2():
        return EkanscryptProcNode(callback2)

    def mkNode3():
        return EkanscryptProcNode(callback3)

    def mkNode4():
        return EkanscryptProcNode(callback4)

    # test that all combinations of nodes and procs can
    # be used as sources or sinks

    print("single")
    for mk1 in [mkProc1, mkNode1]:
        a = mk1()
        pipeline = a()
        print(a)
        stdout = io.BytesIO()
        EkanscryptProc.communicate(pipeline, stdout=stdout)
        print(stdout.getvalue())

    # each of the following tests should print out hello world
    print("double")
    for mk1 in [mkProc1, mkNode1]:
        for mk2 in [mkProc2, mkNode2]:
            a = mk1()
            b = mk2()
            pipeline = b(a())
            print(a, "|>", b)
            stdout = io.BytesIO()
            EkanscryptProc.communicate(pipeline, stdout=stdout)
            print(stdout.getvalue())

    # test that all combinations of nodes and procs can
    # be used as sources or sinks in a 3 process pipeline

    print("triple")
    for mk1 in [mkProc1, mkNode1]:
        for mk2 in [mkProc2, mkNode2]:
            for mk3 in [mkProc3, mkNode3]:
                a = mk1()
                b = mk2()
                c = mk3()
                pipeline = c(b(a()))
                print(a, "|>", b, "|>", c)
                EkanscryptProc.communicate(pipeline)

    # test that all combinations of nodes and procs can
    # be used as sources or sinks in a 4 process pipeline
    #
    print("quad")
    for mk1 in [mkProc1, mkNode1]:
        for mk2 in [mkProc2, mkNode2]:
            for mk3 in [mkProc3, mkNode3]:
                for mk4 in [mkProc4, mkNode4]:
                    a = mk1()
                    b = mk2()
                    c = mk3()
                    d = mk4()
                    pipeline = d(c(b(a())))
                    print(a, "|>", b, "|>", c, "|>", d)
                    EkanscryptProc.communicate(pipeline)

def big_test():

    N = 20
    S = 333
    def callback1(pipe):
        for i in range(N):
            pipe.stdout.write(b"0" * S)

    def callback2(pipe):

        buf = pipe.stdin.read(1024)
        while buf:
            pipe.stdout.write(buf)
            buf = pipe.stdin.read(1024)

    def mkNodeSource():
        return EkanscryptProcNode(callback1)

    def mkNodeSink():
        return EkanscryptProcNode(callback2)

    def mkProcSink():
        return EkanscryptProc("cat", "-")

    for mk2 in [mkNodeSink, mkProcSink]:
        for mk3 in [mkNodeSink, mkProcSink]:
            a = mkNodeSource()
            b = mk2()
            c = mk3()
            print(a,b,c)
            pipeline = c(b(a()))
            buf = io.BytesIO()
            EkanscryptProc.communicate(pipeline, stdout=buf)
            assert len(buf.getvalue()) == N*S, (len(buf.getvalue()),N*S)

def node_test():
    def callback1(pipe):
        for i in range(10):
            pipe.stdout.write(b"0" * 666)

    def callback2(pipe):
        count = 0
        buf = pipe.stdin.read(1024)
        while buf:
            count += len(buf)
            pipe.stdout.write(buf)
            buf = pipe.stdin.read(1024)

    def callback3(pipe):
        count = 0
        buf = pipe.stdin.read(1024)
        while buf:
            count += len(buf)
            pipe.stdout.write(buf)
            buf = pipe.stdin.read(1024)

    a = EkanscryptProcNode(callback1)
    b = EkanscryptProcNode(callback2)
    c = EkanscryptProcNode(callback3)

    pipeline = c(b(a()))
    buf = io.BytesIO()
    EkanscryptProc.communicate(pipeline, stdout=buf)

    data = buf.getvalue()
    assert len(data) == 6660

def main():
    # Note: these tests wont work on windows
    #process_test()
    big_test()
    #node_test()

if __name__ == '__main__':
    main()




