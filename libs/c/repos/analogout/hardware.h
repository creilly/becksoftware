#pragma once
#include "sinusoid.h"
#include "waveform.h"
#include "list.h"

#define PI	3.1415926535

#define MOD_INDEX 0
#define SCAN_INDEX 1

int32 set_trigger();
int32 create_input_task(TaskHandle* taskHandle, float64 buffer_time, float64* sampling_rate_add, uInt32* timebase_divisor_add);
int32 create_output_task(TaskHandle* task_add, float64 buffer_time, float64 sampling_rate, uInt32 timebase_divisor);
int32 read_from_input(TaskHandle taskHandle, Waveform* waveforms[], Sinusoid* sinusoids[], client_queue* client_queues[], int32 nSinusoids, float64* data, int32 size);
int32 write_to_output(TaskHandle taskHandle, int32 samples, Sinusoid* sinusoids[], int32 nSinusoids, float64 sampling_rate, uInt64* samples_written);
int32 get_buffer_gap(TaskHandle taskHandle, uInt64 samples_written, float64 sampling_rate, float64 reaction_time, int32* buffer_gap_add);