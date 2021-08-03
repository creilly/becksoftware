#include "beckvisa.h"

beckvisastatus beckvisa_open_session(beckvisasession* session) {
    beckvisastatus status = viOpenDefaultRM(session);
    if (status < VI_SUCCESS)
    {
        printf("Could not open a session to the VISA Resource Manager!\n");
        return status;
    }
    return VI_SUCCESS;
}

beckvisastatus beckvisa_open_inst(beckvisasession session, char instname[], beckvisainst* inst) {
    beckvisastatus status = viOpen(session, instname, VI_NULL, VI_NULL, inst);
    if (status < VI_SUCCESS)
    {
        printf("Cannot open a session to the device.\n");
        return status;
    }
    return VI_SUCCESS;
}

beckvisastatus beckvisa_close_inst(beckvisainst inst) {
    return viClose(inst);
}

beckvisastatus beckvisa_close_session(beckvisasession session) {
    return viClose(session);
}

beckvisastatus beckvisa_set_timeout(beckvisainst inst) {
    return VI_SUCCESS;
}