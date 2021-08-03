#include "buffer.h"
FloatBuffer create_float_buffer(int32 size)
{
	FloatBuffer buffer;
	buffer.data = (float64*)malloc(sizeof(float64) * size);
	buffer.size = size;
	buffer.write_offset = 0;
	buffer.read_offset = 0;
	return buffer;
}

IntBuffer create_int_buffer(int32 size)
{
	IntBuffer buffer;
	buffer.data = (uInt64*)malloc(sizeof(uInt64) * size);
	buffer.size = size;
	buffer.write_offset = 0;
	buffer.read_offset = 0;
	return buffer;
}

void add_to_float_buffer(FloatBuffer* buffer, float64 datum)
{
	buffer->data[buffer->write_offset] = datum;
	buffer->write_offset = (buffer->write_offset + 1) % buffer->size;
}

void add_to_int_buffer(IntBuffer* buffer, uInt64 datum)
{
	buffer->data[buffer->write_offset] = datum;
	buffer->write_offset = (buffer->write_offset + 1) % buffer->size;
}
