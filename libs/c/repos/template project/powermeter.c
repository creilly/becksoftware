#include <stdio.h>
#include <string.h>

#include "powermeter.h"

pmstatus open_powermeter(pmhandle* handle) {
    ViSession rm;
    ViStatus status = viOpenDefaultRM(&handle->rm);
    if (status < VI_SUCCESS)
    {
        printf("Could not open a session to the VISA Resource Manager!\n");
        return status;
    }
    status = viOpen(handle->rm, "powermeter", VI_NULL, VI_NULL, &handle->inst);
    if (status < VI_SUCCESS)
    {
        printf("Cannot open a session to the device.\n");
        viClose(handle->rm);
        return status;
    }
    char cfgpow[] = "CONF:POW";
    char units[] = "SENSE:POW:UNIT W";
    ViPInt32 count;
    status = viWrite(handle->inst, cfgpow, strlen(cfgpow), &count);
    status = viWrite(handle->inst, units, strlen(units), &count);
    return 0;
}

pmstatus get_power(pmhandle handle, double* power) {
    return viQueryf(handle.inst, "READ?", "%lf", power);
}

pmstatus close_powermeter(pmhandle handle) {
    pmstatus inststatus = viClose(handle.inst);
    pmstatus rmstatus = viClose(handle.rm);
    return inststatus && rmstatus;
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