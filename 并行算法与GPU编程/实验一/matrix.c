#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <windows.h>

#define MATRIX_SIZE 1000
#define THREAD_COUNT 4
#define SAMPLE_COUNT 10

long long *A;
long long *X;
long long *result;

typedef struct
{
    int start_row;
    int end_row;
} ThreadData;

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

void *pthread_mat_vec(void *arg)
{
    ThreadData *data = (ThreadData *)arg;
    int i, j;

    for (i = data->start_row; i < data->end_row; i++)
    {
        long long row_sum = 0;
        for (j = 0; j < MATRIX_SIZE; j++)
        {
            row_sum += A[i * MATRIX_SIZE + j] * X[j];
        }
        result[i] = row_sum;
    }

    return NULL;
}

int main(void)
{
    int i;
    pthread_t thread_ID[THREAD_COUNT];
    ThreadData thread_data[THREAD_COUNT];
    int current_row = 0;
    int base_rows = MATRIX_SIZE / THREAD_COUNT;
    int extra_rows = MATRIX_SIZE % THREAD_COUNT;
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

    for (i = 0; i < THREAD_COUNT; i++)
    {
        int rows = base_rows + (i < extra_rows ? 1 : 0);
        thread_data[i].start_row = current_row;
        thread_data[i].end_row = current_row + rows;
        current_row += rows;
        pthread_create(&thread_ID[i], NULL, pthread_mat_vec, &thread_data[i]);
    }

    for (i = 0; i < THREAD_COUNT; i++)
    {
        pthread_join(thread_ID[i], NULL);
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
    printf("Parallel time: %.6f s\n", end_time - start_time);

    free(A);
    free(X);
    free(result);

    return 0;
}