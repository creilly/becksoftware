#pragma once
#include <winsock2.h>

// low level functions
int init_winsock();
int end_winsock();
int close_connection(SOCKET socket);

// server functions
int create_server(SOCKET* server, int port);
int start_listening(SOCKET socket);
int get_client(SOCKET server, SOCKET* client);

// client functions
int connect_to_server(char servername[], int port, SOCKET* server);

// communcation functions
int read_line(SOCKET socket, char line[], int len, char term[]);
int write_string(SOCKET socket, char buff[]);
int write_line(SOCKET socket, char line[], char term[]);