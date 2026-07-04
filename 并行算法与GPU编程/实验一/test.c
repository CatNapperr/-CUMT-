#include <pthread.h>
#include <stdio.h>

long long n = 1000000;
const int thread_count = 2;
long long sum = 0;
pthread_mutex_t mutexsum;

void *thread_sum(void *rank)
{
    // 初始化参数
    int my_rank = *(int *)rank;
    long long my_sum = 0;
    long long my_n = n / thread_count;
    long long first = my_rank * my_n;
    long long last = first + my_n;
    long long i;

    // 业务逻辑
    for (i = first + 1; i <= last; i++)
    {
        my_sum += i;
    }
    // 结果汇总
    pthread_mutex_lock(&mutexsum);
    sum += my_sum;
    pthread_mutex_unlock(&mutexsum);

    return NULL;
}

int main()
{
    int i;
    pthread_t thread_ID[thread_count];
    int value[thread_count];

    pthread_mutex_init(&mutexsum, NULL);

    // 初始化线程ID
    for (i = 0; i < thread_count; i++)
        value[i] = i;

    // 创建线程
    for (i = 0; i < thread_count; i++)
        pthread_create(&thread_ID[i], NULL, thread_sum, &value[i]);

    // 等待线程执行结束
    for (i = 0; i < thread_count; i++)
        pthread_join(thread_ID[i], NULL);

    // 销毁锁
    pthread_mutex_destroy(&mutexsum);
    printf("Result is: %lld\n", sum);
    return 0;
}
