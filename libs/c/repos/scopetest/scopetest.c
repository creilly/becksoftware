#include "oscilloscope.h"

int main(int argc, char* argv[]) {
	beckvisasession bvs;
	beckvisainst scope;
	if (beckvisa_open_session(&bvs)) { printf("error in session open\n"); }
	if (open_scope(bvs, &scope)) { printf("error in inst open\n"); }
	double result;
	get_scope_measurement(scope, "C1", "MEAN",&result);
	printf("result: %f\n", result);
	beckvisa_close_inst(scope);
	beckvisa_close_session(scope);
	return 0;
}