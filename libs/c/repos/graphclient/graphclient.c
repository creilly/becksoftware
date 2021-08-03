#include "httprequest.h"
#include "json.h"
#include <stdio.h>
#include "graphclient.h"
#include <math.h>

#define GRAPHHOST L"127.0.0.1"
#define GRAPHPORT 8000
#define JSONTYPE L"application/json"
#define GRAPHBUFLEN 2048
#define GRAPHCOMMAND "command"
#define GRAPHPARAMETERS "parameters"
#define GRAPHERROR "_error"

json_object* format_folder(char* folder[], int nlevels) {
	json_object* folder_obj = json_object_new_array();
	for (int i = 0; i < nlevels; i++) {
		json_object_array_add(folder_obj, json_object_new_string(folder[i]));
	}
	return folder_obj;
}

int get_day_folder(char** folder_ptr[], int* nlevels) {
	json_object* parameters = json_object_new_object();
	json_object* response;
	int error = graph_request("get-day-folder", parameters, &response);
	if (error) { return error; }
	error = parse_folder(response, folder_ptr, nlevels);
	json_object_put(response);
	if (error) { return error; }
	return 0;
}

int get_dir(char* folder[], int nlevels, char** files[], int* nfiles, char** folders[], int* nfolders) {
	json_object* parameters = json_object_new_object();
	json_object_object_add(parameters, "folder", format_folder(folder, nlevels));
	json_object* response;
	int error = graph_request("get-dir", parameters, &response);
	if (error) { return error; }
	error = parse_folder(json_object_array_get_idx(response, 0), files, nfiles);
	if (error) { return error; }
	error = parse_folder(json_object_array_get_idx(response, 1), folders, nfolders);
	if (error) { return error; }
	json_object_put(response);
	return 0;
}

json_object* _construct_json_request(char commandstr[], json_object* parameters) {
	json_object* request = json_object_new_object();
	json_object* command = json_object_new_string(commandstr);
	json_object_object_add(request, GRAPHCOMMAND, command);
	json_object_object_add(request, GRAPHPARAMETERS, parameters);
	return request;
}

int _graph_request(json_object* request, json_object** response) {
	*response = NULL;
	char* outputdata;
	int datalen;
	int error = post_request(GRAPHHOST, GRAPHPORT, L"", JSONTYPE, JSONTYPE, json_object_to_json_string(request), &outputdata, &datalen);
	if (error) {
		printf("error in graph http request:\t%d\n", error);
		return error;
	}
	if (!datalen) {
		printf("http response empty\n");
		return -3;
	}
	*response = json_tokener_parse(outputdata);
	free(outputdata);
	if (!*response) {
		printf("json response parsing failed\n");
		return -2;
	}
	json_object** errorobject;
	if (json_object_is_type(*response, json_type_object) && json_object_object_get_ex(*response, GRAPHERROR, &errorobject)) {
		printf("graphclient error: %s\n", json_object_to_json_string(errorobject));
		return -1;
	}
	return 0;
}

int graph_request(char commandstr[], json_object* parameters, json_object** response) {
	json_object* request = _construct_json_request(commandstr, parameters);
	int error = _graph_request(request, response);
	json_object_put(request);
	if (error) {
		printf("error in graph request for command %s:\t%d\n", commandstr, error);
		return error;
	}
	return 0;
}

int parse_folder(json_object* folder_obj, char** folder_ptr[], int* nlevels) {
	*nlevels = json_object_array_length(folder_obj);
	char** folder = (char**)malloc(sizeof(char*) * *nlevels);
	if (!folder) {
		printf("error allocating memory for day folder\n");
		return -2;
	}
	for (int i = 0; i < *nlevels; i++) {
		json_object* foldlet_obj = json_object_array_get_idx(folder_obj, i);
		int foldletlen = json_object_get_string_len(foldlet_obj);
		char* foldlet = (char*)malloc(sizeof(char) * (foldletlen + 1));
		if (!foldlet) {
			printf("error allocating foldlet memory\n");
			return -2;
		}
		strcpy_s(foldlet, foldletlen + 1, json_object_get_string(foldlet_obj));
		folder[i] = foldlet;
	}
	*folder_ptr = folder;
	return 0;
}

int add_dataset(char* folder[], int nfoldlets, char name[], char* fields[], int nfields, char** path[], int* npathlets) {
	json_object* parameters = json_object_new_object();
	json_object_object_add(parameters, "folder", format_folder(folder, nfoldlets));
	json_object_object_add(parameters, "name", json_object_new_string(name));
	json_object_object_add(parameters, "fields", format_folder(fields, nfields));
	json_object* response;
	int error = graph_request("add-dataset", parameters, &response);
	if (error) { return error; }
	error = parse_folder(response, path, npathlets);
	json_object_put(response);
	if (error) { return error; }
	return 0;
}

json_object* format_data(double data[], int datalen) {
	json_object* data_obj = json_object_new_array();
	for (int i = 0; i < datalen; i++) {
		json_object_array_add(data_obj, json_object_new_double(data[i]));
	}
	return data_obj;
}

int add_data(char* path[], int npathlets, double data[], int datalen) {
	json_object* parameters = json_object_new_object();
	json_object_object_add(parameters, "path", format_folder(path, npathlets));
	json_object_object_add(parameters, "data", format_data(data,datalen));
	json_object* response;
	int error = graph_request("add-data", parameters, &response);
	json_object_put(response);
	return error;
}

int get_data(char* path[], int npathlets) {
	json_object* parameters = json_object_new_object();
	json_object_object_add(parameters, "path", format_folder(path, npathlets));
	json_object* response;
	int error = graph_request("get-data", parameters, &response);
	json_object_put(response);
	return error;
}

int add_folder(char* folder[], int nlevels) {
	json_object* parameters = json_object_new_object();
	json_object_object_add(parameters, "folder", format_folder(folder, nlevels));
	json_object* response;
	int error = graph_request("add-folder", parameters, &response);
	if (error) { return error; }
	json_object_put(response);
	return 0;
}

void free_folder(char* folder[], int nlevels) {
	for (int i = 0; i < nlevels; i++) {
		free(folder[i]);
	}
	free(folder);
}

void print_folder(char* folder[], int nlevels) {
	for (int i = 0; i < nlevels; i++) {
		printf("folder at level %d:\t%s\n", i, folder[i]);
	}
}

int concat_folders(char* foldera[], int nfoldera, char* folderb[], int nfolderb, char** folder_ptr, int* nfolder) {
	char** folder = (char**)malloc(sizeof(char*) * (nfoldera + nfolderb));
	if (!folder) {
		printf("malloc error\n");
		return -2;
	}
	for (int i = 0; i < nfoldera; i++) {
		folder[i] = foldera[i];
	}
	for (int i = 0; i < nfolderb; i++) {
		folder[nfoldera+i] = folderb[i];
	}
	*folder_ptr = folder;
	*nfolder = nfoldera + nfolderb;
	return 0;
}