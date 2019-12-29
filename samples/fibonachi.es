
fib(n) => {
    if (n <= 0) {
        return 0;
    } else if (n == 1) {
        return 1;
    } else {
        return fib(n-1) + fib(n-2);
    }
}

x = 0;
while x <= 5 {
    print(fib(x));
    x = x + 1;
}

