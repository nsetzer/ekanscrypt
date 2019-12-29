
# The Man Boy Test described by Donald Knuth
# https://en.wikipedia.org/wiki/Man_or_boy_test
# with modifications as implicit function calls
# are not supported.

# the test is not that the recursion passes
# but that proper aliasing of identifiers is performed
# by the compiler. (In ekanscrypt, the scoping rules
# and name mangling are performed by the parser phase)


A(k, x1, x2, x3, x4, x5) => {

    # k is passed in as an argument to A, but not used in the
    # scope of A, instead B decrements it. B initiates a form
    # of mutual recursion with A.

    B() => {
        # in a single line A and B have different meanings
        # and may be integers or functions
        k = k - 1;
        var B = var A = A(k, B, x1, x2, x3, x4)
        return B;
    }

    if (k <= 0) {

        # this section should be
        # var A = x4 + x5;
        # x4, x5 could be integers or references to the function B
        # these must be explicitly checked at runtime as the compiler
        # does not support implicit function calls

        v4=isinstance(x4,int)?x4:x4()
        v5=isinstance(x5,int)?x5:x5()
        var A = v4 + v5;
        return A;
    } else {
        return B();
    }
}


main() => {

    print(A(0, 1, -1, -1, 1, 0)) # 1
    print(A(1, 1, -1, -1, 1, 0)) # 0
    print(A(2, 1, -1, -1, 1, 0)) # -2
    print(A(3, 1, -1, -1, 1, 0)) # 0
    print(A(4, 1, -1, -1, 1, 0)) # 1
    print(A(5, 1, -1, -1, 1, 0)) # 0
    print(A(6, 1, -1, -1, 1, 0)) # 1
    print(A(7, 1, -1, -1, 1, 0)) # -1
    print(A(8, 1, -1, -1, 1, 0)) # -10
    print(A(9, 1, -1, -1, 1, 0)) # -30

    # for k = 10 the recursion limit must be increased to 1031
    import sys
    sys.setrecursionlimit(1031)

    print(A(10, 1, -1, -1, 1, 0)) # -67

}
