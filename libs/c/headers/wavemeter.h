#pragma once
#include "beckvisa.h"

beckvisastatus open_wavemeter(beckvisasession bvs, beckvisainst* inst);
beckvisastatus get_wnum(beckvisainst wm, double* wnum);