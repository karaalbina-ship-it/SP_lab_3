#include <stdio.h>

int calls = 0;

int touch(int v) {
    calls++;
    return v;
}

int main(void) {
    int a = 17, b = 5;
    printf("%d %d %d %d %d\n", a + b * 2, (a + b) * 2, a / b, a % b, -a / b);
    printf("%d %d\n", -a % b, a % -b);
    printf("%d %d %d\n", 2 + 3 * 4 - 6 / 2, 100 / 10 / 5, 2 - 3 - 4);
    printf("%d %d %d %d\n", a > b, a == b, !(a < b), a >= 17 && b <= 5);
    int x = 10;
    x += 5;
    x *= 3;
    x -= 4;
    x /= 2;
    x %= 7;
    printf("x = %d\n", x);
    int i = 5;
    int j = i++;
    j += ++i;
    printf("i = %d, j = %d\n", i, j);
    int k = 0 && touch(1);
    k = 1 || touch(2);
    k = touch(0) || touch(3);
    printf("k = %d, calls = %d\n", k, calls);
    int m = a > b ? a > 10 ? 2 : 1 : 0;
    printf("m = %d\n", m);
    int big = 2147483647;
    big = big + 1;
    printf("overflow: %d\n", big);
    printf("%5d|%-5d|%c%c|%s|%%\n", 42, 42, 'o', 'k', "str");
    return 0;
}
