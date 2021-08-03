#pragma once
#define WIN32_LEAN_AND_MEAN
#include <Windows.h>
#include <winhttp.h>

int post_request(LPCWSTR hostname, INTERNET_PORT port, LPCWSTR url, LPCWSTR accepttype, LPCWSTR contenttype, char inputdata[], char* outputdata[], int* datalen);