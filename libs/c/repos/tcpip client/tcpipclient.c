#include "tcpip.h"
#include <stdio.h>

#define DEFAULT_BUFLEN 512

int __cdecl main(int argc, char** argv)
{
    if (argc < 4) {
        printf("usage: tcpip.exe hostname portname stringtosend\n");
        return -1;
    }
    char term[] = "\r\n";
    char* hostname = argv[1];
    char* endptr;
    int port = strtol(argv[2], &endptr, 10);
    if (endptr == argv[2]) {
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
    error = connect_to_server(hostname, port, &server);
    if (error) {
        printf("error connecting to host %s at port %d\n",hostname,port);
        end_winsock();
        return -1;
    }
    error = write_line(server, argv[3], term);
    if (error) {
        printf("error writing line\n");
        close_connection(server);
        end_winsock();
        return -1;
    }
    char linebuffer[DEFAULT_BUFLEN];
    error = read_line(server, linebuffer, DEFAULT_BUFLEN, term);
    if (error) {
        printf("error reading line\n");
        close_connection(server);
        end_winsock();
        return -1;
    }
    printf("line read:\n\t%s\n", linebuffer);
    error = close_connection(server);
    if (error) {
        printf("error closing server connection\n");
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