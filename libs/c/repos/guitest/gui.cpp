// HelloWindowsDesktop.cpp
// compile with: /D_UNICODE /DUNICODE /DWIN32 /D_WINDOWS /c

#include <windows.h>
#include <stdlib.h>
#include <string.h>
#include <tchar.h>
#include <NIDAQmx.h>
#include <stdio.h>
#include <math.h>

#define PI	3.1415926535
#define DATA_SIZE 33
#define BUF_SIZE 1000
#define PLOT_SIZE 1000

// Global variables

// waveform amplitude (volts)
float64 amplitude = 5.0;

// The main window class name.
static TCHAR szWindowClass[] = _T("DesktopApp");

// The string that appears in the application's title bar.
static TCHAR szTitle[] = _T("Windows Desktop Guided Tour Application");

HINSTANCE hInst;

// Forward declarations of functions included in this code module:
LRESULT CALLBACK WndProc(HWND, UINT, WPARAM, LPARAM);

// fwd decl of daqmx callback
int32 CVICALLBACK EveryNSamplesCallback(TaskHandle taskHandle, int32 everyNsamplesEventType, uInt32 nSamples, void* callbackData);

struct Waveform {
    float frequency;
    float amplitude;
    float mod_phase;
    float carrier_phase;
};

int CALLBACK WinMain(
    _In_ HINSTANCE hInstance,
    _In_opt_ HINSTANCE hPrevInstance,
    _In_ LPSTR     lpCmdLine,
    _In_ int       nCmdShow
)
{
    BOOL started = 0;
    int32       error = 0;
    TaskHandle  taskHandle = 0;
    float64     data[DATA_SIZE];

    float64     plot[PLOT_SIZE];
    for (int i = 0; i < PLOT_SIZE; i++) {
        plot[i] = 0.0;
    }
    uInt64      plot_index = 0;

    char        errBuff[2048] = { '\0' };
    float64		buffer_time = 1.0;
    float64		mod_period = 2.5;
    float64		carrier_period = .25;
    float64		delta_t = 0.01;
    uInt64		samples_generated = 0;
    uInt64		samples_written = 0;
    float64		mod_phase = 0;
    float64		carrier_phase = 0;
    int32		total_samples_to_write;
    int32		regen_mode;

    int32		buffer_width = buffer_time / delta_t;

    WNDCLASSEX wcex;

    wcex.cbSize = sizeof(WNDCLASSEX);
    wcex.style = CS_HREDRAW | CS_VREDRAW;
    wcex.lpfnWndProc = WndProc;
    wcex.cbClsExtra = 0;
    wcex.cbWndExtra = 0;
    wcex.hInstance = hInstance;
    wcex.hIcon = LoadIcon(hInstance, IDI_APPLICATION);
    wcex.hCursor = LoadCursor(NULL, IDC_ARROW);
    wcex.hbrBackground = (HBRUSH)(COLOR_WINDOW + 1);
    wcex.lpszMenuName = NULL;
    wcex.lpszClassName = szWindowClass;
    wcex.hIconSm = LoadIcon(wcex.hInstance, IDI_APPLICATION);

    if (!RegisterClassEx(&wcex))
    {
        MessageBox(NULL,
            _T("Call to RegisterClassEx failed!"),
            _T("Windows Desktop Guided Tour"),
            NULL);

        return 1;
    }

    // Store instance handle in our global variable
    hInst = hInstance;

    // The parameters to CreateWindow explained:
    // szWindowClass: the name of the application
    // szTitle: the text that appears in the title bar
    // WS_OVERLAPPEDWINDOW: the type of window to create
    // CW_USEDEFAULT, CW_USEDEFAULT: initial position (x, y)
    // 500, 100: initial size (width, length)
    // NULL: the parent of this window
    // NULL: this application does not have a menu bar
    // hInstance: the first parameter from WinMain
    // NULL: not used in this application
    HWND hWnd = CreateWindow(
        szWindowClass,
        szTitle,
        WS_OVERLAPPEDWINDOW,
        CW_USEDEFAULT, CW_USEDEFAULT,
        500, 100,
        NULL,
        NULL,
        hInstance,
        NULL
    );

    if (!hWnd)
    {
        MessageBox(NULL,
            _T("Call to CreateWindow failed!"),
            _T("Windows Desktop Guided Tour"),
            NULL);

        return 1;
    }

    /*********************************************/
    // DAQmx Configure Code
    /*********************************************/
    DAQmxErrChk(DAQmxCreateTask("", &taskHandle));
    DAQmxErrChk(DAQmxCreateAOVoltageChan(taskHandle, "maxwell/ao0", "", -10.0, 10.0, DAQmx_Val_Volts, NULL));
    DAQmxErrChk(DAQmxCfgSampClkTiming(taskHandle, "", 1 / delta_t, DAQmx_Val_Rising, DAQmx_Val_ContSamps, BUF_SIZE));
    DAQmxErrChk(DAQmxCfgOutputBuffer(taskHandle, BUF_SIZE));
    DAQmxErrChk(DAQmxSetWriteRegenMode(taskHandle, DAQmx_Val_DoNotAllowRegen));
    DAQmxErrChk(DAQmxRegisterEveryNSamplesEvent(taskHandle, DAQmx_Val_Transferred_From_Buffer, buffer_width / 2, 0, EveryNSamplesCallback, NULL));

    total_samples_to_write = buffer_width - (samples_written - samples_generated);
    while (total_samples_to_write > 0) {
        int32 samples_to_write = (total_samples_to_write < DATA_SIZE) ? total_samples_to_write : DATA_SIZE;
        for (int32 i = 0; i < samples_to_write; i++) {
            float64 amp = amplitude * sin(mod_phase) * sin(carrier_phase);
            data[i] = amp;
            plot[plot_index] = amp;
            plot_index += 1;
            plot_index = plot_index % PLOT_SIZE;
            mod_phase += delta_t * 2.0 * PI / mod_period;
            if (mod_phase > 2.0 * PI) {
                mod_phase -= 2.0 * PI;
            }
            carrier_phase += delta_t * 2.0 * PI / carrier_period;
            if (carrier_phase > 2.0 * PI) {
                carrier_phase -= 2.0 * PI;
            }
        }
        DAQmxWriteAnalogF64(taskHandle, samples_to_write, 0, 0, DAQmx_Val_GroupByChannel, data, NULL, NULL);
        total_samples_to_write -= samples_to_write;
        samples_written += samples_to_write;
    }
    DAQmxErrChk(DAQmxStartTask(taskHandle));

    // The parameters to ShowWindow explained:
    // hWnd: the value returned from CreateWindow
    // nCmdShow: the fourth parameter from WinMain
    ShowWindow(hWnd,
        nCmdShow);
    UpdateWindow(hWnd);


    // Main message loop:
    MSG msg;
    while (1)
    {
        if (PeekMessage(&msg, NULL, 0, 0, PM_NOREMOVE)) {
            started = 1;
            if (!GetMessage(&msg, NULL, 0, 0)) {
                break;
            }
            else {
                TranslateMessage(&msg);
                DispatchMessage(&msg);
            }    
        }
        DAQmxErrChk(DAQmxGetWriteTotalSampPerChanGenerated(taskHandle, &samples_generated));
        total_samples_to_write = buffer_width - (samples_written - samples_generated);
        int32 samples_to_write = 0;
        while (total_samples_to_write > 0) {
            samples_to_write = (total_samples_to_write < DATA_SIZE) ? total_samples_to_write : DATA_SIZE;
            for (int32 i = 0; i < samples_to_write; i++) {
                float64 amp = amplitude * sin(mod_phase) * sin(carrier_phase);
                data[i] = amp;
                plot[plot_index] = amp;
                plot_index += 1;
                plot_index = plot_index % PLOT_SIZE;
                mod_phase += delta_t * 2.0 * PI / mod_period;
                if (mod_phase > 2.0 * PI) {
                    mod_phase -= 2.0 * PI;
                }
                carrier_phase += delta_t * 2.0 * PI / carrier_period;
                if (carrier_phase > 2.0 * PI) {
                    carrier_phase -= 2.0 * PI;
                }
            }
            error = DAQmxWriteAnalogF64(taskHandle, samples_to_write, 0, 10.0, DAQmx_Val_GroupByChannel, data, NULL, NULL);
            char err_msg[256] = "";
            for (int i = 0; i < 256; i++) { err_msg[i] = 'x'; }
            if (error != 0) {
                DAQmxGetErrorString(error, err_msg, 256);
            }
            total_samples_to_write -= samples_to_write;
            samples_written += samples_to_write;
        }
        if (samples_to_write) {
            // RedrawWindow(hWnd, NULL, NULL, RDW_UPDATENOW);
        }
    }
Error:
    if (DAQmxFailed(error))
        DAQmxGetExtendedErrorInfo(errBuff, 2048);
    if (taskHandle != 0) {
        /*********************************************/
        // DAQmx Stop Code
        /*********************************************/
        DAQmxStopTask(taskHandle);
        DAQmxClearTask(taskHandle);
    }
    return started ? (int)msg.wParam : 0;
}

LRESULT CALLBACK WndProc(HWND hWnd, UINT uMsg, WPARAM wParam,
    LPARAM lParam)
{
    PAINTSTRUCT ps;
    LOGBRUSH lb;
    RECT rc;
    HDC hdc;
    int i;
    HGDIOBJ hPen = NULL;
    HGDIOBJ hPenOld;
    DWORD dwPenStyle[] = {
                           PS_DASH,
                           PS_DASHDOT,
                           PS_DOT,
                           PS_INSIDEFRAME,
                           PS_NULL,
                           PS_SOLID
    };
    UINT uHatch[] = {
                      HS_BDIAGONAL,
                      HS_CROSS,
                      HS_DIAGCROSS,
                      HS_FDIAGONAL,
                      HS_HORIZONTAL,
                      HS_VERTICAL
    };

    switch (uMsg)
    {
    case WM_PAINT:
    {
        GetClientRect(hWnd, &rc);
        rc.left += 10;
        rc.top += 10;
        rc.bottom -= 10;

        // Initialize the pen's brush.
        lb.lbStyle = BS_SOLID;
        lb.lbColor = RGB(255, 0, 0);
        lb.lbHatch = 0;

        hdc = BeginPaint(hWnd, &ps);
        for (i = 0; i < 6; i++)
        {
            hPen = ExtCreatePen(PS_COSMETIC | dwPenStyle[i],
                1, &lb, 0, NULL);
            hPenOld = SelectObject(hdc, hPen);
            MoveToEx(hdc, rc.left + (i * 20), rc.top, NULL);
            LineTo(hdc, rc.left + (i * 20), rc.bottom);
            SelectObject(hdc, hPenOld);
            DeleteObject(hPen);
        }
        rc.left += 150;
        for (i = 0; i < 6; i++)
        {
            lb.lbStyle = BS_HATCHED;
            lb.lbColor = RGB(0, 0, 255);
            lb.lbHatch = uHatch[i];
            hPen = ExtCreatePen(PS_GEOMETRIC,
                5, &lb, 0, NULL);
            hPenOld = SelectObject(hdc, hPen);
            MoveToEx(hdc, rc.left + (i * 20), rc.top, NULL);
            LineTo(hdc, rc.left + (i * 20), rc.bottom);
            SelectObject(hdc, hPenOld);
            DeleteObject(hPen);
        }
        EndPaint(hWnd, &ps);

    }
    break;

    case WM_DESTROY:
        DeleteObject(hPen);
        PostQuitMessage(0);
        break;

    default:
        return DefWindowProc(hWnd, uMsg, wParam, lParam);
    }

    return FALSE;
}