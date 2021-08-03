#include <stdio.h>
#include <NIDAQmx.h>
#include <math.h>

#define DAQmxErrChk(functionCall) if( DAQmxFailed(error=(functionCall)) ) goto Error; else
#define DATA_SIZE 1000
#define BUFF_SIZE 20000

int32 CVICALLBACK EveryNSamplesCallback(TaskHandle taskHandle, int32 everyNsamplesEventType, uInt32 nSamples, void* callbackData);
int32 write_to_buffer(int32 samples);
void Cleanup(void);

static TaskHandle	taskHandle = 0;
static float64		data[DATA_SIZE];

float64 sample_rate = 1000.0;
uInt64 samples_written = 0;
int32 gap = 1000;

int main(void)
{
	int32       error = 0;
	char        errBuff[2048] = { '\0' };

	/*********************************************/
	// DAQmx Configure Code
	/*********************************************/
	DAQmxErrChk(DAQmxCreateTask("", &taskHandle));
	DAQmxErrChk(DAQmxCreateAOVoltageChan(taskHandle, "Dev2/ao0", "", -10.0, 10.0, DAQmx_Val_Volts, NULL));
	DAQmxErrChk(DAQmxSetWriteRegenMode(taskHandle, DAQmx_Val_DoNotAllowRegen));
	DAQmxErrChk(DAQmxCfgOutputBuffer(taskHandle, BUFF_SIZE));
	DAQmxErrChk(DAQmxSetSampTimingType(taskHandle, DAQmx_Val_SampClk));
	DAQmxErrChk(DAQmxSetSampQuantSampMode(taskHandle, DAQmx_Val_ContSamps));
	DAQmxErrChk(DAQmxSetSampClkSrc(taskHandle, "OnboardClock"));
	char src[256];
	DAQmxErrChk(DAQmxGetSampClkSrc(taskHandle, src, 256));
	printf("src:\t%s\n", src);
	DAQmxErrChk(DAQmxRegisterEveryNSamplesEvent(taskHandle, DAQmx_Val_Transferred_From_Buffer, gap/2, 0, EveryNSamplesCallback, NULL));
	bool32 using_ob_mem;
	DAQmxErrChk(DAQmxGetAOUseOnlyOnBrdMem(taskHandle, "", &using_ob_mem));
	printf("using ob mem?\t%d\n", using_ob_mem);
	int32 xfer_mech;
	DAQmxErrChk(DAQmxSetAODataXferMech(taskHandle, "", DAQmx_Val_ProgrammedIO));
	DAQmxErrChk(DAQmxGetAODataXferMech(taskHandle, "", &xfer_mech));
	printf("xfer mech:\t%d\n", xfer_mech);
	getch();
	return 0;
	DAQmxErrChk(write_to_buffer(gap));

	/*********************************************/
	// DAQmx Start Code
	/*********************************************/
	DAQmxErrChk(DAQmxStartTask(taskHandle));

	printf("Acquiring samples continuously.  Press Enter key to interrupt\n");

	getchar();

	DAQmxErrChk(DAQmxStopTask(taskHandle));

	printf("\nWrote %d total samples.\n", (int)samples_written);

Error:
	if (DAQmxFailed(error))
	{
		DAQmxGetExtendedErrorInfo(errBuff, 2048);
		Cleanup();
		printf("DAQmx Error: %s\n", errBuff);
	}
	printf("End of program, press Enter key to quit\n");
	getchar();
	return 0;
}

int32 CVICALLBACK EveryNSamplesCallback(TaskHandle taskHandle, int32 everyNsamplesEventType, uInt32 nSamples, void* callbackData)
{
	printf("samples written:\t%d\n", samples_written);
	char errBuff[2048] = { '\0' };
	int32 error;
	uInt64 samples_generated;
	DAQmxErrChk(DAQmxGetWriteTotalSampPerChanGenerated(taskHandle, &samples_generated));
	uInt64 sample_gap = samples_written - samples_generated;
	int32 samples = gap - sample_gap;
	DAQmxErrChk(write_to_buffer(samples));

Error:
	if (DAQmxFailed(error))
	{
		DAQmxGetExtendedErrorInfo(errBuff, 2048);
		Cleanup();
		printf("DAQmx Error: %s\n", errBuff);
	}
	return 0;
}

int32 write_to_buffer(int32 samples)
{
	int32 error_code = 0;;
	while (samples > 0) {
		int32 chunk = samples < DATA_SIZE ? samples : DATA_SIZE;
		for (int i = 0; i < chunk; i++) {
			data[i] = (samples_written+i) % 5;
		}
		int32 delta_samples_written;
		error_code = DAQmxWriteAnalogF64(taskHandle, chunk, 0, 0, DAQmx_Val_GroupByChannel, data, &delta_samples_written, NULL);
		printf("delta samples written: %d\n", delta_samples_written);
		if (error_code != 0) {
			return error_code;
		}
		samples_written += delta_samples_written;
		samples -= delta_samples_written;
	}
	return 0;
}

void Cleanup(void)
{
	if (taskHandle != 0)
	{
		/*********************************************/
		// DAQmx Stop Code
		/*********************************************/
		DAQmxStopTask(taskHandle);
		DAQmxClearTask(taskHandle);
		taskHandle = 0;
	}
}
