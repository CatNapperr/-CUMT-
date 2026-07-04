#include <stdio.h>
#include <stdlib.h>
#include <windows.h>

#define MATRIX_SIZE 1000
#define SAMPLE_COUNT 10

long long *A;
long long *X;
long long *result;

double current_time_seconds(void)
{
    LARGE_INTEGER frequency;
    LARGE_INTEGER counter;

    QueryPerformanceFrequency(&frequency);
    QueryPerformanceCounter(&counter);

    return (double)counter.QuadPart / (double)frequency.QuadPart;
}

void initialize_data(void)
{
    int i, j;

    for (i = 0; i < MATRIX_SIZE; i++)
    {
        X[i] = (i % 100) + 1;
        for (j = 0; j < MATRIX_SIZE; j++)
        {
            A[i * MATRIX_SIZE + j] = ((i + 1) * (j + 1)) % 97 + 1;
        }
    }
}

int main(void)
{
    int i, j;
    double start_time, end_time;
    long long checksum = 0;

    A = (long long *)malloc(sizeof(long long) * MATRIX_SIZE * MATRIX_SIZE);
    X = (long long *)malloc(sizeof(long long) * MATRIX_SIZE);
    result = (long long *)malloc(sizeof(long long) * MATRIX_SIZE);

    if (A == NULL || X == NULL || result == NULL)
    {
        printf("Memory allocation failed.\n");
        free(A);
        free(X);
        free(result);
        return 1;
    }

    initialize_data();

    start_time = current_time_seconds();

    for (i = 0; i < MATRIX_SIZE; i++)
    {
        result[i] = 0;
        for (j = 0; j < MATRIX_SIZE; j++)
        {
            result[i] += A[i * MATRIX_SIZE + j] * X[j];
        }
    }

    end_time = current_time_seconds();

    for (i = 0; i < SAMPLE_COUNT; i++)
    {
        printf("%lld\n", result[i]);
    }

    for (i = 0; i < MATRIX_SIZE; i++)
    {
        checksum += result[i];
    }

    printf("Checksum: %lld\n", checksum);
    printf("Serial time: %.6f s\n", end_time - start_time);

    free(A);
    free(X);
    free(result);

    return 0;
}