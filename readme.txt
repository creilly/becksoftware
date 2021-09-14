dll loading
-----------

for the daqmx and maxon libraries to work,
you must copy their associated dlls to the
folder that is pointed to by the "BECKDLL"
(no quotes) environment variable.

* daqmx dll:

  	name:

		nicaiu.dll

	typical location:

		C:\Windows\System32

* maxon dll:

  	name:

		EposCmd64.dll

	typical location:

		C:\Program Files (x86)\
		maxon motor ag\
		EPOS Positioning Controller\
		EPOS2\
		04 Programming\
		Windows DLL\
		Microsoft Visual C++\
		Example VC++

grapher data path
-----------------

the root of the file tree of grapher data is
the folder pointed to by the "GRAPHERPATH" 
(no quotes) environment variable.
