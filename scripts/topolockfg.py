import topo
import numpy as np
import piezo
import laselock as ll
import funcgen as fg

DELTAVS = (2.0,1.0,0.6,0.25,0.10)
DVS = (100e-5,50e-5,25e-5,10e-5,1e-5)

PVo = 20.0

Vo = 2.0

def lock_topo():
    with fg.FuncGenHandler() as fgh:
        fg.set_output(fgh,1,False)
    with piezo.PiezoDriverHandler() as pdh:
        piezo.set_piezo_voltage(pdh,PVo)
    with ll.LaseLockHandler() as llh:
        try:
            ic = topo.InstructionClient()
            ll.set_reg_on_off(llh,ll.A,False)
            da = ll.get_li_ampl_aux(llh)
            ll.set_li_ampl_aux(llh,0.0)
            vo = Vo
            for dv, deltav in zip(DVS, DELTAVS):
                ic.set_wide_scan_begin(vo-deltav/2)
                ic.set_wide_scan_end(vo+deltav/2)
                ic.set_wide_scan_step(dv)
                wide_scan = topo.get_wide_scan()
                xdata, ydata, Ydata = map(np.array,wide_scan)
                nmax = ydata.argmax()
                xmax, ymax = xdata[nmax], ydata[nmax]
                print(deltav,':',xmax,',',ymax)
                vo = xmax
        finally:
            ll.set_li_ampl_aux(llh,da)
            with fg.FuncGenHandler() as fgh:
                fg.set_output(fgh,1,True)
        ic.set_output(topo.A,vo)
        ll.set_reg_on_off(llh,ll.A,True)
        
if __name__ == '__main__':
    lock_topo()
