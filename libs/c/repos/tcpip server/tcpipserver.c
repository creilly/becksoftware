#include "tcpip.h"
#include <stdio.h>

#define DEFAULT_BUFLEN 512

int __cdecl main(int argc, char** argv)
{
    if (argc < 2) {
        printf("usage: tcpip.exe portname stringtosend\n");
        return -1;
    }
    char term[] = "\r\n";
    char* endptr;
    int port = strtol(argv[1], &endptr, 10);
    if (endptr == argv[1]) {
        printf("portname invalid. must be decimal integer\n");
        return -1;
    }
    int error;
    error = init_winsock();
    if (error) {
        printf("error intializing\n");
        return -1;
    }
    SOCKET server;
    error = create_server(&server, port);
    if (error) {
        printf("error binding server to port %d\n", port);
        end_winsock();
        return -1;
    }
    error = start_listening(server);
    if (error) {
        printf("error setting server to listening state\n");
        close_connection(server);
        end_winsock();
        return -1;
    }
    SOCKET client;
    error = get_client(server, &client);
    if (error) {
        printf("error setting server to listening state\n");
        close_connection(server);
        end_winsock();
        return -1;
    }
    error = closesocket(server);
    if (error) {
        printf("error closing server connection: %d\n",WSAGetLastError());
        close_connection(client);
        end_winsock();
        return -1;
    }
    if (error) {
        printf("error closing server connection\n");
        close_connection(client);
        end_winsock();
        return -1;
    }
    char linebuffer[DEFAULT_BUFLEN];
    error = read_line(client, linebuffer, DEFAULT_BUFLEN, term);
    if (error) {
        printf("error reading line\n");
        close_connection(client);
        end_winsock();
        return -1;
    }
    printf("line read:\n\t%s\n", linebuffer);
    error = write_line(client, argv[2], term);
    if (error) {
        printf("error writing line\n");
        close_connection(client);
        end_winsock();
        return -1;
    }
    error = close_connection(client);
    if (error) {
        printf("error closing client connection\n");
        end_winsock();
        return -1;
    }
    error = end_winsock();
    if (error) {
        printf("error closing winsock\n");
        return -1;
    }
    return 0;
}