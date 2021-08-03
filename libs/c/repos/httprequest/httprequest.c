#include <stdio.h>
#include "httprequest.h"

int post_request(LPCWSTR hostname, INTERNET_PORT port, LPCWSTR url, LPCWSTR accepttype, LPCWSTR contenttype, char inputdata[], char* outputdata[], int* datalen) {
    int error;
    DWORD dwSize = 0;
    DWORD dwDownloaded = 0;
    BOOL  bResults = FALSE;
    HINTERNET  hSession = NULL,
        hConnect = NULL,
        hRequest = NULL;

    // Use WinHttpOpen to obtain a session handle.
    hSession = WinHttpOpen(NULL,
        WINHTTP_ACCESS_TYPE_DEFAULT_PROXY,
        WINHTTP_NO_PROXY_NAME,
        WINHTTP_NO_PROXY_BYPASS, 0);

    // Specify an HTTP server.
    if (!hSession) {
        error = GetLastError();
        printf("error opening http session handle:\n\t%d\n", error);
        return error;
    }
    // Connect to HTTP server
    hConnect = WinHttpConnect(hSession, hostname, port, 0);
    if (!hConnect) {
        error = GetLastError();
        WinHttpCloseHandle(hSession);
        wprintf(L"error connection to %s:%d:\n\t%d\n", hostname, port, error);
        return error;
    }
    // Initiate a POST request
    hRequest = WinHttpOpenRequest(hConnect, L"POST", url, NULL, WINHTTP_NO_REFERER, NULL, 0);
    if (!hRequest) {
        error = GetLastError();
        WinHttpCloseHandle(hSession);
        WinHttpCloseHandle(hConnect);
        wprintf(L"error opening request:\n\t%d\n", error);
        return error;
    }
    // Add headers
    LPCWSTR headerfields[] = { L"Accept",L"Content-type" };
    LPCWSTR headervalues[] = { accepttype,contenttype };
    for (int i = 0; i < 2; i++) {
        WCHAR header[2048];
        int result = swprintf_s(header, 2048, L"%s: %s", headerfields[i], headervalues[i]);
        if (result < 0) {
            wprintf(L"error formatting header with header field %s and header value %s\n", headerfields[i], headervalues[i]);
            return -1;
        }
        bResults = WinHttpAddRequestHeaders(
            hRequest,
            header,
            -1L,
            WINHTTP_ADDREQ_FLAG_ADD
        );
        if (!bResults) {
            error = GetLastError();
            WinHttpCloseHandle(hRequest);
            WinHttpCloseHandle(hSession);
            WinHttpCloseHandle(hConnect);
            wprintf(L"error adding header \"%s\":\n\t%d\n", header, error);
            return error;
        }
    }
    int len = strlen(inputdata);
    bResults = WinHttpSendRequest(hRequest,
        WINHTTP_NO_ADDITIONAL_HEADERS, 0,
        inputdata, len,
        len, 0);
    if (!bResults) {
        error = GetLastError();
        WinHttpCloseHandle(hRequest);
        WinHttpCloseHandle(hSession);
        WinHttpCloseHandle(hConnect);
        printf("error sending request:\n\t%d\n", error);
        return error;
    }
    // End the request.
    bResults = WinHttpReceiveResponse(hRequest, NULL);
    if (!bResults) {
        error = GetLastError();
        WinHttpCloseHandle(hRequest);
        WinHttpCloseHandle(hSession);
        WinHttpCloseHandle(hConnect);
        printf("error ending request:\n\t%d\n", error);
        return error;
    }
    int bufsize = 0;
    char* oldbuffer;
    char* buffer = NULL;
    do
    {
        // Check for available data.
        dwSize = 0;
        bResults = WinHttpQueryDataAvailable(hRequest, &dwSize);
        if (!bResults) {
            error = GetLastError();
            WinHttpCloseHandle(hRequest);
            WinHttpCloseHandle(hSession);
            WinHttpCloseHandle(hConnect);
            printf("error data query:\n\t%d\n", error);
            return error;
        }
        oldbuffer = buffer;
        buffer = (char*)malloc(sizeof(char) * (bufsize + dwSize + 1));
        if (!buffer) {
            printf("malloc failed\n");
            return -2;
        }
        int i;
        for (i = 0; i < bufsize; i++) {
            buffer[i] = oldbuffer[i];
        }
        if (i) {
            free(oldbuffer);
        }
        bResults = WinHttpReadData(hRequest, buffer + bufsize, dwSize, &dwDownloaded);
        if (!bResults) {
            error = GetLastError();
            WinHttpCloseHandle(hRequest);
            WinHttpCloseHandle(hSession);
            WinHttpCloseHandle(hConnect);
            printf("error data read:\n\t%d\n", error);
            return error;
        }
        bufsize += dwDownloaded;
        buffer[bufsize] = '\0';
    } while (dwDownloaded);
    *outputdata = buffer;
    *datalen = bufsize;
    WinHttpCloseHandle(hRequest);
    WinHttpCloseHandle(hSession);
    WinHttpCloseHandle(hConnect);
    return 0;
}