#include "wavemeter.h"
#include <stdio.h>
#include <string.h>

beckvisastatus open_wavemeter(beckvisasession bvs, beckvisainst* inst) {
	beckvisainst wm;
	beckvisastatus status = beckvisa_open_inst(bvs, "wavemeter", &wm);
	if (status) { return status; }
	*inst = wm;
	status = viSetAttribute(wm, VI_ATTR_TERMCHAR_EN, 1);
	if (status) {
		printf("error on termination enable\n");
		beckvisa_close_inst(wm);
		return status;
	}
	status = viSetAttribute(wm, VI_ATTR_TMO_VALUE, 100);
	if (status) {
		printf("error on first timeout set\n");
		beckvisa_close_inst(wm);
		return status;
	}
	char nextchar;
	ViUInt32 charread;
	int charnum = 0;
	while (1) {
		status = viRead(wm, &nextchar, 1, &charread);
		if (status < 0 && status != VI_ERROR_TMO) {
			printf("error during greeting:\t%d\n", status);
			beckvisa_close_inst(wm);
			return -1;
		}
		if (charnum == 0) {
			if (!charread) {
				printf("no greeting from wavemeter\n");
				beckvisa_close_inst(wm);
				return -2;
			}
			if (nextchar != 'M') {
				printf("incorrect greeting. device already in use?\n");
				beckvisa_close_inst(wm);
				return -3;
			}
		}
		else {
			if (!charread) {
				printf("timeout on greeting at character %d\n", charnum);
				break;
			}
		}
		charnum++;
	}
	status = viSetAttribute(wm, VI_ATTR_TMO_VALUE, 1000);
	if (status) {
		printf("error on second timeout set\n");
		beckvisa_close_inst(wm);
		return status;
	}
	return VI_SUCCESS;
}

char* format_wavemeter_command(char command[], int length, int* fmttedlength) {
	char* buf = (char*)malloc(sizeof(char) * (length + 2));
	if (!buf) {
		printf("malloc for wm write failed\n");
		return NULL;
	}
	*fmttedlength = sprintf_s(buf, length + 2, "%s\n", command);
	return buf;
}

beckvisastatus get_wnum(beckvisainst wm, double* wnum) {
	char wnumqry[] = ":READ:WNUM?";
	int fmttedlength;
	char* fmttedqry = format_wavemeter_command(wnumqry, strlen(wnumqry), &fmttedlength);
	if (!fmttedqry) {
		printf("error formatting wnum query\n");
		return -1;
	}
	beckvisastatus status = viQueryf(wm, fmttedqry, "%lf", wnum);
	free(fmttedqry);
	return status;
}

//int main(int argc, char* argv[]) {
//	beckvisasession bvs;
//	beckvisastatus status = beckvisa_open_session(&bvs);
//	if (status) { return -1; }
//	beckvisainst wm;
//	status = open_wavemeter(bvs, &wm);
//	if (status < 0) { 
//		beckvisa_close_session(bvs);
//		return -1; 
//	}
//	double wnum;
//	status = get_wnum(wm, &wnum);
//	if (status) {
//		printf("error reading wnum:\t%d\n");
//	}
//	else {
//		printf("wnum:\t%lf\n", wnum);
//	}
//	beckvisa_close_inst(wm);
//	beckvisa_close_session(bvs);
//	return 0;
//}