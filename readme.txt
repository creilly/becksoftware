pythonpath
----------

make sure the "PYTHONPATH" environment
variable points to the libs/ folder in
this repo's root directory

dll loading
-----------

for the daqmx and maxon libraries to work,
you must copy their associated dlls to the
folder that is pointed to by the "BECKDLL" 
environment variable.

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
		
* thorlabs rotation stage

	use the: "Thorlabs.MotionControl.Kinesis.DLLutility.exe" 
	utility to copy the necessary dlls for the device (right 
	now the TDC001) to the dlls folder

grapher data path
-----------------

the root of the file tree of grapher data is
the folder pointed to by the "GRAPHERPATH" 
environment variable.

https proxy config
------------------

to download from the command line from EPFL,
I have found it necessary to set the
"HTTPS_PROXY" environment variable to:

	      http://webproxy-slb.epfl.ch:8080/

