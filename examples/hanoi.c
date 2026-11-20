#include <stdio.h>

int moves = 0;

void hanoi(int n, int from, int to, int via) {
    if (n == 0)
        return;
    hanoi(n - 1, from, via, to);
    moves++;
    if (n == 3 || moves <= 3)
        printf("move %d: disk %d %c -> %c\n", moves, n, from, to);
    hanoi(n - 1, via, to, from);
}

int main(void) {
    hanoi(4, 'A', 'C', 'B');
    printf("total moves: %d\n", moves);
    return 0;
}
