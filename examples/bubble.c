#include <stdio.h>

int data[10] = {42, -7, 19, 0, 88, 3, -25, 61, 19, 5};

void show(int n) {
    for (int i = 0; i < n; i++)
        printf("%d%c", data[i], i == n - 1 ? '\n' : ' ');
}

void bubble(int n) {
    int swapped;
    do {
        swapped = 0;
        for (int i = 1; i < n; i++) {
            if (data[i - 1] > data[i]) {
                int t = data[i];
                data[i] = data[i - 1];
                data[i - 1] = t;
                swapped = 1;
            }
        }
        n--;
    } while (swapped);
}

int main(void) {
    show(10);
    bubble(10);
    show(10);
    return 0;
}
