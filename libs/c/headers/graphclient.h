#pragma once
int get_day_folder(char** folder_ptr[], int* nlevels);
int get_dir(char* folder[], int nlevels, char** files[], int* nfiles, char** folders[], int* nfolders);
int add_dataset(char* folder[], int nfoldlets, char name[], char* fields[], int nfields, char** path[], int* npathlets);
int add_data(char* path[], int npathlets, double data[], int datalen);
void free_folder(char* folder[], int nlevels);
int concat_folders(char* foldera[], int nfoldera, char* folderb[], int nfolderb, char** folder_ptr, int* nfolder);
int add_folder(char* folder[], int nlevels);