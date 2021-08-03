#include "tcpip.h"
#include <stdio.h>
#include "topo.h"

#define TOPOIP "10.10.10.10"
#define COMMANDPORT 1998
#define BUFLEN 2048
#define COMMANDREADTERM "\n> "
#define WRITETERM "\n"

int init_session() {
	int error;
	error = init_winsock();
	if (error) {
		printf("error intializing winsock\n");
		return -1;
	}
	return 0;
}

int end_session() {
	int error;
	error = end_winsock();
	if (error) {
		printf("error ending winsock\n");
		return -1;
	}
	return 0;
}

int connect_topo(topohandle* socket) {
	if (connect_to_server(TOPOIP, COMMANDPORT, socket)) { return 1; }
	// read greeting
	char readbuf[BUFLEN];
	if (read_response(*socket, readbuf, BUFLEN)) { return 1; }
	return 0;
}

int disconnect_topo(topohandle socket) {
	int error = close_connection(socket);
	if (error) {
		printf("error disconnecting from topo\n");
		return -1;
	}
}

int get_temperature(topohandle socket, double* temperature) {
	char buf[BUFLEN];
	if (get_param(socket, "laser1:dl:tc:temp-set", buf, BUFLEN)) { return 1; }
	if (parse_float(buf, temperature)) { return 1; }
	return 0;
}

int set_temperature(topohandle socket, double temperature) {
	char buf[BUFLEN];
	char val[BUFLEN];
	if (format_float(temperature, val, BUFLEN)) { return 1; }
	if (set_param(socket, "laser1:dl:tc:temp-set", val)) { return 1; }
	return 0;
}

int get_current(topohandle socket, double* current) {
	char buf[BUFLEN];
	if (get_param(socket, "laser1:dl:cc:current-set", buf, BUFLEN)) { return 1; }
	if (parse_float(buf, current)) { return 1; }
	return 0;
}

int set_current(topohandle socket, double current) {
	char buf[BUFLEN];
	char val[BUFLEN];
	if (format_float(current, val, BUFLEN)) { return 1; }
	if (set_param(socket, "laser1:dl:cc:current-set", val)) { return 1; }
	return 0;
}

int get_etalon(topohandle socket, int* etalon) {
	char buf[BUFLEN];
	if (get_param(socket, "laser1:nlo:servo:etalon:value", buf, BUFLEN)) { return 1; }
	if (parse_int(buf, etalon)) { return 1; }
	return 0;
}

int set_etalon(topohandle socket, int etalon) {
	char buf[BUFLEN];
	char val[BUFLEN];
	if (format_int(etalon, val, BUFLEN)) { return 1; }
	if (set_param(socket, "laser1:nlo:servo:etalon:value", val)) { return 1; }
	return 0;
}

int get_param(topohandle socket, char param[], char paramval[], int buflen) {
	char buf[BUFLEN];
	int result = sprintf_s(buf, BUFLEN, "(param-ref \'%s)", param);
	if (result < 0) {
		printf("error formatting param %s\n", param);
		return 1;
	}
	if (send_command(socket, buf)) { return 1; }
	if (read_response(socket, paramval, buflen)) { return 1; }
	return 0;
}

int set_param(topohandle socket, char param[], char paramval[]) {
	char buf[BUFLEN];
	int result = sprintf_s(buf, BUFLEN, "(param-set! \'%s %s)", param, paramval);
	if (result < 0) {
		printf("error formatting command to set param %s to %s\n", param, paramval);
	}
	if (send_command(socket, buf)) { return 1; }
	if (read_response(socket, buf, BUFLEN)) { return 1; }
	if (parse_int(buf, &result)) { return 1; }
	if (result < 0) {
		printf("topo responded with error for param set of %s to %s\n", param, paramval);
		return 1;
	}
	return 0;
}

int send_command(topohandle socket, char command[]) {
	if (write_line(socket, command, WRITETERM)) { return 1; }
	return 0;
}

int read_response(topohandle socket, char buf[], int buflen) {
	if (read_line(socket, buf, buflen, COMMANDREADTERM)) { return 1; }
	return 0;
}

int parse_float(char raw[], double* value) {
	char* endptr;
	*value = strtod(raw, &endptr);
	if (endptr == raw) {
		printf("error parsing raw float %s\n", raw);
		return 1;
	}
	return 0;
}

int parse_int(char raw[], int* value) {
	char* endptr;
	*value = strtol(raw, &endptr, 10);
	if (endptr == raw) {
		printf("error parsing raw int %s\n", raw);
		return 1;
	}
	return 0;
}

int format_int(int value, char string[], int len) {
	int result = sprintf_s(string, len, "%d", value);
	if (result < 0) {
		printf("error formatting int %d\n", value);
		return 1;
	}
	return 0;
}

int format_float(double value, char string[], int len) {
	int result = sprintf_s(string, len, "%f", value);
	if (result < 0) {
		printf("error formatting float %f\n", value);
		return 1;
	}
	return 0;
}