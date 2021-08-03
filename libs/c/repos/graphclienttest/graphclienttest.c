#include "graphclient.h"

int main(int argc, char* argv[]) {
	char* folder[] = {
		"2021","04"
	};
	char** files;
	int nfiles;
	char** folders;
	int nfolders;
	int error = get_dir(folder, 2, &files, &nfiles, &folders, &nfolders);
	if (error) {
		printf("graphclienttest error:\t%d\n",error);
		return -1;
	}
	for (int i = 0; i < nfolders; i++) {
		printf("folder #%d:\t%s\n", i, folders[i]);
	}
	free_folder(files, nfiles);
	free_folder(folders, nfolders);
}