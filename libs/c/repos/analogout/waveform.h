#pragma once
#include "buffer.h"

typedef struct {
	uInt64 offset;
	FloatBuffer voltage_buffer;
	FloatBuffer phase_buffer;
	float64 voltage;
	float64 phase;
	int32 averaging;
	int32 averaging_counter;
} Waveform;

Waveform create_waveform(int32 buffer_size, int32 averaging);

void update_waveform(Waveform* wf_add, float64 phase, float64 voltage);
