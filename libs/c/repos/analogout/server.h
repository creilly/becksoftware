#pragma once

#include <winsock2.h>

#define MSG_BUFF_LENGTH 256
typedef struct {
	SOCKET	client;
	int		triggered;
	char	buffer[MSG_BUFF_LENGTH];
	int		length;
} Message;

int create_server(SOCKET* server_socket_add);
int get_client(SOCKET server_socket, SOCKET* client_socket, int* client_available);
Message create_message(SOCKET client);
int update_message(Message* msg);
int send_message(SOCKET client, char msg_buf[], int length);
int close_client(SOCKET client);