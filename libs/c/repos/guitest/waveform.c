#include <NIDAQmx.h>
#include <stdio.h>
#include <math.h>

#define PI	3.1415926535
#define DATA_SIZE 33
#define BUF_SIZE 1000

float64 get_sample(float64, float64);

float64 amplitude = 5.0;

int main(void)
{
	int32       error = 0;
	TaskHandle  taskHandle = 0;
	float64     data[DATA_SIZE];
	char        errBuff[2048] = { '\0' };
	float64		buffer_time = 0.1;
	float64		mod_period = 2.5;
	float64		carrier_period = .25;
	float64		delta_t = 0.001;
	uInt64		samples_generated = 0;
	uInt64		samples_written = 0;
	float64		mod_phase = 0;
	float64		carrier_phase = 0;
	int32		total_samples_to_write;
	int32		regen_mode;

	int32		buffer_width = buffer_time / delta_t;

	/*********************************************/
	// DAQmx Configure Code
	/*********************************************/
	DAQmxErrChk(DAQmxCreateTask("", &taskHandle));
	DAQmxErrChk(DAQmxCreateAOVoltageChan(taskHandle, "maxwell/ao0", "", -10.0, 10.0, DAQmx_Val_Volts, NULL));
	DAQmxErrChk(DAQmxCfgSampClkTiming(taskHandle, "", 1 / delta_t, DAQmx_Val_Rising, DAQmx_Val_ContSamps, BUF_SIZE));
	DAQmxErrChk(DAQmxCfgOutputBuffer(taskHandle, BUF_SIZE));
	DAQmxErrChk(DAQmxSetWriteRegenMode(taskHandle, DAQmx_Val_DoNotAllowRegen));

	total_samples_to_write = buffer_width - (samples_written - samples_generated);
	while (total_samples_to_write > 0) {
		printf("Total samples to generate: %d\n", total_samples_to_write);
		int32 samples_to_write = (total_samples_to_write < DATA_SIZE) ? total_samples_to_write : DATA_SIZE;
		for (int32 i = 0; i < samples_to_write; i++) {
			data[i] = amplitude * sin(mod_phase) * sin(carrier_phase);
			mod_phase += delta_t * 2.0 * PI / mod_period;
			/*if (mod_phase > 2.0 * PI) {
				mod_phase -= 2.0 * PI;
			}*/
			carrier_phase += delta_t * 2.0 * PI / carrier_period;
			/*if (carrier_phase > 2.0 * PI) {
				carrier_phase -= 2.0 * PI;
			}*/
		}
		printf("start\n");
		DAQmxErrChk(DAQmxWriteAnalogF64(taskHandle, samples_to_write, 0, 0, DAQmx_Val_GroupByChannel, data, NULL, NULL));
		printf("end\n");
		total_samples_to_write -= samples_to_write;
		samples_written += samples_to_write;
	}

	/*********************************************/
	// DAQmx Start Code
	/*********************************************/
	DAQmxErrChk(DAQmxStartTask(taskHandle));
	while (mod_phase / (2 * PI) < 10) {
		printf("mod phase: %f\n", mod_phase);
		DAQmxErrChk(DAQmxGetWriteTotalSampPerChanGenerated(taskHandle, &samples_generated));
		total_samples_to_write = buffer_width - (samples_written - samples_generated);
		while (total_samples_to_write > 0) {
			printf("Total samples to generate: %d\n", total_samples_to_write);
			int32 samples_to_write = (total_samples_to_write < DATA_SIZE) ? total_samples_to_write : DATA_SIZE;
			for (int32 i = 0; i < samples_to_write; i++) {
				data[i] = amplitude * sin(mod_phase) * sin(carrier_phase);
				mod_phase += delta_t * 2.0 * PI / mod_period;
				/*if (mod_phase > 2.0 * PI) {
					mod_phase -= 2.0 * PI;
				}*/
				carrier_phase += delta_t * 2.0 * PI / carrier_period;
				/*if (carrier_phase > 2.0 * PI) {
					carrier_phase -= 2.0 * PI;
				}*/
			}
			printf("start\n");
			DAQmxErrChk(DAQmxWriteAnalogF64(taskHandle, samples_to_write, 0, 10.0, DAQmx_Val_GroupByChannel, data, NULL, NULL));
			printf("end\n");
			total_samples_to_write -= samples_to_write;
			samples_written += samples_to_write;
		}
	}

Error:
	if (DAQmxFailed(error))
		DAQmxGetExtendedErrorInfo(errBuff, 2048);
	if (taskHandle != 0) {
		/*********************************************/
		// DAQmx Stop Code
		/*********************************************/
		DAQmxStopTask(taskHandle);
		DAQmxClearTask(taskHandle);
	}
	if (DAQmxFailed(error))
		printf("DAQmx Error: %s\n", errBuff);
	printf("End of program, press Enter key to quit\n");
	getchar();
	return 0;
}

float64 get_sample(float64 mod_phase, float64 carrier_phase) {
	return amplitude * sin(mod_phase) * sin(carrier_phase);
}
