#include <stdio.h>

int sorted[16];
int probes;

int find(int key, int n) {
    int lo = 0, hi = n - 1;
    probes = 0;
    while (lo <= hi) {
        int mid = (lo + hi) / 2;
        probes++;
        if (sorted[mid] == key)
            return mid;
        if (sorted[mid] < key)
            lo = mid + 1;
        else
            hi = mid - 1;
    }
    return -1;
}

int main(void) {
    for (int i = 0; i < 16; i++)
        sorted[i] = i * i;
    for (int key = 0; ; key += 7) {
        if (key > 60)
            break;
        int at = find(key, 16);
        if (at < 0) {
            printf("%2d: not found (%d probes)\n", key, probes);
            continue;
        }
        printf("%2d: index %d (%d probes)\n", key, at, probes);
    }
    {
        int probes = 99;
        printf("shadowed probes = %d\n", probes);
    }
    printf("global probes = %d\n", probes);
    return 0;
}
