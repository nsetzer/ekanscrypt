
import io
import os
import sys

class EkanscryptIo(object):
    def __init__(self):
        super(EkanscryptIo, self).__init__()

        self.stdout = sys.stdout
        self.stderr = sys.stderr
        self.stdin = sys.stdin
        self.open = open
        self.BytesIO = io.BytesIO
        self.StringIO = io.BytesIO
        self.argv = sys.argv
        self.path = os.path
        self.listdir = os.listdir
        self.io = io
        self.sys = sys
        self.os = os
