#include <stdio.h>
#include "list.h"

void append(client_queue* list_add, SOCKET client) {
	node_t* tail = (node_t*)malloc(sizeof(node_t));
	tail->client = client;
	tail->next = NULL;
	node_t** head_add = list_add;
	while (*head_add != NULL) {
		head_add = &(*head_add)->next;
	}
	*head_add = tail;
}

int pop(client_queue* list_add, SOCKET* client_add) {
	node_t* old_head = *list_add;
	if (old_head == NULL) {
		return 0;
	}
	*client_add = old_head->client;
	node_t* new_head = old_head->next;
	free(old_head);
	*list_add = new_head;
	return 1;
}

int get_list_item(client_queue list, int index, SOCKET* client_add) {
	node_t* head = list;
	int i = 0;
	while (head != NULL) {
		if (i == index) {
			*client_add = head->client;
			return 1;
		}
		head = head->next;
		i++;
	}
	return 0;
}

int get_list_length(client_queue list) {
	node_t* head = list;
	int i = 0;
	while (head != NULL) {
		head = head->next;
		i++;
	}
	return i;
}

void print_list(client_queue list) {
	node_t* head = list;
	int i = 0;
	while (head != NULL) {
		printf("%d:\t%u\n", i, head->client);
		head = head->next;
		i += 1;
	}
	if (!i) {
		printf("list empty!\n");
	}
}