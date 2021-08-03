#pragma once
#include "beckvisa.h"

beckvisastatus open_scope(beckvisasession bvs, beckvisainst* scope);
beckvisastatus set_rms_voltage(beckvisainst scope, double voltage);