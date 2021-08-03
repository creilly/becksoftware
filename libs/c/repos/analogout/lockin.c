#undef UNICODE

#define WIN32_LEAN_AND_MEAN

#include "hardware.h"
#include <stdio.h>
#include <Windows.h>
#include "waveform.h"
#include "server.h"
#include <stdlib.h>
#include "list.h"

#define DAQmxErrChk(functionCall) if( DAQmxFailed(error=(functionCall)) ) goto Error; else

#define BUFFER_SIZE 50000
#define ZEROS_SIZE 10000
#define DATA_SIZE 65536

int32 CVICALLBACK DoneCallback(TaskHandle taskHandle, int32 status, void* callbackData);

int main(void)
{
	// server variables
	SOCKET	server;
	SOCKET	client;
	Message msg;
	int		server_error;
	int		reading_client = 0;

	// client queues
	client_queue mod_queue = NULL; // initialize empty
	client_queue scan_queue = NULL;
	client_queue* client_queues[2];
	client_queues[MOD_INDEX] = &mod_queue;
	client_queues[SCAN_INDEX] = &scan_queue;

	// hardware variables
	int32       error = 0;
	TaskHandle  aotask = 0;
	TaskHandle	aitask = 0;
	TaskHandle	dotask = 0;
	char        errBuff[2048] = { '\0' };
	float64		buffer_time = 1.0; // seconds
	float64*	data = (float64*)malloc(sizeof(float64) * 2 * DATA_SIZE);

	// timing variables
	float64 sampling_rate;
	uInt32 timebase_divisor;
	float64 reaction_time = 0.05; // seconds
	uInt64 samples_written = 0;

	// program state variables
	bool32 task_stopped = 0;

	// Sinusoids
	float64 mod_amp = 1.0;
	float64 mod_freq = 1000.0 + PI/10;

	float64 scan_amp = 1.0;
	float64 scan_freq = 3.0 + PI/10;

	Sinusoid mod_sin = create_sinusoid(mod_amp, mod_freq, BUFFER_SIZE, ZEROS_SIZE);
	Sinusoid scan_sin = create_sinusoid(scan_amp, scan_freq, BUFFER_SIZE, ZEROS_SIZE);

	Sinusoid* sinusoids[2];
	sinusoids[MOD_INDEX] = &mod_sin;
	sinusoids[SCAN_INDEX] = &scan_sin;

	// create server
	server_error = create_server(&server);
	if (server_error != 0) {
		printf("could not open server. exiting.\n");
		return -1;
	}

	/*********************************************/
	// DAQmx Configure Code
	/*********************************************/
	DAQmxErrChk(create_input_task(&aitask, buffer_time, &sampling_rate, &timebase_divisor));
	DAQmxErrChk(create_output_task(&aotask, buffer_time, sampling_rate, timebase_divisor));
	DAQmxErrChk(DAQmxRegisterDoneEvent(aotask, 0, DoneCallback, &task_stopped));

	// configure waveforms

	int32 mod_averaging = sampling_rate / mod_freq / 100;
	Waveform mod_wf = create_waveform(BUFFER_SIZE, mod_averaging ? mod_averaging : 1);
	int32 scan_averaging = sampling_rate / scan_freq / 100;
	Waveform scan_wf = create_waveform(BUFFER_SIZE, scan_averaging ? scan_averaging : 1);

	Waveform* waveforms[2];
	waveforms[MOD_INDEX] = &mod_wf;
	waveforms[SCAN_INDEX] = &scan_wf;

	// initialize output buffer
	DAQmxErrChk(write_to_output(aotask, sampling_rate * reaction_time, sinusoids, 2, sampling_rate, &samples_written));

	/*********************************************/
	// DAQmx Start Code
	/*********************************************/
	DAQmxErrChk(DAQmxStartTask(aotask));
	DAQmxErrChk(DAQmxStartTask(aitask));
	DAQmxErrChk(set_trigger());

	uInt64 prev_samples_read = mod_wf.offset;
	int client_available;
	while (!task_stopped) {
		if (!reading_client) {
			server_error = get_client(server, &client, &client_available);
			if (server_error != 0) {
				printf("server error. closing.");
				return -1;
			}
			if (client_available) {
				reading_client = 1;
				msg = create_message(client);
				printf("client connected\n");
			}
		}
		if (reading_client) {
			server_error = update_message(&msg);
			if (server_error == -3) {
				// receive complete, handle message
				char command = msg.buffer[0];
				switch (command) {
					case 'f': {
						int channel = msg.buffer[1] - '0';
						if (msg.buffer[2] == '?') {
							char response[11 + 2 + 1];
							sprintf_s(response, 11+2+1, "%11.4e\r\n", sinusoids[channel]->frequency);
							send_message(client, response, 11 + 2);
						}
						else {
							float64 frequency = atof(msg.buffer + 2);
							sinusoids[channel]->frequency = frequency;
							int32 averaging = sampling_rate / frequency / 100;
							averaging = averaging ? averaging : 1;
							waveforms[channel]->averaging = averaging;
							waveforms[channel]->averaging_counter = 0;
							send_message(client, "0\r\n", 3);
						}
						close_client(client);
						reading_client = 0;
						break;
					}
					case 'w': {
						int channel = msg.buffer[1] - '0';
						append(client_queues[channel], client);
						reading_client = 0;
						break;
					}
					default: {
						close_client(client);
						reading_client = 0;
						break;
					}
				}
			}
			else if (server_error == 1 || server_error == -1 || server_error == -2) {
				// close connection
				close_client(client);
				reading_client = 0;
			}
		}
		DAQmxErrChk(read_from_input(aitask, waveforms, sinusoids, client_queues, 2, data, DATA_SIZE));
		int32 buffer_gap;
		DAQmxErrChk(get_buffer_gap(aotask, samples_written, sampling_rate, reaction_time, &buffer_gap));
		if (buffer_gap > 0) {
			DAQmxErrChk(write_to_output(aotask, buffer_gap, sinusoids, 2, sampling_rate, &samples_written));
		}
		//printf("samples read:\t%d,\t", mod_wf.offset-prev_samples_read);
		prev_samples_read = mod_wf.offset;
		//printf("buffer gap:\t%d\n", buffer_gap);
		//Sleep(200);
	}
	printf("task stopped detected\n");

Error:
	if (DAQmxFailed(error))
		DAQmxGetExtendedErrorInfo(errBuff, 2048);
	if (aotask != 0) {
		/*********************************************/
		// DAQmx Stop Code
		/*********************************************/
		DAQmxStopTask(aotask);
		DAQmxClearTask(aotask);
	}
	if (DAQmxFailed(error))
		printf("DAQmx Error: %s\n", errBuff);
	return 0;
}

int32 CVICALLBACK DoneCallback(TaskHandle taskHandle, int32 status, void* callbackData)
{
	int32   error = 0;
	char    errBuff[2048] = { '\0' };

	// Check to see if an error stopped the task.
	DAQmxErrChk(status);

Error:
	if (DAQmxFailed(error)) {
		DAQmxGetExtendedErrorInfo(errBuff, 2048);
		DAQmxClearTask(taskHandle);
		printf("DAQmx Error: %s\n", errBuff);
	}
	bool32* task_stopped_add = (bool32*)callbackData;
	*task_stopped_add = 1;
	return 0;
}
