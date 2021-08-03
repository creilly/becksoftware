#include <stdio.h>
#include <string.h>
#include "powermeter.h"

beckvisastatus open_powermeter(beckvisasession session, beckvisainst* inst) {
    beckvisastatus status = beckvisa_open_inst(session, "powermeter", inst);
    if (status < VI_SUCCESS)
    {
        printf("Cannot open power meter.\n");
        return status;
    }
    char cfgpow[] = "CONF:POW";
    char units[] = "SENSE:POW:UNIT W";
    ViPInt32 count;
    status = viWrite(*inst, cfgpow, strlen(cfgpow), &count);
    printf("conf power status: %d\n", status);
    status = viWrite(*inst, units, strlen(units), &count);
    printf("conf units status: %d\n", status);
    return 0;
}

beckvisastatus get_power(beckvisainst inst, double* power) {
    return viQueryf(inst, "READ?", "%lf", power);
}

//int main(void)
//{
//    pmstatus status;
//    pmhandle handle;
//    if (open_powermeter(&handle) < 0) { return -1; }
//    double power;
//    if (get_power(handle,&power) < 0) { return -1; }
//    printf("power: %f\n", power);
//    close_powermeter(handle);
//    return 0;
//}