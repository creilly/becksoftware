#pragma once
#include "server.h"

typedef struct node {
	SOCKET client;
	struct node* next;
} node_t;

typedef node_t* client_queue;

void append(client_queue* list_add, SOCKET client);
int pop(client_queue* list_add, SOCKET* client_add);
int get_list_item(client_queue list, int index, SOCKET* client_add);
int get_list_length(client_queue list);
void print_list(client_queue list);