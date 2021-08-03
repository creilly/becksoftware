#include <NIDAQmx.h>
#include <stdlib.h>
#include <math.h>
#include "hardware.h"
#include "list.h"
#include <stdio.h>

#define STR_BUF_SIZE 256
#define TRIGGER_CHANNEL "/Dev1/PFI5"
#define DO_CHANNEL "Dev1/port1/line1"

#define DEBUG_CLOCK "/Dev1/PFI4"
#define CLOCK ""

int32 set_trigger() {
	TaskHandle taskHandle;
	int32 error;
	error = DAQmxCreateTask("", &taskHandle);
	if (error != 0) { return error; }
	error = DAQmxCreateDOChan(taskHandle, DO_CHANNEL, "", DAQmx_Val_ChanPerLine);
	if (error != 0) { return error; }
	uInt8 data[1] = { FALSE };
	error = DAQmxWriteDigitalLines(taskHandle, 1, TRUE, 0, DAQmx_Val_GroupByChannel, data, NULL, NULL);
	if (error != 0) { return error; }
	data[0] = TRUE;
	error = DAQmxWriteDigitalLines(taskHandle, 1, TRUE, 0, DAQmx_Val_GroupByChannel, data, NULL, NULL);
	if (error != 0) { return error; }
	error = DAQmxStopTask(taskHandle);
	if (error != 0) { return error; }
	error = DAQmxClearTask(taskHandle);
	return error;
}

// sets the timing equal to the max sampling rate
int32 create_input_task(TaskHandle* task_add, float64 buffer_time, float64* sampling_rate_add, uInt32* timebase_divisor_add) {
	int32 error;
	error = DAQmxCreateTask("", task_add);
	TaskHandle taskHandle = *task_add;
	if (error != 0) { return error; }
	error = DAQmxCreateAIVoltageChan(taskHandle, "Dev1/ai0,Dev1/ai1", "", DAQmx_Val_Diff, -10.0, 10.0, DAQmx_Val_Volts, NULL);
	if (error != 0) { return error; }
	float64 max_sampling_rate;
	error = DAQmxGetSampClkMaxRate(taskHandle, &max_sampling_rate);
	if (error != 0) {return error;}
	int32 buffer_size = max_sampling_rate * buffer_time;
	error = DAQmxCfgSampClkTiming(taskHandle, CLOCK, max_sampling_rate, DAQmx_Val_Rising, DAQmx_Val_ContSamps, buffer_size);
	if (error != 0) { return error; }
	error = DAQmxGetSampClkRate(taskHandle, sampling_rate_add);
	if (error != 0) { return error; }
	error = DAQmxGetSampClkTimebaseDiv(taskHandle, timebase_divisor_add);
	if (error != 0) { return error; }
	error = DAQmxCfgDigEdgeStartTrig(taskHandle, TRIGGER_CHANNEL, DAQmx_Val_Rising);
	return error;
}

int32 create_output_task(TaskHandle* task_add, float64 buffer_time, float64 sampling_rate, uInt32 timebase_divisor) {
	int32 error;
	error = DAQmxCreateTask("", task_add);
	TaskHandle taskHandle = *task_add;
	if (error != 0) { return error; }
	error = DAQmxCreateAOVoltageChan(taskHandle, "Dev1/ao0,Dev1/ao1", "", -10.0, 10.0, DAQmx_Val_Volts, NULL);
	if (error != 0) { return error; }
	int32 buffer_size = sampling_rate * buffer_time;
	error = DAQmxCfgSampClkTiming(taskHandle, CLOCK, sampling_rate, DAQmx_Val_Rising, DAQmx_Val_ContSamps, buffer_size);
	if (error != 0) { return error; }
	error = DAQmxSetSampClkTimebaseDiv(taskHandle, timebase_divisor); // this ensures tasks stay synched
	if (error != 0) { return error; }
	error = DAQmxSetWriteRegenMode(taskHandle, DAQmx_Val_DoNotAllowRegen);
	if (error != 0) { return error; }
	error = DAQmxCfgOutputBuffer(taskHandle, buffer_size);
	if (error != 0) { return error; }
	error = DAQmxCfgDigEdgeStartTrig(taskHandle, TRIGGER_CHANNEL, DAQmx_Val_Rising);
	return error;
}

int32 read_from_input(TaskHandle taskHandle, Waveform* waveforms[], Sinusoid* sinusoids[], client_queue* client_queues[], int32 nSinusoids, float64* data, int32 size)
{
	int32 error;
	int32 samples_read;
	int32 iters = 0;
	do {
		error = DAQmxReadAnalogF64(taskHandle, DAQmx_Val_Auto, 0, DAQmx_Val_GroupByChannel, data, size, &samples_read, NULL);
		//printf("iters:\t%d\n", iters);
		iters++;
		//printf("samples read / size:\t%d\t%d\n", samples_read, size);
		if (error != 0) { return error; }
		for (int i = 0; i < nSinusoids; i++) {
			Sinusoid* sinu = sinusoids[i];
			Waveform* wf = waveforms[i];
			uInt64 zero = sinu->zeros.data[sinu->zeros.read_offset];
			for (int j = 0; j < samples_read; j++) {
				if (wf->offset + j == zero) {
					if (get_list_length(*client_queues[i])) {
						int32 ro = wf->voltage_buffer.read_offset;
						int32 wo = wf->voltage_buffer.write_offset;
						int32 bl = wf->voltage_buffer.size;
						int32 length = 2 * ( wo < ro ? wo - ro + bl : (wo - ro) );
						// printf("ro:\t%d\t|\two:\t%d\t|\tbl:\t%d\t|\tle:\t%d\n", ro, wo, bl, length);
						int32 width = 11;
						int32 prec = 4;
						char fmt[32];
						sprintf_s(fmt, 32, "%%%d.%de", width, prec);
						// printf("fmt:\t%s\n", fmt);
						int nNumber = length;
						int nDelim = length ? length - 1 : 0;
						int nTerm = 2;
						int buff_size = nNumber * width + nDelim + nTerm + 1; // last char for null terminator
						// printf("buff_size:\t%d\n", buff_size);
						char* write_buff = (char*)malloc(sizeof(char) * buff_size);
						int offset = 0;
						// interleaved write, i.e. phase1\tvoltage1\tphase2\tvoltage2\t...\tphaseN\tvoltageN\r\n
						for (int k = 0; k < length; k++) {
							offset += sprintf_s(
								write_buff + offset, 
								buff_size - offset, 
								fmt, (
									k % 2 ? wf->voltage_buffer : wf->phase_buffer
								).data[(ro + k/2) % wf->voltage_buffer.size]
							);
							if (k < length - 1) {
								write_buff[offset++] = '\t';
							}
						}
						write_buff[offset++] = '\r';
						write_buff[offset++] = '\n';
						write_buff[offset] = '\0';
						SOCKET client;
						int clients = 0;
						while (pop(client_queues[i], &client)) {
							clients += 1;
							send_message(client, write_buff, buff_size - 1);
							close_client(client);
						}
						free(write_buff);
					}
					wf->phase_buffer.read_offset = wf->phase_buffer.write_offset;
					wf->voltage_buffer.read_offset = wf->voltage_buffer.write_offset;
					sinu->zeros.read_offset = (sinu->zeros.read_offset + 1) % sinu->zeros.size;
					zero = sinu->zeros.data[sinu->zeros.read_offset];
				}
				update_waveform(wf, sinu->buffer.data[(sinu->buffer.read_offset + j) % sinu->buffer.size], data[i * samples_read + j]);
			}
			sinu->buffer.read_offset = (sinu->buffer.read_offset + samples_read) % sinu->buffer.size;
			wf->offset += samples_read;
		}
	} while (nSinusoids*samples_read == size);
}

int32 get_buffer_gap(TaskHandle taskHandle, uInt64 samples_written, float64 sampling_rate, float64 reaction_time, int32* buffer_gap_add)
{
	uInt64 samples_generated;
	int32 error = DAQmxGetWriteTotalSampPerChanGenerated(taskHandle, &samples_generated);
	if (error != 0) { return error; }
	int32 delta = samples_written - samples_generated;
	int32 buffer_gap = (int32)(sampling_rate * reaction_time) - delta;
	*buffer_gap_add = buffer_gap;
	return 0;
}

int32 write_to_output(TaskHandle taskHandle, int32 samples, Sinusoid* sinusoids[], int32 nSinusoids, float64 sampling_rate, uInt64* samples_written_add) {
	float64* data = (float64*)malloc(sizeof(float64) * 2 * samples);
	for (int i = 0; i < nSinusoids; i++) {
		Sinusoid* sinusoid = sinusoids[i];
		float64 amplitude = sinusoid->amplitude;
		float64 frequency = sinusoid->frequency;
		float64 phase = sinusoid->phase;
		for (int j = 0; j < samples; j++) {
			add_to_float_buffer(&sinusoid->buffer, phase);
			data[i * samples + j] = sinusoid->amplitude * cos(phase);
			phase += 2.0 * PI * sinusoid->frequency / sampling_rate;
			if (phase > 2.0 * PI) {
				phase -= 2.0 * PI;
				add_to_int_buffer(&sinusoid->zeros, *samples_written_add + j + 1);
			}
		}
		sinusoid->phase = phase;
	}
	int32 error = DAQmxWriteAnalogF64(taskHandle, samples, 0, 0, DAQmx_Val_GroupByChannel, data, NULL, NULL);
	free(data);
	if (error != 0) {
		return error;
	}
	else {
		*samples_written_add += samples;
		return 0;
	}
}
