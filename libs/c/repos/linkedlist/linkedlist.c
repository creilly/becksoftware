#include <stdio.h>

typedef struct node {
	int data;
	struct node* next;
} node_t;

void append(node_t** list_add, int data) {
	node_t* tail = (node_t*)malloc(sizeof(node_t));
	tail->data = data;
	tail->next = NULL;
	node_t** head_add = list_add;
	while (*head_add != NULL) {
		head_add = &(*head_add)->next;
	}
	*head_add = tail;
}

void print_list(node_t* list) {
	node_t* head = list;
	int i = 0;
	while (head != NULL) {
		printf("%d:\t%d\n", i, head->data);
		head = head->next;
		i += 1;
	}
	if (!i) {
		printf("list empty!\n");
	}
}

int pop(node_t** list_add, int* data_add) {
	node_t* old_head = *list_add;
	if (old_head == NULL) {
		return 0;
	}
	*data_add = old_head->data;
	node_t* new_head = old_head->next;
	free(old_head);
	*list_add = new_head;
	return 1;
}

int get_list_item(node_t* list, int index, int* data_add) {
	node_t* head = list;
	int i = 0;
	while (head != NULL) {
		if (i == index) {
			*data_add = head->data;
			return 1;
		}
		head = head->next;
		i++;
	}
	return 0;
}

int get_list_length(node_t* list) {
	node_t* head = list;
	int i = 0;
	while (head != NULL) {
		head = head->next;
		i++;
	}
	return i;
}

int main(void) {
	node_t* list = NULL;
	print_list(list);
	append(&list, 4);
	print_list(list);
	append(&list, 5);
	print_list(list);
	int data;
	int popped;
	printf("get item 0 result:\t%d\n", get_list_item(list, 0, &data));
	printf("item 0 value:\t%d\n", data);
	printf("get item 1 result:\t%d\n", get_list_item(list, 1, &data));
	printf("item 1 value:\t%d\n", data);
	printf("pop result:\t%d\n", pop(&list, &popped));
	printf("popped:\t%d\n", popped);
	printf("get item 0 result:\t%d\n", get_list_item(list, 0, &data));
	printf("item 0 value:\t%d\n", data);
	printf("get item 1 result:\t%d\n", get_list_item(list, 1, &data));
	printf("item 1 value:\t%d\n", data);
	printf("pop result:\t%d\n", pop(&list, &popped));
	printf("popped:\t%d\n", popped);
	printf("get item 0 result:\t%d\n", get_list_item(list, 0, &data));
	printf("item 0 value:\t%d\n", data);
	printf("get item 1 result:\t%d\n", get_list_item(list, 1, &data));
	printf("item 1 value:\t%d\n", data);
	printf("pop result:\t%d\n", pop(&list, &popped));
	printf("popped:\t%d\n", popped);
	printf("get item 0 result:\t%d\n", get_list_item(list, 0, &data));
	printf("item 0 value:\t%d\n", data);
	printf("get item 1 result:\t%d\n", get_list_item(list, 1, &data));
	printf("item 1 value:\t%d\n", data);
	return 0;
}