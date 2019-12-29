#! python3 $this

import os
import struct
import glob
import inspect
import re
from .exception import TokenError

class Namespace(object):
    def __init__(self, **kwargs):
        self.__name__ = "unknown"
        for name, value in kwargs.items():
            setattr(self, name, value)

    def __repr__(self):
        return "<module '%s' (namespace)>" % self.__name__

    def __str__(self):
        return "<module '%s' (namespace)>" % self.__name__

def prefix_count(text, char):
    count = 0
    for c in text:
        if c == char:
            count += 1
        else:
            break;
    return count

def edit_distance(hyp, ref, eq=None):
    """
    given: two sequences hyp and ref (str, list, or bytes)

    solve E(i,j) -> E(m,n)
    """

    if len(hyp) == 0:
        return [(None, elem) for elem in ref], 0, 0, 0, len(ref)

    if len(ref) == 0:
        return [(elem, None) for elem in hyp], 0, 0, len(hyp), 0

    e = [0,]*(len(hyp)*len(ref))
    s = lambda i,j: i*len(ref)+j
    d = lambda i,j: 0 if hyp[i]==ref[j] else 1
    E = lambda i,j: e[s(i,j)]

    e[s(0,0)] = d(0,0)

    # build the error table using dynamic programming
    # first build the top and left edge
    for i in range(1,len(hyp)):
        e[s(i,0)] = min([1+i, d(i,0)+i])

    for j in range(1,len(ref)):
        e[s(0,j)] = min([1+j, d(0,j)+j])

    # fill in remaining squares
    for i in range(1,len(hyp)):
        for j in range(1,len(ref)):
            e[s(i,j)] = min([1+E(i-1,j),1+E(i,j-1),d(i,j)+E(i-1,j-1)])

    # reverse walk
    # find number of substitutions/insertions/deletions
    i=len(hyp)-1
    j=len(ref)-1
    seq = []
    cor=sub=del_=ins=0
    while i > 0 and j > 0:
        _a,_b,_c,_d = E(i,j),E(i-1,j),E(i,j-1),E(i-1,j-1)

        if _d<=_a and _d<_b and _d<_c:
            seq.append((hyp[i], ref[j]))
            if eq(hyp[i], ref[j]):
                cor+=1;
            else:
                sub+=1
            i,j = i-1,j-1
        elif _b <= _c:
            seq.append((hyp[i], None))
            i = i-1
            ins+=1
        else:
            seq.append((None, ref[j]))
            j = j-1
            del_+=1

    while i >= 0 and j >= 0:
        seq.append((hyp[i], ref[j]))
        if eq(hyp[i], ref[j]):
            cor+=1
        else:
            sub+=1
        i = i-1
        j = j-1

    while i >= 0:
        seq.append((hyp[i], None))
        i = i-1
        ins+=1

    while j >= 0:
        seq.append((None, ref[j]))
        j = j-1
        del_+=1

    if sub + ins + del_ == 0:
        assert cor == len(hyp), (cor, len(hyp))

    return reversed(seq), cor, sub, ins, del_

def intBitsToFloat(b):
    """
    Type-Pun an integer into a float
    """
    s = struct.pack('>L', b)
    return struct.unpack('>f', s)[0]

def intBitsToDouble(b):
    """
    Type-Pun an integer into a double
    """
    s = struct.pack('>Q', b)
    return struct.unpack('>d', s)[0]

def floatBitsToInt(b):
    """
    Type-Pun a float into an integer
    """
    s = struct.pack('>f', b)
    return struct.unpack('>L', s)[0]

def doubleBitsToInt(b):
    """
    Type-Pun a double into an integer
    """
    s = struct.pack('>d', b)
    return struct.unpack('>Q', s)[0]

number_prefix = {"0x": 16, "0o": 8, "0n":4, "0b": 2, '0f': -1}
number_suffix = ["tb", "gb", "mb", "kb", "b", "t", "g", "m", "k", "b"]
number_factors = {
    "tb": 1024*1024*1024*1024,
    "gb": 1024*1024*1024,
    "mb": 1024*1024,
    "kb": 1024,
    "b" : 1,
    "t" : 1000*1000*1000*1000,
    "g" : 1000*1000*1000,
    "m":  1000*1000,
    "k":  1000,
}

def parseNumber(token):
    text = token.value

    text = text.replace("_", "")

    imaginary = False
    if text.endswith('j'):
        imaginary = True
        text = text[:-1]

    factor = None
    for fix in number_suffix:
        if text.endswith(fix):
            factor = number_factors[fix]
            text = text[:-len(fix)]

    base = 10
    for fix in number_prefix.keys():
        if text.startswith(fix):
            text = text[len(fix):]
            base = number_prefix[fix]
            break

    value = None
    if base == -1:
        text = text[2:]
        try:
            value = int(text, 16)
        except Exception as e:
            value = None

        if value and len(text) == 8:
            value = intBitsToFloat(value)
        elif value and len(text) == 16:
            value = intBitsToDouble(value)
        else:
            raise TokenError(token, "invalid numerical constant expected 8 or 16 digits")
    else:
        try:
            value = int(text, base)
        except Exception as e:
            value = None
    if not value and "." in text or 'e' in text:
        try:
            if base == 10:
                value = float(text)
        except Exception as e:
            value = None

    if value is None:
        raise TokenError(token, "invalid numerical constant")

    if value and factor:
        value *= factor

    if imaginary:
        value *= 1j

    return value

def _format_replace(text, _globals, _locals):

    if text in _locals:
        return str(_locals[text])

    if text in _globals:
        return str(_globals[text])

    if text in os.environ:
        return str(os.environ[text])

    return ""

def _format(string, _globals, _locals):

    index = len(string) - 1
    while index >= 0:
        if string[index] == '$':
            s = string.find('{', index)
            e = string.find('}', index)
            if s >= 0 and s < e:
                label = string[s+1:e]
                replacement = _format_replace(label, _globals, _locals)
                string = string[:index] + replacement + string[e+1:]

        index -= 1
    return string

def es_format(string):

    frame = inspect.currentframe()
    _globals = frame.f_back.f_globals
    _locals = frame.f_back.f_locals
    return _format(string, _globals, _locals)

def es_glob(string):
    # TODO: implement bash substitutions
    # i.e.
    #  file{txt,md} -> [file.txt, file.md]
    frame = inspect.currentframe()
    _globals = frame.f_back.f_globals
    _locals = frame.f_back.f_locals
    string = _format(string, _globals, _locals)
    return glob.glob(string)

flags = {
    "i": re.IGNORECASE,
    "l": re.LOCALE,
    "m": re.MULTILINE,
    "s": re.DOTALL,
    "u": re.UNICODE,
    "x": re.VERBOSE,
    "g": None,
}

def es_regex(string):

    return re.compile(string)


def main():

    print(hex(floatBitsToInt(3.14)))
    print(intBitsToFloat(0x4048f5c3))

    print(hex(doubleBitsToInt(3.14)))
    print(intBitsToDouble(0x40091eb851eb851f))

if __name__ == '__main__':
    main()


