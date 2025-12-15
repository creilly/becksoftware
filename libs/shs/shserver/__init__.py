import beckhttpserver as bhs, time
import sampleheater, topo, socket

CU_HV_RELAY = 5
EC_RES = 50 # ohm
EC_TOPO_CHAN = topo.FINE2
TOPO_TIMEOUT = 0.25
class SampleHeaterApp(bhs.BeckApp):
    def __init__(
            self,
            sh_handle : sampleheater.SampleHeaterHandler,            
        ):
        self.sh = sh_handle  
        self._connect_topo()

    def _connect_topo(self):
        try:  
            self.ic = topo.InstructionClient(TOPO_TIMEOUT)
        except socket.timeout:
            print('topo connection timed out.')
            self.ic = None

    @bhs.command('reconnect topo')
    def reconnect_topo(self):
        return self._connect_topo()

    @bhs.command('get temperature')
    def get_delay(self):
        return self.sh.get_temperature()
    
    @bhs.command('get operation mode')
    def get_operation_mode(self):
        return self.sh.get_operation_mode()

    @bhs.command('goto operate')
    def goto_operate(self):
        self.sh.go_to_operate()

    @bhs.command('goto standby')
    def goto_standby(self):
        self.sh.go_to_standby()

    @bhs.command('get cc sp')
    def get_cc_sp(self):
        return self.sh.get_cc_setpoint()
    
    @bhs.command('get cc')
    def get_cc(self):
        return self.sh.get_cc()
    
    @bhs.command('get cv')
    def get_cv(self):
        return self.sh.get_cv()
    
    @bhs.command('set cc sp')
    def set_cc_sp(self,cc):
        self.sh.set_cc_setpoint(cc)
    
    @bhs.command('get ev sp')
    def get_ev_sp(self):
        return self.sh.get_ev_setpoint()
    
    @bhs.command('get ev')
    def get_ev(self):
        return self.sh.get_ev()
    
    @bhs.command('get ec')
    def get_ec(self):
        if self.ic is None:
            return None
        try:            
            ec = self.ic.get_input(EC_TOPO_CHAN) / EC_RES            
            return ec
        except (socket.timeout,ConnectionError,TimeoutError) as e:
            print('error on emission current read:',e)
            self.ic = None
            return None
    
    @bhs.command('set ev sp')
    def set_ev_sp(self,ev):
        self.sh.set_ev_setpoint(ev)
    
    @bhs.command('get heating mode')
    def get_heating_mode(self):
        return self.sh.get_heating_mode()
    
    @bhs.command('set heating mode')
    def set_heating_mode(self,heating_mode):
        self.sh.set_heating_mode(heating_mode)
        self._set_hv(
            {
                sampleheater.RES:False,
                sampleheater.EB:True
            }[heating_mode]
        )

    @bhs.command('get hv')
    def get_hv(self):
        return self.sh.get_relay_mode(CU_HV_RELAY) == self.sh.ST_ON
    
    @bhs.command('set hv')
    def set_hv(self,enabled):        
        self._set_hv(enabled)

    def _set_hv(self,enabled):
        return self.sh.set_relay_mode(
            CU_HV_RELAY,{
                True:self.sh.ST_ON,
                False:self.sh.ST_OFF
            }[enabled]
        )
    
    @bhs.command('get remote mode')
    def get_remote_mode(self):
        return self.sh.get_remote_control_status()
    
    @bhs.command('release control')
    def release_control(self):
        self.sh.release_control()