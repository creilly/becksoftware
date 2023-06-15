# update 20230118

# dephasing rate in radians per microsecond
# vrms : noise amplitude into homemade 1MHz bandpass filter
# see domenico, ..., thomann APPLIED OPTICS / Vol. 49, No. 25 (2010) pg 4801
# and
# Z:\chris\scripts-data\2022\11\21\toponoisean\20221121\slope\fancyfit.png
#
dfdv = 0.096 # MHz rms per mV rms
fc = 15.3 # MHz effective topo bandwidth at 80 MHz nominal bandwidth
pi = 3.14159
# return dephasing rate gamma in radians / microsecond
def get_gamma(vrms):
    return 2 * pi / fc * (dfdv*vrms)**2

# vvv old

vrmso = 30 # millivolts
gammao = 80e6 # radians per second

# # vrms in millivolts
# # returns gamma in radians per second
def get_gamma_old(vrms):
    return (vrms/vrmso)**2 * gammao

if __name__ == '__main__':
    import numpy as np
    from matplotlib import pyplot as plt
    voltages = np.linspace(0,400,100)
    plt.plot(voltages,1e6*get_gamma(voltages),label='new')
    plt.plot(voltages,get_gamma_old(voltages),label='old')
    plt.legend()
    plt.show()