#include <stdio.h>

int fib_rec(int n) {
    return n < 2 ? n : fib_rec(n - 1) + fib_rec(n - 2);
}

int fib_iter(int n) {
    int a = 0, b = 1;
    while (n-- > 0) {
        int t = a + b;
        a = b;
        b = t;
    }
    return a;
}

int main(void) {
    for (int i = 0; i <= 20; i += 4)
        printf("fib(%2d) = %5d %5d\n", i, fib_rec(i), fib_iter(i));
    printf("fib(46) = %d\n", fib_iter(46));
    return 0;
}
