
def es_print(*args):
    first = True
    for item in args:
        if not first:
            sys.stderr.write(" ")
        sys.stderr.write("%s" % item)
        sys.stderr.flush()
        first = False
    sys.stderr.write("\n")
    sys.stderr.flush()

def es_drill(x, y):

    if x is None:
        return None

    if isinstance(x, list):
        if isinstance(x, int):
            if 0 <= y < len(x):
                return x[y]
    elif y in x:
        return x[y]
    elif isinstance(y, str):
        if hasattr(x, y):
            return getattr(x, y)
    return None