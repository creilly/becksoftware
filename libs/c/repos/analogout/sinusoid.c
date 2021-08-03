#include "sinusoid.h"
#include <string.h>
#include <stdio.h>

Sinusoid create_sinusoid(float64 amplitude, float64 frequency, int32 buffer_size, int32 zeros_size) {
	Sinusoid sinusoid;
	sinusoid.amplitude = amplitude;
	sinusoid.frequency = frequency;
	sinusoid.phase = 0.0;
	sinusoid.buffer = create_float_buffer(buffer_size);
	sinusoid.zeros = create_int_buffer(zeros_size);
	for (int i = 0; i < zeros_size; i++) {
		sinusoid.zeros.data[i] = -1;
	}
	return sinusoid;
}

// warning: doesn't handle overflow
int format_sinusoid_state(Sinusoid sinusoid, char str_buffer[], int buffer_size)
{
	int length = 0;
	char tmp_buffer[512];
	int32 data[] = {
		sinusoid.buffer.write_offset,
		sinusoid.buffer.read_offset,
		sinusoid.zeros.write_offset,
		sinusoid.zeros.read_offset,
	};
	char* lines[] = {
		"buffer write offset",
		"buffer read offset",
		"zeros write offset",
		"zeros read offset"
	};
	length = copy_string(str_buffer, "sinusoid state:\n", length);
	for (int i = 0; i < 4; i++) {
		sprintf_s(tmp_buffer, 512, "\t%s\t:\t%d\n", lines[i], data[i]);
		length = copy_string(str_buffer, tmp_buffer, length);
	}
	return length;
}

int copy_string(char target[], char source[], int offset) {
	int i;
	for (i = 0; i < strlen(source); i++) {
		target[offset + i] = source[i];
	}
	target[offset + i] = '\0';
	return offset + i;
}