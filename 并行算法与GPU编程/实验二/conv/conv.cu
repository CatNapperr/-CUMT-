#include <cuda_runtime.h>
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <chrono>

// 定义数据类型
typedef float real;

// ==================== 卷积参数结构体 ====================
typedef struct
{
    int batch;              // 批量大小（本示例固定为1，简化处理）
    int in_c;               // 输入通道数
    int in_h, in_w;         // 输入特征图高宽
    int out_c;              // 输出通道数
    int kernel_h, kernel_w; // 卷积核高宽（通常相等，为正方形）
    int stride_h, stride_w; // 步长（本示例固定为1）
} ConvParams;

// 输出尺寸计算公式（VALID卷积）
inline void calc_output_size(const ConvParams &p, int &out_h, int &out_w)
{
    out_h = (p.in_h - p.kernel_h) / p.stride_h + 1;
    out_w = (p.in_w - p.kernel_w) / p.stride_w + 1;
}

// ==================== 朴素卷积核（全局内存直接访问） ====================
// 每个线程负责计算一个输出点（out_c, out_h, out_w）
// 需要遍历所有输入通道和卷积核窗口
__global__ void conv_naive(const real *input, const real *kernel, real *output,
                           int in_c, int in_h, int in_w,
                           int out_c, int kernel_h, int kernel_w,
                           int out_h, int out_w)
{
    // 输出索引
    int out_x = blockIdx.x * blockDim.x + threadIdx.x; // 输出宽度方向
    int out_y = blockIdx.y * blockDim.y + threadIdx.y; // 输出高度方向
    int out_chan = blockIdx.z;                         // 输出通道

    if (out_x >= out_w || out_y >= out_h || out_chan >= out_c)
        return;

    // 计算输入起始坐标（stride=1）
    int in_start_x = out_x;
    int in_start_y = out_y;

    real sum = 0.0f;
    // 遍历输入通道和卷积核
    for (int ic = 0; ic < in_c; ++ic)
    {
        for (int ky = 0; ky < kernel_h; ++ky)
        {
            for (int kx = 0; kx < kernel_w; ++kx)
            {
                int in_x = in_start_x + kx;
                int in_y = in_start_y + ky;
                // 输入索引: [ic][in_y][in_x] (行主序)
                int in_idx = ic * in_h * in_w + in_y * in_w + in_x;
                // 卷积核索引: [out_chan][ic][ky][kx]
                int kernel_idx = out_chan * in_c * kernel_h * kernel_w +
                                 ic * kernel_h * kernel_w + ky * kernel_w + kx;
                sum += input[in_idx] * kernel[kernel_idx];
            }
        }
    }
    // 输出索引: [out_chan][out_y][out_x]
    int out_idx = out_chan * out_h * out_w + out_y * out_w + out_x;
    output[out_idx] = sum;
}

// ==================== 共享内存优化卷积核 ====================
// 将输入的一个图块（包含halo区域）加载到共享内存，减少全局内存访问
// 每个线程块负责计算一个输出图块（TILE_Y x TILE_X），共享内存装载相应的输入块
#define TILE_Y 16 // 输出图块高度
#define TILE_X 16 // 输出图块宽度

__global__ void conv_shared(const real *input, const real *kernel, real *output,
                            int in_c, int in_h, int in_w,
                            int out_c, int kernel_h, int kernel_w,
                            int out_h, int out_w)
{
    extern __shared__ real shmem[];
    int tx = threadIdx.x;
    int ty = threadIdx.y;

    // 当前线程块负责的输出图块起始坐标（左上角）
    int base_x = blockIdx.x * TILE_X;
    int base_y = blockIdx.y * TILE_Y;

    // 当前线程负责的输出点坐标
    int out_x = base_x + tx;
    int out_y = base_y + ty;
    int out_chan = blockIdx.z;

    // 通道越界直接返回（通道与块索引绑定，块内所有线程同通道）
    if (out_chan >= out_c)
        return;

    // 共享内存图块尺寸（包含卷积核半径的halo）
    int shm_h = TILE_Y + kernel_h - 1;
    int shm_w = TILE_X + kernel_w - 1;

    real sum = 0.0f;

    // 遍历所有输入通道
    for (int ic = 0; ic < in_c; ++ic)
    {
        // ----- 阶段1：将当前通道的输入图块加载到共享内存 -----
        // 每个线程负责加载多个点（步长为 TILE_Y, TILE_X），保证覆盖整个 shm_h x shm_w
        for (int i = ty; i < shm_h; i += TILE_Y)
        {
            for (int j = tx; j < shm_w; j += TILE_X)
            {
                int in_y = base_y + i; // 全局输入行坐标
                int in_x = base_x + j; // 全局输入列坐标
                if (in_y >= 0 && in_y < in_h && in_x >= 0 && in_x < in_w)
                {
                    int in_idx = ic * in_h * in_w + in_y * in_w + in_x;
                    shmem[i * shm_w + j] = input[in_idx];
                }
                else
                {
                    // 边界外填充0（VALID卷积不会访问到有效区域外，但为安全置0）
                    shmem[i * shm_w + j] = 0.0f;
                }
            }
        }
        __syncthreads();

        // ----- 阶段2：计算卷积（仅当输出点有效时）-----
        if (out_x < out_w && out_y < out_h)
        {
            for (int ky = 0; ky < kernel_h; ++ky)
            {
                for (int kx = 0; kx < kernel_w; ++kx)
                {
                    // 当前卷积窗口对应共享内存中的位置：
                    // 因为共享内存存储的是以(base_y, base_x)为起点的输入图块，
                    // 而当前输出点(out_y, out_x)对应的输入窗口左上角就是(out_y, out_x)，
                    // 它的共享内存坐标就是 (ty + ky, tx + kx)
                    int shm_y = ty + ky;
                    int shm_x = tx + kx;
                    real in_val = shmem[shm_y * shm_w + shm_x];
                    int kernel_idx = out_chan * in_c * kernel_h * kernel_w +
                                     ic * kernel_h * kernel_w + ky * kernel_w + kx;
                    sum += in_val * kernel[kernel_idx];
                }
            }
        }
        __syncthreads(); // 确保下次加载新通道前共享内存已使用完毕
    }

    // 写入输出（仅当输出点有效）
    if (out_x < out_w && out_y < out_h)
    {
        int out_idx = out_chan * out_h * out_w + out_y * out_w + out_x;
        output[out_idx] = sum;
    }
}

// ==================== 主机端封装函数 ====================
void convolution_gpu(const real *h_input, const real *h_kernel, real *h_output,
                     const ConvParams &p, float &kernel_time_ms, bool use_shared = true)
{
    real *d_input, *d_kernel, *d_output;
    int out_h, out_w;
    calc_output_size(p, out_h, out_w);

    size_t input_size = p.batch * p.in_c * p.in_h * p.in_w * sizeof(real);
    size_t kernel_size = p.out_c * p.in_c * p.kernel_h * p.kernel_w * sizeof(real);
    size_t output_size = p.batch * p.out_c * out_h * out_w * sizeof(real);

    // 分配设备内存
    cudaMalloc(&d_input, input_size);
    cudaMalloc(&d_kernel, kernel_size);
    cudaMalloc(&d_output, output_size);

    // 拷贝到设备
    cudaMemcpy(d_input, h_input, input_size, cudaMemcpyHostToDevice);
    cudaMemcpy(d_kernel, h_kernel, kernel_size, cudaMemcpyHostToDevice);

    // 配置内核
    dim3 block, grid;
    size_t shm_size = 0;

    if (use_shared)
    {
        // 共享内存版本：每个block计算 TILE_Y x TILE_X 个输出点
        block = dim3(TILE_X, TILE_Y);
        grid = dim3((out_w + TILE_X - 1) / TILE_X,
                    (out_h + TILE_Y - 1) / TILE_Y,
                    p.out_c);
        int shm_h = TILE_Y + p.kernel_h - 1;
        int shm_w = TILE_X + p.kernel_w - 1;
        shm_size = shm_h * shm_w * sizeof(real);
    }
    else
    {
        // 朴素版本：每个线程一个输出点
        block = dim3(16, 16); // 256线程/块
        grid = dim3((out_w + block.x - 1) / block.x,
                    (out_h + block.y - 1) / block.y,
                    p.out_c);
    }

    cudaEvent_t start, stop;
    cudaEventCreate(&start);
    cudaEventCreate(&stop);
    cudaEventRecord(start);

    if (use_shared)
    {
        conv_shared<<<grid, block, shm_size>>>(d_input, d_kernel, d_output,
                                               p.in_c, p.in_h, p.in_w,
                                               p.out_c, p.kernel_h, p.kernel_w,
                                               out_h, out_w);
    }
    else
    {
        conv_naive<<<grid, block>>>(d_input, d_kernel, d_output,
                                    p.in_c, p.in_h, p.in_w,
                                    p.out_c, p.kernel_h, p.kernel_w,
                                    out_h, out_w);
    }

    cudaEventRecord(stop);
    cudaEventSynchronize(stop);
    cudaEventElapsedTime(&kernel_time_ms, start, stop);

    // 拷贝结果回主机
    cudaMemcpy(h_output, d_output, output_size, cudaMemcpyDeviceToHost);

    cudaFree(d_input);
    cudaFree(d_kernel);
    cudaFree(d_output);
    cudaEventDestroy(start);
    cudaEventDestroy(stop);
}

// ==================== CPU串行卷积（用于验证） ====================
void conv_cpu(const real *input, const real *kernel, real *output,
              const ConvParams &p)
{
    int out_h, out_w;
    calc_output_size(p, out_h, out_w);

    for (int oc = 0; oc < p.out_c; ++oc)
    {
        for (int oy = 0; oy < out_h; ++oy)
        {
            for (int ox = 0; ox < out_w; ++ox)
            {
                real sum = 0.0f;
                for (int ic = 0; ic < p.in_c; ++ic)
                {
                    for (int ky = 0; ky < p.kernel_h; ++ky)
                    {
                        for (int kx = 0; kx < p.kernel_w; ++kx)
                        {
                            int in_y = oy + ky;
                            int in_x = ox + kx;
                            int in_idx = ic * p.in_h * p.in_w + in_y * p.in_w + in_x;
                            int kernel_idx = oc * p.in_c * p.kernel_h * p.kernel_w +
                                             ic * p.kernel_h * p.kernel_w + ky * p.kernel_w + kx;
                            sum += input[in_idx] * kernel[kernel_idx];
                        }
                    }
                }
                int out_idx = oc * out_h * out_w + oy * out_w + ox;
                output[out_idx] = sum;
            }
        }
    }
}

// ==================== 结果验证 ====================
bool verify(const real *cpu_out, const real *gpu_out, int size, real eps = 1e-5)
{
    for (int i = 0; i < size; ++i)
    {
        if (fabs(cpu_out[i] - gpu_out[i]) > eps)
        {
            printf("Mismatch at %d: cpu=%f, gpu=%f\n", i, cpu_out[i], gpu_out[i]);
            return false;
        }
    }
    return true;
}

// ==================== 主函数 ====================
int main()
{
    // 定义卷积参数
    ConvParams p;
    p.batch = 1;
    p.in_c = 3; // RGB输入
    p.in_h = 224;
    p.in_w = 224;
    p.out_c = 64;
    p.kernel_h = 3;
    p.kernel_w = 3;
    p.stride_h = 1;
    p.stride_w = 1;

    int out_h, out_w;
    calc_output_size(p, out_h, out_w);
    printf("Input: %dx%dx%d, Kernel: %dx%d, Output: %dx%dx%d\n",
           p.in_c, p.in_h, p.in_w, p.kernel_h, p.kernel_w, p.out_c, out_h, out_w);

    // 分配主机内存
    size_t input_size = p.batch * p.in_c * p.in_h * p.in_w * sizeof(real);
    size_t kernel_size = p.out_c * p.in_c * p.kernel_h * p.kernel_w * sizeof(real);
    size_t output_size = p.batch * p.out_c * out_h * out_w * sizeof(real);

    real *h_input = (real *)malloc(input_size);
    real *h_kernel = (real *)malloc(kernel_size);
    real *h_cpu_out = (real *)malloc(output_size);
    real *h_gpu_naive = (real *)malloc(output_size);
    real *h_gpu_shared = (real *)malloc(output_size);

    // 随机初始化输入和卷积核
    srand(12345);
    for (size_t i = 0; i < input_size / sizeof(real); ++i)
        h_input[i] = rand() / (real)RAND_MAX;
    for (size_t i = 0; i < kernel_size / sizeof(real); ++i)
        h_kernel[i] = rand() / (real)RAND_MAX;

    // CPU串行计算（作为基准）
    auto cpu_start = std::chrono::high_resolution_clock::now();
    conv_cpu(h_input, h_kernel, h_cpu_out, p);
    auto cpu_end = std::chrono::high_resolution_clock::now();
    double cpu_time_ms = std::chrono::duration<double, std::milli>(cpu_end - cpu_start).count();
    printf("CPU time: %.3f ms\n", cpu_time_ms);

    // GPU 朴素版本
    float naive_time_ms;
    convolution_gpu(h_input, h_kernel, h_gpu_naive, p, naive_time_ms, false);
    printf("GPU naive time: %.3f ms\n", naive_time_ms);
    bool ok_naive = verify(h_cpu_out, h_gpu_naive, output_size / sizeof(real));
    printf("Naive verification: %s\n", ok_naive ? "PASS" : "FAIL");

    // GPU 共享内存优化版本
    float shared_time_ms;
    convolution_gpu(h_input, h_kernel, h_gpu_shared, p, shared_time_ms, true);
    printf("GPU shared memory time: %.3f ms\n", shared_time_ms);
    bool ok_shared = verify(h_cpu_out, h_gpu_shared, output_size / sizeof(real));
    printf("Shared verification: %s\n", ok_shared ? "PASS" : "FAIL");

    // 加速比
    printf("\nSpeedup (CPU/Naive): %.2f\n", cpu_time_ms / naive_time_ms);
    printf("Speedup (CPU/Shared): %.2f\n", cpu_time_ms / shared_time_ms);

    // 释放内存
    free(h_input);
    free(h_kernel);
    free(h_cpu_out);
    free(h_gpu_naive);
    free(h_gpu_shared);

    return 0;
}