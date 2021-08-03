#include "waveform.h"

Waveform create_waveform(int32 buffer_size, int32 averaging) {
	Waveform wf;
	wf.voltage = 0;
	wf.phase = 0;
	wf.voltage_buffer = create_float_buffer(buffer_size);
	wf.phase_buffer = create_float_buffer(buffer_size);
	wf.averaging = averaging;
	wf.averaging_counter = 0;
	wf.offset = 0;
	return wf;
}

void update_waveform(Waveform* wf_add, float64 phase, float64 voltage) {
	wf_add->phase = ((wf_add->averaging - 1) * wf_add->phase + phase) / wf_add->averaging;
	// wf_add->voltage = ((wf_add->averaging - 1) * wf_add->voltage + voltage) / wf_add->averaging;
	// ^^^ smooth averaging
	// vvv decimation
	wf_add->voltage = voltage;
	wf_add->averaging_counter = (wf_add->averaging_counter + 1) % wf_add->averaging;
	if (wf_add->averaging_counter == 0) {
		add_to_float_buffer(&wf_add->phase_buffer, phase);
		add_to_float_buffer(&wf_add->voltage_buffer, voltage);
	}
}