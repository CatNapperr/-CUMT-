#include <cuda_runtime.h>
#include <stdio.h>
#include <stdlib.h>
#include <vector>
#include <chrono>

typedef int DataType;

// ---------- 串行版本（基准） ----------
void conv2d_serial(const DataType *input, const DataType *kernel,
                   int rows, int cols, int kRows, int kCols,
                   DataType *output)
{
    int outRows = rows - kRows + 1;
    int outCols = cols - kCols + 1;
    for (int r = 0; r < outRows; ++r)
    {
        for (int c = 0; c < outCols; ++c)
        {
            int sum = 0;
            for (int ky = 0; ky < kRows; ++ky)
            {
                for (int kx = 0; kx < kCols; ++kx)
                {
                    sum += input[(r + ky) * cols + (c + kx)] *
                           kernel[ky * kCols + kx];
                }
            }
            output[r * outCols + c] = sum;
        }
    }
}

// ---------- 朴素并行卷积（全局内存直接访问） ----------
__global__ void conv2d_naive(const DataType *input, const DataType *kernel,
                             int rows, int cols, int kRows, int kCols,
                             DataType *output, int outRows, int outCols)
{
    int out_x = blockIdx.x * blockDim.x + threadIdx.x;
    int out_y = blockIdx.y * blockDim.y + threadIdx.y;
    if (out_x >= outCols || out_y >= outRows)
        return;

    int sum = 0;
    for (int ky = 0; ky < kRows; ++ky)
    {
        for (int kx = 0; kx < kCols; ++kx)
        {
            int in_row = out_y + ky;
            int in_col = out_x + kx;
            sum += input[in_row * cols + in_col] *
                   kernel[ky * kCols + kx];
        }
    }
    output[out_y * outCols + out_x] = sum;
}

// ---------- 共享内存优化并行卷积 ----------
#define TILE_Y 16
#define TILE_X 16

__global__ void conv2d_shared(const DataType *input, const DataType *kernel,
                              int rows, int cols, int kRows, int kCols,
                              DataType *output, int outRows, int outCols)
{
    // 动态共享内存，大小为 shm_h * shm_w
    extern __shared__ DataType shmem[];
    int tx = threadIdx.x;
    int ty = threadIdx.y;

    // 当前块负责的输出图块左上角坐标
    int base_x = blockIdx.x * TILE_X;
    int base_y = blockIdx.y * TILE_Y;

    // 当前线程负责的输出点坐标
    int out_x = base_x + tx;
    int out_y = base_y + ty;

    // 输入图块尺寸（包含卷积所需的 halos）
    int shm_h = TILE_Y + kRows - 1;
    int shm_w = TILE_X + kCols - 1;

    // ----- 阶段1：将当前输入图块加载到共享内存（所有线程协同）-----
    // 每个线程负责加载多个点，保证覆盖整个 shm_h x shm_w 区域
    for (int i = ty; i < shm_h; i += TILE_Y)
    {
        for (int j = tx; j < shm_w; j += TILE_X)
        {
            int in_y = base_y + i;
            int in_x = base_x + j;
            if (in_y >= 0 && in_y < rows && in_x >= 0 && in_x < cols)
            {
                shmem[i * shm_w + j] = input[in_y * cols + in_x];
            }
            else
            {
                shmem[i * shm_w + j] = 0; // 边界外填充0（VALID卷积实际不需要，但安全）
            }
        }
    }
    __syncthreads();

    // ----- 阶段2：卷积计算（仅当输出点有效时）-----
    if (out_x < outCols && out_y < outRows)
    {
        int sum = 0;
        for (int ky = 0; ky < kRows; ++ky)
        {
            for (int kx = 0; kx < kCols; ++kx)
            {
                // 当前输出点对应的输入窗口在共享内存中的偏移就是 (ty + ky, tx + kx)
                DataType in_val = shmem[(ty + ky) * shm_w + (tx + kx)];
                DataType ker_val = kernel[ky * kCols + kx];
                sum += in_val * ker_val;
            }
        }
        output[out_y * outCols + out_x] = sum;
    }
}

// ---------- 主机端封装函数 ----------
void conv2d_gpu(const DataType *h_input, const DataType *h_kernel,
                int rows, int cols, int kRows, int kCols,
                DataType *h_output, float &kernel_time_ms, bool use_shared)
{
    int outRows = rows - kRows + 1;
    int outCols = cols - kCols + 1;

    DataType *d_input, *d_kernel, *d_output;
    size_t input_size = rows * cols * sizeof(DataType);
    size_t kernel_size = kRows * kCols * sizeof(DataType);
    size_t output_size = outRows * outCols * sizeof(DataType);

    cudaMalloc(&d_input, input_size);
    cudaMalloc(&d_kernel, kernel_size);
    cudaMalloc(&d_output, output_size);

    cudaMemcpy(d_input, h_input, input_size, cudaMemcpyHostToDevice);
    cudaMemcpy(d_kernel, h_kernel, kernel_size, cudaMemcpyHostToDevice);

    dim3 block, grid;
    size_t shm_size = 0;

    if (use_shared)
    {
        block = dim3(TILE_X, TILE_Y);
        grid = dim3((outCols + TILE_X - 1) / TILE_X,
                    (outRows + TILE_Y - 1) / TILE_Y);
        int shm_h = TILE_Y + kRows - 1;
        int shm_w = TILE_X + kCols - 1;
        shm_size = shm_h * shm_w * sizeof(DataType);
    }
    else
    {
        block = dim3(16, 16);
        grid = dim3((outCols + block.x - 1) / block.x,
                    (outRows + block.y - 1) / block.y);
    }

    cudaEvent_t start, stop;
    cudaEventCreate(&start);
    cudaEventCreate(&stop);
    cudaEventRecord(start);

    if (use_shared)
    {
        conv2d_shared<<<grid, block, shm_size>>>(d_input, d_kernel,
                                                 rows, cols, kRows, kCols,
                                                 d_output, outRows, outCols);
    }
    else
    {
        conv2d_naive<<<grid, block>>>(d_input, d_kernel,
                                      rows, cols, kRows, kCols,
                                      d_output, outRows, outCols);
    }

    cudaEventRecord(stop);
    cudaEventSynchronize(stop);
    cudaEventElapsedTime(&kernel_time_ms, start, stop);

    cudaMemcpy(h_output, d_output, output_size, cudaMemcpyDeviceToHost);

    cudaFree(d_input);
    cudaFree(d_kernel);
    cudaFree(d_output);
    cudaEventDestroy(start);
    cudaEventDestroy(stop);
}

// ---------- 结果验证 ----------
bool verify(const DataType *ref, const DataType *res, int size)
{
    for (int i = 0; i < size; ++i)
    {
        if (ref[i] != res[i])
        {
            printf("Mismatch at %d: ref=%d, res=%d\n", i, ref[i], res[i]);
            return false;
        }
    }
    return true;
}

// ---------- 主函数 ----------
int main()
{
    // 配置参数
    int rows = 1024, cols = 1024;
    int kRows = 3, kCols = 3;
    int outRows = rows - kRows + 1;
    int outCols = cols - kCols + 1;

    printf("Input: %dx%d, Kernel: %dx%d, Output: %dx%d\n",
           rows, cols, kRows, kCols, outRows, outCols);

    // 分配主机内存
    std::vector<DataType> h_input(rows * cols);
    std::vector<DataType> h_kernel(kRows * kCols);
    std::vector<DataType> h_cpu_out(outRows * outCols);
    std::vector<DataType> h_naive_out(outRows * outCols);
    std::vector<DataType> h_shared_out(outRows * outCols);

    // 随机初始化（整数0-9）
    srand(12345);
    for (int i = 0; i < rows * cols; ++i)
        h_input[i] = rand() % 10;
    for (int i = 0; i < kRows * kCols; ++i)
        h_kernel[i] = rand() % 5;

    // CPU 串行
    auto cpu_start = std::chrono::high_resolution_clock::now();
    conv2d_serial(h_input.data(), h_kernel.data(),
                  rows, cols, kRows, kCols, h_cpu_out.data());
    auto cpu_end = std::chrono::high_resolution_clock::now();
    double cpu_time_ms = std::chrono::duration<double, std::milli>(cpu_end - cpu_start).count();
    printf("CPU serial time: %.3f ms\n", cpu_time_ms);

    // GPU 朴素版本
    float naive_time_ms;
    conv2d_gpu(h_input.data(), h_kernel.data(),
               rows, cols, kRows, kCols, h_naive_out.data(), naive_time_ms, false);
    printf("GPU naive time: %.3f ms\n", naive_time_ms);
    if (verify(h_cpu_out.data(), h_naive_out.data(), outRows * outCols))
        printf("Naive verification: PASS\n");
    else
        printf("Naive verification: FAIL\n");

    // GPU 共享内存版本
    float shared_time_ms;
    conv2d_gpu(h_input.data(), h_kernel.data(),
               rows, cols, kRows, kCols, h_shared_out.data(), shared_time_ms, true);
    printf("GPU shared memory time: %.3f ms\n", shared_time_ms);
    if (verify(h_cpu_out.data(), h_shared_out.data(), outRows * outCols))
        printf("Shared verification: PASS\n");
    else
        printf("Shared verification: FAIL\n");

    // 加速比
    printf("\nSpeedup (CPU/Naive): %.2f\n", cpu_time_ms / naive_time_ms);
    printf("Speedup (CPU/Shared): %.2f\n", cpu_time_ms / shared_time_ms);
    printf("Speedup (Naive/Shared): %.2f\n", naive_time_ms / shared_time_ms);

    return 0;
}