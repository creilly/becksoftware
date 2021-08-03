#pragma once
#include "buffer.h"

typedef struct {
	float64 amplitude;
	float64 frequency;
	float64 phase;
	FloatBuffer buffer;
	IntBuffer zeros;
} Sinusoid;

Sinusoid create_sinusoid(float64 amplitude, float64 frequency, int32 buffer_size, int32 zeros_size);
int format_sinusoid_state(Sinusoid sinusoid, char str_buffer[], int buffer_size);
int copy_string(char target[], char source[], int offset);