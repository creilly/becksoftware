#undef UNICODE

#define WIN32_LEAN_AND_MEAN

#include <windows.h>
#include "server.h"
#include <ws2tcpip.h>
#include <stdlib.h>
#include <stdio.h>

// Need to link with Ws2_32.lib
#pragma comment (lib, "Ws2_32.lib")
// #pragma comment (lib, "Mswsock.lib")

#define DEFAULT_BUFLEN 512
#define DEFAULT_PORT "27015"

int create_server(SOCKET* server_socket_add) {
    WSADATA wsaData;
    int iResult;

    SOCKET ListenSocket = INVALID_SOCKET;

    struct addrinfo* result = NULL;
    struct addrinfo hints;

    // Initialize Winsock
    iResult = WSAStartup(MAKEWORD(2, 2), &wsaData);
    if (iResult != 0) {
        printf("WSAStartup failed with error: %d\n", iResult);
        return 1;
    }

    ZeroMemory(&hints, sizeof(hints));
    hints.ai_family = AF_INET;
    hints.ai_socktype = SOCK_STREAM;
    hints.ai_protocol = IPPROTO_TCP;
    hints.ai_flags = AI_PASSIVE;

    // Resolve the server address and port
    iResult = getaddrinfo(NULL, DEFAULT_PORT, &hints, &result);
    if (iResult != 0) {
        printf("getaddrinfo failed with error: %d\n", iResult);
        WSACleanup();
        return 1;
    }

    // Create a SOCKET for connecting to server
    ListenSocket = socket(result->ai_family, result->ai_socktype, result->ai_protocol);
    if (ListenSocket == INVALID_SOCKET) {
        printf("socket failed with error: %ld\n", WSAGetLastError());
        freeaddrinfo(result);
        WSACleanup();
        return 1;
    }

    ULONG iMode = 1;
    iResult = ioctlsocket(ListenSocket, FIONBIO, &iMode);
    if (iResult != 0) {
        printf("Error at socket(): %ld\n", WSAGetLastError());
        freeaddrinfo(result);
        closesocket(ListenSocket);
        WSACleanup();
        return 1;
    }

    // Setup the TCP listening socket
    iResult = bind(ListenSocket, result->ai_addr, (int)result->ai_addrlen);
    if (iResult == SOCKET_ERROR) {
        printf("bind failed with error: %d\n", WSAGetLastError());
        freeaddrinfo(result);
        closesocket(ListenSocket);
        WSACleanup();
        return 1;
    }

    freeaddrinfo(result);

    iResult = listen(ListenSocket, SOMAXCONN);
    if (iResult == SOCKET_ERROR) {
        printf("listen failed with error: %d\n", WSAGetLastError());
        closesocket(ListenSocket);
        WSACleanup();
        return 1;
    }
    *server_socket_add = ListenSocket;
    return 0;
}

int get_client(SOCKET server_socket, SOCKET* client_socket, int* client_available) {
    *client_socket = accept(server_socket, NULL, NULL);
    if (*client_socket == INVALID_SOCKET) {
        int error = WSAGetLastError();
        if (error == WSAEWOULDBLOCK) {
            *client_available = 0;
            return 0;
        }
        else {
            printf("accept failed with error: %d\n", WSAGetLastError());
            closesocket(server_socket);
            WSACleanup();
            return 1;
        }
    }
    else {
        *client_available = 1;
        return 0;
    }
}
Message create_message(SOCKET client)
{
    Message msg;
    msg.length = 0;
    msg.triggered = 0;
    msg.client = client;
    msg.buffer[0] = '\0';
    return msg;
}
// 0    :   no error
// +1   :   socket error
// -1   :   connection closed
// -2   :   max message length exceeded
// -3   :   message handled
int update_message(Message* msg) {
    int result = recv(msg->client, msg->buffer + msg->length, MSG_BUFF_LENGTH - msg->length, 0);
    if (result == SOCKET_ERROR) {
        int error = WSAGetLastError();
        if (error != WSAEWOULDBLOCK) {
            printf("recv failed with error: %d\n", WSAGetLastError());
            closesocket(msg->client);
            WSACleanup();
            return 1;
        }
        else {
            return 0;
        }
    }
    else if (result > 0) {
        int chars_read = result;
        printf("Bytes received: %d\n", chars_read);
        for (int i = 0; i < chars_read; i++) {
            char c = msg->buffer[msg->length];
            msg->length += 1;
            if (msg->length == MSG_BUFF_LENGTH) {
                return -2;
            }
            if (c == '\r') {
                msg->triggered = 1;
            }
            else {
                if (msg->triggered && c == '\n') {
                    msg->buffer[msg->length] = '\0';
                    printf("message received:\n\t%s\n", msg->buffer);
                    return -3;
                }
                msg->triggered = 0;
            }
        }
        return 0;
    }
    else if (result == 0) {
        printf("Connection closed...\n");
        return -1;
    }
}

int send_message(SOCKET client, char msg_buf[], int length) {
    int offset = 0;
    do {
        int result = send(client, msg_buf + offset, length-offset, 0);
        if (result == SOCKET_ERROR) {
            printf("send failed with error: %d\n", WSAGetLastError());
            closesocket(client);
            WSACleanup();
            return 1;
        }
        //char* tmp_buff = (char*)malloc(sizeof(char)*(result+1));
        //for (int i = 0; i < result; i++) {
        //    tmp_buff[i] = msg_buf[offset + i];
        //}
        //tmp_buff[result] = '\0';
        //printf("sending:\t%s\n",tmp_buff);
        //free(tmp_buff);
        offset += result;
    } while (offset < length);
    return 0;
}

int close_client(SOCKET client) {
    int error = shutdown(client, SD_SEND);
    if (error == SOCKET_ERROR) {
        printf("shutdown failed with error: %d\n", WSAGetLastError());
        closesocket(client);
        return 1;
    }
    // cleanup
    closesocket(client);
    return 0;
}