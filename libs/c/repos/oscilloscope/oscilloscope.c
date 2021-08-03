#include "beckvisa.h"
#include "visa.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#define SCOPEBUFLEN 256

beckvisastatus set_rms_voltage(beckvisainst scope, double voltage) {
	int error;
	char writebuffer[SCOPEBUFLEN];
	int commandlen = sprintf_s(writebuffer, SCOPEBUFLEN, "vbs app.WaveSource.StdDev = %f", voltage);
	if (commandlen < 0) {
		printf("error formatting rms command\n");
		return -1;
	}
	ViUInt32 count;
	if ((error = viWrite(scope, writebuffer, strlen(writebuffer), &count)) < 0) {
		printf("error writting rms command\n");
		return error;
	}
	return VI_SUCCESS;
}

beckvisastatus open_scope(beckvisasession bvs, beckvisainst* scope) {
	return beckvisa_open_inst(bvs, "oscilloscope", scope);
}

beckvisastatus get_scope_measurement(beckvisainst scope, char channel[], char measurement[], double* result) {
	int error;
	char writebuffer[SCOPEBUFLEN];
	int commandlen = sprintf_s(writebuffer, SCOPEBUFLEN, "%s:PAVA? %s", channel, measurement);
	if (commandlen < 0) {
		printf("error formatting rms command\n");
		return -1;
	}
	ViUInt32 count;
	if ((error = viWrite(scope, writebuffer, strlen(writebuffer), &count)) < 0) {
		printf("error writting rms command\n");
		return error;
	}
	char readbuffer[SCOPEBUFLEN];
	if (
		(
			error = viRead(scope, readbuffer, SCOPEBUFLEN, &count) 
		)< 0
	) {
		printf("error reading from scope\n");
		return error;
	}
	readbuffer[count] = '\0';
	char* substr = strchr(readbuffer, ',');
	if (!substr) {
		printf("error parsing measurement response: no comma delimiter found\n");
		return -2;
	}
	substr++;
	char* endchar;
	*result = strtod(substr, &endchar);
	if (endchar == substr) {
		printf("error parsing measurement response: no float found\n");
		return -3;
	};
	return VI_SUCCESS;
}

//int main(int argc, char* argv[]) {
//	beckvisasession bvs;
//	beckvisainst scope;
//	if (beckvisa_open_session(&bvs)) { printf("error in session open\n"); }
//	if (open_scope(bvs, &scope)) { printf("error in inst open\n"); }
//	set_rms_voltage(scope, 0.050);
//	beckvisa_close_inst(scope);
//	beckvisa_close_session(scope);
//	return 0;
//}