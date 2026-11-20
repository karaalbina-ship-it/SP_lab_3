#include <stdio.h>

int steps(int n) {
    int k = 0;
    while (n != 1) {
        n = n % 2 == 0 ? n / 2 : 3 * n + 1;
        k++;
    }
    return k;
}

int main(void) {
    int best = 1, longest = 0;
    for (int n = 1; n < 1000; n++) {
        int s = steps(n);
        if (s > longest) {
            longest = s;
            best = n;
        }
    }
    printf("longest chain below 1000: n = %d, %d steps\n", best, longest);
    int n = 27;
    do {
        printf("%d ", n);
        n = n % 2 ? 3 * n + 1 : n / 2;
    } while (n > 100);
    printf("...\n");
    return 0;
}
