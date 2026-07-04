#define _CRT_SECURE_NO_WARNINGS

#include <windows.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define IMAGE_CHANNELS 1
#define DEFAULT_INPUT_PRIMARY "lena_grey.bmp"
#define DEFAULT_INPUT_FALLBACK "lena_gray.bmp"
#define DEFAULT_SERIAL_OUTPUT "lena_gray_serial.bmp"
#define DEFAULT_PARALLEL_OUTPUT "lena_gray_parallel.bmp"

#pragma pack(push, 1)
typedef struct
{
    uint16_t bfType;
    uint32_t bfSize;
    uint16_t bfReserved1;
    uint16_t bfReserved2;
    uint32_t bfOffBits;
} BmpFileHeader;

typedef struct
{
    uint32_t biSize;
    int32_t biWidth;
    int32_t biHeight;
    uint16_t biPlanes;
    uint16_t biBitCount;
    uint32_t biCompression;
    uint32_t biSizeImage;
    int32_t biXPelsPerMeter;
    int32_t biYPelsPerMeter;
    uint32_t biClrUsed;
    uint32_t biClrImportant;
} BmpInfoHeader;
#pragma pack(pop)

typedef struct
{
    int width;
    int height;
    int channels;
    uint8_t *pixels;
} Image;

typedef struct
{
    const uint8_t *padded;
    uint8_t *output;
    int width;
    int height;
    int padded_width;
    int row_begin;
    int row_end;
} WorkerArgs;

static const int kLaplacianKernel[3][3] = {
    {-1, -1, -1},
    {-1, 8, -1},
    {-1, -1, -1}};

static void free_image(Image *image)
{
    if (image == NULL)
    {
        return;
    }
    free(image->pixels);
    image->pixels = NULL;
    image->width = 0;
    image->height = 0;
    image->channels = 0;
}

static int default_thread_count(void)
{
    SYSTEM_INFO info;
    GetSystemInfo(&info);
    return info.dwNumberOfProcessors > 0 ? (int)info.dwNumberOfProcessors : 1;
}

static double elapsed_ms(LARGE_INTEGER start, LARGE_INTEGER end, LARGE_INTEGER frequency)
{
    return (double)(end.QuadPart - start.QuadPart) * 1000.0 / (double)frequency.QuadPart;
}

static uint8_t clamp_byte(int value)
{
    if (value < 0)
    {
        return 0;
    }
    if (value > 255)
    {
        return 255;
    }
    return (uint8_t)value;
}

static int read_bmp_image_impl(const char *path, Image *image, int quiet)
{
    FILE *file = NULL;
    BmpFileHeader file_header;
    BmpInfoHeader info_header;
    uint8_t *pixels = NULL;
    uint8_t *row_buffer = NULL;
    int width;
    int height;
    int top_down;
    size_t file_row_bytes;
    size_t pixel_bytes;
    int file_row;
    int dst_row;
    int status = -1;

    memset(image, 0, sizeof(*image));

    file = fopen(path, "rb");
    if (file == NULL)
    {
        if (!quiet)
        {
            fprintf(stderr, "Failed to open input file: %s\n", path);
        }
        return -1;
    }

    if (fread(&file_header, sizeof(file_header), 1, file) != 1 ||
        fread(&info_header, sizeof(info_header), 1, file) != 1)
    {
        if (!quiet)
        {
            fprintf(stderr, "Failed to read BMP headers from %s\n", path);
        }
        goto cleanup;
    }

    if (file_header.bfType != 0x4D42 ||
        info_header.biSize != 40 ||
        info_header.biPlanes != 1 ||
        info_header.biCompression != 0 ||
        info_header.biBitCount != IMAGE_CHANNELS * 8)
    {
        if (!quiet)
        {
            fprintf(stderr, "Unsupported BMP format in %s\n", path);
        }
        goto cleanup;
    }

    width = info_header.biWidth;
    height = info_header.biHeight < 0 ? -info_header.biHeight : info_header.biHeight;
    top_down = info_header.biHeight < 0;
    if (width <= 0 || height <= 0)
    {
        if (!quiet)
        {
            fprintf(stderr, "Invalid image dimensions in %s\n", path);
        }
        goto cleanup;
    }

    file_row_bytes = (((size_t)width * IMAGE_CHANNELS + 3u) / 4u) * 4u;
    pixel_bytes = (size_t)width * (size_t)height * IMAGE_CHANNELS;
    pixels = (uint8_t *)malloc(pixel_bytes);
    row_buffer = (uint8_t *)malloc(file_row_bytes);
    if (pixels == NULL || row_buffer == NULL)
    {
        if (!quiet)
        {
            fprintf(stderr, "Out of memory while loading %s\n", path);
        }
        goto cleanup;
    }

    if (fseek(file, (long)file_header.bfOffBits, SEEK_SET) != 0)
    {
        if (!quiet)
        {
            fprintf(stderr, "Failed to seek BMP pixel data in %s\n", path);
        }
        goto cleanup;
    }

    for (file_row = 0; file_row < height; ++file_row)
    {
        if (fread(row_buffer, 1, file_row_bytes, file) != file_row_bytes)
        {
            if (!quiet)
            {
                fprintf(stderr, "Failed to read BMP pixel data from %s\n", path);
            }
            goto cleanup;
        }

        dst_row = top_down ? file_row : (height - 1 - file_row);
        memcpy(pixels + (size_t)dst_row * (size_t)width * IMAGE_CHANNELS,
               row_buffer,
               (size_t)width * IMAGE_CHANNELS);
    }

    image->width = width;
    image->height = height;
    image->channels = IMAGE_CHANNELS;
    image->pixels = pixels;
    pixels = NULL;
    status = 0;

cleanup:
    free(row_buffer);
    free(pixels);
    fclose(file);
    return status;
}

static int read_bmp_image(const char *path, Image *image)
{
    return read_bmp_image_impl(path, image, 0);
}

static int try_read_bmp_image(const char *path, Image *image)
{
    return read_bmp_image_impl(path, image, 1);
}

static int write_bmp_image(const char *path, const Image *image)
{
    FILE *file = NULL;
    BmpFileHeader file_header;
    BmpInfoHeader info_header;
    uint8_t palette[1024];
    uint8_t *row_buffer = NULL;
    size_t row_bytes;
    size_t image_bytes;
    int i;
    int src_row;
    int status = -1;

    file = fopen(path, "wb");
    if (file == NULL)
    {
        fprintf(stderr, "Failed to open output file: %s\n", path);
        return -1;
    }

    row_bytes = (((size_t)image->width * IMAGE_CHANNELS + 3u) / 4u) * 4u;
    image_bytes = row_bytes * (size_t)image->height;

    memset(&file_header, 0, sizeof(file_header));
    memset(&info_header, 0, sizeof(info_header));
    file_header.bfType = 0x4D42;
    file_header.bfOffBits = 54u + 1024u;
    file_header.bfSize = (uint32_t)(file_header.bfOffBits + image_bytes);

    info_header.biSize = 40u;
    info_header.biWidth = image->width;
    info_header.biHeight = image->height;
    info_header.biPlanes = 1;
    info_header.biBitCount = IMAGE_CHANNELS * 8;
    info_header.biCompression = 0;
    info_header.biSizeImage = (uint32_t)image_bytes;
    info_header.biXPelsPerMeter = 2835;
    info_header.biYPelsPerMeter = 2835;
    info_header.biClrUsed = 256;
    info_header.biClrImportant = 256;

    if (fwrite(&file_header, sizeof(file_header), 1, file) != 1 ||
        fwrite(&info_header, sizeof(info_header), 1, file) != 1)
    {
        fprintf(stderr, "Failed to write BMP headers to %s\n", path);
        goto cleanup;
    }

    for (i = 0; i < 256; ++i)
    {
        palette[i * 4 + 0] = (uint8_t)i;
        palette[i * 4 + 1] = (uint8_t)i;
        palette[i * 4 + 2] = (uint8_t)i;
        palette[i * 4 + 3] = 0;
    }

    if (fwrite(palette, sizeof(palette), 1, file) != 1)
    {
        fprintf(stderr, "Failed to write grayscale palette to %s\n", path);
        goto cleanup;
    }

    row_buffer = (uint8_t *)calloc(1, row_bytes);
    if (row_buffer == NULL)
    {
        fprintf(stderr, "Out of memory while writing %s\n", path);
        goto cleanup;
    }

    for (src_row = image->height - 1; src_row >= 0; --src_row)
    {
        memcpy(row_buffer,
               image->pixels + (size_t)src_row * (size_t)image->width * IMAGE_CHANNELS,
               (size_t)image->width * IMAGE_CHANNELS);
        if (fwrite(row_buffer, 1, row_bytes, file) != row_bytes)
        {
            fprintf(stderr, "Failed to write BMP pixel data to %s\n", path);
            goto cleanup;
        }
    }

    status = 0;

cleanup:
    free(row_buffer);
    fclose(file);
    return status;
}

static uint8_t *make_padded_image(const Image *image, int *padded_width)
{
    int width = image->width + 2;
    int height = image->height + 2;
    size_t total_bytes = (size_t)width * (size_t)height * IMAGE_CHANNELS;
    uint8_t *padded = (uint8_t *)calloc(total_bytes, 1);
    int row;

    if (padded == NULL)
    {
        return NULL;
    }

    for (row = 0; row < image->height; ++row)
    {
        memcpy(padded + ((size_t)(row + 1) * (size_t)width + 1u) * IMAGE_CHANNELS,
               image->pixels + (size_t)row * (size_t)image->width * IMAGE_CHANNELS,
               (size_t)image->width * IMAGE_CHANNELS);
    }

    *padded_width = width;
    return padded;
}

static void convolve_rows(const uint8_t *padded,
                          uint8_t *output,
                          int width,
                          int height,
                          int padded_width,
                          int row_begin,
                          int row_end)
{
    int y;
    int x;
    int channel;
    int ky;
    int kx;
    (void)height;
    for (y = row_begin; y < row_end; ++y)
    {
        for (x = 0; x < width; ++x)
        {
            for (channel = 0; channel < IMAGE_CHANNELS; ++channel)
            {
                int sum = 0;
                for (ky = 0; ky < 3; ++ky)
                {
                    const uint8_t *src_row = padded + ((size_t)(y + ky) * (size_t)padded_width + (size_t)x) * IMAGE_CHANNELS;
                    for (kx = 0; kx < 3; ++kx)
                    {
                        sum += kLaplacianKernel[ky][kx] * src_row[kx * IMAGE_CHANNELS + channel];
                    }
                }
                if (sum < 0)
                {
                    sum = -sum;
                }
                output[((size_t)y * (size_t)width + (size_t)x) * IMAGE_CHANNELS + channel] = clamp_byte(sum);
            }
        }
    }
}

static void *worker_main(void *arg)
{
    WorkerArgs *worker = (WorkerArgs *)arg;
    convolve_rows(worker->padded,
                  worker->output,
                  worker->width,
                  worker->height,
                  worker->padded_width,
                  worker->row_begin,
                  worker->row_end);
    return NULL;
}

static int run_parallel(const uint8_t *padded,
                        uint8_t *output,
                        int width,
                        int height,
                        int padded_width,
                        int thread_count)
{
    pthread_t *threads = NULL;
    WorkerArgs *args = NULL;
    int status = -1;
    int failed = 0;
    int base_rows;
    int remainder;
    int row_begin;
    int i;
    int rows;

    if (thread_count < 1)
    {
        thread_count = 1;
    }
    if (thread_count > height)
    {
        thread_count = height;
    }

    threads = (pthread_t *)malloc((size_t)thread_count * sizeof(*threads));
    args = (WorkerArgs *)malloc((size_t)thread_count * sizeof(*args));
    if (threads == NULL || args == NULL)
    {
        fprintf(stderr, "Out of memory while creating worker threads\n");
        goto cleanup;
    }

    base_rows = height / thread_count;
    remainder = height % thread_count;
    row_begin = 0;
    for (i = 0; i < thread_count; ++i)
    {
        rows = base_rows + (i < remainder ? 1 : 0);
        args[i].padded = padded;
        args[i].output = output;
        args[i].width = width;
        args[i].height = height;
        args[i].padded_width = padded_width;
        args[i].row_begin = row_begin;
        args[i].row_end = row_begin + rows;

        if (pthread_create(&threads[i], NULL, worker_main, &args[i]) != 0)
        {
            fprintf(stderr, "Failed to create pthread worker %d\n", i);
            failed = 1;
            thread_count = i;
            goto join_and_cleanup;
        }

        row_begin += rows;
    }

join_and_cleanup:
    for (i = 0; i < thread_count; ++i)
    {
        pthread_join(threads[i], NULL);
    }
    status = failed ? -1 : 0;

cleanup:
    free(threads);
    free(args);
    return status;
}

static int compare_buffers(const uint8_t *lhs, const uint8_t *rhs, size_t byte_count, size_t *mismatch_index)
{
    size_t i;
    for (i = 0; i < byte_count; ++i)
    {
        if (lhs[i] != rhs[i])
        {
            if (mismatch_index != NULL)
            {
                *mismatch_index = i;
            }
            return 0;
        }
    }
    if (mismatch_index != NULL)
    {
        *mismatch_index = (size_t)-1;
    }
    return 1;
}

static void print_usage(const char *program_name)
{
    printf("Usage: %s [input.bmp] [threads] [serial_out.bmp] [parallel_out.bmp]\n", program_name);
    printf("Default input is %s.\n", DEFAULT_INPUT_PRIMARY);
}

int main(int argc, char **argv)
{
    const char *input_path = NULL;
    const char *serial_output_path = NULL;
    const char *parallel_output_path = NULL;
    Image source;
    Image serial_image;
    Image parallel_image;
    uint8_t *padded = NULL;
    int padded_width = 0;
    int thread_count;
    double serial_ms;
    double parallel_ms;
    LARGE_INTEGER frequency;
    LARGE_INTEGER start;
    LARGE_INTEGER end;
    size_t byte_count;
    size_t mismatch_index;
    int match;

    if (argc > 1 && (strcmp(argv[1], "-h") == 0 || strcmp(argv[1], "--help") == 0))
    {
        print_usage(argv[0]);
        return 0;
    }

    if (argc == 1)
    {
        if (try_read_bmp_image(DEFAULT_INPUT_PRIMARY, &source) == 0)
        {
            input_path = DEFAULT_INPUT_PRIMARY;
        }
        else if (try_read_bmp_image(DEFAULT_INPUT_FALLBACK, &source) == 0)
        {
            input_path = DEFAULT_INPUT_FALLBACK;
        }
        else
        {
            fprintf(stderr, "Failed to open default input files: %s or %s\n", DEFAULT_INPUT_PRIMARY, DEFAULT_INPUT_FALLBACK);
            return 1;
        }
    }
    else
    {
        input_path = argv[1];
        if (read_bmp_image(input_path, &source) != 0)
        {
            return 1;
        }
    }

    thread_count = (argc > 2) ? atoi(argv[2]) : default_thread_count();
    serial_output_path = (argc > 3) ? argv[3] : DEFAULT_SERIAL_OUTPUT;
    parallel_output_path = (argc > 4) ? argv[4] : DEFAULT_PARALLEL_OUTPUT;

    padded = make_padded_image(&source, &padded_width);
    if (padded == NULL)
    {
        fprintf(stderr, "Failed to allocate padded image\n");
        free_image(&source);
        return 1;
    }

    serial_image.width = source.width;
    serial_image.height = source.height;
    serial_image.channels = source.channels;
    serial_image.pixels = (uint8_t *)malloc((size_t)source.width * (size_t)source.height * source.channels);
    parallel_image.width = source.width;
    parallel_image.height = source.height;
    parallel_image.channels = source.channels;
    parallel_image.pixels = (uint8_t *)malloc((size_t)source.width * (size_t)source.height * source.channels);
    if (serial_image.pixels == NULL || parallel_image.pixels == NULL)
    {
        fprintf(stderr, "Failed to allocate output buffers\n");
        free(padded);
        free_image(&source);
        free_image(&serial_image);
        free_image(&parallel_image);
        return 1;
    }

    QueryPerformanceFrequency(&frequency);

    QueryPerformanceCounter(&start);
    convolve_rows(padded, serial_image.pixels, source.width, source.height, padded_width, 0, source.height);
    QueryPerformanceCounter(&end);
    serial_ms = elapsed_ms(start, end, frequency);

    QueryPerformanceCounter(&start);
    if (run_parallel(padded, parallel_image.pixels, source.width, source.height, padded_width, thread_count) != 0)
    {
        free(padded);
        free_image(&source);
        free_image(&serial_image);
        free_image(&parallel_image);
        return 1;
    }
    QueryPerformanceCounter(&end);
    parallel_ms = elapsed_ms(start, end, frequency);

    if (write_bmp_image(serial_output_path, &serial_image) != 0 ||
        write_bmp_image(parallel_output_path, &parallel_image) != 0)
    {
        free(padded);
        free_image(&source);
        free_image(&serial_image);
        free_image(&parallel_image);
        return 1;
    }

    byte_count = (size_t)source.width * (size_t)source.height * source.channels;
    match = compare_buffers(serial_image.pixels, parallel_image.pixels, byte_count, &mismatch_index);

    printf("Input: %s\n", input_path);
    printf("Image: %dx%d, %d channel(s)\n", source.width, source.height, source.channels);
    printf("Threads: %d\n", thread_count > 0 ? thread_count : 1);
    printf("Serial time: %.3f ms\n", serial_ms);
    printf("Parallel time: %.3f ms\n", parallel_ms);
    if (parallel_ms > 0.0)
    {
        printf("Speedup: %.3fx\n", serial_ms / parallel_ms);
    }
    else
    {
        printf("Speedup: inf\n");
    }

    if (match)
    {
        printf("Verification: serial and parallel outputs are identical.\n");
    }
    else
    {
        printf("Verification: mismatch at byte %lu.\n", (unsigned long)mismatch_index);
    }

    free(padded);
    free_image(&source);
    free_image(&serial_image);
    free_image(&parallel_image);
    return match ? 0 : 2;
}