#pragma once
typedef unsigned int topohandle;
int init_session();
int end_session();
int connect_topo(topohandle* socket);
int disconnect_topo(topohandle socket);
int get_current(topohandle socket, double* current);
int set_current(topohandle socket, double current);
int get_etalon(topohandle socket, int* etalon);
int set_etalon(topohandle socket, int etalon);
int get_temperature(topohandle socket, double* temperature);
int set_temperature(topohandle socket, double temperature);