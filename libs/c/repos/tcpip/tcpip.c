#include <winsock2.h>
#include <ws2tcpip.h>
#include <stdio.h>

// Need to link with Ws2_32.lib, Mswsock.lib, and Advapi32.lib
#pragma comment (lib, "Ws2_32.lib")
#pragma comment (lib, "Mswsock.lib")
#pragma comment (lib, "AdvApi32.lib")

int init_winsock() {
    WSADATA wsaData;
    // Initialize Winsock
    int iResult = WSAStartup(MAKEWORD(2, 2), &wsaData);
    if (iResult != 0) {
        printf("WSAStartup failed with error: %d\n", iResult);
        return 1;
    }
    return 0;
}

int end_winsock() {
    int error = WSACleanup();
    if (error == SOCKET_ERROR) {
        printf("winsock end failed with error: %d\n", WSAGetLastError());
        return 1;
    }
    return 0;
}

// listen on all interfaces
int create_server(SOCKET* server, int port) {
    int iResult;

    SOCKET ListenSocket = INVALID_SOCKET;

    struct addrinfo* result = NULL;
    struct addrinfo hints;

    ZeroMemory(&hints, sizeof(hints));
    hints.ai_family = AF_INET;
    hints.ai_socktype = SOCK_STREAM;
    hints.ai_protocol = IPPROTO_TCP;
    hints.ai_flags = AI_PASSIVE;

    // Resolve the server address and port
    char portname[16];
    int fmt_result = sprintf_s(portname, 16, "%d", port);
    if (fmt_result < 0) {
        printf("error formatting portname");
        return 1;
    }

    // Resolve the server address and port
    iResult = getaddrinfo(NULL, portname, &hints, &result);
    if (iResult != 0) {
        printf("getaddrinfo failed with error: %d\n", iResult);
        return 1;
    }

    // Create a SOCKET for connecting to server
    ListenSocket = socket(result->ai_family, result->ai_socktype, result->ai_protocol);
    if (ListenSocket == INVALID_SOCKET) {
        printf("socket failed with error: %ld\n", WSAGetLastError());
        freeaddrinfo(result);
        return 1;
    }

    // // vvv set to non-blocking
    //ULONG iMode = 1;
    //iResult = ioctlsocket(ListenSocket, FIONBIO, &iMode);
    //if (iResult != 0) {
    //    printf("Error at socket(): %ld\n", WSAGetLastError());
    //    freeaddrinfo(result);
    //    closesocket(ListenSocket);
    //    WSACleanup();
    //    return 1;
    //}

    // Setup the TCP listening socket
    iResult = bind(ListenSocket, result->ai_addr, (int)result->ai_addrlen);
    if (iResult == SOCKET_ERROR) {
        printf("bind failed with error: %d\n", WSAGetLastError());
        freeaddrinfo(result);
        closesocket(ListenSocket);
        return 1;
    }

    freeaddrinfo(result);

    *server = ListenSocket;

    return 0;
}

int start_listening(SOCKET socket) {
    int iResult = listen(socket, SOMAXCONN);
    if (iResult == SOCKET_ERROR) {
        printf("listen failed with error: %d\n", WSAGetLastError());
        return 1;
    }
    return 0;
}

// wait indefinitely
int get_client(SOCKET server, SOCKET* client) {
    *client = accept(server, NULL, NULL);
    if (*client == INVALID_SOCKET) {
        printf("accept failed with error: %d\n", WSAGetLastError());
        return 1;
    }
    return 0;
}

int connect_to_server(char servername[], int port, SOCKET* server) {
    SOCKET ConnectSocket = INVALID_SOCKET;
    struct addrinfo* result = NULL,
        * ptr = NULL,
        hints;
    int iResult;

    ZeroMemory(&hints, sizeof(hints));
    hints.ai_family = AF_UNSPEC;
    hints.ai_socktype = SOCK_STREAM;
    hints.ai_protocol = IPPROTO_TCP;

    // Resolve the server address and port
    char portname[16];
    int fmt_result = sprintf_s(portname, 16, "%d", port);
    if (fmt_result < 0) {
        printf("error formatting portname");
        return 1;
    }
    iResult = getaddrinfo(servername, portname, &hints, &result);
    if (iResult != 0) {
        printf("getaddrinfo failed with error: %d\n", iResult);
        return 1;
    }

    // Attempt to connect to an address until one succeeds
    for (ptr = result; ptr != NULL; ptr = ptr->ai_next) {

        // Create a SOCKET for connecting to server
        ConnectSocket = socket(ptr->ai_family, ptr->ai_socktype,
            ptr->ai_protocol);
        if (ConnectSocket == INVALID_SOCKET) {
            printf("socket failed with error: %ld\n", WSAGetLastError());
            return 1;
        }

        // Connect to server.
        iResult = connect(ConnectSocket, ptr->ai_addr, (int)ptr->ai_addrlen);
        if (iResult == SOCKET_ERROR) {
            closesocket(ConnectSocket);
            ConnectSocket = INVALID_SOCKET;
            continue;
        }
        break;
    }

    freeaddrinfo(result);

    if (ConnectSocket == INVALID_SOCKET) {
        printf("Unable to connect to server!\n");
        return 1;
    }

    *server = ConnectSocket;
    return 0;
}

int close_connection(SOCKET socket) {
    int iResult = shutdown(socket, SD_SEND);
    if (iResult == SOCKET_ERROR) {
        printf("shutdown failed with error: %d\n", WSAGetLastError());
        closesocket(socket);
        return 1;
    }
    iResult = closesocket(socket);
    if (iResult == SOCKET_ERROR) {
        printf("winsock end failed with error: %d\n", WSAGetLastError());
        return 1;
    }
    return 0;
}

int read_line(SOCKET socket, char line[], int len, char term[]) {
    while (1) {
        int result = recv(socket, line, len - 1, MSG_PEEK);
        int error;
        if (result == SOCKET_ERROR) {
            error = WSAGetLastError();
            printf("recv peek failed with error: %d\n", error);
            return 1;
        }
        if (result == 0) {
            printf("connection closed\n");
            return 1;
        }
        line[result] = '\0';
        char* termstart = strstr(line, term);
        if (termstart == NULL) {
            // printf("received incomplete message:\n\t%s\n", line);
            continue;
        }
        int linelen = termstart - line + strlen(term);
        result = recv(socket, line, termstart - line + strlen(term), 0);
        if (result == 0) {
            printf("connection closed\n");
            return 1;
        }
        if (result == SOCKET_ERROR) {
            error = WSAGetLastError();
            if (error != WSAEMSGSIZE) {
                printf("recv failed with error: %d\n", error);
                return 1;
            }
        }
        line[result] = '\0';
        return 0;
    }
}

int write_string(SOCKET socket, char buff[]) {
    int result = send(socket, buff, strlen(buff), 0);
    if (result == SOCKET_ERROR) {
        printf("socket failed with error: %d\n", WSAGetLastError());
        return 1;
    }
    return 0;
}

int write_line(SOCKET socket, char line[], char term[]) {
    char* strings[] = { line,term };
    int result;
    for (int i = 0; i < 2; i++) {
        result = write_string(socket, strings[i]);
        if (result) {
            return result;
        }
    }
    return 0;
}