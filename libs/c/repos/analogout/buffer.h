#pragma once
#include <NIDAQmx.h>
typedef struct {
	float64*	data;
	int32		size;
	int32		read_offset;
	int32		write_offset;
} FloatBuffer;

typedef struct {
	uInt64*		data;
	int32		size;
	int32		read_offset;
	int32		write_offset;
} IntBuffer;

FloatBuffer create_float_buffer(int32 size);
IntBuffer create_int_buffer(int32 size);
void add_to_float_buffer(FloatBuffer* buffer, float64 datum);
void add_to_int_buffer(IntBuffer* buffer, uInt64 datum);