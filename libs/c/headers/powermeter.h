#pragma once
#include "beckvisa.h"

beckvisastatus open_powermeter(beckvisasession session, beckvisainst* inst);
beckvisastatus get_power(beckvisainst inst, double* power);