#include <stdio.h>
#include <NIDAQmx.h>
#include "topo.h"
#include "graphclient.h"
#include "beckvisa.h"
#include "powermeter.h"
#include "wavemeter.h"
#include "oscilloscope.h"
#include <string.h>
#include <math.h>
#include <stdlib.h>
#include "time.h"
#define WIN32_LEAN_AND_MEAN
#include <Windows.h>

#define DAQmxErrChk(functionCall) if( DAQmxFailed(error=(functionCall)) ) goto Error; else
#define ZeroChk(fnccall, message) if(fnccall) {printf(message); printf("\n"); printf("error:\t%d",fnccall); printf("\n"); goto Error;} else

int main(void)
{
	// topo variables
	int toposessionopen = 0;
	int topoconnected = 0;

	// visa variables
	beckvisasession bvs;
	int bvsopen = 0;
	beckvisainst pm;
	int pmopen = 0;
	beckvisainst wm;
	int wmopen = 0;
	beckvisainst os;
	int osopen = 0;

	// program vars
	double gdata[5];
	double rms_values[] = { 1E-3, 25E-3, 50E-3, 75E-3, 100E-3, 125E-3, 150E-3 };
	int nrms_values = sizeof(rms_values) / sizeof(double);

	// connect to topo
	ZeroChk(init_session(), "error starting topo session");
	toposessionopen = 1;

	topohandle topo;
	ZeroChk(connect_topo(&topo), "error connecting to topo\n");
	topoconnected = 1;

	// create new dataset
	char** folder;
	int nfoldlets;
	if (get_day_folder(&folder, &nfoldlets)) { return -1; }
	char** path;
	int npathlets;
	char nametemplate[] = "etalon scan, %.3fv rms noise";
	char* fields[] = {
		"dfb temp (C)",
		"wnum (cm-1)",
		"power (W)",
		"avg (V)",
		"rms (V)"
	};

	// open VISA session
	ZeroChk(beckvisa_open_session(&bvs), "error opening visa session");
	bvsopen = 1;

	// connect to powermeter
	ZeroChk(open_powermeter(bvs, &pm), "error opening powermeter");
	pmopen = 1;

	// connect to powermeter
	ZeroChk(open_wavemeter(bvs, &wm), "error opening wavemeter");
	wmopen = 1;

	// connect to powermeter
	ZeroChk(open_scope(bvs, &os), "error opening wavemeter");
	osopen = 1;

	for (int i = 0; i < nrms_values; i++) {
		char name[256];
		double rms_value = rms_values[i];
		ZeroChk(set_rms_voltage(os, rms_value), "error setting rms voltage");
		sprintf_s(name, 256, nametemplate, rms_value);
		ZeroChk(add_dataset(folder, nfoldlets, name, fields, 5, &path, &npathlets), "error creating grapher dataset");

		// configure temperature scan
		float64 inittemp;
		ZeroChk(get_temperature(topo, &inittemp), "error reading topo temperature");
		float64 direction = inittemp > 27 ? -1 : +1;
		float64 dtemp = 0.0002;
		float64 mhzperdegc = 30000;
		float64 deltafreq = 650; // MHz
		float64 deltatempmax = deltafreq / mhzperdegc;
		float64 deltatemp = 0;
		float64 temp;

		while (deltatemp < deltatempmax) {
			// set new temperature
			temp = inittemp + direction * deltatemp;
			ZeroChk(set_temperature(topo, temp), "error setting temperature");

			// put current temp in 0th column
			gdata[0] = temp;

			Sleep(500);

			// measure laser power
			double power;
			ZeroChk(get_power(pm, &power), "error measuring power");

			// put laser power in 2nd column
			gdata[2] = power;

			double average;
			ZeroChk(get_scope_measurement(os, "C2", "MEAN", &average),"error measuring C2 average");

			// put average pd signal in 3rd column
			gdata[3] = average;

			double rms;
			ZeroChk(get_scope_measurement(os, "C1", "SDEV", &rms), "error measuring C1 rms");

			// put rms pd signal in 4th column
			gdata[4] = rms;

			// measure wnum
			double wnum;
			ZeroChk(get_wnum(wm, &wnum), "error reading wnum");

			// put wnum in 1st column
			gdata[1] = wnum;

			printf("rms noise: %f\tdfb temp: %f\twnum: %f\tpower: %f\tavg: %f\trms: %f\n", rms_value, temp, wnum, power, average, rms);

			// add row to dataset
			ZeroChk(add_data(path, npathlets, gdata, 5), "error adding row to dataset");

			// increment temp
			deltatemp += dtemp;
		}
	}
Error:
	if (topoconnected) { disconnect_topo(topo); }
	if (toposessionopen) { end_session(); }
	if (pmopen) { beckvisa_close_inst(pm); }
	if (wmopen) { beckvisa_close_inst(wm); }
	if (osopen) { beckvisa_close_inst(os); }
	if (bvsopen) { beckvisa_close_session(bvs); }
	printf("End of program, press Enter key to quit\n");
	getchar();
	return 0;
}

int _main(void)
{
	// topo variables
	int toposessionopen = 0;
	int topoconnected = 0;

	// visa variables
	beckvisasession bvs;
	int bvsopen = 0;
	beckvisainst pm;
	int pmopen = 0;
	beckvisainst wm;
	int wmopen = 0;
	beckvisainst os;
	int osopen = 0;

	// daqmx variables
	int32       error = 0;
	TaskHandle  taskHandle = 0;
	int32       read;
	float64		acquisition_time = 0.5; // seconds
	float64		window_times[] = {
		5E-5,
		1E-4,2E-4,5E-4,
		1E-3,2E-3,5E-3,
		1E-2,2E-2,5E-2,
		1E-1
	};
	int nwindow_times = sizeof(window_times) / sizeof(window_times[0]);
	char        errBuff[2048] = { '\0' };

	// program vars
	int nrootvars = 4;
	float64* gdata = NULL;
	float64* data = NULL;

	// connect to topo
	ZeroChk(init_session(), "error starting topo session");
	toposessionopen = 1;

	topohandle topo;
	ZeroChk(connect_topo(&topo), "error connecting to topo\n");
	topoconnected = 1;

	// configure ni daq card
	DAQmxErrChk(DAQmxCreateTask("", &taskHandle));
	DAQmxErrChk(DAQmxCreateAIVoltageChan(taskHandle, "Dev1/ai0", "", DAQmx_Val_Cfg_Default, -10.0, 10.0, DAQmx_Val_Volts, NULL));
	DAQmxErrChk(DAQmxCreateAIVoltageChan(taskHandle, "Dev1/ai1", "", DAQmx_Val_Diff, -0.5, 0.5, DAQmx_Val_Volts, NULL));
	DAQmxErrChk(DAQmxCfgSampClkTiming(taskHandle, "", 10000.0, DAQmx_Val_Rising, DAQmx_Val_FiniteSamps, 250));
	float64 sample_rate;
	DAQmxErrChk(DAQmxGetSampClkMaxRate(taskHandle, &sample_rate));
	DAQmxErrChk(DAQmxSetSampClkRate(taskHandle, sample_rate));
	DAQmxErrChk(DAQmxGetSampClkRate(taskHandle, &sample_rate));
	int samples = sample_rate * acquisition_time;
	data = (float64*)malloc(sizeof(float64) * 2 * samples);
	DAQmxErrChk(DAQmxSetSampQuantSampPerChan(taskHandle, samples));

	// create new dataset
	char** folder;
	int nfoldlets;
	if (get_day_folder(&folder, &nfoldlets)) { return -1; }
	char** path;
	int npathlets;
	char name[] = "short scan, series, with dither, new temp";
	char** fields = (char**)malloc(sizeof(char*) * (nrootvars + nwindow_times));
	char xaxis[] = "temperature (celsius)";
	char powerlabel[] = "power (watts)";
	char dcvoltage[] = "dc voltage (volts)";
	char wnumlab[] = "wavenumber (cm-1)";
	fields[0] = xaxis;
	fields[1] = wnumlab;
	fields[2] = powerlabel;
	fields[3] = dcvoltage;
	char yaxistemplate[] = "rms voltage (volts) window time %5.0e seconds"; // formatter happens to have same length
	int yaxislen = strlen(yaxistemplate);
	for (int i = 0; i < nwindow_times; i++) {
		char* yaxis = (char*)malloc(sizeof(char) * (1 + yaxislen));
		sprintf_s(yaxis, yaxislen + 1, yaxistemplate, window_times[i]);
		fields[nrootvars + i] = yaxis;
	}

	// open VISA session
	ZeroChk(beckvisa_open_session(&bvs), "error opening visa session");
	bvsopen = 1;

	// connect to powermeter
	ZeroChk(open_powermeter(bvs, &pm), "error opening powermeter");
	pmopen = 1;

	// connect to powermeter
	ZeroChk(open_wavemeter(bvs, &wm), "error opening wavemeter");
	wmopen = 1;

	// connect to powermeter
	ZeroChk(open_scope(bvs, &os), "error opening wavemeter");
	osopen = 1;

	// allocate buffer for row data
	gdata = (float64*)malloc(sizeof(float64) * (nrootvars + nwindow_times));

	for (int trial = 0; trial < 20; trial++) {
		// create new dataset
		ZeroChk(add_dataset(folder, nfoldlets, name, fields, nrootvars + nwindow_times, &path, &npathlets), "error creating grapher dataset");
		
		// configure temperature scan
		float64 inittemp;
		ZeroChk(get_temperature(topo, &inittemp), "error reading topo temperature");
		float64 direction = inittemp > 27 ? -1 : +1;
		float64 dtemp = 0.0005;
		float64 mhzperdegc = 30000;
		float64 deltafreq = 500; // MHz
		float64 deltatempmax = deltafreq / mhzperdegc;
		float64 deltatemp = 0;
		float64 temp;

		while (deltatemp < deltatempmax) {
			// set new temperature
			temp = inittemp + direction * deltatemp;
			ZeroChk(set_temperature(topo, temp), "error setting temperature");

			// put current temp in 0th column
			gdata[0] = temp;

			Sleep(500);

			// measure laser power
			double power;
			ZeroChk(get_power(pm, &power), "error measuring power");

			// put laser power in 1st column
			gdata[2] = power;

			// get photodiode signal
			DAQmxErrChk(DAQmxStartTask(taskHandle));
			DAQmxErrChk(DAQmxReadAnalogF64(taskHandle, samples, 10.0 * acquisition_time, DAQmx_Val_GroupByChannel, data, 2 * samples, &read, NULL));
			DAQmxErrChk(DAQmxStopTask(taskHandle));

			// measure average photodiode signal
			float64 average = 0;
			for (int i = 0; i < read; i++) {
				average += data[i];
			}
			average = average / read;

			// put average pd signal in 3rd column
			gdata[3] = average;

			// compute average rms for different time windows
			for (int i = 0; i < nwindow_times; i++) {
				float64 window = window_times[i];
				int samps_per_window = sample_rate * window;
				int samplecount = 0;
				int rmscount = 0;
				float64 avgrms = 0;
				float64 firstmom = 0;
				float64 secondmom = 0;
				for (int j = 0; j < read; j++) {
					if (samplecount == samps_per_window) {
						float64 rms = sqrt(secondmom - firstmom * firstmom);
						avgrms = avgrms * rmscount / (1 + rmscount) + rms / (1 + rmscount);
						rmscount += 1;
						samplecount = 0;
					}
					float64 voltage = data[read + j];
					firstmom = firstmom * samplecount / (1 + samplecount) + voltage / (1 + samplecount);
					secondmom = secondmom * samplecount / (1 + samplecount) + voltage * voltage / (1 + samplecount);
					samplecount++;
				}
				printf("trial:\t%d\ttemperature:\t%f\twindow time:\t%5.0e\tavgrms\t%f\n", trial, temp, window, avgrms);
				// store avg rms in (nrootvars+i)th column
				if (avgrms != avgrms) {
					avgrms = 0.0;
				}
				gdata[nrootvars + i] = avgrms;
			}
			// measure wnum
			double wnum;
			ZeroChk(get_wnum(wm, &wnum), "error reading wnum");

			// add wnum to row
			gdata[1] = wnum;

			// add row to dataset
			ZeroChk(add_data(path, npathlets, gdata, nrootvars + nwindow_times), "error adding row to dataset");

			// increment temp
			deltatemp += dtemp;
		}
	}
Error:
	if (data) { free(data); }
	if (gdata) { free(gdata); }
	if (topoconnected) { disconnect_topo(topo); }
	if (toposessionopen) { end_session(); }
	if (pmopen) { beckvisa_close_inst(pm); }
	if (wmopen) { beckvisa_close_inst(wm); }
	if (bvsopen) { beckvisa_close_session(bvs); }
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
