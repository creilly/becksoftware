#pragma once
#include "beckvisa.h"

beckvisastatus open_scope(beckvisasession bvs, beckvisainst* scope);
beckvisastatus set_rms_voltage(beckvisainst scope, double voltage);
beckvisastatus get_scope_measurement(beckvisainst scope, char channel[], char measurement[], double* result);