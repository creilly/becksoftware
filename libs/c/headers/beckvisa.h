#pragma once
#include "visa.h"

typedef ViSession beckvisasession;
typedef ViSession beckvisainst;
typedef ViStatus beckvisastatus;
beckvisastatus beckvisa_open_session(beckvisasession* session);
beckvisastatus beckvisa_open_inst(beckvisasession session, char instname[], beckvisainst* inst);
beckvisastatus beckvisa_close_inst(beckvisainst inst);
beckvisastatus beckvisa_close_session(beckvisasession session);